"""Adversarial state-flow checks independent of delegated route tests."""
from datetime import datetime
from analyzer.frontend import Frontend
from analyzer.state import ScenarioState,U
from builders import build,LIBRARY


def body_value(tmp_path,script,key='key'):
    project,db,_=build(tmp_path,LIBRARY)
    (tmp_path/'add.js').write_text(script)
    frontend=Frontend(project);site=next(iter(frontend.sites.values()));state=ScenarioState(db)
    state.now=datetime(2042,3,9)
    expression={**site['body_fields'],**site.get('conditional_fields',{})}.get(key,'')
    return frontend.evaluate(expression,state,definitions=site['definitions'])


def test_scalar_copy_and_member_read_are_snapshots(tmp_path):
    assert body_value(tmp_path,'''function add(){
      var x="early";var copy=x;x="late";
      var body={key:copy};$.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }''')=='early'
    assert body_value(tmp_path,'''function add(){
      var source={key:"early"};var copy=source.key;source.key="late";
      $.ajax({url:"/books",type:"POST",data:{key:copy}});
    }''')=='early'


def test_branch_guard_uses_value_at_branch_entry(tmp_path):
    assert body_value(tmp_path,'''function add(){
      var flag=true; var body=new Object();
      if(flag){body.key="early";}else{body.key="other";} flag=false;
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }''')=='early'


def test_object_alias_tracks_writes_and_cannot_bind_replacement(tmp_path):
    assert body_value(tmp_path,'''function add(){
      var body=new Object();body.key="old";var alias=body;body.key="changed";
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(alias)});
    }''')=='changed'
    assert body_value(tmp_path,'''function add(){
      var body={key:"old"};var alias=body;body={key:"replacement"};
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(alias)});
    }''') is U


def test_compound_assignment_does_not_turn_into_rhs(tmp_path):
    assert body_value(tmp_path,'''function add(){
      var key="prefix";key+="suffix";
      $.ajax({url:"/books",type:"POST",data:{key:key}});
    }''') is U


def test_block_scoped_binding_does_not_leak_into_outer_request(tmp_path):
    assert body_value(tmp_path,'''function add(){
      let key="outer";{let key="inner";}
      $.ajax({url:"/books",type:"POST",data:{key:key}});
    }''')=='outer'


def test_unknown_mutator_invalidates_object_values(tmp_path):
    assert body_value(tmp_path,'''function add(){
      var body={key:"before"};mutate(body);
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }''') is U


def test_self_referential_date_padding_keeps_clock_provenance(tmp_path):
    assert body_value(tmp_path,'''function add(){
      var date=new Date();var month=date.getMonth()+1;
      if(month>=1 && month<=9){month="0"+month;}
      var key=date.getFullYear()+"-"+month+"-"+date.getDate();
      $.ajax({url:"/books",type:"POST",data:{key:key}});
    }''')=='2042-03-9'


def test_conditional_expression_and_short_circuit_writes_remain_guarded(tmp_path):
    assert body_value(tmp_path,'''function add(){var key="old";
      unknown() ? (key="yes") : (key="no");
      $.ajax({url:"/books",type:"POST",data:{key:key}});
    }''') is U
    assert body_value(tmp_path,'''function add(){var key="old";
      unknown() && (key="yes");
      $.ajax({url:"/books",type:"POST",data:{key:key}});
    }''') is U


def test_synchronous_callbacks_and_local_function_writes_are_not_ignored(tmp_path):
    for call in ['[1].forEach(function(){key="changed";});',
                 '(function(){key="changed";})();',
                 'function change(){key="changed";} change();']:
        assert body_value(tmp_path,'function add(){var key="before";'+call+
          '$.ajax({url:"/books",type:"POST",data:{key:key}});}') is U


def test_deleted_literal_property_is_not_still_known_present(tmp_path):
    assert body_value(tmp_path,'''function add(){var body={key:"gone",title:"kept"};
      delete body.key;
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }''') is U


def test_mutator_inside_an_initializer_also_invalidates_argument(tmp_path):
    assert body_value(tmp_path,'''function add(){var body={key:"before"};
      var result=mutate(body);
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }''') is U


def test_short_circuit_delete_cannot_become_a_proven_omission(tmp_path):
    assert body_value(tmp_path,'''function add(){var body={key:"before"};
      unknown() && delete body.key;
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }''') is U
    assert body_value(tmp_path,'''function add(){var body={key:"before"};
      false && delete body.key;
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }''')=='before'
