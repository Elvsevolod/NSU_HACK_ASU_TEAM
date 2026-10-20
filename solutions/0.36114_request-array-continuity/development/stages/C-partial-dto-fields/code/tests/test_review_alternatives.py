import pytest
from analyzer.paths import run_paths
from analyzer.java_collections import JavaRecord
from analyzer.state import ScenarioState, U
from builders import build


@pytest.mark.parametrize('limit', [1, 2, 8])
def test_dispatch_does_not_apply_opposite_mutations_sequentially(tmp_path, limit):
    project, db, ids = build(tmp_path, {'Api.java': '''interface Strategy {void apply(Counter counter);}
      class Up implements Strategy {public void apply(Counter counter){counter.count++;}}
      class Down implements Strategy {public void apply(Counter counter){counter.count--;}}
      class Counter {public int count;public int mandatory;}
      class Api { Strategy strategy; int entry(Counter counter){strategy.apply(counter);counter.mandatory=7;return counter.count;} }'''})
    counter = JavaRecord('Counter', {'__type__': 'Counter', 'count': 0, 'mandatory': 0}, ['count', 'mandatory'])
    outcomes = run_paths(project, ScenarioState(db), ids['Api.entry'], {'counter': counter}, limit=limit)
    assert {item['result'] for item in outcomes} <= {-1, 1, U}
    assert all(item['engine'].uncertain == 0 for item in outcomes)
    assert counter['count'] == 0 and counter['mandatory'] == 0
    assert all(not any('recursion' in warning for warning in item['engine'].warnings) for item in outcomes)


def test_unknown_condition_forks_state_and_arguments_together(tmp_path):
    project, db, ids = build(tmp_path, {'Api.java': '''class Counter {public int count;}
      class Api {int entry(Counter counter,boolean flag){if(flag){counter.count++;}else{counter.count--;}return counter.count;}}'''})
    state = ScenarioState(db)
    counter = JavaRecord('Counter', {'__type__': 'Counter', 'count': 0}, ['count'])
    state.browser['form']['counter'] = counter
    outcomes = run_paths(project, state, ids['Api.entry'], {'counter': counter, 'flag': U}, limit=1)
    result = outcomes[0]
    assert result['result'] is U
    assert result['state'].browser['form']['counter']['count'] is U
    assert counter['count'] == 0


@pytest.mark.parametrize('limit',[1,2,8])
def test_mixed_return_and_throw_keep_catch_and_normal_continuations_separate(tmp_path,limit):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      int entry(boolean flag){try{if(flag){throw new IllegalStateException();}normal();}
        catch(IllegalStateException failure){caught();return 2;}after();return 1;}
      void normal(){} void caught(){} void after(){} }'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{'flag':U},limit=limit)
    assert {row['result'] for row in outcomes}=={1,2}
    for row in outcomes:
        methods={target for _,rel,target in row['engine'].edges if rel=='executes'}
        if row['result']==1:
            assert ids['Api.normal'] in methods and ids['Api.after'] in methods
            assert ids['Api.caught'] not in methods
        else:
            assert ids['Api.caught'] in methods
            assert ids['Api.normal'] not in methods and ids['Api.after'] not in methods
