from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import pytest
from analyzer.context import read_context, supported_value, context_spans
from analyzer.frontend import Frontend
from analyzer.grounding import references
from analyzer.paths import run_paths, join_states
from analyzer.project import Project
from analyzer.state import ScenarioState, U
from builders import build, INVENTORY, LIBRARY


def targets(outcome, name):
    return {t for _, rel, t in outcome['engine'].edges if rel == name}


@pytest.mark.parametrize('flag,branch', [(True, 'accept'), (False, 'reject')])
def test_inventory_source_conditions_and_constructor(tmp_path, flag, branch):
    project, db, ids = build(tmp_path, INVENTORY, rows={'reservations': []})
    paths = run_paths(project, ScenarioState(db), ids['StockController.reserve'], {'key': 'new-item', 'enabled': flag})
    assert len(paths) == 1
    executed = targets(paths[0], 'executes')
    assert ids['StockWorker.' + branch] in executed
    assert ids['StockWorker.' + ('reject' if flag else 'accept')] not in executed
    assert (ids['Reservation.<init>'] in executed) == flag
    assert len(paths[0]['state'].database.tables[('service', 'reservations')]) == int(flag)
    if flag:
        assert paths[0]['result']['key'] == 'new-item'
    assert db.tables[('service', 'reservations')] == []


def test_unknown_condition_keeps_database_paths_separate(tmp_path):
    project, db, ids = build(tmp_path, INVENTORY, rows={'reservations': []})
    paths = run_paths(project, ScenarioState(db), ids['StockController.reserve'], {'key': 'new-item', 'enabled': U})
    assert len(paths) == 2
    assert sorted(len(p['state'].database.tables[('service', 'reservations')]) for p in paths) == [0, 1]
    assert len(db.tables[('service', 'reservations')]) == 0
    joined = join_states([p['state'] for p in paths])
    assert joined.database.rows(project.nodes['res:table:service.reservations']) is None


def test_path_budget_does_not_preserve_stale_database_as_known(tmp_path):
    project, db, ids = build(tmp_path, INVENTORY, rows={'reservations': []})
    paths = run_paths(project, ScenarioState(db), ids['StockController.reserve'], {'key': 'new-item', 'enabled': U}, limit=1)
    assert len(paths) == 1 and paths[0]['approximate']
    assert paths[0]['state'].database.rows(project.nodes['res:table:service.reservations']) is None
    assert db.tables[('service', 'reservations')] == []


def test_fresh_input_keeps_type_and_does_not_invent_a_numeric_value(tmp_path):
    sources = {'Entry.java': 'class Entry { int entry(int count) { if (count > 5) { return 1; } return 2; } }'}
    project, db, ids = build(tmp_path, sources)
    state = ScenarioState(db)
    value = state.fresh_input('count', 'int')
    assert value['__type__'] == 'int' and 'fresh_unique' in value['__constraints__']
    assert state.fresh_input('count', 'int')['__symbol__'] != value['__symbol__']
    paths = run_paths(project, state, ids['Entry.entry'], {'count': value})
    assert {item['result'] for item in paths} == {1, 2}


@pytest.mark.parametrize('key,branch,result', [('b1', 'available', 'A book'), ('missing', 'missing', 'absent')])
def test_library_query_uses_provided_database(tmp_path, key, branch, result):
    project, db, ids = build(tmp_path, LIBRARY, module='catalog', rows={'books': [{'key': 'b1', 'title': 'A book'}]})
    paths = run_paths(project, ScenarioState(db), ids['BookController.lookup'], {'key': key})
    assert len(paths) == 1
    assert paths[0]['result'] == result
    assert ids['BookController.' + branch] in targets(paths[0], 'executes')
    assert 'res:table:catalog.books' in targets(paths[0], 'data')


def test_repository_date_query_uses_declared_java_field_type(tmp_path):
    sources = {
        'Event.java': '@Entity @Table(name="events") class Event { @Id String key; Date due; }',
        'EventStore.java': 'interface EventStore extends JpaRepository<Event, String> { Event findByDue(Date due); }',
        'Entry.java': 'class Entry { EventStore repository; String entry(Date due) { Event event = repository.findByDue(due); if (event == null) { return "absent"; } return event.key; } }',
    }
    project, db, ids = build(tmp_path, sources, rows={'events': [{'key': 'e1', 'due': '2030-02-03 00:00:00'}]})
    path = run_paths(project, ScenarioState(db), ids['Entry.entry'], {'due': datetime(2030, 2, 3)})[0]
    assert path['result'] == 'e1'
    assert db.tables[('service', 'events')][0]['due'] == '2030-02-03 00:00:00'


