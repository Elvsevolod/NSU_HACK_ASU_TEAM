"""The ASCII slice of java.lang.Integer.parseInt, with explicit failure."""
from .state import U
from .java_exceptions import JavaThrow


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
