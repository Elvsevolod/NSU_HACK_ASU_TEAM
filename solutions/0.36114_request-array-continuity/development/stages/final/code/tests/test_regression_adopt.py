import pytest

from analyzer.java_collections import JavaRecord
from analyzer.paths import run_paths
from analyzer.state import ScenarioState, U
from builders import build


@pytest.mark.parametrize('limit', [1, 2, 4, 8])
def test_selected_completion_keeps_locals_receiver_and_joint_aliases(tmp_path, limit):
    project, database, ids = build(tmp_path, {'Api.java': '''class Box {int n;}
      class Api {Box held;
        int entry(Box box, boolean flag){
          Box local=box; held=box;
          try {if(flag){box.n=7;throw new IllegalStateException();}else{box.n=9;}}
          catch(IllegalStateException failure){return local.n*10+held.n;}
          return local.n*10+held.n;
        }
      }'''})
    box = JavaRecord('Box', {'__type__':'Box','n':0}, ['n'])
    state = ScenarioState(database)
    state.browser['form']['alias'] = box
    state.database.tables[('service','boxes')] = [box]
    outcomes = run_paths(project, state, ids['Api.entry'], {'box':box,'flag':U}, limit=limit)
    assert {row['result'] for row in outcomes} == {77, 99}
    for row in outcomes:
        browser_box = row['state'].browser['form']['alias']
        assert browser_box['n'] == row['result'] // 11
        assert row['state'].database.tables[('service','boxes')][0] is browser_box
    assert box['n'] == 0
