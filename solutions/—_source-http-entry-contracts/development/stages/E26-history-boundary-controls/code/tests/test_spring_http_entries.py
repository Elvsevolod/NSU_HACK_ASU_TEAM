"""Source and wire obligations frozen before the transfer follow-up patch."""
import json

import pytest

from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.frontend import Frontend
from analyzer.project import Project
from analyzer.request import MISSING
from analyzer.state import ScenarioState
from builders import build


def grounder(project):
    frontend = Frontend(project)
    index = ContractIndex(project, frontend)
    return ContractGrounder(project, frontend, index, None, {'facts': {}, 'unresolved': []})


def services(tmp_path, units=('inventory-app',)):
    project, db, ids = build(tmp_path, {
        'Api.java': 'import org.springframework.web.bind.annotation.*; @RestController class Api {'
                    '@PostMapping("/records") String write(@RequestBody Object body){return "saved";}'
                    '@GetMapping("/records") String read(){return "read";} }',
    }, module='inventory-module')
    project.skeleton['nodes']['module:inventory-module']['deployment_units'] = list(units)
    (tmp_path/'skeleton.json').write_text(json.dumps(project.skeleton))
    return Project(tmp_path/'skeleton.json', tmp_path), db, ids


def test_boot_plain_mapped_class_is_not_a_registered_controller(tmp_path):
    project, db, ids = build(tmp_path, {
        'App.java': 'import org.springframework.boot.autoconfigure.SpringBootApplication; @SpringBootApplication class App {void start(){}}',
        'Active.java': 'import org.springframework.web.bind.annotation.*; @RestController class Active {@GetMapping("/records") String read(){return "active";}}',
        'Plain.java': 'import org.springframework.web.bind.annotation.GetMapping; class Plain {@GetMapping("/records") String read(){return "plain";}}',
    })
    candidate = grounder(project)
    assert {c['entry'] for c in candidate.index.contracts.values()} == {ids['Active.read']}
    proposals, _ = candidate.step('GET http://service/records', ScenarioState(db))
    assert [p['entry'] for p in proposals] == [ids['Active.read']]


def test_mapping_on_a_bean_is_not_enough_without_a_handler_stereotype(tmp_path):
    project, db, ids = build(tmp_path, {
        'App.java': 'import org.springframework.boot.autoconfigure.SpringBootApplication; import org.springframework.context.annotation.Bean; '
                    '@SpringBootApplication class App {@Bean Plain bean(){return new Plain();}}',
        'Plain.java': 'import org.springframework.web.bind.annotation.GetMapping; class Plain {@GetMapping("/records") String read(){return "plain";}}',
    })
    proposals, detail = grounder(project).step('GET http://service/records', ScenarioState(db))
    assert proposals == [] and detail['unresolved']


def test_unknown_meta_annotation_is_not_proof_of_absent_controller(tmp_path):
    project, db, ids = build(tmp_path, {
        'App.java': 'import org.springframework.boot.autoconfigure.SpringBootApplication; @SpringBootApplication class App {void start(){}}',
        'Api.java': 'import org.springframework.web.bind.annotation.GetMapping; @CustomWeb class Api {@GetMapping("/records") String read(){return "custom";}}',
    })
    assert ids['Api.read'] in {c['entry'] for c in grounder(project).index.contracts.values()}
    assert any('registration' in message.lower() for message in project.route_warnings)


def test_active_profile_gate_survives_registration_refinement(tmp_path):
    project, db, ids = build(tmp_path, {
        'App.java': 'import org.springframework.boot.autoconfigure.SpringBootApplication; @SpringBootApplication class App {void start(){}}',
        'Api.java': 'import org.springframework.web.bind.annotation.*; import org.springframework.context.annotation.Profile; '
                    '@RestController @Profile("disabled") class Api {@GetMapping("/records") String read(){return "off";}}',
    })
    assert grounder(project).step('GET http://service/records', ScenarioState(db))[0] == []


def test_deployment_host_uses_input_units_instead_of_module_substring(tmp_path):
    project, db, ids = services(tmp_path)
    proposals, _ = grounder(project).step('GET http://inventory-app/records', ScenarioState(db))
    assert [p['entry'] for p in proposals] == [ids['Api.read']]
    assert proposals[0]['request'].deployment == 'inventory-app'


def test_module_substring_is_not_a_deployment_alias(tmp_path):
    project, db, ids = services(tmp_path)
    assert grounder(project).step('GET http://inventory/records', ScenarioState(db))[0] == []


def test_exact_deployment_preserves_the_requested_unit(tmp_path):
    project, db, ids = services(tmp_path, ('inventory-a', 'inventory-b'))
    proposals, _ = grounder(project).step('GET http://INVENTORY-B/records', ScenarioState(db))
    assert len(proposals) == 1
    assert proposals[0]['request'].deployment == 'inventory-b'


def test_relative_request_keeps_all_declared_deployments(tmp_path):
    project, db, ids = services(tmp_path, ('inventory-a', 'inventory-b'))
    proposals, _ = grounder(project).step('GET /records', ScenarioState(db))
    assert {p['request'].deployment for p in proposals} == {'inventory-a', 'inventory-b'}
    assert all(p['unresolved'] for p in proposals)


def test_explicit_headers_retain_occurrences_and_native_body_values(tmp_path):
    project, db, ids = services(tmp_path)
    action = 'POST http://inventory-module/records\r\nX-Trace: first\r\nx-trace: second\r\nContent-Type: application/problem+json\r\n\r\n{"id":21,"ready":false,"value":null}'
    proposals, _ = grounder(project).step(action, ScenarioState(db))
    assert len(proposals) == 1
    request = proposals[0]['request']
    assert request.headers == {'x-trace': ['first', 'second'], 'content-type': ['application/problem+json']}
    assert request.body == {'id': 21, 'ready': False, 'value': None}
    assert type(request.body['id']) is int and type(request.body['ready']) is bool
    assert request.record()['provenance']['quote'] == action


def test_header_only_request_has_missing_body(tmp_path):
    project, db, ids = services(tmp_path)
    proposals, _ = grounder(project).step('GET http://inventory-module/records\nX-Token: source-literal', ScenarioState(db))
    assert len(proposals) == 1
    assert proposals[0]['request'].headers == {'x-token': ['source-literal']}
    assert proposals[0]['request'].body is MISSING


@pytest.mark.parametrize('suffix', ['Bad Header: x', 'X-Trace: one\n folded', 'X-Trace: one\n\n{bad-json}'])
def test_invalid_explicit_wire_is_refused_before_execution(tmp_path, suffix):
    project, db, ids = services(tmp_path)
    proposals, detail = grounder(project).step('POST http://inventory-module/records\n'+suffix, ScenarioState(db))
    assert proposals == [] and detail['unresolved']


def test_legacy_json_body_still_bypasses_nl_retrieval(tmp_path):
    project, db, ids = services(tmp_path)
    candidate = grounder(project)
    candidate.index.rank = lambda *a, **kw: pytest.fail('explicit HTTP entered retrieval')
    proposals, _ = candidate.step('POST http://inventory-module/records\n{"id":0}', ScenarioState(db))
    assert proposals[0]['request'].body == {'id': 0}
    assert proposals[0]['request'].headers == {'content-type': ['application/json']}
