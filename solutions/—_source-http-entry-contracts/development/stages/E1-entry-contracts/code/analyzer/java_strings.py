"""Java String contracts for the explicitly supported regex subset."""
import re

from .state import U
from .java_exceptions import JavaThrow


def is_blank(value):
    # Character.isWhitespace excludes nonbreaking spaces, unlike Python strip.
    return all(char in '\t\n\v\f\r\x1c\x1d\x1e\x1f ' or
               '\u2000' <= char <= '\u2006' or '\u2008' <= char <= '\u200a' or
               char in '\u1680\u2028\u2029\u205f\u3000' for char in value)


def split(value, pattern, limit=0, issue=lambda message: None):
    if not isinstance(pattern, str) or type(limit) is not int:
        issue('String.split regex or limit is unknown')
        return U
    # Do not silently interpret Java-specific syntax with Python regex rules.
    if re.search(r'\\[pPkKQERXGZzuhHvV]|\(\?|\+\+|\*\+|\?\+|\}\+|&&', pattern):
        issue('String.split Java regex feature is outside the supported subset')
        return U
    try:
        expression = re.compile(pattern, re.ASCII)
    except re.error:
        raise JavaThrow({'__type__': 'PatternSyntaxException'}) from None
    if limit == 1 or value == '':
        return [value]
    parts, start = [], 0
    for match in expression.finditer(value):
        if match.start() == match.end() == 0:
            continue
        if limit > 0 and len(parts) == limit - 1:
            break
        parts.append(value[start:match.start()])
        start = match.end()
    if not parts and start == 0:
        return [value]
    parts.append(value[start:])
    if limit == 0:
        while parts and parts[-1] == '':
            parts.pop()
    return parts