@pytest.mark.parametrize('predicate,approximate', [('b.title = ?1', False), ('b.title = ?1 or b.key = ?1', True)])
def test_explicit_repository_query_overrides_method_name(tmp_path, predicate, approximate):
    sources = dict(LIBRARY)
    sources['BookStore.java'] = sources['BookStore.java'].replace('Book findByKey', '@Query("select b from Book b where ' + predicate + '") Book findByKey')
    project, db, ids = build(tmp_path, sources, rows={'books': [{'key': 'b1', 'title': 'A book'}]})
    paths = run_paths(project, ScenarioState(db), ids['BookController.lookup'], {'key': 'A book'})
    assert all(item['approximate'] == approximate for item in paths)
    if not approximate:
        assert len(paths) == 1 and paths[0]['result'] == 'A book'
    else:
        assert any('predicate is not fully modeled' in warning for item in paths for warning in item['engine'].warnings)


def test_source_mutation_changes_calls(tmp_path):
    project, db, ids = build(tmp_path / 'before', INVENTORY, rows={'reservations': []})
    original = run_paths(project, ScenarioState(db), ids['StockController.reserve'], {'key': 'x', 'enabled': True})[0]
    changed = {k: v.replace('input.enabled', '!input.enabled') for k, v in INVENTORY.items()}
    project2, db2, ids2 = build(tmp_path / 'after', changed, rows={'reservations': []})
    other = run_paths(project2, ScenarioState(db2), ids2['StockController.reserve'], {'key': 'x', 'enabled': True})[0]
    assert ids['StockWorker.accept'] in targets(original, 'executes')
    assert ids2['StockWorker.reject'] in targets(other, 'executes')


def test_removed_source_call_is_not_recovered_from_a_stale_graph(tmp_path):
    project, db, ids = build(tmp_path, INVENTORY, rows={'reservations': []})
    before = run_paths(project, ScenarioState(db), ids['StockController.reserve'], {'key': 'x', 'enabled': True})[0]
    file = tmp_path / 'StockWorker.java'
    file.write_text(file.read_text().replace('repository.save(item);', ''))
    changed = Project(tmp_path / 'skeleton.json', tmp_path)
    after = run_paths(changed, ScenarioState(db), ids['StockController.reserve'], {'key': 'x', 'enabled': True})[0]
    assert 'res:table:service.reservations' in targets(before, 'data')
    assert not targets(after, 'data')
    assert ids['Reservation.<init>'] in targets(after, 'executes')


def test_unresolved_body_invalidates_possible_database_effects(tmp_path):
    project, db, ids = build(tmp_path, INVENTORY, rows={'reservations': []})
    project.ast.pop(ids['StockWorker.accept'])
    path = run_paths(project, ScenarioState(db), ids['StockController.reserve'], {'key': 'x', 'enabled': True})[0]
    assert path['approximate']
    assert path['state'].database.rows(project.nodes['res:table:service.reservations']) is None


def test_nested_constructor_name_uses_source_declaration(tmp_path):
    sources = {'Outer.java': 'class Outer { Inner entry() { return new Inner("value"); } static class Inner { String key; Inner(String key) { this.key = key; } } }'}
    project, db, ids = build(tmp_path, sources)
    data = json.loads((tmp_path / 'skeleton.json').read_text())
    data['nodes']['type:service:Inner']['fqn'] = 'Outer$Inner'
    (tmp_path / 'skeleton.json').write_text(json.dumps(data))
    project = Project(tmp_path / 'skeleton.json', tmp_path)
    path = run_paths(project, ScenarioState(db), ids['Outer.entry'], {})[0]
    assert path['result']['key'] == 'value'
    assert ids['Inner.<init>'] in targets(path, 'executes')


def test_consistent_business_renaming_preserves_graph(tmp_path):
    replacements = {'StockController': 'WarehouseApi', 'StockWorker': 'WarehouseLogic', 'StockRequest': 'WarehouseInput',
                    'ReservationStore': 'AllocationStore', 'Reservation': 'Allocation',
                    'reserve': 'allocate', 'accept': 'approve', 'reject': 'deny', 'reservations': 'allocations'}
    renamed = {}
    for file, source in INVENTORY.items():
        for a, b in replacements.items():
            file, source = file.replace(a, b), source.replace(a, b)
        renamed[file] = source
    p, db, ids = build(tmp_path / 'a', INVENTORY, rows={'reservations': []})
    q, db2, ids2 = build(tmp_path / 'b', renamed, module='renamed', rows={'allocations': []})
    left = run_paths(p, ScenarioState(db), ids['StockController.reserve'], {'key': 'x', 'enabled': True})[0]['engine'].edges
    right = run_paths(q, ScenarioState(db2), ids2['WarehouseApi.allocate'], {'key': 'x', 'enabled': True})[0]['engine'].edges
    normalized = set()
    for edge in right:
        def restore(value):
            value = value.replace('renamed', 'service')
            for a, b in sorted(replacements.items(), key=lambda pair: -len(pair[1])):
                value = value.replace(b, a)
            return value
        normalized.add(tuple(restore(x) for x in edge))
    assert normalized == left


