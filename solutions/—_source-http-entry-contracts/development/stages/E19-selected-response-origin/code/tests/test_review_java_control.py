"""Independent source-only counterexamples from the engineering review."""
import pytest

from analyzer.engine import Engine
from analyzer.state import ScenarioState, U
from builders import build


def execute(tmp_path, body, extra='', params=None, parameters=''):
    project, db, ids = build(tmp_path, {'Api.java':
        'class Api { Object entry(' + parameters + ') {' + body + '}' + extra + '}'})
    engine = Engine(project, ScenarioState(db))
    return engine.run(ids['Api.entry'], params or {}), engine, ids


@pytest.mark.parametrize('body,expected', [
    ('do { return 7; } while(false);', 7),
    ('do { throw new IllegalStateException(); } while(false);', U),
    ('int n=0; do { n++; } while(n<3); return n;', 3),
    ('int n=0; do { n++; continue; } while(n<3); return n;', 3),
    ('int n=0; do { n++; break; } while(true); return n;', 1),
    ('int n=0; do { n++; } while(++n<3); return n;', 4),
    ('try { do { return 3; } while(false); } finally { cleanup(); }', 3),
    ('try { do { throw new IllegalStateException(); } while(false); } catch(RuntimeException e) { return 5; }', 5),
])
def test_do_executes_before_testing_the_condition(tmp_path, body, expected):
    value, engine, ids = execute(tmp_path, body, 'void cleanup(){}')
    assert value == expected
    if 'finally' in body:
        assert ('', 'executes', ids['Api.cleanup']) in engine.edges
    if expected is U:
        assert engine.outcome == 'uncaught application exception'


@pytest.mark.parametrize('literal,expected', [
    ('""', True), ('" "', True), ('"\\t\\n"', True),
    ('"\\u2003"', True), ('"\\u00a0"', False), ('" a "', False),
])
def test_string_isblank_uses_java_whitespace(tmp_path, literal, expected):
    value, _, _ = execute(tmp_path, 'return ' + literal + '.isBlank();')
    assert value is expected


@pytest.mark.parametrize('expression,expected', [
    ('"a,".split(",").length', 1),
    ('"a,,".split(",",-1).length', 3),
    ('"a,b,c".split(",",2).length', 2),
    ('"a,b,c".split(",",2)[1]', 'b,c'),
    ('"".split(",").length', 1),
    ('",,".split(",").length', 0),
    ('"a1b22c".split("[0-9]+").length', 3),
    ('"ab".split("").length', 2),
])
def test_string_split_preserves_java_regex_and_limit(tmp_path, expression, expected):
    value, _, _ = execute(tmp_path, 'return ' + expression + ';')
    assert value == expected


def test_same_signature_on_distinct_receivers_is_not_recursion(tmp_path):
    project, db, ids = build(tmp_path, {'Node.java': '''class Node {
      Node next; int value;
      int step(){ if(next==null) return value; return next.step(); }
    } class Api { int entry(){Node a=new Node();Node b=new Node();
      a.next=b;b.next=null;b.value=9;return a.step();} }'''})
    engine = Engine(project, ScenarioState(db))
    assert engine.run(ids['Api.entry'], {}) == 9
    assert not any('recursion' in warning for warning in engine.warnings)


@pytest.mark.parametrize('declaration', [
    'int count=initial();int initial(){return 7;}',
    'int count;{count=initial();}int initial(){return 7;}',
    'int count=initial();Box(){count++;}int initial(){return 6;}',
])
def test_instance_initializers_execute_source_helpers(tmp_path,declaration):
    project, db, ids = build(tmp_path, {'Box.java': 'class Box{'+declaration+'}class Api{int entry(){return new Box().count;}}'})
    engine = Engine(project, ScenarioState(db))
    assert engine.run(ids['Api.entry'], {}) == 7
    assert ('', 'executes', ids['Box.initial']) in engine.edges
    if 'Box.<init>' in ids:
        assert (ids['Box.<init>'],'calls',ids['Box.initial']) in engine.edges
    else:
        assert (ids['Api.entry'],'calls',ids['Box.initial']) not in engine.edges


def test_initializer_failure_keeps_constructor_prefix_and_skips_body(tmp_path):
    project, db, ids = build(tmp_path, {'Box.java': '''class Box{int n=fail();
      Box(){after();}int fail(){throw new RuntimeException();}void after(){}}
      class Api{Object entry(){return new Box();}}'''})
    engine = Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{}) is U
    assert ('','executes',ids['Box.<init>']) in engine.edges
    assert ('','executes',ids['Box.fail']) in engine.edges
    assert ('','executes',ids['Box.after']) not in engine.edges


def test_nested_source_calls_inside_an_implicit_initializer_are_exported(tmp_path):
    project, db, ids = build(tmp_path, {'Box.java': '''class Box{int n=initial();
      int initial(){return nested();}int nested(){return 9;}}
      class Api{Object entry(){return new Box().n;}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})==9
    assert (ids['Box.initial'],'calls',ids['Box.nested']) in engine.edges
