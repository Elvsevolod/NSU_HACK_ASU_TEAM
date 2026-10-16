"""Source-derived behavior checks. Hidden graph quality is measured only by the site."""
from copy import deepcopy
from datetime import datetime
import builtins
import io
import json
import os
from pathlib import Path
import socket

import pytest

from analyzer.__main__ import analyze
from analyzer.engine import Engine
from analyzer.grounding import Grounder, parameters
from analyzer.models import construct, library
from analyzer.project import Project
from analyzer.state import Database, ScenarioState, U


@pytest.fixture(scope='module')
def analyzed():
    root = Path(os.environ.get('TT_CHALLENGE_ROOT', Path(__file__).resolve().parents[4] / 'tt-challenge'))
    original_io, original_open = io.open, builtins.open

    def guard(opener):
        def checked(file, *args, **kwargs):
            if isinstance(file, (str, Path)) and 'gold' in Path(file).parts:
                raise AssertionError('Inference must not read gold')
            return opener(file, *args, **kwargs)
        return checked

    def offline(*args, **kwargs):
        raise AssertionError('Inference must not access the network')

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(io, 'open', guard(original_io))
        patch.setattr(builtins, 'open', guard(original_open))
        patch.setattr(socket.socket, 'connect', offline)
        patch.setattr(socket, 'create_connection', offline)
        project = Project(root / 'skeleton/trainticket.json.gz', root / 'targets/trainticket')
        grounder = Grounder(project)
        database = Database(root / 'context/db-after-warmup.sql.gz')
        initial = deepcopy(database.tables)
        results = {}
        inputs = {}
        for sid in ('S2', 'S5', 'S6', 'S7'):
            inputs[sid] = json.loads((root / 'scenarios' / (sid + '.json')).read_text())
            results[sid] = analyze(project, grounder, database, inputs[sid])
        renamed = deepcopy(inputs['S7'])
        renamed['id'] = 'arbitrary-user-scenario'
        results['renamed'] = analyze(project, grounder, database, renamed)
        paid = deepcopy(inputs['S7'])
        paid['steps'] = [s for s in paid['steps'] if not s['action'].lower().startswith('collect')]
        results['not-collected'] = analyze(project, grounder, database, paid)
        assert database.tables == initial
        assert not project.source_errors
        yield project, grounder, database, results


def steps(analyzed, sid):
    return {s['n']: s for s in analyzed[3][sid][1]['steps']}


def remote_targets(step):
    return {e['target'] for e in step['edges'] if e['relation'] == 'remote'}


def test_s7_collected_order_rejects_cancellation_and_rebooking(analyzed):
    s = steps(analyzed, 'S7')
    assert [s[n]['state_after']['orders'][0]['status'] for n in (4, 6, 7, 10)] == [0, 1, 2, 2]
    for n in (8, 9, 10):
        assert s[n]['result']['status'] == 0
        assert all('ts-order-service:' in target or 'ts-order-other-service:' in target for target in remote_targets(s[n]))
    assert not any('getTripAllDetailInfo' in e['target'] for e in s[10]['edges'])


def test_s7_consignment_update_reuses_record_without_repricing(analyzed):
    s = steps(analyzed, 'S7')
    old, updated = s[11]['result']['data'], s[12]['result']['data']
    assert old['id'] == updated['id']
    assert old['weight'] == updated['weight'] == 3
    assert old['price'] == updated['price']
    assert old['phone'] != updated['phone'] and old['consignee'] != updated['consignee']
    assert not remote_targets(s[12])
    assert not any('#insertConsignRecord(' in e['target'] for e in s[12]['edges'])


def test_removing_collection_step_allows_cancellation(analyzed):
    s = steps(analyzed, 'not-collected')
    assert s[10]['state_before']['orders'][0]['status'] == 4  # Cancellation now succeeds.
    assert s[9]['result']['status'] == 1


