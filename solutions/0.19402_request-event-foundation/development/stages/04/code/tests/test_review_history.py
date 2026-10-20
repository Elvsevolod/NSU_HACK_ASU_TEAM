from analyzer.history_refs import references
from analyzer.provenance import history_value
from analyzer.state import U
from builders import build


SOURCE = '''class Invoice { @Id String id; } class Api {
  @GetMapping("/invoices") java.util.List<Invoice> list(){return null;}
  @GetMapping("/invoices/{invoiceId}") String show(@PathVariable String invoiceId){return invoiceId;}
}'''


def test_singleton_is_the_latest_collection(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': SOURCE})
    history = [{'entry': ids['Api.list'], 'result': [{'__type__': 'Invoice', 'id': 'A'}, {'__type__': 'Invoice', 'id': 'B'}]},
               {'entry': ids['Api.list'], 'result': [{'__type__': 'Invoice', 'id': 'C'}]}]
    assert history_value(project, ids['Api.show'], 'invoiceId', 'Open first invoice', history)[1] == 'C'


def test_empty_collection_blocks_stale_ordinal(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': SOURCE})
    history = [{'entry': ids['Api.list'], 'result': [{'__type__': 'Invoice', 'id': 'A'}, {'__type__': 'Invoice', 'id': 'B'}]},
               {'entry': ids['Api.list'], 'result': []}]
    assert history_value(project, ids['Api.show'], 'invoiceId', 'Open first invoice', history) is None


def test_later_read_does_not_replace_collection_order(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': SOURCE})
    history = [{'result': [{'__type__': 'Invoice', 'id': 'B'}, {'__type__': 'Invoice', 'id': 'A'}]},
               {'result': {'__type__': 'Invoice', 'id': 'A'}}]
    ref = history_value(project, ids['Api.show'], 'invoiceId', 'Open first invoice', history)
    assert ref == ('history[0].result[0].id', 'B')


def test_empty_wrapper_records_producer_and_element_schema(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': SOURCE})
    item = {'entry': ids['Api.list'], 'step': 2, 'result': {'data': []}}
    ref = references(project, item, 1)['collections'][0]
    assert ref['element_types'] == ('Invoice',)
    assert ref['size'] == 0 and ref['complete'] is True
    assert ref['producer'] == '2:' + ids['Api.list']


def test_unknown_producer_and_result_after_path_join_do_not_reuse_old_collection(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': SOURCE})
    history = [{'result': [{'__type__': 'Invoice', 'id': 'A'}]},
               {'entry': U, 'result': U, 'action': U, 'step': 2}]
    assert references(project, history[-1], 1)['objects'] == []
    assert history_value(project, ids['Api.show'], 'invoiceId', 'Open first invoice', history) is None
