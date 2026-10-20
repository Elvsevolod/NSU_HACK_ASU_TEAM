"""Source expression types must survive boxing at a Map operation."""
import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


@pytest.mark.parametrize('setup,key,lookup',[
    ('','"id"+7','"id7"'),
    ('','(("k"+1)+2)','"k12"'),
    ('','2>1','true'),
    ('','!(2>3)','true'),
    ('','2==2 && 3!=4','true'),
    ('String text="key-tail";','text.substring(0,3)','"key"'),
    ('','"code".substring(0,2).substring(1)','"o"'),
    ('','"xy".charAt(0)',"'x'"),
    ('','true ? "left" : "right"','"left"'),
    ('','true ? 1 : 2L','1L'),
    ('','false ? 2L : 1','1L'),
])
def test_expression_result_has_the_correct_boxed_key_type(tmp_path,setup,key,lookup):
    source='import java.util.*;class Api {String entry(){'+setup+'Map map=new HashMap();map.put('+key+',"found");return (String)map.get('+lookup+');}}'
    project,db,ids=build(tmp_path,{'Api.java':source})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})=='found'
    assert not engine.warnings


@pytest.mark.parametrize('key,wrong',[("'x'",'"x"'),('1','1L'),('true ? 1 : 2L','1'),('"x".charAt(0)','"x"')])
def test_equal_python_values_do_not_erase_java_key_class(tmp_path,key,wrong):
    source='import java.util.*;class Api {Object entry(){Map map=new HashMap();map.put('+key+',"found");return map.get('+wrong+');}}'
    project,db,ids=build(tmp_path,{'Api.java':source})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{}) is None


def test_erased_object_type_does_not_guess_a_boxed_integer_from_a_python_number(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api {
      Object entry(Object input){Map map=new HashMap();map.put(input,"found");return map.get(1L);}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{'input':1}) is U
    assert engine.operation_issues[('unsupported_map_key','put')]


def test_source_namesake_string_method_keeps_its_declared_return_type(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class String {
      long substring(int start){return 4L;}}
      class Api {Object entry(){String input=new String();Map map=new HashMap();
        map.put(input.substring(0),"found");if(map.get(4)!=null){return "wrong";}return map.get(4L);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='found'


@pytest.mark.parametrize('expression,expected',[("'A'+1",66),("'A'+'B'",131),('"A"+1','A1'),("1+'A'",66)])
def test_char_arithmetic_and_string_concatenation_use_operand_types(tmp_path,expression,expected):
    project,db,ids=build(tmp_path,{'Api.java':'class Api {Object entry(){return '+expression+';}}'})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==expected


def test_declared_string_and_literal_conditional_share_the_native_string_type(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api {
      Object entry(){String part="left";Map map=new HashMap();map.put(true?part:"right","found");return map.get("left");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='found'


@pytest.mark.parametrize('expression,expected',[("'\\n'+1",11),("'\\t'+1",10),("'\\141'+1",98),("'\\''+1",40),("'\\u0041'+1",66)])
def test_character_literals_are_decoded_before_numeric_promotion(tmp_path,expression,expected):
    project,db,ids=build(tmp_path,{'Api.java':'class Api {int entry(){return '+expression+';}}'})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==expected


def test_boxed_character_is_unboxed_for_numeric_addition(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':"class Api {int entry(){Character c='A';return c+1;}}"})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==66
