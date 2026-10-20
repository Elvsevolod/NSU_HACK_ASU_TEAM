from copy import deepcopy
from pathlib import Path
import pytest
from analyzer.__main__ import analyze
from analyzer.frontend import Frontend
from analyzer.grounding import Grounder
from analyzer.state import ScenarioState, U
from builders import build, INVENTORY, LIBRARY


class StaticRetrieval:
    def __init__(self, methods):
        self.methods = methods

    def candidates(self, action):
        return self.methods


class Proposal:
    def __init__(self, handler, bindings):
        self.handler, self.bindings = handler, bindings

    def propose(self, task, payload, schema):
        return {'hypotheses': [{'handler': self.handler, 'ui_site': '', 'reason': 'fixture request',
                                'bindings': deepcopy(self.bindings)}], 'unresolved': []}


def binding(parameter, value, quote, source='literal', reference=''):
    return {'parameter': parameter, 'value': value, 'quote': quote, 'source': source, 'reference': reference}


def test_unsupported_model_literal_is_not_used(tmp_path):
    project, db, ids = build(tmp_path, LIBRARY, rows={'books': []})
    mid = ids['BookController.lookup']
    frontend = Frontend(project)
    parser = Proposal(mid, [binding('key', 'invented', 'Open the first book')])
    grounder = Grounder(project, frontend, StaticRetrieval([mid]), parser, {'facts': {}})
    proposals, _ = grounder.step('Open the first book', ScenarioState(db))
    assert 'key' not in proposals[0]['params']
    assert any('Unsupported' in warning for warning in proposals[0]['unresolved'])


def test_model_cannot_introduce_a_handler(tmp_path):
    project, db, ids = build(tmp_path, LIBRARY, rows={'books': []})
    mid = ids['BookController.lookup']
    parser = Proposal('method:invented:MadeUp#run()', [])
    grounder = Grounder(project, Frontend(project), StaticRetrieval([mid]), parser, {'facts': {}})
    proposals, detail = grounder.step('Open book', ScenarioState(db))
    assert not proposals and detail['unresolved']


def test_context_changes_propagate_to_request(tmp_path):
    project, db, ids = build(tmp_path, LIBRARY, rows={'books': []})
    mid = ids['BookController.lookup']
    parser = Proposal(mid, [binding('key', None, '', 'context', 'chosen_key')])
    values = []
    for value in ('first', 'second'):
        context = {'facts': {'chosen_key': {'value': value, 'kind': 'default', 'quote': value}}}
        grounder = Grounder(project, Frontend(project), StaticRetrieval([mid]), parser, context)
        choices, _ = grounder.step('Open book', ScenarioState(db))
        values.append(choices[0]['params']['key'])
    assert values == ['first', 'second']


def test_history_binding_resolves_returned_object_key(tmp_path):
    project, db, ids = build(tmp_path, LIBRARY, rows={'books': []})
    mid = ids['BookController.lookup']
    parser = Proposal(mid, [binding('key', None, '', 'history', 'history[0].result[1].key')])
    grounder = Grounder(project, Frontend(project), StaticRetrieval([mid]), parser, {'facts': {}})
    state = ScenarioState(db)
    state.history.append({'step': 1, 'action': 'Read books', 'result': [{'key': 'a'}, {'key': 'b'}]})
    choices, _ = grounder.step('Open the second book', state)
    assert choices[0]['params']['key'] == 'b'


def test_boolean_literal_normalization_preserves_quoted_meaning(tmp_path):
    project, db, ids = build(tmp_path, INVENTORY, rows={'reservations': []})
    mid = ids['StockController.reserve']
    parser = Proposal(mid, [binding('enabled', 'true', 'reservation enabled')])
    grounder = Grounder(project, Frontend(project), StaticRetrieval([mid]), parser, {'facts': {}})
    choices, _ = grounder.step('Reserve with reservation enabled', ScenarioState(db))
    assert choices[0]['params']['enabled'] is True


@pytest.mark.parametrize('word,value', [('enabled', True), ('disabled', False), ('not enabled', False)])
def test_boolean_normalization_records_the_actual_input_phrase(tmp_path, word, value):
    project, db, ids = build(tmp_path, INVENTORY, rows={'reservations': []})
    mid = ids['StockController.reserve']
    parser = Proposal(mid, [binding('enabled', value, str(value).lower())])
    grounder = Grounder(project, Frontend(project), StaticRetrieval([mid]), parser, {'facts': {}})
    choices, _ = grounder.step('Reserve with reservation ' + word, ScenarioState(db))
    assert choices[0]['params']['enabled'] is value
    assert choices[0]['bindings']['enabled']['quote'] == word


