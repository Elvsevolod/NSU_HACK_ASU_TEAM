import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def test_foreach_variable_keeps_declared_string_type_when_used_as_a_map_key(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api {
      Object entry(){Map map=new HashMap();for(String key:Arrays.asList("known")){map.put(key,"found");}
      return map.get("known");}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})=='found'
    assert not engine.warnings


def test_foreach_receiver_type_keeps_the_source_getter_return_type(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Item {
      String key="known";String getKey(){return key;}}
      class Api {Object entry(){Map map=new HashMap();for(Item row:Arrays.asList(new Item())){
      map.put(row.getKey(),"found");}return map.get("known");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='found'


@pytest.mark.parametrize('action',['break;','continue;','if(true){break;}','try{throw new IllegalStateException();}catch(IllegalStateException failure){break;}'])
def test_foreach_scope_restores_a_shadowed_field_value_and_type(tmp_path,action):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api {String key="outer";
      Object inspect(){Map map=new HashMap();for(int key:Arrays.asList(1)){'''+action+'''}
      map.put(key,"found");return map.get("outer");}}class Start{Object entry(){return new Api().inspect();}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Start.entry'],{})=='found'


def test_object_foreach_element_stays_unknown_if_its_boxed_class_is_unproven(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api {
      Object entry(List input){Map map=new HashMap();for(Object key:input){map.put(key,"found");}
      return map.get(1L);}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{'input':[1]}) is U
    assert engine.operation_issues[('unsupported_map_key','put')]


def test_explicit_lambda_parameter_type_survives_callback_execution(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import java.util.stream.Collectors;
      class Api {Object entry(){Map map=new HashMap();Arrays.asList("known").stream()
      .map((String key)->{map.put(key,"found");return key;}).collect(Collectors.toList());
      return map.get("known");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='found'
