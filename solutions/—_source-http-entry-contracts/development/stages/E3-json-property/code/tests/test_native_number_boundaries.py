"""Java numeric results must not inherit Python widths, scale or float precision."""
from decimal import Decimal
import pytest
from analyzer.java_exceptions import JavaThrow
from analyzer.java_numbers import int_value
from analyzer.models import construct
from analyzer.state import U
from test_boxed_heap_flow import run


def test_a_boxed_float_cannot_silently_use_binary64_precision(tmp_path):
    result,e,_=run(tmp_path,'Object value=0.1f;Float number=(Float)value;return number.doubleValue()==0.1d;')
    assert result is U and e.approximate
    assert any('float scalar promotion' in warning for warning in e.warnings)


@pytest.mark.parametrize('body,expected',[
    ('Long value=2147483648L;return value.intValue();',-2147483648),
    ('Long value=-2147483649L;return value.intValue();',2147483647),
    ('Double value=2147483648.0;return value.intValue();',2147483647),
    ('Double value=-2147483649.0;return value.intValue();',-2147483648),
    ('return new BigDecimal("-4294967297.99").intValue();',-1),
    ('return new BigDecimal("1E+100000").intValue();',0),
])
def test_number_int_value_obeys_the_receivers_numeric_contract(tmp_path,body,expected):
    result,e,_=run(tmp_path,body,schema='import java.math.BigDecimal;')
    assert result==expected and not e.approximate


@pytest.mark.parametrize('value,expected',[(float('nan'),0),(float('inf'),2147483647),
    (-float('inf'),-2147483648),(1.9,1),(-1.9,-1),(Decimal('0.001'),0),
    (Decimal('-1E+100000'),0),(Decimal('4294967297'),1)])
def test_int_value_handles_nonfinite_doubles_and_bounded_decimal_conversion(value,expected):
    assert int_value(value)==expected


@pytest.mark.parametrize('left,right,expected',[
    ('1.0','1.00',False),('1.00','1.00',True),('-0.0','0.0',True),('0','0.0',False),
])
def test_big_decimal_equals_includes_scale(tmp_path,left,right,expected):
    result,e,_=run(tmp_path,'return new BigDecimal("'+left+'").equals(new BigDecimal("'+right+'"));',schema='import java.math.BigDecimal;')
    assert result is expected and not e.approximate


def test_big_decimal_double_constructor_preserves_the_exact_binary_value(tmp_path):
    result,e,_=run(tmp_path,'return new BigDecimal(0.1).compareTo(new BigDecimal("0.1"))>0;',schema='import java.math.BigDecimal;')
    assert result is True and not e.approximate


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-float('inf')])
def test_big_decimal_nonfinite_constructor_is_a_java_failure(value):
    with pytest.raises(JavaThrow) as error:construct('BigDecimal',[value],U)
    assert error.value.value['__type__']=='NumberFormatException'


def test_big_decimal_does_not_silently_round_an_exact_operation(tmp_path):
    result,e,_=run(tmp_path,'return new BigDecimal("123456789012345678901234567890").add(new BigDecimal("1")).equals(new BigDecimal("123456789012345678901234567891"));',schema='import java.math.BigDecimal;')
    assert result is U and e.approximate
    assert any('BigDecimal operation precision' in warning for warning in e.warnings)
