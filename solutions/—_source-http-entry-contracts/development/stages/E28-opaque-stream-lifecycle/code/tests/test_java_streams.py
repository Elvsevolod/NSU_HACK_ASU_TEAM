from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState, U
from builders import build


def source(body):
    return {'Api.java': '''import java.util.*; import java.util.stream.Collectors;
      class Api { List<Integer> values;
      Object run(List<Integer> rows, int lower){ BODY }
      int mark(int number){ return number * 2; }
    }'''.replace('BODY', body)}


def test_filter_and_map_preserve_full_encounter_order_and_source_calls(tmp_path):
    project, db, ids = build(tmp_path, source('''return rows.stream()
      .filter(number -> number >= lower).map(number -> mark(number))
      .collect(Collectors.toList());'''))
    engine = Engine(project, ScenarioState(db))
    assert engine.run(ids['Api.run'], {'rows': list(range(66)), 'lower': 1}) == list(range(2, 132, 2))
    assert (ids['Api.run'], 'calls', ids['Api.mark']) in engine.edges
    assert not engine.approximate


def test_intermediate_stream_filter_is_lazy_and_captures_original_scalar(tmp_path):
    project, db, ids = build(tmp_path, source('''List<Integer> seen=new ArrayList<>();
      Object pending=rows.stream().filter(number -> {seen.add(number);return true;});
      return seen.size();'''))
    engine = Engine(project, ScenarioState(db))
    assert engine.run(ids['Api.run'], {'rows': [4, 2], 'lower': 1}) == 0
    project, db, ids = build(tmp_path/'capture', source('''int threshold=lower;
      Object pending=rows.stream().filter(number -> number >= threshold);
      return pending.collect(Collectors.toList());'''))
    assert Engine(project, ScenarioState(db)).run(ids['Api.run'], {'rows': [4, 2], 'lower': 3}) == [4]


def test_unknown_filter_membership_retains_alternatives_and_never_claims_exact_size(tmp_path):
    project, db, ids = build(tmp_path, source('''return rows.stream()
      .filter(number -> number >= lower).collect(Collectors.toList());'''))
    outcomes = run_paths(project, ScenarioState(db), ids['Api.run'], {'rows': [4], 'lower': U})
    assert {repr(outcome['result']) for outcome in outcomes} == {'[]', '[4]'}
    engine = Engine(project, ScenarioState(db), conservative=True)
    assert engine.run(ids['Api.run'], {'rows': [4], 'lower': U}) is U
    assert engine.approximate
    assert any('unknown stream membership' in warning for warning in engine.warnings)


def test_stream_does_not_treat_project_collectors_as_java_library(tmp_path):
    project, db, ids = build(tmp_path, {
      'Api.java': '''import java.util.*; class Api {
        Object run(List<Integer> rows){return rows.stream().collect(Collectors.toList());}
      } class Collectors {static String toList(){return "custom";}}'''})
    engine = Engine(project, ScenarioState(db))
    assert engine.run(ids['Api.run'], {'rows': [4]}) is U
    assert engine.approximate
    assert any('unsupported stream operation' in warning for warning in engine.warnings)


def test_stream_cannot_be_reused_after_terminal_operation(tmp_path):
    project, db, ids = build(tmp_path, source('''Object pending=rows.stream();
      pending.collect(Collectors.toList());return pending.collect(Collectors.toList());'''))
    engine = Engine(project, ScenarioState(db))
    assert engine.run(ids['Api.run'], {'rows': [4], 'lower': 0}) is U
    assert engine.outcome=='uncaught application exception'
    assert not engine.approximate


def test_old_pipeline_stage_is_unusable_after_linking_an_intermediate_operation(tmp_path):
    project, db, ids = build(tmp_path, source('''Object start=rows.stream();
      Object filtered=start.filter(number -> true);
      return start.collect(Collectors.toList());'''))
    engine=Engine(project, ScenarioState(db))
    assert engine.run(ids['Api.run'], {'rows':[1], 'lower':0}) is U
    assert engine.outcome=='uncaught application exception'
    assert not engine.approximate
