from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState, U
from builders import build


def test_fallback_candidates_do_not_fabricate_a_known_false_call(tmp_path):
    project, db, ids = build(tmp_path, {'Api.java': '''class Api {
      Object entry(){unsupported();if(false){excluded();}return "ok";}
      void excluded(){} }'''})
    engine = Engine(project, ScenarioState(db))
    engine.run(ids['Api.entry'], {})
    assert ('', 'executes', ids['Api.excluded']) not in engine.edges
    assert not any(event['edge'][2] == ids['Api.excluded'] for event in engine.events)


def test_explicit_fallback_separates_static_candidates_from_events(tmp_path):
    project, db, ids = build(tmp_path, {'Api.java': '''class Api {
      void entry(){if(false){excluded();}} void excluded(){} }'''})
    engine = Engine(project, ScenarioState(db))
    engine.fallback(ids['Api.entry'])
    assert not engine.edges and not engine.events
    assert ('', 'executes', ids['Api.excluded']) in engine.candidate_edges


def test_unknown_branch_does_not_taint_an_unconditional_following_call(tmp_path):
    project, db, ids = build(tmp_path, {'Api.java': '''class Api {
      void entry(boolean flag){before();if(flag){conditional();}after();}
      void before(){} void conditional(){} void after(){} }'''})
    outcomes = run_paths(project, ScenarioState(db), ids['Api.entry'], {'flag': U})
    for item in outcomes:
        engine = item['engine']
        assert ('', 'executes', ids['Api.before']) in engine.confirmed_edges
        assert ('', 'executes', ids['Api.after']) in engine.confirmed_edges
        assert ('', 'executes', ids['Api.conditional']) not in engine.confirmed_edges
        for event in engine.events:
            assert event['request'] == 1 and event['callsite']
            assert event['context'] in engine.event_contexts
            assert all(assumption in engine.assumption_registry.values()
                       for assumption in engine.event_contexts[event['context']]['assumptions'])
