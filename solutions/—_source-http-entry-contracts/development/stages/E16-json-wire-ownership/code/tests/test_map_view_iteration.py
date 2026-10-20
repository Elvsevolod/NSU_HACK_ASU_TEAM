import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from builders import build


def project(tmp_path,body):
    return build(tmp_path,{'Api.java':'import java.util.*;class Api{Object entry(){'+body+'}}'})


def test_hashmap_first_key_is_not_taken_from_python_insertion_order(tmp_path):
    p,db,ids=project(tmp_path,'Map map=new HashMap();map.put("later",1);map.put("earlier",2);return map.keySet().iterator().next();')
    outcomes=run_paths(p,ScenarioState(db),ids['Api.entry'],{})
    assert {o['result'] for o in outcomes}=={'earlier','later'}
    assert all(o['approximate'] for o in outcomes)


def test_linked_map_preserves_mixed_key_class_insertion_order(tmp_path):
    p,db,ids=project(tmp_path,'Map map=new LinkedHashMap();map.put(1,"integer");map.put("1","text");map.put(\'x\',"character");Iterator it=map.values().iterator();return it.next()+":"+it.next()+":"+it.next();')
    engine=Engine(p,ScenarioState(db));assert engine.run(ids['Api.entry'],{})=='integer:text:character'
    assert not engine.approximate


def test_linked_map_replacement_does_not_move_an_existing_key(tmp_path):
    p,db,ids=project(tmp_path,'Map map=new LinkedHashMap();map.put("first",1);map.put("second",2);map.put("first",3);return map.keySet().iterator().next();')
    assert Engine(p,ScenarioState(db)).run(ids['Api.entry'],{})=='first'


def test_linked_map_copy_from_hashmap_does_not_invent_a_known_order(tmp_path):
    p,db,ids=project(tmp_path,'Map map=new HashMap();map.put("left",1);map.put("right",2);Map copy=new LinkedHashMap(map);return copy.keySet().iterator().next();')
    outcomes=run_paths(p,ScenarioState(db),ids['Api.entry'],{})
    assert {o['result'] for o in outcomes}=={'left','right'}
    assert all(o['approximate'] for o in outcomes)


@pytest.mark.parametrize('statements,exception',[
 ('it.remove();','IllegalStateException'),
 ('it.next();it.remove();it.remove();','IllegalStateException'),
 ('it.next();it.next();','NoSuchElementException'),
 ('map.put("new","v");it.next();','ConcurrentModificationException'),
])
def test_iterator_failure_stops_before_the_following_statement(tmp_path,statements,exception):
    p,db,ids=project(tmp_path,'Map map=new HashMap();map.put("key","value");Iterator it=map.keySet().iterator();try{'+statements+'return "wrong";}catch('+exception+' failure){return "caught";}')
    assert Engine(p,ScenarioState(db)).run(ids['Api.entry'],{})=='caught'


def test_iterator_removal_does_not_depend_on_the_removed_value_being_known(tmp_path):
    p,db,ids=project(tmp_path,'Map map=new HashMap();map.put("key",unknown());Iterator it=map.keySet().iterator();it.next();it.remove();return map.isEmpty();')
    assert Engine(p,ScenarioState(db)).run(ids['Api.entry'],{}) is True


def test_both_branch_updates_remain_visible_through_a_caller_view(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{Object entry(boolean flag){Map map=new HashMap();map.put("k","v");
      erase(map.keySet(),flag);return map.isEmpty();}void erase(Collection view,boolean flag){if(flag){view.clear();}else{view.clear();}}}'''})
    assert Engine(p,ScenarioState(db),conservative=True).run(ids['Api.entry'],{'flag':U}) is True


def test_view_keeps_backing_identity_after_agreed_branch_writes(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{Object entry(boolean flag){Map map=new HashMap();Set keys=map.keySet();
      if(flag){map.put("k","v");}else{map.put("k","v");}keys.clear();return map.isEmpty();}}'''})
    assert Engine(p,ScenarioState(db),conservative=True).run(ids['Api.entry'],{'flag':U}) is True


def test_unsupported_float_widening_keeps_a_diagnostic(tmp_path):
    p,db,ids=project(tmp_path,'Map<String,Float> map=new HashMap();map.put("key",0.1f);for(double item:map.values()){return item;}return "missing";')
    engine=Engine(p,ScenarioState(db));assert engine.run(ids['Api.entry'],{}) is U
    assert engine.approximate and any('scalar promotion' in w for w in engine.warnings)
