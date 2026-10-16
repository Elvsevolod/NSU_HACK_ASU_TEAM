import json
from pathlib import Path

import pytest
from tree_sitter import Language, Parser
import tree_sitter_java

from analyzer.engine import Engine
from analyzer.grounding import intent, parameters
from analyzer.project import Project, text, walk
from analyzer.state import Database, ScenarioState, U, sql_rows


class EmptyDatabase:
    tables = {}

    def copy(self):
        return EmptyDatabase()


def tiny_project(tmp_path, body, signature='boolean enabled'):
    source = 'class Demo {\n void entry(' + signature + ') {\n' + body + '\n}\n void left() {}\n void right() {}\n}\n'
    (tmp_path / 'Demo.java').write_text(source)
    tree = Parser(Language(tree_sitter_java.language())).parse(source.encode())
    nodes = {'module:app': {'kind': 'module', 'name': 'app'},
             'type:app:Demo': {'kind': 'type', 'fqn': 'Demo', 'module': 'app', 'file': 'Demo.java'}}
    ids = {}
    methods = [n for n in walk(tree.root_node) if n.type == 'method_declaration']
    for method in methods:
        name = text(method.child_by_field_name('name'))
        params = [text(p.child_by_field_name('type')) for p in method.child_by_field_name('parameters').named_children]
        mid = f'method:app:Demo#{name}({",".join(params)})'
        ids[name] = mid
        nodes[mid] = dict(kind='method', name=name, owner='type:app:Demo', module='app',
                          file='Demo.java', line=method.start_point.row + 1, end=method.end_point.row + 1,
                          params_as_written=params, annotations=[], abstract=False)
    edges = []
    for method in methods:
        mid = ids[text(method.child_by_field_name('name'))]
        for call in walk(method):
            if call.type == 'method_invocation':
                name_node = call.child_by_field_name('name')
                name = text(name_node)
                row, col = name_node.start_point.row + 1, name_node.start_point.column + 1
                cid = f'call:{mid}@{row}:{col}'
                nodes[cid] = dict(kind='call_site', method=mid, callee=name, receiver_type='Demo',
                                  receiver='', line=row, col=col, arg_count=0, file='Demo.java')
                if name in ids:
                    edges.append({'source': cid, 'type': 'calls', 'target': ids[name]})
    path = tmp_path / 'skeleton.json'
    path.write_text(json.dumps({'nodes': nodes, 'edges': edges, 'project': 'test'}))
    return Project(path, tmp_path), ids


@pytest.mark.parametrize('enabled,expected', [(True, {'left'}), (False, {'right'}), (U, {'left', 'right'})])
def test_conditions_keep_only_feasible_calls(tmp_path, enabled, expected):
    project, ids = tiny_project(tmp_path, 'if (enabled) { left(); } else { right(); }')
    engine = Engine(project, ScenarioState(EmptyDatabase()))
    engine.run(ids['entry'], {'enabled': enabled})
    calls = {target for _, relation, target in engine.edges if relation == 'calls'}
    assert calls == {ids[name] for name in expected}


def test_early_return_excludes_later_calls(tmp_path):
    project, ids = tiny_project(tmp_path, 'if (enabled) { left(); return; } right();')
    engine = Engine(project, ScenarioState(EmptyDatabase()))
    engine.run(ids['entry'], {'enabled': True})
    assert (ids['entry'], 'calls', ids['left']) in engine.edges
    assert not any(target == ids['right'] for _, _, target in engine.edges)


def test_short_circuit_does_not_execute_rhs(tmp_path):
    project, ids = tiny_project(tmp_path, 'if (false && left()) { right(); }')
    engine = Engine(project, ScenarioState(EmptyDatabase()))
    engine.run(ids['entry'], {'enabled': True})
    assert not any(relation == 'calls' for _, relation, _ in engine.edges)


def test_two_calls_in_same_method_have_separate_guards(tmp_path):
    project, ids = tiny_project(tmp_path, 'if (enabled) { left(); }\nif (!enabled) { left(); }')
    engine = Engine(project, ScenarioState(EmptyDatabase()))
    engine.run(ids['entry'], {'enabled': False})
    edge = (ids['entry'], 'calls', ids['left'])
    assert edge in engine.edges
    assert len(engine.evidence[edge]) == 1


