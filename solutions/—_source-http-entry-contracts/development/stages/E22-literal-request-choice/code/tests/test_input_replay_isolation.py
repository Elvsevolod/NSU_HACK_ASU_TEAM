"""Replay inputs are owned by one execution, with cross-root aliases intact."""
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from analyzer.java_collections import JavaRecord,JavaMap
from builders import build


def fixture(tmp_path,body,parameters='Item item,boolean flag',mapping=''):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Item{public boolean active=false;public int count=0;public Item child;}
      class Api{'''+mapping+'Object entry('+parameters+'){'+body+'}}'})
    return p,ScenarioState(db),ids['Api.entry']


def item(**values):
    return JavaRecord('Item',{'__type__':'Item','active':False,'count':0,**values},wire_fields={'active','count','child'})


def test_alternatives_do_not_mutate_the_same_input_dto(tmp_path):
    p,state,entry=fixture(tmp_path,'if(flag){item.active=true;}return item.active;')
    initial=item();paths=run_paths(p,state,entry,{'item':initial,'flag':U},4)
    assert {x['result'] for x in paths}=={False,True}
    assert initial['active'] is False


def test_list_shape_belongs_to_one_alternative(tmp_path):
    p,state,entry=fixture(tmp_path,'if(flag){values.add("new");}return values.size();','List<String> values,boolean flag')
    values=['initial'];paths=run_paths(p,state,entry,{'values':values,'flag':U},4)
    assert {x['result'] for x in paths}=={1,2} and values==['initial']


def test_map_writes_belong_to_one_alternative(tmp_path):
    p,state,entry=fixture(tmp_path,'if(flag){values.put("new","value");}return values.size();','Map<String,String> values,boolean flag')
    values=JavaMap({'initial':'old'});paths=run_paths(p,state,entry,{'values':values,'flag':U},4)
    assert {x['result'] for x in paths}=={1,2} and values.mapping=={'initial':'old'}


def test_conservative_restart_does_not_apply_a_prebranch_write_twice(tmp_path):
    p,state,entry=fixture(tmp_path,'item.count=item.count+1;if(flag){}return item.count;')
    initial=item();paths=run_paths(p,state,entry,{'item':initial,'flag':U},limit=1)
    assert len(paths)==1 and paths[0]['result']==1 and initial['count']==0


def test_two_parameter_names_keep_their_alias_inside_one_path(tmp_path):
    p,state,entry=fixture(tmp_path,'first.active=true;return second.active;','Item first,Item second')
    initial=item();paths=run_paths(p,state,entry,{'first':initial,'second':initial},4)
    assert [x['result'] for x in paths]==[True] and initial['active'] is False


def test_input_and_state_are_copied_as_one_graph(tmp_path):
    p,state,entry=fixture(tmp_path,'item.active=true;return item.active;','Item item')
    initial=item();state.browser['form']['selected']=initial
    paths=run_paths(p,state,entry,{'item':initial},4)
    assert paths[0]['result'] is True
    assert paths[0]['state'].browser['form']['selected']['active'] is True
    assert state.browser['form']['selected'] is initial and initial['active'] is False


def test_exception_path_does_not_modify_the_next_replay(tmp_path):
    p,state,entry=fixture(tmp_path,'if(flag){item.active=true;throw new RuntimeException();}return item.active;')
    initial=item();paths=run_paths(p,state,entry,{'item':initial,'flag':U},4)
    assert {x['result'] for x in paths if x['engine'].outcome=='returned'}=={False}
    assert any(x['engine'].outcome=='uncaught application exception' for x in paths)
    assert initial['active'] is False


def test_source_request_body_remains_separate_from_browser_state(tmp_path):
    p,state,entry=fixture(tmp_path,'item.active=true;return item.active;','@RequestBody Item item','@PostMapping("/items") ')
    initial=item();state.browser['form']['selected']=initial
    paths=run_paths(p,state,entry,{'item':initial},4)
    assert paths[0]['result'] is True
    assert paths[0]['state'].browser['form']['selected']['active'] is False
    assert initial['active'] is False


def test_joint_snapshot_preserves_a_cycle_and_cross_root_alias(tmp_path):
    from analyzer.heap_join import clone_environment
    _,state,_=fixture(tmp_path,'return true;','')
    initial=item();initial['child']=initial
    state.browser['form']['selected']=initial
    (owned_state,params),_=clone_environment((state,{'item':initial,'alias':initial}))
    copied=params['item']
    assert copied is not initial and copied is params['alias'] and copied['child'] is copied
    assert owned_state.browser['form']['selected'] is copied
    copied['active']=True
    assert initial['child'] is initial and initial['active'] is False


def test_an_immutable_callback_node_is_not_deepcopied(tmp_path):
    p,state,entry=fixture(tmp_path,'return true;','Object callback')
    callback=('lambda',p.ast[entry],{},(),())
    paths=run_paths(p,state,entry,{'callback':callback},4)
    assert [x['result'] for x in paths]==[True] and callback[1] is p.ast[entry]


def test_a_direct_engine_invocation_still_models_java_reference_mutation(tmp_path):
    p,state,entry=fixture(tmp_path,'item.active=true;return item.active;','Item item')
    initial=item()
    assert Engine(p,state).run(entry,{'item':initial}) is True
    assert initial['active'] is True
