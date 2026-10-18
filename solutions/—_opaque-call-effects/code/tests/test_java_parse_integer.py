import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from builders import build


@pytest.mark.parametrize('expression,expected',[
    ('Integer.parseInt("42")',42),('Integer.parseInt("-19")',-19),
    ('Integer.parseInt("+3")',3),('Integer.parseInt("7f",16)',127),
    ('Integer.parseInt("110",2)',6),('Integer.parseInt("0004")',4),
    ('Integer.parseInt("2147483647")',2147483647),
    ('Integer.parseInt("-2147483648")',-2147483648),
    ('java.lang.Integer.parseInt("42")',42),
])
def test_parse_integer_known_values_follow_java_rules(tmp_path,expression,expected):
    project,db,ids=build(tmp_path,{'Api.java':'class Api {int entry(){return '+expression+';}}'})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==expected


@pytest.mark.parametrize('expression',[
    'Integer.parseInt("bad")','Integer.parseInt("2147483648")',
    'Integer.parseInt("-2147483649")','Integer.parseInt(" 12")',
    'Integer.parseInt("1_2")','Integer.parseInt("")','Integer.parseInt("+")',
    'Integer.parseInt(null)','Integer.parseInt("10",1)','Integer.parseInt("9",8)',
])
def test_known_parse_failure_selects_catch_and_skips_following_call(tmp_path,expression):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {String entry(){try{
      '''+expression+''';return after();}catch(NumberFormatException failure){return rejected();}}
      String after(){return "wrong";}String rejected(){return "rejected";}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})=='rejected'
    targets={target for _,relation,target in engine.edges if relation=='executes'}
    assert targets=={ids['Api.entry'],ids['Api.rejected']}


def test_unknown_number_keeps_both_return_and_exception_paths_with_diagnostics(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {String entry(String input){try{
      Integer.parseInt(input);return after();}catch(NumberFormatException failure){return rejected();}}
      String after(){return "after";}String rejected(){return "rejected";}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{'input':U})
    assert {o['result'] for o in outcomes}=={'after','rejected'}
    assert all(any('parseInt' in warning for warning in o['engine'].warnings) for o in outcomes)


def test_an_unresolved_dependency_named_integer_is_not_assumed_to_be_the_jdk(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import other.library.Integer;
      class Api {Object entry(){return Integer.parseInt("42");}}'''})
    engine=Engine(project,ScenarioState(db),conservative=True)
    assert engine.run(ids['Api.entry'],{}) is U
    assert engine.warnings


def test_a_receiver_variable_named_integer_is_not_a_jdk_type(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import external.library.Parser;
      class Api {Object entry(Parser Integer){return Integer.parseInt("42");}}'''})
    engine=Engine(project,ScenarioState(db),conservative=True)
    assert engine.run(ids['Api.entry'],{'Integer':U}) is U
    assert engine.warnings


def test_comment_text_cannot_change_native_type_imports(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''// import other.library.Integer;
      class Api {int entry(){return Integer.parseInt("42");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==42
