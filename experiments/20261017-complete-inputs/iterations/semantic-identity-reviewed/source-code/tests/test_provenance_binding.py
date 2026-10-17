from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.engine import Engine
from analyzer.frontend import Frontend
from analyzer.provenance import contains_unknown, history_value
from analyzer.state import ScenarioState, U
from analyzer.request_semantics import filter_bindings
from analyzer.__main__ import analyze
from analyzer.paths import join_states
from builders import build, LIBRARY


def test_history_uses_entity_owner_not_string_id(tmp_path):
    sources = dict(LIBRARY)
    sources['Reader.java'] = 'class Reader { String key; String title; }'
    project, _, ids = build(tmp_path, sources)
    history = [{'action': 'Add reader', 'result': {'__type__': 'Reader', 'key': 'wrong', 'title': 'wrong'}}]
    assert history_value(project, ids['BookController.lookup'], 'key', 'Open book', history) is None
    history.append({'action': 'Add book', 'result': {'__type__': 'Book', 'key': 'b2', 'title': 'Second'}})
    assert history_value(project, ids['BookController.lookup'], 'key', 'Open book', history)[1] == 'b2'


def test_two_objects_require_explicit_selection_and_preserve_order(tmp_path):
    project, _, ids = build(tmp_path, LIBRARY)
    history = [{'action': 'List books', 'result': [{'__type__': 'Book', 'key': 'b2'}, {'__type__': 'Book', 'key': 'b1'}]}]
    assert history_value(project, ids['BookController.lookup'], 'key', 'Open book', history) is None
    assert history_value(project, ids['BookController.lookup'], 'key', 'Open second book', history)[1] == 'b1'
    assert history_value(project, ids['BookController.lookup'], 'key', 'Open third book', history) is None


def test_failed_and_untyped_results_do_not_fabricate_entities(tmp_path):
    project, _, ids = build(tmp_path, LIBRARY)
    history = [{'action': 'Add book', 'parameters': {'key': 'not-created'},
                'result': {'__type__': 'Result', 'status': 0, 'data': None}},
               {'action': 'Open something', 'result': {'key': 'untyped'}}]
    assert history_value(project, ids['BookController.lookup'], 'key', 'Open new book', history) is None
    assert contains_unknown({'payload': [U]})
    assert contains_unknown({'__json__': {'key': U}})


def test_path_and_query_aliases_require_matching_route(tmp_path):
    source = {'Library.java': '''@RestController class Library {
      @GetMapping("/library/{key}") String lookup(@PathVariable(name="key") String code,
        @RequestParam(name="limit", defaultValue="9") int maximum,
        @RequestParam(value="q", required=false) String query) { return code; }
    }'''}
    project, db, ids = build(tmp_path, source)
    engine = Engine(project, ScenarioState(db))
    target = ids['Library.lookup']
    assert engine.path_parameters(target, '/library/a%20b?limit=5&q=poetry') == {
        'key': 'a b', 'code': 'a b', 'maximum': '5', 'query': 'poetry'}
    assert engine.path_parameters(target, '/library/x')['maximum'] == '9'
    assert engine.path_parameters(target, '/library/x')['query'] is None
    assert engine.path_parameters(target, '/unrelated/x') == {}


def test_omitted_dto_defaults_are_not_defaults_for_unknown_inputs(tmp_path):
    source = {'Shelf.java': '''@RestController class Shelf {
      @PostMapping("/shelves") int add(@RequestBody ShelfInput input) { return input.capacity; }
    } class ShelfInput { int capacity; boolean locked; String label; int configured=7; }'''}
    project, db, ids = build(tmp_path, source)
    (tmp_path / 'ui.js').write_text('$.ajax({url:"/shelves",type:"POST",data:{capacity:unknown()}});')
    frontend = Frontend(project)
    site = next(iter(frontend.sites.values()))
    site['body_complete'] = True
    grounder = ContractGrounder(project, frontend, ContractIndex(project, frontend), None, {'facts': {}})
    choices, _ = grounder.step('Add shelf', ScenarioState(db))
    choice = choices[0]
    assert 'capacity' not in choice['params']
    assert choice['params']['locked'] is False
    assert choice['params']['label'] is None
    assert choice['params']['configured'] == 7
    assert choice['unresolved'] == ['Unknown input: capacity']