def test_lazy_exception_supplier_not_eagerly_called(tmp_path):
    project, ids = tiny_project(tmp_path, 'value.orElseThrow(() -> left());', 'Object value')
    engine = Engine(project, ScenarioState(EmptyDatabase()))
    engine.run(ids['entry'], {'value': {'optional': {'id': 'found'}}})
    assert not any(target == ids['left'] for _, _, target in engine.edges)


def test_sql_quotes_nulls_and_commas():
    rows = list(sql_rows("(1,'a,b','it\\'s',NULL),(2,'','x\\ny',3.5)"))
    assert rows == [[1, 'a,b', "it's", None], [2, '', 'x\ny', 3.5]]


def test_database_isolation(tmp_path):
    path = tmp_path / 'dump.sql'
    path.write_text("USE `ts_order`;\nCREATE TABLE `orders` (\n `id` int,\n `account_id` varchar(36)\n) ENGINE=InnoDB;\nINSERT INTO `orders` VALUES (1,'a');\n")
    original = Database(path)
    a, b = ScenarioState(original), ScenarioState(original)
    a.database.tables[('ts_order', 'orders')][0]['accountId'] = 'changed'
    assert b.database.tables[('ts_order', 'orders')][0]['accountId'] == 'a'
    assert original.tables[('ts_order', 'orders')][0]['accountId'] == 'a'


def test_optional_services_are_per_purchase():
    state = ScenarioState(EmptyDatabase())
    first = parameters('Book first-class with food and insurance and luggage of 2 kg', state, {})
    second = parameters('Book second-class without food, assurance or consignment', state, {})
    assert first['foodType'] == 1 and first['assurance'] == 1 and first['consigneeWeight'] == 2
    assert second['foodType'] == 0 and second['assurance'] == 0 and second['consigneeName'] == ''


def test_cancel_filter_is_not_cancellation():
    assert intent("Refresh the list of orders filtered by 'Cancel' status", ScenarioState(EmptyDatabase())) == ('order', 'queryOrdersForRefresh')


def test_admin_price_and_trip_details_are_not_confused():
    state = ScenarioState(EmptyDatabase())
    state.role = 'admin'
    assert intent('Add a price configuration for train type GaoTieSix', state) == ('admin-basic-info', 'addPrice')
    assert intent('Open details of the cheapest trip', state)[1] == 'getTripAllDetailInfo'


def test_viewing_regular_orders_does_not_change_booking_train():
    state = ScenarioState(EmptyDatabase())
    assert intent('Refresh orders for regular trains', state)[0] == 'order-other'
    assert intent("Refresh orders filtered by 'Paid'", state)[0] == 'order'


def test_real_scenario_is_offline_independent_of_id_and_does_not_read_gold(monkeypatch):
    import io
    import os
    import socket
    from copy import deepcopy
    from analyzer.__main__ import analyze
    from analyzer.grounding import Grounder

    root = Path(os.environ.get('TT_CHALLENGE_ROOT', Path(__file__).resolve().parents[4] / 'tt-challenge'))
    original_open = io.open

    def guarded_open(file, *args, **kwargs):
        if isinstance(file, (str, Path)) and 'gold' in Path(file).parts:
            raise AssertionError('Inference attempted to read gold')
        return original_open(file, *args, **kwargs)

    def forbidden_connection(*args, **kwargs):
        raise AssertionError('Inference attempted network access')

    monkeypatch.setattr(io, 'open', guarded_open)
    monkeypatch.setattr(socket.socket, 'connect', forbidden_connection)
    project = Project(root / 'skeleton/trainticket.json.gz', root / 'targets/trainticket')
    grounder = Grounder(project)
    database = Database(root / 'context/db-after-warmup.sql.gz')
    before = deepcopy(database.tables)
    scenario = json.loads((root / 'scenarios/S0.json').read_text())
    original, _ = analyze(project, grounder, database, scenario)
    scenario['id'] = 'renamed-input'
    renamed, _ = analyze(project, grounder, database, scenario)
    normalize = lambda answer: {(None if e['relation'] == 'executes' else e['source'], e['relation'], e['target']) for e in answer['edges']}
    assert normalize(original) == normalize(renamed)
    assert database.tables == before
    assert not project.source_errors


def test_new_account_does_not_inherit_existing_passenger_identity():
    state = ScenarioState(EmptyDatabase())
    intent('Register a new account', state)
    intent('Log in with username and password', state)
    assert state.user is U and state.account_id is U
