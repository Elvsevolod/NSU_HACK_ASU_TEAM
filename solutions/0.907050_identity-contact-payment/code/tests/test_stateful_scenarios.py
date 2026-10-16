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
        for sid in ('S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7'):
            inputs[sid] = json.loads((root / 'scenarios' / (sid + '.json')).read_text())
            results[sid] = analyze(project, grounder, database, inputs[sid])
        renamed = deepcopy(inputs['S7'])
        renamed['id'] = 'arbitrary-user-scenario'
        results['renamed'] = analyze(project, grounder, database, renamed)
        for sid in ('S3', 'S4'):
            renamed = deepcopy(inputs[sid])
            renamed['id'] = 'arbitrary-user-scenario'
            results['renamed-' + sid] = analyze(project, grounder, database, renamed)
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


@pytest.mark.parametrize('sid, renamed', [('S7', 'renamed'), ('S3', 'renamed-S3'), ('S4', 'renamed-S4')])
def test_stateful_analysis_does_not_depend_on_scenario_id(analyzed, sid, renamed):
    normalize = lambda block: {(None if e['relation'] == 'executes' else e['source'], e['relation'], e['target']) for e in block['edges']}
    assert normalize(analyzed[3][sid][0]) == normalize(analyzed[3][renamed][0])


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


def test_s4_registration_identity_reaches_login_contact_and_order(analyzed):
    s = steps(analyzed, 'S4')
    user = s[1]['result']['data']
    contact = s[3]['result']['data']
    order = s[7]['state_after']['orders'][0]
    assert user['userId'] != ScenarioState(analyzed[2]).account_id
    assert s[2]['result']['data']['userId'] == contact['accountId'] == order['accountId'] == user['userId']
    assert s[2]['parameters']['username'] == user['userName']
    assert order['contactsDocumentNumber'] == contact['documentNumber'] == user['documentNum']
    assert s[8]['result']['data'] == [order]


def test_s4_food_and_external_payment_then_refund(analyzed):
    s = steps(analyzed, 'S4')
    assert s[6]['result']['status'] == 1
    food = s[6]['result']['data']['trainFoodList'][0]
    assert (s[7]['parameters']['foodName'], s[7]['parameters']['foodPrice']) == (food['foodName'], food['price'])
    assert s[7]['result']['msg'] == 'Success.'
    assert 'ts-inside-payment-service:' in s[11]['entry']
    assert any('ts-payment-service:' in target for target in remote_targets(s[11]))
    assert [s[n]['state_after']['orders'][0]['status'] for n in (7, 11, 13)] == [0, 1, 4]
    assert s[12]['result']['data'] == '40.00'
    assert s[14]['parameters']['enableStateQuery'] is True and s[14]['parameters']['state'] == 4
    assert [order['status'] for order in s[14]['result']['data']] == [4]


def test_s3_two_contacts_and_two_orders_remain_distinct(analyzed):
    s = steps(analyzed, 'S3')
    existing, new = s[5]['result']['data'][0], s[6]['result']['data']
    assert existing['id'] != new['id']
    assert s[7]['parameters']['contactsId'] == existing['id']
    assert s[8]['parameters']['contactsId'] == new['id']
    first, second = s[8]['state_after']['orders']
    assert first['contactsDocumentNumber'] == existing['documentNumber']
    assert second['contactsDocumentNumber'] == new['documentNumber']
    assert [first['seatClass'], second['seatClass']] == [2, 3]
    assert first['id'] != second['id']
    assert s[10]['parameters']['orderId'] == s[12]['parameters']['orderId'] == first['id']
    assert s[11]['parameters']['orderId'] == s[13]['parameters']['orderId'] == second['id']
    assert [order['status'] for order in s[13]['state_after']['orders']] == [1, 1]
    assert not any('ts-payment-service:' in target for n in (12, 13) for target in remote_targets(s[n]))


def test_assurance_enum_preserves_constructor_fields(analyzed):
    s = steps(analyzed, 'S3')
    assert s[15]['result']['data'] == [{'__type__': 'AssuranceTypeBean', 'index': 1,
                                      'name': 'Traffic Accident Assurance', 'price': 3.0}]
    assert s[7]['result']['msg'] == 'Success.'
    assert any('assurance.entity.Assurance#<init>' in edge['target'] for edge in s[7]['edges'])


@pytest.mark.parametrize('sid, step_number', [('S4', 1), ('S3', 6)])
def test_duplicate_registration_or_contact_is_rejected_by_source(analyzed, sid, step_number):
    project, _, database, _ = analyzed
    state = ScenarioState(database)
    step = steps(analyzed, sid)[step_number]
    first = Engine(project, state).run(step['entry'], deepcopy(step['parameters']))
    after_first = deepcopy(state.database.tables)
    second = Engine(project, state).run(step['entry'], deepcopy(step['parameters']))
    assert first['status'] == 1 and second['status'] == 0
    assert state.database.tables == after_first


@pytest.mark.parametrize('balance, duplicate, succeeds, external', [(0, False, True, True),
                                                                 (10000, False, True, False),
                                                                 (0, True, False, True)])
def test_payment_branch_depends_on_balance_and_external_response(analyzed, balance, duplicate, succeeds, external):
    project, grounder, database, _ = analyzed
    state = ScenarioState(database)
    order = deepcopy(steps(analyzed, 'S4')[7]['state_after']['orders'][0])
    state.account_id, state.last_trip, state.last_order = order['accountId'], order['trainNumber'], order['id']
    state.orders = [order]
    state.database.tables[('ts_order', 'orders')].append(order)
    if balance:
        state.database.tables[('ts_inside_payment', 'inside_money')].append({'id': 'topup', 'userId': state.account_id, 'money': str(balance)})
    if duplicate:
        state.database.tables[('ts_payment', 'payment')].append({'id': 'duplicate', 'orderId': order['id'], 'userId': state.account_id, 'price': order['price']})
    entry, params, _ = grounder.step('Pay for the order', state)
    engine = Engine(project, state)
    result = engine.run(entry, params)
    targets = {target for _, relation, target in engine.edges if relation == 'remote'}
    assert result['status'] == int(succeeds)
    assert any('ts-payment-service:' in target for target in targets) is external
    assert any('#modifyOrder(' in target for target in targets) is succeeds
    saved = next(row for row in state.database.tables[('ts_order', 'orders')] if row['id'] == order['id'])
    assert saved['status'] == int(succeeds)


def test_missing_new_contact_does_not_fall_back_to_old_contact(analyzed):
    state = ScenarioState(analyzed[2])
    state.last_contact = 'existing-contact'
    params = parameters('Book a seat for the new contact', state, analyzed[0].enums)
    assert params['contactsId'] is U