def test_bad_coercion_is_reported_unknown(tmp_path):
    source = {'Counter.java': '''@RestController class Counter {
      @PostMapping("/counter") int add(@RequestBody Count input) { return input.amount; }
    } class Count { int amount; }'''}
    project, db, _ = build(tmp_path, source)
    (tmp_path / 'ui.js').write_text('$.ajax({url:"/counter",type:"POST",data:{amount:"many"}});')
    frontend = Frontend(project)
    grounder = ContractGrounder(project, frontend, ContractIndex(project, frontend), None, {'facts': {}})
    choices, _ = grounder.step('Add counter', ScenarioState(db))
    assert 'amount' not in choices[0]['params']
    assert choices[0]['unresolved'] == ['Unknown input: amount']


def test_json_body_string_is_allowed_only_for_declared_body(tmp_path):
    source = {'Api.java': '''@RestController class Api {
      @PostMapping("/items") String add(@RequestBody String payload) { return payload; }
      @GetMapping("/names/{name}") String lookup(@PathVariable String name) { return name; }
    }'''}
    project, db, ids = build(tmp_path, source)
    marker = {'__json__': {'key': 'k2'}}
    assert Engine(project, ScenarioState(db)).run(ids['Api.add'], {'payload': marker}) == marker
    assert Engine(project, ScenarioState(db)).run(ids['Api.lookup'], {'name': marker}) is U


def test_filter_values_and_flags_are_derived_from_source(tmp_path):
    source = {'Shelf.java': '''@RestController class Shelf {
      @PostMapping("/shelves/query") int query(@RequestBody ShelfQuery input) { return input.state; }
    } class ShelfQuery {
      boolean active; int state;
      void enableStateQuery(int targetState) { active=true; state=targetState; }
    }
    enum ShelfState { EMPTY(11), FULL(37); private int number; ShelfState(int number) { this.number=number; } }
    enum ReaderState { FULL(88); private int number; ReaderState(int number) { this.number=number; } }
    '''}
    project, _, ids = build(tmp_path, source)
    result = filter_bindings(project, ids['Shelf.query'], "List shelves filtered by 'Full' state")
    assert {k: v for k, v, _, _ in result} == {'active': True, 'state': 37}
    assert filter_bindings(project, ids['Shelf.query'], 'List full shelves') == []
    unknown = filter_bindings(project, ids['Shelf.query'], "List shelves filtered by 'Broken' state")
    assert {k: v for k, v, _, _ in unknown} == {'active': True, 'state': U}


def test_polite_prefix_does_not_change_primary_action(tmp_path):
    source = {'Warehouse.java': '''@RestController class Warehouse {
      @PostMapping("/shipments/{id}/abort") String abortShipment(String id) { return "aborted"; }
      @PostMapping("/shipments/{id}/collect") String collectShipment(String id) { return "collected"; }
    }'''}
    project, _, ids = build(tmp_path, source)
    index = ContractIndex(project, Frontend(project))
    assert index.rank('Try to abort the collected shipment')[0][2]['entry'] == ids['Warehouse.abortShipment']
    assert index.rank('Abort the collected shipment')[0][2]['entry'] == ids['Warehouse.abortShipment']


def test_unknown_url_component_does_not_erase_known_identity(tmp_path):
    source = {'Worker.java': '''@RestController class Worker {
      @GetMapping("/items/{itemId}/readers/{readerId}") String lookup(@PathVariable String itemId,
          @PathVariable String readerId) { return readerId; }
    }'''}
    project, db, _ = build(tmp_path, source)
    (tmp_path / 'ui.js').write_text('$.ajax({url:"/items/"+unknown()+"/readers/"+sessionStorage.getItem("principal"),type:"GET"});')
    frontend = Frontend(project)
    state = ScenarioState(db)
    state.browser['storage']['principal'] = 'reader-7'
    grounder = ContractGrounder(project, frontend, ContractIndex(project, frontend), None, {'facts': {}})
    choices, _ = grounder.step('Lookup item', state)
    assert choices[0]['params'] == {'readerId': 'reader-7'}
    assert choices[0]['unresolved'] == ['Unknown input: itemId']


def test_related_type_name_does_not_turn_a_copy_id_into_a_book_id(tmp_path):
    sources = dict(LIBRARY)
    sources['BookCopy.java'] = 'class BookCopy { @Id String key; }'
    project, _, ids = build(tmp_path, sources)
    history = [{'action': 'Add book copy', 'result': {'__type__': 'BookCopy', 'key': 'copy-not-book'}}]
    assert history_value(project, ids['BookController.lookup'], 'key', 'Open book', history) is None
    assert history_value(project, ids['BookController.lookup'], 'bookId', 'Open book', history) is None