def test_context_values_require_source_evidence():
    class Parser:
        def propose(self, task, payload, schema):
            def ref(quote):
                return next(key for key, value in payload['spans'].items() if quote in value[2] and value[1] != 'rule')
            return {'clock': ref('3 February 2030'),
                    'credentials': [{'parameter': 'username', 'reference': ref('alice')}],
                    'defaults': [{'parameter': 'invented', 'reference': 'invented'}], 'rules': [], 'unresolved': []}
    ctx = read_context({'date': 'The system clock is 3 February 2030', 'account': 'Use account alice / secret'}, Parser())
    assert ctx['clock'] == datetime(2030, 2, 3)
    assert ctx['facts']['username']['value'] == 'alice'
    assert 'invented' not in ctx['facts'] and ctx['unresolved']


def test_context_rule_cannot_be_used_as_an_atomic_request_default():
    class Parser:
        def propose(self, task, payload, schema):
            reference = next(key for key, value in payload['spans'].items() if value[1] == 'rule')
            return {'clock': '', 'credentials': [], 'defaults': [{'parameter': 'invalid_default', 'reference': reference}], 'rules': [], 'unresolved': []}
    context = read_context({'account': 'Use account alice / secret with the default settings.'}, Parser())
    assert not context['facts'] and any('Rejected unsupported' in item for item in context['unresolved'])


def test_context_date_is_one_atomic_value_not_separate_day_and_year():
    spans, _, _ = context_spans({'time': 'The clock is 3 February 2030; capacity is 5.'})
    assert any(span['type'] == 'date' and span['value'] == '2030-02-03' for span in spans.values())
    assert not any(span['type'] == 'number' and span['value'] in (3, 2030) for span in spans.values())
    assert any(span['type'] == 'number' and span['value'] == 5 for span in spans.values())


@pytest.mark.parametrize('day,branch', [(2, 'before'), (4, 'after')])
def test_context_clock_changes_source_date_branch(tmp_path, day, branch):
    source = {'Entry.java': '''class Entry {
       void entry() { Date now = new Date(); Date cutoff = new Date(130, 1, 3, 0, 0, 0);
          if (now.before(cutoff)) { before(); } else { after(); } }
       void before() {} void after() {}
    }'''}
    project, db, ids = build(tmp_path, source)
    state = ScenarioState(db, {'clock': datetime(2030, 2, day)})
    result = run_paths(project, state, ids['Entry.entry'], {})[0]
    executed = targets(result, 'executes')
    assert ids['Entry.' + branch] in executed
    assert ids['Entry.' + ('after' if branch == 'before' else 'before')] not in executed


@pytest.mark.parametrize('value,quote,expected', [
    ('2031-11-01', 'departing on 1 November 2031', True),
    ('2026-10-01', 'departing on 1 November 2031', False),
    (False, 'without delivery', True), ('made-up', 'add a new object', False),
    (False, 'reservation not enabled', True), (True, 'reservation not enabled', False),
])
def test_literal_grounding(value, quote, expected):
    assert supported_value(value, quote) == expected


def test_frontend_extracts_request_and_response_state(tmp_path):
    project, db, ids = build(tmp_path, LIBRARY, module='catalog', rows={'books': []})
    (tmp_path / 'screen.html').write_text('<script src="screen.js"></script><input id="key" value="b1">')
    (tmp_path / 'screen.js').write_text('''function openBook() {
      var request = new Object(); request.key = $("#key").val();
      var data = JSON.stringify(request);
      $.ajax({type: "get", url: "/books/" + request.key, data: data,
        success: function(response) { if (response.ok == 1) { sessionStorage.setItem("selected", response.item.key); } }
      });
    }''')
    frontend = Frontend(project)
    site = next(iter(frontend.sites.values()))
    assert site['handlers'] == [ids['BookController.lookup']]
    assert site['body_fields']['key'] == '$("#key").val()'
    state = ScenarioState(db)
    frontend.enter(site, state)
    assert frontend.evaluate(site['body_fields']['key'], state) == 'b1'
    frontend.apply_response(site, {'ok': 1, 'item': {'key': 'b2'}}, state)
    assert state.browser['storage']['selected'] == 'b2'
    frontend.apply_response(site, {'ok': 0, 'item': {'key': 'bad'}}, state)
    assert state.browser['storage']['selected'] == 'b2'


def test_history_references_retain_first_and_second_objects():
    refs = references([{'key': 'first'}, {'key': 'second'}], 'history[0].result')
    assert refs['history[0].result[0].key'] == 'first'
    assert refs['history[0].result[1].key'] == 'second'


def test_no_project_business_constants_in_inference():
    code = Path(__file__).parents[1]
    forbidden = ('TripId', 'OrderStatus', 'SeatClass', 'registerUser', 'fdse_microservice',
                 '111111', '2026-10-01', 'ts-travel-service', 'last_order', 'last_trip')
    for path in (code / 'analyzer').glob('*.py'):
        source = path.read_text()
        assert not any(word in source for word in forbidden), path
