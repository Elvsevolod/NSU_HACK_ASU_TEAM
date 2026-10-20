import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


@pytest.mark.parametrize('key',['box.getValue()','box.value'])
def test_class_type_parameter_named_string_is_not_the_jdk_string_class(tmp_path,key):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Box<String>{String value;String getValue(){return value;}}
      class Api{Object entry(){Box box=new Box();box.value='x';Map map=new HashMap();map.put('''+key+''',"found");return map.get("x");}}'''})
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Api.entry'],{}) is U
    assert engine.operation_issues[('unsupported_map_key','put')]


@pytest.mark.parametrize('type_name,value,lookup,method_name',[('String',"'x'",'"x"','identity'),('Integer','1L','1','identity'),('Integer','1','1L','parseLong')])
def test_method_type_parameter_does_not_supply_a_fabricated_native_boxed_class(tmp_path,type_name,value,lookup,method_name):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{<'''+type_name+'''>'''+type_name+''' '''+method_name+'''('''+type_name+''' value){return value;}
      Object entry(){Map map=new HashMap();map.put('''+method_name+'''('''+value+'''),"found");return map.get('''+lookup+''');}}'''})
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Api.entry'],{}) is U
    assert engine.operation_issues[('unsupported_map_key','put')]


def test_type_parameter_in_a_generic_return_does_not_leak_into_stream_contract(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import java.util.stream.Collectors;
      class Api{<String>List<String> values(String value){return Arrays.asList(value);}
      Object entry(){Map map=new HashMap();values('x').stream().map(key->{map.put(key,"found");return key;})
      .collect(Collectors.toList());return map.get("x");}}'''})
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Api.entry'],{}) is U
    assert engine.operation_issues[('unsupported_map_key','put')]


def test_fully_qualified_jdk_type_is_preserved_inside_a_generic_class(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Box<String>{java.lang.String value="x";
      java.lang.String getValue(){return value;}}
      class Api{Object entry(){Box box=new Box();Map map=new HashMap();map.put(box.getValue(),"found");return map.get("x");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='found'


def test_unresolved_generic_boolean_unboxing_is_never_silently_confirmed(tmp_path):
    from analyzer.paths import run_paths
    project,db,ids=build(tmp_path,{'Api.java':'''class Api{String entry(){return check(null);}
      <Boolean extends java.lang.Boolean>String check(Boolean input){if(input){return after();}return "done";}
      String after(){return "wrong";}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert outcomes and all(o['approximate'] for o in outcomes)
    assert all(any('null scalar conversion' in warning for warning in o['engine'].warnings) for o in outcomes)