def test_s2_separate_orders_cancel_then_refund_cheaper_rebooking(analyzed):
    s = steps(analyzed, 'S2')
    orders = s[14]['state_after']['orders']
    assert len(orders) == 2 and orders[0]['id'] != orders[1]['id']
    assert [o['status'] for o in orders] == [4, 3]
    assert orders[1]['seatClass'] == 3
    assert s[9]['result']['data'] == '280.00'
    assert s[14]['result']['status'] == 1
    targets = remote_targets(s[14])
    assert any('#drawBack(' in target for target in targets)
    assert any('ts-order-other-service:' in target and '#saveOrderInfo(' in target for target in targets)
    assert not any('ts-payment-service:' in target or '#deleteOrder(' in target or '#createNewOrder(' in target for target in targets)
    assert s[6]['parameters']['foodName'] == s[11]['parameters']['foodName'] != U
    assert s[4]['entry'].startswith('method:ts-station-food-service:')


def test_s5_keeps_cheapest_selection_through_other_searches(analyzed):
    s = steps(analyzed, 'S5')
    cheapest = s[2]['result']['data'][0]['tripId']
    assert cheapest == s[6]['parameters']['tripId'] == s[8]['parameters']['tripId']
    assert s[5]['result']['data']['firstSectionResult']
    # The supplied routes have no Suzhou -> Nanjing segment in that direction.
    assert s[5]['result']['data']['secondSectionResult'] == []
    assert [s[n]['state_after']['orders'][0]['status'] for n in (8, 10, 11, 12)] == [0, 1, 2, 6]


def test_s6_admin_created_route_is_used_for_passenger_purchase(analyzed):
    s = steps(analyzed, 'S6')
    assert all(s[n]['result']['status'] == 1 for n in range(2, 7))
    route = s[4]['result']['data']['id']
    assert s[5]['parameters']['routeId'] == s[6]['parameters']['routeId'] == route
    assert s[8]['result']['data'][0]['tripId']['number'] == '9101'
    order = s[13]['state_after']['orders'][0]
    assert order['trainNumber'] == s[6]['parameters']['tripId'] and order['status'] == 1


def test_stateful_analysis_does_not_depend_on_scenario_id(analyzed):
    normalize = lambda block: {(None if e['relation'] == 'executes' else e['source'], e['relation'], e['target']) for e in block['edges']}
    assert normalize(analyzed[3]['S7'][0]) == normalize(analyzed[3]['renamed'][0])


def test_changed_weight_reaches_price_service(analyzed):
    project, grounder, database, _ = analyzed
    state = ScenarioState(database)
    record = deepcopy(steps(analyzed, 'S7')[11]['result']['data'])
    rid = next(r for r, n in project.nodes.items() if n['kind'] == 'data_resource' and n.get('name') == 'consign_record')
    state.database.rows(project.nodes[rid]).append(record)
    state.last_consign = deepcopy(record)
    entry, params, _ = grounder.step('Update consignee and change luggage weight to 9 kg', state)
    engine = Engine(project, state)
    result = engine.run(entry, params)
    assert result['status'] == 1 and result['data']['weight'] == 9
    assert any(relation == 'remote' and 'ts-consign-price-service:' in target for _, relation, target in engine.edges)


def test_admin_values_are_extracted_from_text_not_fixed_to_given_names(analyzed):
    state = ScenarioState(analyzed[2])
    state.role = 'admin'
    p = parameters('Add a new station Example Town with a stay time of 8 minutes', state, {})
    assert p['name'] == 'exampletown' and p['stayTime'] == 8
    p = parameters('Add a new train type ExampleType with 42 second-class and 17 first-class seats and an average speed of 123', state, {})
    assert (p['name'], p['economyClass'], p['confortClass'], p['averageSpeed']) == ('ExampleType', 42, 17, 123)


def test_http_wrapper_and_decimal_comparison_are_preserved():
    now = datetime(2026, 9, 15)
    handled, response = construct('ResponseEntity<>', [{'status': 1}, 'OK'], now)
    assert handled and response['body']['status'] == 1
    _, a = construct('BigDecimal', ['350.0'], now)
    _, b = construct('BigDecimal', ['122.5'], now)
    assert library('compareTo', a, [b], '', now) == (True, 1)
    assert library('subtract', a, [b], '', now)[1] == 227.5
