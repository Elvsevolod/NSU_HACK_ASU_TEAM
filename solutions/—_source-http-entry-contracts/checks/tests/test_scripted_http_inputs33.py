"""Client controls reject absent/failed/partial/wrong-kind producers."""
from copy import deepcopy
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripted_http_inputs33 import value, ScriptInputError, script_grounder
from analyzer.state import U


def reference():return {'$response': 1, 'path': ['id'], 'native_kind': 'Long'}


def producer(identity=41):
    return [{'step': 1, 'entry': 'create', 'result': {'id': identity},
             'outcome': 'returned', 'exploration': {'complete': True}}]


def test_literal_and_body_do_not_change_the_input():
    body = {'id': None, 'fields': ['one', 2, False]}
    before = deepcopy(body)
    actual, fact = value(body, [])
    actual['fields'].append('changed')
    assert body == before and fact['source'] == 'explicit_script'


def test_long_reference_keeps_the_producer_identity_and_origin():
    symbolic = {'__symbol__': 'generated-test', '__type__': 'Long', '__constraints__': ['non_null']}
    history = producer(symbolic)
    actual, fact = value(reference(), history)
    assert actual == symbolic and actual is not symbolic
    assert fact['source'] == 'history' and fact['reference'] == 'history[0].result.id'
    assert fact['producer_observation']['exploration']['complete'] is True
    assert fact['producer_observation']['digest']


@pytest.mark.parametrize('history', [[], producer(U), producer(None), producer(True), producer('41'),
    producer(2**63), producer({'__symbol__': 'x', '__type__': 'Integer'}),
    [{**producer()[0], 'outcome': 'HTTP error response'}],
    [{**producer()[0], 'exploration': {'complete': False}}],
    [{**producer()[0], 'result': {}}]])
def test_incomplete_or_incompatible_history_never_uses_a_database_default(history):
    with pytest.raises(ScriptInputError):value(reference(), history)


@pytest.mark.parametrize('spec', [dict(reference(), extra=True), {'$unknown': 1},
    {**reference(), '$response': True}, {**reference(), 'path': ['__type__']},
    {**reference(), 'native_kind': 'String'}])
def test_invalid_reference_operators_are_rejected(spec):
    with pytest.raises(ScriptInputError):value(spec, producer())


def test_http_response_body_is_the_history_value():
    history = producer()
    history[0]['result'] = {'__type__': 'ResponseEntity', '__http_entity__': True, 'status': 201, 'body': {'id': 41}}
    assert value(reference(), history)[0] == 41


def control(tmp_path, parameters, deployment='service'):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'code/tests'))
    from builders import build
    from analyzer.frontend import Frontend
    from analyzer.state import ScenarioState
    project, db, ids = build(tmp_path, {'Api.java': '''import org.springframework.web.bind.annotation.*;
      @RestController class Api{
        @GetMapping("/records/{id}") Long read(@PathVariable Long id){return id;}
      }'''})
    class NoRanking:
        def rank(self, *args):raise AssertionError('Explicit controls cannot use NL ranking')
    recipe = {'deployment': deployment, 'method': 'GET', 'route_template': '/records/{id}',
              'parameters': parameters, 'headers': {}}
    grounder = script_grounder({'case:1': recipe})(project, Frontend(project), NoRanking(), None, {'facts': {}})
    return project, ids, grounder, ScenarioState(db)


def test_control_executes_through_the_normal_wire_binding(tmp_path):
    from analyzer.engine import Engine
    from analyzer.request import BoundParameters
    project, ids, grounder, state = control(tmp_path, {'id': 73})
    proposals, _ = grounder.step('@http-script:case:1', state)
    assert len(proposals) == 1
    p = proposals[0]
    assert p['request'].record()['path'] == ['records', '73']
    engine = Engine(project, p['state'])
    assert engine.run(p['entry'], BoundParameters(p['params'], p['request'])) == 73
    assert ('', 'executes', ids['Api.read']) in engine.edges
    assert state.history == []


def test_bad_numeric_wire_still_fails_in_server_binding(tmp_path):
    from analyzer.engine import Engine
    from analyzer.request import BoundParameters
    project, ids, grounder, state = control(tmp_path, {'id': 'bad-number'})
    proposals, _ = grounder.step('@http-script:case:1', state)
    p = proposals[0]
    engine = Engine(project, p['state'])
    engine.run(p['entry'], BoundParameters(p['params'], p['request']))
    assert engine.outcome == 'HTTP binding failure'
    assert ('', 'executes', ids['Api.read']) not in engine.edges


def test_wrong_deployment_is_refused_without_a_ranked_fallback(tmp_path):
    _, _, grounder, state = control(tmp_path, {'id': 73}, 'different-service')
    proposals, detail = grounder.step('@http-script:case:1', state)
    assert proposals == [] and detail['unresolved']


def test_generated_history_identity_is_preserved_in_the_wire(tmp_path):
    project, ids, grounder, state = control(tmp_path, {'id': reference()})
    symbolic = {'__symbol__': 'fresh-long', '__type__': 'Long', '__constraints__': ['non_null']}
    state.history = producer(symbolic)
    proposals, detail = grounder.step('@http-script:case:1', state)
    assert len(proposals) == 1 and not detail['unresolved']
    p = proposals[0]
    path = p['request'].record()['path']
    assert path[0] == 'records' and path[1]['__type__'] == 'String'
    assert path[1]['__integral_origin__'] == symbolic
    assert p['bindings']['id']['source'] == 'history'
    assert p['params']['id'] == symbolic
