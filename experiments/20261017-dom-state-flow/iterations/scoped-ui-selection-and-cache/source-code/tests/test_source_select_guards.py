from analyzer.frontend import Frontend
from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.state import ScenarioState
from builders import build


def selector_fixture(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      @PostMapping("/records/first") String first(@RequestBody Input input){return input.caption;}
      @PostMapping("/records/second") String second(@RequestBody Input input){return input.caption;}
    } class Input {String caption;}'''})
    (tmp_path/'page.html').write_text('''<select v-model="mode">
      <option v-for="choice in choices" v-bind:value="choice.code">{{choice.label}}</option>
      </select><script src="ui.js"></script>''')
    (tmp_path/'ui.js').write_text('''new Vue({data:{mode:1,choices:[{code:1,label:"Blue"},{code:2,label:"Red"}]},
      methods:{read(){
        if(this.mode==1){$.ajax({url:"/records/first",type:"POST",data:{caption:"A"}});}
        if(this.mode==2){$.ajax({url:"/records/second",type:"POST",data:{caption:"B"}});}
      }}});''')
    frontend=Frontend(project)
    index=ContractIndex(project,frontend)
    grounder=ContractGrounder(project,frontend,index,None,{'facts':{}})
    return frontend,grounder,ScenarioState(db),ids


def test_handler_guard_can_ground_a_source_declared_select_option(tmp_path):
    frontend,grounder,state,ids=selector_fixture(tmp_path)
    proposals,_=grounder.step('Read the second record',state)
    assert proposals and proposals[0]['entry']==ids['Api.second']
    assert proposals[0]['state'].browser['form']['mode']==2
    assert any('source selector' in issue for issue in proposals[0]['unresolved'])
    assert state.browser['form']=={}


def test_explicit_different_label_cannot_be_overridden_to_force_a_handler(tmp_path):
    _,grounder,state,ids=selector_fixture(tmp_path)
    proposals,detail=grounder.step('Read the second record with Blue',state)
    assert proposals and proposals[0]['entry']==ids['Api.first']
    assert proposals[0]['state'].browser['form']['mode']==1
    assert any('Source selector conflict' in issue for issue in proposals[0]['unresolved'])


def test_known_false_request_guard_cannot_switch_to_an_unrelated_handler(tmp_path):
    _,grounder,state,ids=selector_fixture(tmp_path)
    path=tmp_path/'ui.js'
    path.write_text(path.read_text().replace('if(this.mode==2)','if("Xy".indexOf("X"))'))
    frontend=Frontend(grounder.project)
    index=ContractIndex(grounder.project,frontend)
    fresh=ContractGrounder(grounder.project,frontend,index,None,{'facts':{}})
    proposals,detail=fresh.step('Read the second record',state)
    assert proposals==[]
    assert any('guard' in issue.lower() for issue in detail['unresolved'])


def test_negated_label_does_not_select_the_negated_option(tmp_path):
    _,grounder,state,ids=selector_fixture(tmp_path)
    proposals,_=grounder.step('Read the second record with Red, not Blue',state)
    assert proposals and proposals[0]['entry']==ids['Api.second']
    assert proposals[0]['state'].browser['form']['mode']==2
