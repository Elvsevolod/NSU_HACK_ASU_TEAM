from copy import deepcopy
import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from analyzer.java_collections import JsonObject
from analyzer.models import library
from builders import build


def project(tmp_path,body):
    return build(tmp_path,{'Api.java':'import java.util.*;class Api{Object entry(){'+body+'}}'})


def test_linked_values_removal_removes_the_first_duplicate_mapping(tmp_path):
    p,db,ids=project(tmp_path,'Map map=new LinkedHashMap();map.put("left","same");map.put("right","same");'
      'map.values().remove("same");return map.containsKey("left")==false && map.containsKey("right");')
    assert Engine(p,ScenarioState(db)).run(ids['Api.entry'],{}) is True


def test_hashmap_duplicate_removal_keeps_each_legal_remaining_mapping(tmp_path):
    p,db,ids=project(tmp_path,'Map map=new HashMap();map.put("left","same");map.put("right","same");'
      'map.values().remove("same");return map.containsKey("left");')
    outcomes=run_paths(p,ScenarioState(db),ids['Api.entry'],{})
    assert {o['result'] for o in outcomes}=={True,False}
    assert all(o['approximate'] for o in outcomes)


def test_existing_values_view_reads_a_replacement_value(tmp_path):
    p,db,ids=project(tmp_path,'Map map=new HashMap();map.put("key","old");Collection view=map.values();'
      'map.put("key","new");return view.contains("new") && !view.contains("old");')
    assert Engine(p,ScenarioState(db)).run(ids['Api.entry'],{}) is True


def test_view_clear_recovers_known_contents_after_an_unsupported_map_mutator(tmp_path):
    p,db,ids=project(tmp_path,'Map map=new HashMap();Set view=map.keySet();map.compute("key",(k,v)->"unknown");'
      'view.clear();return map.isEmpty();')
    engine=Engine(p,ScenarioState(db));assert engine.run(ids['Api.entry'],{}) is True
    assert engine.approximate and engine.operation_issues[('unsupported_map_mutation','compute')]


def test_user_json_properties_cannot_forge_a_native_map_view():
    fake=JsonObject({'__map_view__':'keys','backing':{'__map__':{'private':'value'}}})
    before=deepcopy(fake)
    assert library('clear',fake,[],'input',U)==(False,U)
    assert fake==before


def test_map_view_deepcopy_retains_only_its_copied_backing(tmp_path):
    p,db,ids=project(tmp_path,'Map map=new HashMap();map.put("key","value");return map.values();')
    original=Engine(p,ScenarioState(db)).run(ids['Api.entry'],{})
    copy=deepcopy(original)
    library('clear',copy,[],'copy',U)
    assert library('size',original,[],'original',U)==(True,1)
    assert library('size',copy,[],'copy',U)==(True,0)


@pytest.mark.parametrize('read',[
    'map.values().iterator().next()',
    'entry.getValue()',
])
def test_widened_direct_generic_reads_preserve_the_actual_character_class(tmp_path,read):
    p,db,ids=project(tmp_path,'Map<String,String> map=new HashMap();Map raw=map;raw.put("key",\'x\');'
      'Map.Entry<String,String> entry=map.entrySet().iterator().next();return '+read+';')
    engine=Engine(p,ScenarioState(db));assert engine.run(ids['Api.entry'],{})=='x'
    assert not engine.approximate and engine.last_invoke_kind=='Character'


@pytest.mark.parametrize('read',['map.values().iterator().next()','entry.getValue()'])
def test_a_narrow_consumer_rejects_a_polluted_direct_generic_read(tmp_path,read):
    p,db,ids=project(tmp_path,'Map<String,String> map=new HashMap();Map raw=map;raw.put("key",\'x\');'
      'Map.Entry<String,String> entry=map.entrySet().iterator().next();String value='+read+';return value;')
    engine=Engine(p,ScenarioState(db));assert engine.run(ids['Api.entry'],{}) is U
    assert engine.outcome=='uncaught application exception' and not engine.approximate
    assert any('ClassCastException' in w for w in engine.warnings)