def test_prepared_language_template_keeps_actual_reference_across_states(tmp_path):
    project, db, ids = build(tmp_path, LIBRARY, rows={'books': []})
    mid = ids['BookController.lookup']

    class Parser:
        calls = 0
        def propose(self, task, payload, schema):
            self.calls += 1
            ref = next(alias for alias, item in payload['references'].items()
                       if item['path'] == 'history[0].result.key')
            return {'hypotheses': [{'handler': 'H0', 'ui_site': '', 'reason': 'Prior response reference',
                                   'bindings': [binding('key', None, '', 'history', ref)]}], 'unresolved': []}

    parser = Parser()
    grounder = Grounder(project, Frontend(project), StaticRetrieval([mid]), parser, {'facts': {}})
    state = ScenarioState(db)
    state.history.append({'step': 1, 'action': 'Earlier query', 'result': {'key': 'first'}})
    proposals, selection = grounder.step('Read the previously selected book', state)
    altered = deepcopy(state)
    altered.browser['form']['extra'] = 'different ordering of references'
    altered.history[0]['result']['key'] = 'second'
    other, _ = grounder.step('Read the previously selected book', altered, prepared_proposal=selection['proposal'])
    assert proposals[0]['params']['key'] == 'first'
    assert other[0]['params']['key'] == 'second'
    assert parser.calls == 1


def test_database_reference_identity_is_stable_when_rows_reorder(tmp_path):
    project, db, ids = build(tmp_path, LIBRARY, rows={'books': [
        {'key': 'b1', 'title': 'First'}, {'key': 'b2', 'title': 'Second'}]})
    mid = ids['BookController.lookup']
    class Parser:
        def propose(self, task, payload, schema):
            ref = next(alias for alias, item in payload['references'].items()
                       if item['path'].startswith('database:') and item['path'].endswith('.key') and item['value'] == 'b2')
            return {'hypotheses': [{'handler': 'H0', 'ui_site': '', 'reason': 'Provided record',
                                   'bindings': [binding('key', None, '', 'database', ref)]}], 'unresolved': []}
    grounder = Grounder(project, Frontend(project), StaticRetrieval([mid]), Parser(), {'facts': {}})
    state = ScenarioState(db)
    _, selection = grounder.step('Read the selected book', state)
    state.database.tables[('service', 'books')].reverse()
    choices, _ = grounder.step('Read the selected book', state, prepared_proposal=selection['proposal'])
    assert choices[0]['params']['key'] == 'b2'


def test_inference_is_id_independent_and_does_not_modify_initial_db(tmp_path):
    project, db, ids = build(tmp_path, INVENTORY, rows={'reservations': []})
    mid = ids['StockController.reserve']
    parser = Proposal(mid, [binding('key', 'item', 'item'), binding('enabled', True, 'enabled')])
    retrieval = StaticRetrieval([mid])
    context = {'facts': {}, 'clock': None, 'unresolved': []}
    scenario = {'id': 'alpha', 'steps': [{'n': 1, 'action': 'Reserve item with reservation enabled'}]}
    a, detail = analyze(project, Frontend(project), retrieval, parser, db, context, scenario)
    scenario['id'] = 'arbitrary-name'
    b, _ = analyze(project, Frontend(project), retrieval, parser, db, context, scenario)
    normalize = lambda answer: {(None if e['relation'] == 'executes' else e['source'], e['relation'], e['target']) for e in answer['edges']}
    assert normalize(a) == normalize(b)
    assert db.tables[('service', 'reservations')] == []
    assert len(detail['confirmed']) == len(a['edges'])
    assert not detail['possible']


def test_unknown_input_is_reported_and_paths_are_exported_as_possible(tmp_path):
    project, db, ids = build(tmp_path, INVENTORY, rows={'reservations': []})
    mid = ids['StockController.reserve']
    parser = Proposal(mid, [binding('key', 'item', 'item')])
    scenario = {'id': 'arbitrary', 'steps': [{'n': 1, 'action': 'Reserve item'}]}
    answer, report = analyze(project, Frontend(project), StaticRetrieval([mid]), parser, db,
                             {'facts': {}, 'clock': None, 'unresolved': []}, scenario)
    assert report['analysis_status'] == 'partial'
    assert report['possible']
    assert {e['target'] for e in answer['edges']} >= {ids['StockWorker.accept'], ids['StockWorker.reject']}


def test_unknown_guards_do_not_mix_mutually_exclusive_paths(tmp_path):
    from analyzer.paths import run_paths
    sources = {'Logic.java': '''class Logic {
       void entry(boolean enabled) { if (enabled) { return; } after(); }
       void after() {}
    }'''}
    p, db, ids = build(tmp_path, sources)
    paths = run_paths(p, ScenarioState(db), ids['Logic.entry'], {'enabled': U})
    assert len(paths) == 2
    assert sorted(ids['Logic.after'] in {e[2] for e in item['engine'].edges} for item in paths) == [False, True]


def test_embedded_id_and_enum_are_derived_from_declarations(tmp_path):
    sources = {
        'Document.java': '@Entity @Table(name="documents") class Document { @EmbeddedId DocumentKey key; String title; }',
        'DocumentKey.java': '@Embeddable class DocumentKey { Medium medium; long serial; }',
        'Medium.java': 'enum Medium { PAPER, ELECTRONIC }',
    }
    project, db, _ = build(tmp_path, sources, module='archive', rows={'documents': [{'medium': 1, 'serial': 42, 'title': 'Sample'}]})
    record = project.materialize(db, 'res:table:archive.documents', db.tables[('archive', 'documents')][0])
    assert record['key']['medium']['__enum__'] == 'Medium.ELECTRONIC'
    assert record['key']['serial'] == 42
