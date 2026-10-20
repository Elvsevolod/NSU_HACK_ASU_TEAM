import pytest
from analyzer.paths import run_paths
from analyzer.state import ScenarioState, U
from builders import build


@pytest.mark.parametrize('limit', [1, 4, 8])
def test_nullable_collection_keeps_normal_and_caught_completion_at_small_budget(tmp_path, limit):
    project, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;class Api {
      String entry(List<String> values){try{values.size();return after();}
       catch(NullPointerException failure){return failed();}}
      String after(){return "after";}String failed(){return "caught";}}'''})
    outcomes = run_paths(project, ScenarioState(db), ids['Api.entry'], {'values':U}, limit=limit)
    assert {row['result'] for row in outcomes} == {'after','caught'}
    assert all(row['engine'].outcome == 'returned' for row in outcomes)
    assert all(not row['engine'].state.database.unknown_tables for row in outcomes)
