"""Row click argument decoding: accepted shapes and scope isolation."""

from polygraph.ui_extract.row_arguments import decode_row_event


def _scope(kind, scope, collection, row):
    return {'kind': kind, 'scope': scope, 'collection': collection, 'row': row}


def test_row_field_with_scalar_literals():
    scopes = {'record': _scope('row', 1, 'invoices', 'record')}
    assert decode_row_event('openRow(record.id, 7, 2.5, "paid", true, null)', scopes) == {
        'collection': 'invoices', 'row': 'record', 'handler': 'openRow',
        'arguments': [{'field': 'id'}, {'literal': 7}, {'literal': 2.5},
                      {'literal': 'paid'}, {'literal': True}, {'literal': None}]}


def test_deep_chain_index_and_whole_row_object():
    scopes = {'record': _scope('row', 3, 'invoices', 'record'),
              'i': _scope('index', 3, 'invoices', 'record')}
    assert decode_row_event('choose(record.client.id, i, record)', scopes) == {
        'collection': 'invoices', 'row': 'record', 'handler': 'choose',
        'arguments': [{'field': 'client.id'}, {'index': True}, {'object': True}]}


def test_index_only_call_uses_loop_owner():
    scopes = {'i': _scope('index', 5, 'rooms', 'stay')}
    assert decode_row_event('selectRow(i, 1)', scopes) == {
        'collection': 'rooms', 'row': 'stay', 'handler': 'selectRow',
        'arguments': [{'index': True}, {'literal': 1}]}
    assert decode_row_event('ping(1, "x")', dict(scopes)) is None


def test_nested_same_collection_scopes_reject_mixing():
    scopes = {'outer': _scope('row', 1, 'entries', 'outer'),
              'inner': _scope('row', 2, 'entries', 'inner')}
    assert decode_row_event('link(outer.id, inner.id)', scopes) is None
    assert decode_row_event('link(outer.id, 1)', scopes) is not None


def test_shadowed_and_unbound_identifiers_reject():
    assert decode_row_event('openRow(record.id)', {'record': None}) is None
    assert decode_row_event('openRow(ghost.id)', {}) is None
    scopes = {'record': _scope('row', 1, 'invoices', 'record')}
    assert decode_row_event('openRow(ghost.id, record.id)', scopes) is None


def test_unsupported_argument_shapes_reject_event():
    scopes = {'record': _scope('row', 1, 'invoices', 'record'),
              'i': _scope('index', 1, 'invoices', 'record')}
    for expression in (
            'openRow(this.record.id)',
            "openRow(record['id'])",
            'openRow(record.id + 1)',
            'openRow(getRecord(record.id))',
            'openRow(...record.tags)',
            'openRow(record?.id)',
            'openRow(`x${record.id}`)',
            'openRow(i.value)',
            'openRow(record.id = 5)',
            'store.openRow(record.id)',
            'openRow?.(record.id)'):
        assert decode_row_event(expression, scopes) is None, expression


def test_multiple_statements_reject_entire_event():
    scopes = {'record': _scope('row', 1, 'invoices', 'record')}
    assert decode_row_event('openRow(record.id); leak()', scopes) is None
    assert decode_row_event('openRow(record.id), leak()', scopes) is None


def test_strict_literals_accept_escapes_and_reject_unsafe_numbers():
    scopes = {'record': _scope('row', 1, 'invoices', 'record')}
    assert decode_row_event("mark(record.id, 'a\\u0041\\n', 0x10)", scopes) == {
        'collection': 'invoices', 'row': 'record', 'handler': 'mark',
        'arguments': [{'field': 'id'}, {'literal': 'aA\n'}, {'literal': 16}]}
    assert decode_row_event('mark(record.id, 9007199254740991)', scopes) is not None
    assert decode_row_event("mark(record.id, 'b\\z')", scopes) is None
    assert decode_row_event('mark(record.id, 1e999)', scopes) is None
    assert decode_row_event('mark(record.id, 0xFFFFFFFFFFFFFFFF)', scopes) is None
