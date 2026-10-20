from datetime import datetime
from tree_sitter import Parser, Language
import tree_sitter_javascript
from analyzer.form_flow import vue_form_flows
from analyzer.frontend import Frontend
from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.state import ScenarioState, U
from analyzer.jsflow import definitions_before
from analyzer.project import text, walk
from builders import build


PARSER=Parser(Language(tree_sitter_javascript.language()))

def flow(source):
    return vue_form_flows(PARSER.parse(source.encode()).root_node)[0]


def test_source_projection_uses_parameter_position_and_prior_assignment():
    out=flow('''new Vue({methods:{choose(arbitrary,display){
      this.selectedId=arbitrary;this.caption=display;this.copy=this.caption;
    }}});''')
    selector=out['projectors'][0]
    assert selector['parameters']==['arbitrary','display']
    assert selector['fields']['selectedId']=='arbitrary'
    assert selector['fields']['caption']=='display'
    assert selector['fields']['copy']=='(display)'


def test_comments_between_component_methods_do_not_disable_source_equations():
    out=flow('''new Vue({methods:{
      // Pick the item shown in the table.
      choose(key){this.selectedId=key;this.day=this.clock();},
      /* Read the supplied clock, without changing the component. */
      clock(){var now=new Date();return now.getFullYear();}
    }});''')
    assert any(selector['handler']=='choose' for selector in out['projectors'])
    assert 'clock' in out['helpers']


def test_source_pure_clock_helper_is_distinct_from_a_mutating_helper():
    out=flow('''new Vue({methods:{choose(key){this.today=this.clock();this.selectedId=key;},
      clock(){var now=new Date();var day=now.getDate();if(day<10){day="0"+day;}return day;}
    }});''')
    assert out['projectors'][0]['handler']=='choose'
    assert 'clock' in out['helpers']
    bad=flow('''new Vue({methods:{choose(key){this.selectedId=key;this.clock();},
      clock(){this.selectedId="other";return 5;}}});''')
    assert not any(p['handler']=='choose' for p in bad['projectors'])


def test_opaque_or_async_calls_and_component_watchers_cannot_prove_final_form_values():
    for body in ('this.selectedId=key;unknown();','this.selectedId=key;setTimeout(()=>{this.selectedId="other";},1);',
                 'this.selectedId=key;this[dynamic]=0;', 'this.selectedId=key;key.id="changed";',
                 'this.selectedId=key;return;this.selectedId="other";'):
        out=flow('new Vue({methods:{choose(key){'+body+'}}});')
        assert not out['projectors']
    assert not flow('new Vue({watch:{selectedId(){this.value=1;}},methods:{choose(key){this.selectedId=key;}}});')['projectors']
    assert not flow('new Vue({methods:{choose:(key)=>{this.selectedId=key;}}});')['projectors']


def test_form_snapshot_is_not_the_last_mutated_value():
    root=PARSER.parse(b'function choose(key){this.id=key;this.saved=this.id;this.id="later";}').root_node
    fn=root.named_children[0];body=fn.child_by_field_name('body')
    defs,_=definitions_before(fn,body.children[-1])
    assert defs['this.saved']=='(key)' and defs['this.id']=='"later"'


def test_replaced_helper_and_aliased_component_do_not_lose_owner_information():
    out=flow('''new Vue({methods:{choose(key){var component=this;component.selectedId=key;}}});''')
    assert out['projectors'][0]['fields']=={'selectedId':'key'}
    out=flow('''new Vue({methods:{choose(key){this.clock();this.selectedId=key;},
      clock(){return 1;},replace(fn){this.clock=fn;}}});''')
    assert not any(p['handler']=='choose' for p in out['projectors'])


