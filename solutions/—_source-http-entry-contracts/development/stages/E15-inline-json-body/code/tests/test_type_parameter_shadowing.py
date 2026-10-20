import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from analyzer.project import walk,text
from builders import build


@pytest.mark.parametrize('key',['box.getValue()','box.value'])
def test_class_type_parameter_named_string_is_not_the_jdk_string_class(tmp_path,key):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Box<String>{String value;String getValue(){return value;}}
      class Api{Object entry(){Box box=new Box();box.value='x';Map map=new HashMap();map.put('''+key+''',"found");return map.get("x");}}'''})
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Api.entry'],{}) is None
    assert not engine.operation_issues[('unsupported_map_key','put')] and not engine.approximate
    engine.method=ids['Api.entry'];engine.variable_types={'box':'Box'}
    # The raw member still erases to Object. Its observed field assignment
    # supplies Character, so it cannot match a String key with the same text.
    assert project.methods[ids['Box.getValue']]['return_raw']=='String'
    expression=next(node for node in walk(project.ast[engine.method]) if text(node)==key and node.type in ('field_access','method_invocation'))
    assert engine.source_type(expression)=='java.lang.Object'


@pytest.mark.parametrize('type_name,value,lookup,method_name,key_kind',[('String',"'x'",'"x"','identity','Character'),('Integer','1L','1','identity','Long'),('Integer','1','1L','parseLong','Integer')])
def test_method_type_parameter_does_not_supply_a_fabricated_native_boxed_class(tmp_path,type_name,value,lookup,method_name,key_kind):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{<'''+type_name+'''>'''+type_name+''' '''+method_name+'''('''+type_name+''' value){return value;}
      Object entry(){Map map=new HashMap();map.put('''+method_name+'''('''+value+'''),"found");return map.get('''+lookup+''');}}'''})
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Api.entry'],{}) is None
    assert not engine.operation_issues[('unsupported_map_key','put')] and not engine.approximate
    # Source inference proves the boxed argument kind; the binder's spelling
    # does not turn Character into String or Long into Integer.
    engine.method=ids['Api.entry']
    call=next(node for node in walk(project.ast[engine.method]) if node.type=='method_invocation'
              and text(node.child_by_field_name('name'))==method_name)
    assert engine.map_key_type(call)==key_kind


def test_type_parameter_in_a_generic_return_does_not_leak_into_stream_contract(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import java.util.stream.Collectors;
      class Api{<String>List<String> values(String value){return Arrays.asList(value);}
      Object entry(){Map map=new HashMap();values('x').stream().map(key->{map.put(key,"found");return key;})
      .collect(Collectors.toList());return map.get("x");}}'''})
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Api.entry'],{}) is None
    assert not engine.operation_issues[('unsupported_map_key','put')] and not engine.approximate
    engine.method=ids['Api.entry']
    call=next(node for node in walk(project.ast[engine.method]) if node.type=='method_invocation'
              and text(node.child_by_field_name('name'))=='values')
    assert engine.source_type(call)=='java.util.List<java.lang.Character>'


def test_fully_qualified_jdk_type_is_preserved_inside_a_generic_class(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Box<String>{java.lang.String value="x";
      java.lang.String getValue(){return value;}}
      class Api{Object entry(){Box box=new Box();Map map=new HashMap();map.put(box.getValue(),"found");return map.get("x");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='found'


def test_bounded_generic_boolean_null_guarantees_failure_before_following_calls(tmp_path):
    from analyzer.paths import run_paths
    project,db,ids=build(tmp_path,{'Api.java':'''class Api{String entry(){return check(null);}
      <Boolean extends java.lang.Boolean>String check(Boolean input){if(input){return after();}return "done";}
      String after(){return "wrong";}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert outcomes and all(o['engine'].outcome=='uncaught application exception' for o in outcomes)
    assert all(not o['approximate'] for o in outcomes)
    assert all(not any('#after(' in target for _,kind,target in o['engine'].edges if kind=='calls') for o in outcomes)
