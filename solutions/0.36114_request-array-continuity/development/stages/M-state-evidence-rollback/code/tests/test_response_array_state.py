import pytest
from analyzer.frontend import Frontend
from analyzer.state import ScenarioState,U
from builders import build


def fixture(tmp_path,body,context='',setup='var vm=this;'):
    project,db,_=build(tmp_path,{'Api.java':'class Api {@GetMapping("/invoices") String list(){return "ok";}}'})
    (tmp_path/'page.html').write_text('<script src="ui.js"></script>')
    (tmp_path/'ui.js').write_text('''new Vue({data:{items:[],shown:[]},methods:{load(){'''+setup+'''
      $.ajax({url:"/invoices",type:"GET",'''+context+'''success:function(payload){'''+body+'''}});
    }}});''')
    frontend=Frontend(project);site=next(iter(frontend.sites.values()));state=ScenarioState(db)
    frontend.enter(site,state)
    return frontend,site,state


def test_source_array_copy_preserves_every_row_and_type_across_concat(tmp_path):
    frontend,site,state=fixture(tmp_path,'''console.log(payload);vm.items=[];var count=payload.data.length;
      for(var index=0;index<count;index++){vm.items[index]=payload.data[index];}
      vm.shown=vm.shown.concat(vm.items);''')
    rows=[{'__type__':'Invoice','id':str(i)} for i in range(65)]
    frontend.apply_response(site,{'data':rows},state)
    assert state.browser['form']['shown']==rows
    rows[0]['id']='changed'
    assert state.browser['form']['shown'][0]['id']=='0'


def test_unsupported_transform_does_not_turn_a_response_into_a_known_empty_list(tmp_path):
    frontend,site,state=fixture(tmp_path,'''vm.items=[];for(var i=0;i<payload.data.length;i++){
      vm.items[i]=payload.data[i].amount;}vm.shown=vm.items;''')
    frontend.apply_response(site,{'data':[{'amount':7}]},state)
    assert state.browser['form']['items'] is U and state.browser['form']['shown'] is U
    assert any('Unsupported browser response loop' in warning for warning in frontend.unsupported)


@pytest.mark.parametrize('context,expected',[('',[]),('context:this,',[{'id':'one'}])])
def test_jquery_callback_this_is_settings_unless_context_is_supplied(tmp_path,context,expected):
    frontend,site,state=fixture(tmp_path,'''this.items=[];for(var i=0;i<payload.data.length;i++){
      this.items[i]=payload.data[i];}this.shown=this.items;''',context)
    frontend.apply_response(site,{'data':[{'id':'one'}]},state)
    assert state.browser['form']['shown']==expected


def test_unknown_local_array_mutation_and_nested_callbacks_cannot_confirm_values(tmp_path):
    frontend,site,state=fixture(tmp_path,'''var local=[];for(var i=0;i<payload.data.length;i++){local[i]=payload.data[i];}
      vm.items=local;setTimeout(function(){vm.shown=[1];},1);''')
    frontend.apply_response(site,{'data':[{'id':'one'}]},state)
    assert state.browser['form']['items'] is U and state.browser['form']['shown'] is U


def test_response_local_scalar_snapshot_does_not_use_a_later_assignment(tmp_path):
    frontend,site,state=fixture(tmp_path,'''var value=payload.id;vm.chosen=value;value="later";''')
    frontend.apply_response(site,{'id':'before'},state)
    assert state.browser['form']['chosen']=='before'
