from analyzer.heap_join import clone_execution
from analyzer.java_collections import JavaRecord
from analyzer.state import ScenarioState
from builders import build


def test_completed_unaliased_response_can_be_shared_with_an_owned_journal_list(tmp_path):
    _, db, _ = build(tmp_path, {'Api.java': 'class Api {void entry(){}}'})
    state = ScenarioState(db)
    item = {'result': {'__type__': 'Historical', 'id': 'old'}}
    state.history.append(item)
    (owned, params), _ = clone_execution(state, {'key': 'new'})
    assert owned.history is not state.history and owned.history[0] is item
    owned.history.append({'result': None})
    assert len(state.history) == 1


def test_live_alias_into_history_is_copied_jointly(tmp_path):
    _, db, _ = build(tmp_path, {'Api.java': 'class Api {void entry(){}}'})
    state = ScenarioState(db)
    value = JavaRecord('Item', {'id': 'old'}, ['id'])
    state.history.append({'result': value})
    state.browser['form']['selected'] = value
    (owned, params), _ = clone_execution(state, {'input': value})
    assert owned.history[0]['result'] is params['input'] is owned.browser['form']['selected']
    params['input']['id'] = 'changed'
    assert value['id'] == 'old'
