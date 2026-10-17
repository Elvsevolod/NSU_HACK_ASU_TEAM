import math

import pytest

from polygraph.ui_extract.native import JavaScriptError, NativeJS, NativeUnavailable
from polygraph.ui_extract.state import JS_UNDEFINED, U, SymbolicValue


@pytest.fixture
def js():
    return NativeJS()


def test_number_rounding_and_negative_zero_follow_ecmascript(js):
    assert js.run('+', 9007199254740992, 1) == 9007199254740992
    assert js.run('===', js.run('+', 9007199254740992, 1), 9007199254740992) is True
    assert math.copysign(1, js.run('/', 0, -1)) == -1
    assert js.run('/', 1, -0.0) == -math.inf
    assert js.run('truth', math.nan) is False
    assert js.run('truth', math.inf) is True
    assert js.run('===', math.nan, math.nan) is False


def test_equality_coercion_and_truth_are_not_python_rules(js):
    assert js.run('==', '', 0) is True
    assert js.run('===', '', 0) is False
    assert js.run('==', None, JS_UNDEFINED) is True
    assert js.run('===', None, JS_UNDEFINED) is False
    assert js.run('truth', []) is True
    assert js.run('truth', {}) is True
    assert js.run('==', [1], 1) is True


def test_utf16_strings_and_parseint_are_evaluated_by_native_engine(js):
    assert js.run('charAt', '😀', 0) == '\ud83d'
    assert js.run('substring', '😀abc', 2, 4) == 'ab'
    assert js.run('parseInt', '12px') == 12
    assert js.run('parseInt', '0xff') == 255
    assert js.run('parseInt', '10', 2) == 2
    assert js.literal("'escaped\\n'", 'string') == 'escaped\n'
    assert js.literal('0x10', 'number') == 16


def test_stringify_omission_array_null_and_number_text_are_standard(js):
    payload = {'missing': JS_UNDEFINED, 'null': None, 'values': [JS_UNDEFINED, math.nan, math.inf], 'id': 9007199254740993}
    assert js.run('JSON.stringify', payload) == '{"null":null,"values":[null,null,null],"id":9007199254740992}'
    assert js.run('JSON.stringify', JS_UNDEFINED) is JS_UNDEFINED
    assert js.run('JSON.stringify', {'10': 'ten', '2': 'two', 'first': 1}) == '{"2":"two","10":"ten","first":1}'


def test_metadata_shaped_application_json_is_plain_data(js):
    value = {'__symbol__': 'invented-id', '__type__': 'String', '__proto__': {'polluted': True}}
    assert js.run('JSON.parse', js.run('JSON.stringify', value)) == value
    assert js.context.eval('Object.prototype.polluted') is None
    assert js.run('String', value) == '[object Object]'


def test_abstract_values_never_become_concrete_native_tokens(js):
    symbol = SymbolicValue({'__symbol__': 'opaque', '__type__': 'String'})
    before = js.calls
    assert js.run('==', symbol, 'opaque') is U
    assert js.run('JSON.stringify', {'value': symbol}) is U
    assert js.run('+', U, 1) is U
    assert js.calls == before


def test_native_json_boundary_does_not_invent_object_reference_identity(js):
    value={'x':1}
    assert js.run('===',value,value) is U


@pytest.mark.parametrize('raw,kind', [('(function(){globalThis.changed=true;return 1;})()', 'number'), ('1;globalThis.changed=true', 'number'), ('fetch("https://example.test")', 'string')])
def test_literal_api_cannot_evaluate_an_application_expression(js, raw, kind):
    assert js.literal(raw, kind) is U
    assert js.context.eval('globalThis.changed') is None
    assert js.context.eval('typeof process+":"+typeof require+":"+typeof fetch') == 'undefined:undefined:undefined'


def test_known_js_exception_is_distinct_from_unknown(js):
    with pytest.raises(JavaScriptError, match='SyntaxError'):
        js.run('JSON.parse', '{invalid')
    assert js.run('+', 2, 3) == 5


def test_memory_and_time_budget_failures_are_reported():
    js = NativeJS(memory_bytes=256 * 1024)
    with pytest.raises(NativeUnavailable):
        js.run('split', 'x' * 500000, '')
