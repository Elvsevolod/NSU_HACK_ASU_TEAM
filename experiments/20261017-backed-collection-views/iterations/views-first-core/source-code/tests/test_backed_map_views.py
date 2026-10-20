"""JDK view contracts, independent of any application domain."""
import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def run(tmp_path,body):
    project,db,ids=build(tmp_path,{'Api.java':'import java.util.*;class Api{Object entry(){'+body+'}}'})
    engine=Engine(project,ScenarioState(db));return engine.run(ids['Api.entry'],{}),engine


@pytest.mark.parametrize('view',['keySet','values','entrySet'])
def test_view_size_tracks_later_map_updates(tmp_path,view):
    result,_=run(tmp_path,'Map map=new HashMap();Collection view=map.'+view+'();map.put("key","value");return view.size();')
    assert result==1


@pytest.mark.parametrize('view',['keySet','values','entrySet'])
def test_clear_through_view_clears_the_backing_map(tmp_path,view):
    result,_=run(tmp_path,'Map map=new HashMap();map.put("key","value");map.'+view+'().clear();return map.isEmpty();')
    assert result is True


def test_key_removal_through_view_preserves_other_mappings(tmp_path):
    result,_=run(tmp_path,'Map map=new HashMap();map.put("left","a");map.put("right","b");Set keys=map.keySet();keys.remove("left");if(map.get("left")!=null){return "not-removed";}return map.get("right");')
    assert result=='b'


@pytest.mark.parametrize('view',['keySet','values','entrySet'])
def test_view_add_fails_without_modifying_the_map(tmp_path,view):
    result,_=run(tmp_path,'Map map=new HashMap();try{map.'+view+'().add("bad");return "wrong";}catch(UnsupportedOperationException failure){return map.isEmpty();}')
    assert result is True


def test_entry_obtained_from_view_updates_the_backing_mapping(tmp_path):
    result,_=run(tmp_path,'Map map=new HashMap();map.put("key","old");Map.Entry entry=(Map.Entry)map.entrySet().iterator().next();entry.setValue("new");return map.get("key");')
    assert result=='new'


def test_iterator_remove_is_reflected_in_an_existing_view(tmp_path):
    result,_=run(tmp_path,'Map map=new HashMap();map.put("key","value");Set keys=map.keySet();Iterator iterator=keys.iterator();iterator.next();iterator.remove();return keys.isEmpty();')
    assert result is True


def test_iterating_one_entry_preserves_key_and_value(tmp_path):
    result,_=run(tmp_path,'Map<String,String> map=new HashMap();map.put("key","value");for(Map.Entry<String,String> entry:map.entrySet()){return entry.getKey()+entry.getValue();}return "missing";')
    assert result=='keyvalue'


def test_values_contains_does_not_confuse_character_and_string(tmp_path):
    result,_=run(tmp_path,'Map map=new HashMap();map.put("key",\'x\');return map.values().contains("x");')
    assert result is False


def test_values_contains_does_not_confuse_integer_and_long(tmp_path):
    result,_=run(tmp_path,'Map map=new HashMap();map.put("key",1L);return map.values().contains(1);')
    assert result is False


def test_existing_map_equality_does_not_confuse_character_and_string_values(tmp_path):
    result,_=run(tmp_path,'Map left=new HashMap();Map right=new HashMap();left.put("key",\'x\');right.put("key","x");return left.equals(right);')
    assert result is False


def test_unknown_branch_join_preserves_a_known_map_alias(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{Object entry(boolean flag){
      Map map=new HashMap();Map alias=map;if(flag){map.put("key","same");}else{map.put("key","same");}
      alias.put("later","visible");return map.get("later");}}'''})
    engine=Engine(project,ScenarioState(db),conservative=True);assert engine.run(ids['Api.entry'],{'flag':U})=='visible'
