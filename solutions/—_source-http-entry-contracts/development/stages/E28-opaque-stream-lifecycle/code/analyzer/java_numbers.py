"""Bounded Java numeric conversions, independent of Python integer widths."""
from decimal import Decimal
import math
from .state import U
from .java_exceptions import JavaThrow


def int_value(value):
    """Number.intValue: integral/decimal low bits versus double saturation."""
    if type(value) is float:
        if math.isnan(value):return 0
        if value>=2147483647:return 2147483647
        if value<=-2147483648:return -2147483648
        return int(value)
    if isinstance(value,Decimal):
        if not value.is_finite():return U
        sign,digits,exponent=value.as_tuple()
        if exponent<0:digits=digits[:max(0,len(digits)+exponent)]
        low=0
        for digit in digits:low=(low*10+digit)%(1<<32)
        if exponent>0:low=low*pow(10,exponent,1<<32)%(1<<32)
        value=-low if sign else low
    if type(value) is int:return (value+(1<<31))%(1<<32)-(1<<31)
    return U


def parse_integer(value, radix=10):
    if value is U or radix is U:
        return U
    if value is None:
        raise JavaThrow({'__type__':'NumberFormatException'})
    if not isinstance(value,str) or type(radix) is not int:
        return U
    if not 2 <= radix <= 36:
        raise JavaThrow({'__type__':'NumberFormatException'})
    if not value.isascii():
        return U
    negative=value.startswith('-')
    digits=value[1:] if value.startswith(('-','+')) else value
    if not digits:
        raise JavaThrow({'__type__':'NumberFormatException'})
    limit=2147483648 if negative else 2147483647
    result=0
    for char in digits.lower():
        digit=ord(char)-ord('0') if '0'<=char<='9' else ord(char)-ord('a')+10 if 'a'<=char<='z' else -1
        if not 0 <= digit < radix:
            raise JavaThrow({'__type__':'NumberFormatException'})
        result=result*radix+digit
        if result>limit:
            raise JavaThrow({'__type__':'NumberFormatException'})
    return -result if negative else result
