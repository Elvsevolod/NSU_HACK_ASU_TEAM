from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.frontend import Frontend
from analyzer.state import ScenarioState
from builders import build


def test_html_click_row_fields_bind_request_parameters_by_source_position(tmp_path):
    project, db, ids=build(tmp_path,{'Api.java':'''class Api {
      @PostMapping("/invoices/{key}") String amend(@PathVariable String key,@RequestBody Edit input){return key;}
    } class Edit {String created;String destination;} class Invoice {@Id String id;String createdAt;String address;}'''})
    (tmp_path/'page.html').write_text('''<html><body><table>
      <tr v-for="(record,index) in invoices"><td><button @click="amend(record.id,record.createdAt,record.address)">Amend</button></td></tr>
      </table><script src="ui.js"></script></body></html>''')
    (tmp_path/'ui.js').write_text('''var vm=new Vue({data:{invoices:[]},methods:{
      amend(invoiceKey,when,place){$.ajax({url:"/invoices/"+invoiceKey,type:"POST",data:{created:when,destination:place}});}
    }});''')
    frontend=Frontend(project)
    site=next(iter(frontend.sites.values()))
    assert site['row_bindings'][0]['parameters']==['invoiceKey','when','place']
    first={'__type__':'Invoice','id':'first','createdAt':'2024-01-01','address':'North'}
    second={'__type__':'Invoice','id':'second','createdAt':'2024-02-02','address':'South'}
    state=ScenarioState(db)
    frontend.enter(site,state)
    state.browser['form']['invoices']=[first,second]
    state.history=[{'result':[first,second]}]
    grounder=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}})
    choices,_=grounder.step('Amend the second invoice',state)
    assert choices[0]['params']=={'key':'second','created':'2024-02-02','destination':'South'}
    assert 'row=' in choices[0]['bindings']['created']['reference']
    ambiguous,_=grounder.step('Amend invoice',state)
    assert 'created' not in ambiguous[0]['params']
    assert 'destination' not in ambiguous[0]['params']


def test_row_handler_name_cannot_cross_vue_components(tmp_path):
    project,db,_=build(tmp_path,{'Api.java':'''class Api {
      @GetMapping("/items/{key}") String show(@PathVariable String key){return key;}
    } class Item {@Id String key;}'''})
    (tmp_path/'page.html').write_text('''<div v-for="row in items"><button @click="show(row.key)">Show</button></div><script src="ui.js"></script>''')
    (tmp_path/'ui.js').write_text('''new Vue({methods:{show(key){$.ajax({url:"/items/"+key,type:"GET"});}}});
      new Vue({methods:{show(key){}}});''')
    frontend=Frontend(project)
    assert all(not site['row_bindings'] for site in frontend.sites.values())
    assert any('ambiguous Vue' in warning for warning in frontend.warnings)


def test_row_index_nested_member_and_whole_object_share_one_selected_row(tmp_path):
    project,db,_=build(tmp_path,{'Api.java':'''class Api {
      @PostMapping("/invoices") String amend(@RequestBody Edit input){return input.client;}
    } class Edit {int position;String client;String label;}
    class Invoice {@Id String id;String label;}'''})
    (tmp_path/'page.html').write_text('''<div v-for="(record,index) in invoices">
      <button @click="amend(index,record.client.id,record)">Amend</button></div><script src="ui.js"></script>''')
    (tmp_path/'ui.js').write_text('''new Vue({data:{invoices:[]},methods:{
      amend(slot,person,whole){$.ajax({url:"/invoices",type:"POST",data:{position:slot,client:person,label:whole.label}});}
    }});''')
    frontend=Frontend(project);site=next(iter(frontend.sites.values()));state=ScenarioState(db)
    frontend.enter(site,state)
    rows=[{'__type__':'Invoice','id':'one','client':{'id':'c1'},'label':'North'},
          {'__type__':'Invoice','id':'two','client':{'id':'c2'},'label':'South'}]
    state.browser['form']['invoices']=rows;state.history=[{'result':rows}]
    grounder=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}})
    proposal=grounder.step('Amend the second invoice',state)[0][0]
    assert proposal['params']=={'position':1,'client':'c2','label':'South'}
