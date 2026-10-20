"""Order-independent writes and examples where reducing the loop is unsound."""
import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from builders import build


def project(tmp_path,body):
    return build(tmp_path,{'Api.java':'import java.util.*;class Api{Object entry(){'+body+'}}'})


@pytest.mark.parametrize('reverse',[False,True])
@pytest.mark.parametrize('source,destination,key',[('source','destination','key'),('input','output','code')])
def test_large_unordered_copy_preserves_every_mapping_without_an_order_budget(tmp_path,reverse,source,destination,key):
    indices=list(range(90))
    if reverse:indices.reverse()
    writes=''.join(source+'.put("key'+str(i)+'",'+str(i)+'L);' for i in indices)
    p,db,ids=project(tmp_path,'Map<String,Long> '+source+'=new HashMap();'+writes+
      'Map<String,Long> '+destination+'=new HashMap();for(String '+key+':'+source+'.keySet()){'+
      destination+'.put('+key+','+source+'.get('+key+'));}return '+destination+';')
    engine=Engine(p,ScenarioState(db));result=engine.run(ids['Api.entry'],{})
    assert result.mapping=={'key'+str(i):i for i in range(90)}
    assert set(result.value_types.values())=={'Long'}
    assert not engine.approximate


@pytest.mark.parametrize('key_type,key',[('Integer','1'),('Character',"'x'"),('Boolean','true')])
def test_native_boxed_keys_keep_their_classes_during_copy(tmp_path,key_type,key):
    p,db,ids=project(tmp_path,'Map<'+key_type+',String> source=new HashMap();source.put('+key+',"yes");'
      'Map destination=new HashMap();for('+key_type+' key:source.keySet()){destination.put(key,source.get(key));}return destination.get('+key+');')
    assert Engine(p,ScenarioState(db)).run(ids['Api.entry'],{})=='yes'


def test_copy_does_not_invent_linked_destination_insertion_order(tmp_path):
    p,db,ids=project(tmp_path,'Map<String,String> source=new HashMap();source.put("left","a");source.put("right","b");'
      'Map destination=new LinkedHashMap();for(String key:source.keySet()){destination.put(key,source.get(key));}return destination.keySet().iterator().next();')
    outcomes=run_paths(p,ScenarioState(db),ids['Api.entry'],{})
    assert {o['result'] for o in outcomes}=={'left','right'}
    assert all(o['approximate'] for o in outcomes)


def test_replacing_only_existing_linked_keys_preserves_their_order(tmp_path):
    p,db,ids=project(tmp_path,'Map<String,String> source=new HashMap();source.put("left","a");source.put("right","b");'
      'Map destination=new LinkedHashMap();destination.put("right","old");destination.put("left","old");'
      'for(String key:source.keySet()){destination.put(key,source.get(key));}return destination.keySet().iterator().next();')
    engine=Engine(p,ScenarioState(db));assert engine.run(ids['Api.entry'],{})=='right'
    assert not engine.approximate


def test_order_dependent_destination_reads_keep_both_possible_results(tmp_path):
    p,db,ids=project(tmp_path,'Map<String,String> source=new HashMap();source.put("left","a");source.put("right","b");'
      'Map destination=new HashMap();for(String key:source.keySet()){destination.put(key,destination.size());}return destination.get("left");')
    outcomes=run_paths(p,ScenarioState(db),ids['Api.entry'],{})
    assert {o['result'] for o in outcomes}=={0,1}
    assert all(o['approximate'] for o in outcomes)


def test_early_break_is_not_treated_as_an_entire_map_copy(tmp_path):
    p,db,ids=project(tmp_path,'Map<String,String> source=new HashMap();source.put("left","a");source.put("right","b");'
      'Map destination=new HashMap();for(String key:source.keySet()){destination.put(key,source.get(key));break;}return destination.size();')
    outcomes=run_paths(p,ScenarioState(db),ids['Api.entry'],{})
    assert {o['result'] for o in outcomes}=={1}


def test_a_colliding_constant_destination_key_keeps_both_possible_values(tmp_path):
    p,db,ids=project(tmp_path,'Map<String,String> source=new HashMap();source.put("left","a");source.put("right","b");'
      'Map destination=new HashMap();for(String key:source.keySet()){destination.put("single",source.get(key));}return destination.get("single");')
    outcomes=run_paths(p,ScenarioState(db),ids['Api.entry'],{})
    assert {o['result'] for o in outcomes}=={'a','b'}


def test_polluted_generic_keys_still_fail_before_the_loop_body(tmp_path):
    p,db,ids=project(tmp_path,'Map<String,String> source=new HashMap();Map raw=source;raw.put(1,"bad");Map destination=new HashMap();'
      'try{for(String key:source.keySet()){destination.put(key,source.get(key));}return "wrong";}catch(ClassCastException error){return destination.isEmpty();}')
    assert Engine(p,ScenarioState(db)).run(ids['Api.entry'],{}) is True


def test_an_unsupported_view_stream_remains_visible_in_diagnostics(tmp_path):
    p,db,ids=project(tmp_path,'Map<String,String> source=new HashMap();source.put("key","value");return source.values().stream();')
    engine=Engine(p,ScenarioState(db));assert engine.run(ids['Api.entry'],{}) is U
    assert engine.approximate and engine.operation_issues[('unsupported_map_view_operation','stream')]
