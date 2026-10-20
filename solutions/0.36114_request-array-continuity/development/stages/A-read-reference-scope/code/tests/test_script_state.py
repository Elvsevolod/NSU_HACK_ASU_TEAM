from analyzer.frontend import Frontend
from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.state import ScenarioState, U
from builders import build


def fixture(tmp_path, callback='cachedItems=reply;', parameters='', initializer='null'):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      @GetMapping("/catalog") Item catalog(){return null;}
      @PostMapping("/checkout") String checkout(@RequestBody Input input){return input.selectedId;}
    } class Input {String selectedId;} class Item {String id;}'''})
    (tmp_path/'page.html').write_text('<script src="ui.js"></script>')
    (tmp_path/'ui.js').write_text('var cachedItems='+initializer+''';
      function load(){$.ajax({url:"/catalog",type:"GET",success:function(reply){'''+callback+'''}});}
      function checkout('''+parameters+'''){$.ajax({url:"/checkout",type:"POST",
        data:{selectedId:cachedItems[0].id}});}''')
    frontend=Frontend(project)
    index=ContractIndex(project,frontend)
    site=next(s for s in frontend.sites.values() if ids['Api.catalog'] in s['handlers'])
    contract=next(c for c in index.contracts.values() if c['entry']==ids['Api.checkout'])
    state=ScenarioState(db)
    frontend.enter(site,state)
    grounder=ContractGrounder(project,frontend,index,None,{'facts':{}})
    return frontend,site,state,grounder,contract


def parameters(grounder,state,contract):
    return grounder._bind('Checkout item',state,contract,1)['params']


def test_observed_response_can_be_read_through_declared_script_binding(tmp_path):
    frontend,site,state,grounder,contract=fixture(tmp_path)
    frontend.apply_response(site,[{'__type__':'Item','id':'remote-one'}],state)
    assert parameters(grounder,state,contract)['selectedId']=='remote-one'
    frontend.apply_response(site,[{'__type__':'Item','id':'remote-two'}],state)
    assert parameters(grounder,state,contract)['selectedId']=='remote-two'


def test_callback_local_binding_does_not_overwrite_program_binding(tmp_path):
    frontend,site,state,grounder,contract=fixture(tmp_path,'var cachedItems=reply;',initializer='[{id:"initial"}]')
    frontend.apply_response(site,[{'__type__':'Item','id':'wrong-local'}],state)
    assert parameters(grounder,state,contract)['selectedId']=='initial'


def test_handler_parameter_does_not_borrow_the_program_value(tmp_path):
    frontend,site,state,grounder,contract=fixture(tmp_path,parameters='cachedItems')
    frontend.apply_response(site,[{'__type__':'Item','id':'wrong-global'}],state)
    assert 'selectedId' not in parameters(grounder,state,contract)


def test_unknown_guarded_global_write_does_not_keep_old_known_rows(tmp_path):
    frontend,site,state,grounder,contract=fixture(tmp_path,'if(reply.allowed){cachedItems=reply.rows;}')
    frontend.apply_response(site,{'allowed':True,'rows':[{'__type__':'Item','id':'old'}]},state)
    assert parameters(grounder,state,contract)['selectedId']=='old'
    frontend.apply_response(site,{'allowed':U,'rows':[{'__type__':'Item','id':'unproved'}]},state)
    assert 'selectedId' not in parameters(grounder,state,contract)


def test_script_bindings_are_isolated_between_scenarios(tmp_path):
    frontend,site,state,grounder,contract=fixture(tmp_path)
    fresh=ScenarioState(state.database)
    frontend.apply_response(site,[{'__type__':'Item','id':'only-left'}],state)
    assert parameters(grounder,state,contract)['selectedId']=='only-left'
    assert 'selectedId' not in parameters(grounder,fresh,contract)


def test_http_response_state_does_not_share_mutable_backend_result_objects(tmp_path):
    frontend,_,state,_,_=fixture(tmp_path)
    (tmp_path/'ui.js').write_text('''new Vue({data:{items:[]},methods:{load(){
      $.ajax({url:"/catalog",type:"GET",context:this,success:function(reply){this.items=reply;}});
    }}});''')
    fresh=Frontend(frontend.project)
    site=next(iter(fresh.sites.values()))
    fresh.enter(site,state)
    result=[{'__type__':'Item','id':'received'}]
    fresh.apply_response(site,result,state)
    result[0]['id']='server-changed'
    assert state.browser['form']['items'][0]['id']=='received'
