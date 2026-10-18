from analyzer.engine import Engine,merge
from analyzer.java_collections import JavaMap,JavaObject
from analyzer.models import library
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from builders import build


def test_join_does_not_turn_a_maybe_present_key_into_a_present_key():
    joined=merge(JavaMap({'optional':'yes'}),JavaMap())
    assert isinstance(joined,JavaMap)
    assert library('containsKey',joined,['optional'],'map',U)==(True,U)


def test_join_retains_map_operations_for_definitely_present_keys():
    joined=merge(JavaMap({'mode':'left','shared':'known'}),JavaMap({'mode':'right','shared':'known'}))
    assert isinstance(joined,JavaMap)
    assert library('get',joined,['shared'],'map',U)==(True,'known')
    assert library('get',joined,['mode'],'map',U)==(True,U)
    assert library('containsKey',joined,['mode'],'map',U)==(True,True)


def test_join_does_not_choose_one_concrete_class_from_equal_business_fields():
    left=JavaObject('Left',{'__type__':'business'})
    right=JavaObject('Right',{'__type__':'business'})
    assert merge(left,right) is U
    assert merge(left,left) is left
    assert merge([left],[right]) is U


def test_cyclic_containers_widen_without_recursive_comparison():
    left=JavaMap();left.mapping['self']=left
    right=JavaMap();right.mapping['self']=right
    assert merge(left,right).mapping['self'] is U
    left=[];left.append(left)
    right=[];right.append(right)
    assert merge(left,right) is U


def test_map_size_and_emptiness_follow_mappings_not_the_internal_wrapper():
    value=JavaMap()
    assert library('size',value,[],'map',U)==(True,0)
    assert library('isEmpty',value,[],'map',U)==(True,True)
    library('put',value,['present',None],'map',U)
    assert library('size',value,[],'map',U)==(True,1)
    assert library('isEmpty',value,[],'map',U)==(True,False)


def test_unsupported_map_view_does_not_create_a_confirmed_iteration_order(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {String entry(){Map map=new HashMap();map.put("second","b");map.put("first","a");
        Object key=map.keySet().iterator().next();
        if("first".equals(key)){return first();}return other();}
        String first(){return "first";}String other(){return "other";}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert {outcome['result'] for outcome in outcomes}=={'first','other'}
    assert all(any('Map' in warning for warning in outcome['engine'].warnings) for outcome in outcomes)


def test_unmodeled_map_mutator_does_not_leave_stale_mappings(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {String entry(){Map map=new HashMap();map.put("mode","before");
        map.replaceAll((key,value)->"after");return (String)map.get("mode");}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{}) is U
    assert any('Map' in warning for warning in engine.warnings)


def test_unknown_uri_variable_map_does_not_crash_or_bind_an_internal_marker(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;class Api {
      @GetMapping("/items/{key}") String read(@PathVariable String key){return key;}}
      class Caller {RestTemplate rest;String entry(Map vars){
        return rest.getForObject("http://service/items/{key}",String.class,vars);}}'''})
    engine=Engine(project,ScenarioState(db),conservative=True)
    assert engine.run(ids['Caller.entry'],{'vars':JavaMap(U)}) is U
    assert engine.warnings


def test_a_business_field_cannot_forge_uri_template_variables(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;class Api {
      @GetMapping("/items/{key}") String read(@PathVariable String key){return key;}}
      class Caller {RestTemplate rest;String entry(Object vars){
        return rest.getForObject("http://service/items/{key}",String.class,vars);}}'''})
    engine=Engine(project,ScenarioState(db),conservative=True)
    assert engine.run(ids['Caller.entry'],{'vars':{'__map__':{'key':'forged'}}}) is U
    assert engine.warnings