def test_declared_named_reference_can_flow_from_a_related_entity(tmp_path):
    sources = dict(LIBRARY)
    sources['Loan.java'] = 'class Loan { @Id String key; String bookId; }'
    project, _, ids = build(tmp_path, sources)
    history = [{'action': 'Open loan', 'result': {'__type__': 'Loan', 'key': 'loan-1', 'bookId': 'book-7'}}]
    assert history_value(project, ids['BookController.lookup'], 'bookId', 'Open book', history)[1] == 'book-7'
    assert history_value(project, ids['BookController.lookup'], 'key', 'Open book', history) is None


def test_history_binding_works_across_requests_without_repeating_ids(tmp_path):
    project, db, ids = build(tmp_path, LIBRARY, rows={'books': []})
    frontend = Frontend(project)
    index = ContractIndex(project, frontend)
    scenario = {'id': 'library-sequence', 'steps': [
        {'n': 1, 'action': 'Add book key "k1" title "First"'},
        {'n': 2, 'action': 'Add book key "k2" title "Second"'},
        {'n': 3, 'action': 'Open second book'}]}
    _, report = analyze(project, frontend, index, None, db, {'facts': {}, 'unresolved': []}, scenario,
                        grounder_type=ContractGrounder)
    third = report['steps'][2]['alternatives'][0]
    assert third['entry'] == ids['BookController.lookup']
    assert third['parameters']['key'] == 'k2'
    assert third['result'] == 'Second'
    assert third['bindings']['key']['source'] == 'history'
    assert db.summary() == {'service.books': 0}


def test_joined_conflicting_entity_ids_stay_unknown(tmp_path):
    project, db, ids = build(tmp_path, LIBRARY)
    left, right = ScenarioState(db), ScenarioState(db)
    left.history = [{'result': {'__type__': 'Book', 'key': 'k1'}}]
    right.history = [{'result': {'__type__': 'Book', 'key': 'k2'}}]
    merged = join_states([left, right])
    assert history_value(project, ids['BookController.lookup'], 'key', 'Open book', merged.history) is None


def test_ambiguous_filter_does_not_keep_a_false_ui_default(tmp_path):
    source = {'Shelf.java': '''@RestController class Shelf {
      @PostMapping("/shelves") int query(@RequestBody ShelfQuery input) { return 1; }
    } class ShelfQuery {
      boolean arrival; boolean departure; String arrivalDate; String departureDate;
      void enableArrivalDateQuery(String date) { arrival=true; arrivalDate=date; }
      void enableDepartureDateQuery(String date) { departure=true; departureDate=date; }
    }'''}
    project, _, ids = build(tmp_path, source)
    bindings = filter_bindings(project, ids['Shelf.query'], 'List shelves filtered by date')
    assert {key: value for key, value, _, _ in bindings} == {
        'arrival': U, 'departure': U, 'arrivalDate': U, 'departureDate': U}


def test_response_order_and_creation_order_are_distinct_evidence(tmp_path):
    project, _, ids = build(tmp_path, LIBRARY)
    a, b = {'__type__': 'Book', 'key': 'a'}, {'__type__': 'Book', 'key': 'b'}
    history = [{'action': 'Add book', 'result': a}, {'action': 'Add book', 'result': b},
               {'action': 'List books', 'result': [b, a]}, {'action': 'Open book', 'result': a}]
    lookup = ids['BookController.lookup']
    assert history_value(project, lookup, 'key', 'Open first book found', history)[1] == 'b'
    assert history_value(project, lookup, 'key', 'Open first new book', history)[1] == 'a'
    assert history_value(project, lookup, 'key', 'Open second new book', history)[1] == 'b'
    assert history_value(project, lookup, 'key', 'Open new book', history)[1] == 'b'


def test_ordinal_for_another_entity_does_not_select_a_book(tmp_path):
    project,_,ids=build(tmp_path,LIBRARY)
    history=[{'action':'List books','result':[{'__type__':'Book','key':'a'},{'__type__':'Book','key':'b'}]}]
    assert history_value(project,ids['BookController.lookup'],'key','Open book for the second reader',history) is None
    assert history_value(project,ids['BookController.lookup'],'key','Open book with second-class delivery',history) is None
    assert history_value(project,ids['BookController.lookup'],'key','Open second new book',history)[1]=='b'
