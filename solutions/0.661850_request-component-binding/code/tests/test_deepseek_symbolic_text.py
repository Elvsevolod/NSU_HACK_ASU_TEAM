"""Symbolic String concatenation and http URL decomposition: sound or unknown."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzer.state import U
from analyzer.symbolic_text import concat_text, http_text_parts


def uuid_atom(symbol='uuid-1'):
    return {'__symbol__': symbol, '__type__': 'String', '__length__': 36, '__uuid_text__': True}


def url_with_id(*pieces):
    text = pieces[0]
    for piece in pieces[1:]:
        text = concat_text(text, piece)
    return text


def test_literal_only_concat_returns_str():
    assert concat_text('a', 'b') == 'ab'
    assert concat_text('', 'x') == 'x'


def test_same_expression_same_symbol_and_different_text_differs():
    atom = uuid_atom()
    left = url_with_id('http://localhost:8080/invoices/', atom, '/events')
    right = url_with_id('http://localhost:8080/invoices/', uuid_atom(), '/events')
    assert left['__symbol__'] == right['__symbol__']
    assert left['__symbol__'].startswith('text-')
    assert left['__symbol__'] != url_with_id('http://localhost:8080/invoices/', atom, '/other')['__symbol__']


def test_length_sums_known_parts_and_is_omitted_for_unknown():
    atom = uuid_atom()
    merged = concat_text('pre-', atom)
    assert merged['__length__'] == 40
    opaque = {'__symbol__': 'note-1', '__type__': 'String'}
    unknown = concat_text('pre-', opaque)
    assert '__length__' not in unknown
    assert unknown['__text_parts__'][-1] == opaque


def test_result_is_copied_and_inputs_stay_unchanged():
    atom = uuid_atom()
    base = concat_text('http://h/', atom)
    url = concat_text(base, '/e')
    base['__text_parts__'].append('changed')
    assert url['__text_parts__'] == ['http://h/', atom, '/e']
    url['__text_parts__'][1]['__mutated__'] = True
    assert '__mutated__' not in atom


def test_concat_refuses_non_string_inputs():
    assert concat_text(U, 'a') is U
    assert concat_text('a', U) is U
    assert concat_text(7, 'a') is U
    assert concat_text({'__symbol__': 'n', '__type__': 'Integer'}, 'a') is U


def test_url_segments_keep_opaque_id():
    atom = uuid_atom()
    parts = http_text_parts(url_with_id('http://localhost:8080/invoices/', atom, '/events'))
    assert parts['scheme'] == 'http' and parts['hostname'] == 'localhost'
    assert parts['segments'][0] == 'invoices'
    assert parts['segments'][1]['__symbol__'] == atom['__symbol__']
    assert parts['segments'][1]['__uuid_text__'] is True
    assert parts['segments'][2] == 'events'


def test_url_segment_mixes_literal_prefix_and_id():
    atom = uuid_atom()
    parts = http_text_parts(concat_text('https://shop.example.com/invoices/user-', atom))
    assert parts['scheme'] == 'https' and parts['hostname'] == 'shop.example.com'
    segment = parts['segments'][-1]
    assert segment['__type__'] == 'String'
    assert segment['__text_parts__'][0] == 'user-'
    assert segment['__text_parts__'][1]['__symbol__'] == atom['__symbol__']
    assert segment['__length__'] == 41


def test_url_parsing_refuses_unknown_shapes():
    atom = uuid_atom()
    arbitrary = {'__symbol__': 'note-1', '__type__': 'String'}
    short = {'__symbol__': 'uuid-2', '__type__': 'String', '__uuid_text__': True, '__length__': 12}
    assert http_text_parts('http://localhost:8080/a') is None
    assert http_text_parts(U) is None
    assert http_text_parts({'__symbol__': 's', '__type__': 'String'}) is None
    assert http_text_parts(url_with_id(atom, '/x')) is None
    assert http_text_parts(concat_text('http://h/a/', arbitrary)) is None
    assert http_text_parts(concat_text('http://h/a/', short)) is None
    assert http_text_parts(url_with_id('http://h/a/', atom, '?x=1')) is None
    assert http_text_parts(url_with_id('http://h/a/', atom, '#frag')) is None
    assert http_text_parts(url_with_id('http://h/a/', atom, ';v=1')) is None
    assert http_text_parts(url_with_id('http://h/a/', atom, '/%2F')) is None
    assert http_text_parts({'__symbol__': 's', '__type__': 'String',
                            '__text_parts__': [atom, '/x']}) is None