def form_fixture(tmp_path, extra_methods=''):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      @PutMapping("/invoices") String amend(@RequestBody Edit input){return input.invoiceId;}
    } class Edit {String invoiceId;String destination;String name;String date;}
    class Invoice {@Id String id;String address;String clientName;String label;}
    '''})
    (tmp_path/'page.html').write_text('''<table><tr v-for="(row,position) in invoices"><td>
      <button @click="choose(row.id,row.address,row.clientName)">Choose</button></td></tr></table>
      <input v-model="caption"><script src="ui.js"></script>''')
    (tmp_path/'ui.js').write_text('''new Vue({data:{invoices:[],chosenId:'',place:'',caption:'',day:''},methods:{
      choose(arbitrary,label,person){this.chosenId=arbitrary;this.place=label;this.caption=person;this.day=this.clock();},
      clock(){var now=new Date();var d=now.getDate();if(d<10){d="0"+d;}return now.getFullYear()+"-01-"+d;},
      amend(){var vm=this;$.ajax({url:"/invoices",type:"PUT",data:{invoiceId:vm.chosenId,destination:vm.place,name:vm.caption,date:vm.day}});}
      '''+extra_methods+'}});')
    frontend=Frontend(project);site=next(iter(frontend.sites.values()))
    state=ScenarioState(db);state.now=datetime(2024,1,9)
    frontend.enter(site,state)
    rows=[{'__type__':'Invoice','id':'one','address':'North','clientName':'Ada'},
          {'__type__':'Invoice','id':'two','address':'South','clientName':'Bea'}]
    state.browser['form']['invoices']=rows
    state.history=[{'result':rows}]
    grounder=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}})
    return grounder,site,state


def test_source_equations_transfer_a_selected_row_across_handlers(tmp_path):
    grounder,site,state=form_fixture(tmp_path)
    proposal=grounder.step('Amend the second invoice',state)[0][0]
    assert proposal['params']=={'invoiceId':'two','destination':'South','name':'Bea','date':'2024-01-09'}
    assert proposal['bindings']['destination']['source']=='ui_projection'
    assert 'page.html:' in proposal['bindings']['destination']['reference']
    assert any('event execution is unobserved' in issue for issue in proposal['unresolved'])
    assert state.browser['form']['place']==''


def test_new_edit_cannot_reuse_an_old_prefill_without_a_new_value(tmp_path):
    grounder,site,state=form_fixture(tmp_path)
    proposal=grounder.step("Change the second invoice's name",state)[0][0]
    assert 'name' not in proposal['params']
    assert proposal['params']['destination']=='South'
    assert 'Unknown input: name' in proposal['unresolved']
    assert proposal['state'].browser['form']['caption'] is U


def test_ambiguous_writers_and_unobserved_collections_prevent_projection(tmp_path):
    grounder,site,state=form_fixture(tmp_path,',replace(){this.place="different";}')
    proposal=grounder.step('Amend the second invoice',state)[0][0]
    assert proposal['params']['destination']==''
    assert 'destination' not in grounder.frontend.projected_form_values(site,site['handlers'][0],'Amend second invoice',state)
    state.browser['form']['invoices']=[]
    assert not grounder.frontend.projected_form_values(site,site['handlers'][0],'Amend second invoice',state)


def test_alias_writers_spread_and_local_shadowing_are_not_ignored(tmp_path):
    grounder,site,state=form_fixture(tmp_path,',replace(){var vm=this;vm.place="different";}')
    assert 'place' not in grounder.frontend.projected_form_values(site,site['handlers'][0],'Amend second invoice',state)
    out=flow('new Vue({methods:{choose(key){this.clock();this.id=key;},clock(){return 1;},replace(fn){var vm=this;vm.clock=fn;}}});')
    assert not any(p['handler']=='choose' for p in out['projectors'])
    assert not flow('new Vue({methods:{...shared,choose(key){this.id=key;}}});')['projectors']
    assert not flow('new Vue({methods:{choose(key){var vm=this;var vm=other;vm.id=key;}}});')['projectors']


def test_amend_name_requires_a_new_value_too(tmp_path):
    grounder,_,state=form_fixture(tmp_path)
    proposal=grounder.step("Amend the second invoice's name",state)[0][0]
    assert 'name' not in proposal['params']


def test_preparation_reads_the_state_before_user_input_updates(tmp_path):
    grounder,site,state=form_fixture(tmp_path)
    source=grounder.project.root/site['file']
    source.write_text(source.read_text().replace('this.place=label;this.caption=person;','this.caption=this.place;this.place=label;'))
    frontend=Frontend(grounder.project)
    grounder=ContractGrounder(grounder.project,frontend,ContractIndex(grounder.project,frontend),None,{'facts':{}})
    state.browser['form']['place']='Before'
    proposal=grounder.step('Amend the second invoice with destination="After"',state)[0][0]
    assert proposal['params']['destination']=='After'
    assert proposal['params']['name']=='Before'


def test_async_and_accessor_helpers_are_not_plain_scalar_functions():
    for helper in ('async clock(){return 5;}','get clock(){return 5;}','*clock(){return 5;}'):
        out=flow('new Vue({methods:{choose(key){this.day=this.clock();this.id=key;},'+helper+'}});')
        assert 'clock' not in out['helpers']
        assert not any(p['handler']=='choose' for p in out['projectors'])


def test_structured_values_do_not_become_python_repr_in_browser_strings(tmp_path):
    grounder,_,state=form_fixture(tmp_path)
    state.browser['form']['kind']={'__type__':'Category','name':'Express'}
    assert grounder.frontend.evaluate('this.kind+"12"',state) is U
    assert grounder.frontend.evaluate('this.kind.__type__',state) is U
    assert grounder.frontend.evaluate('false+"12"',state)=='false12'
