"""Symbolic String concatenation and http(s) URL decomposition.

concat_text joins Python str literals and String symbols (a dict with
__symbol__ and __type__ String/java.lang.String). Prior __text_parts__ lists
are flattened, adjacent literals merge, opaque atoms are preserved by
deepcopy, and a literal-only expression collapses back to str. A composite's
__symbol__ is a sha256 of the canonical part list, so equal expressions share
one id and no concrete text is invented; __length__ appears only when every
part length is known.

http_text_parts reads a composite String symbol whose first literal carries a
complete http(s) authority and the start of the path. It returns scheme,
hostname and slash segments, keeping opaque uuid text atoms in place and inner
empty segments; leading and trailing empties are dropped like the existing
route indexing. Query, fragment, matrix, encoded slash, opaque authority and
variable text that is not known uuid text are refused.
"""
import hashlib
import json
import re
from copy import deepcopy
from urllib.parse import urlsplit

from .state import U

_STRING_TYPES = ('String', 'java.lang.String')
_ABSOLUTE = re.compile(r'(https?)://([^/?#;]+)(/.*)', re.S | re.I)
_ENCODED_SLASH = re.compile(r'%2f', re.I)


def _string_symbol(value):
    return (isinstance(value, dict) and isinstance(value.get('__symbol__'), str)
            and value.get('__type__') in _STRING_TYPES)


def _parts(value):
    """Deep-copied parts of a String value; a prior composite is flattened."""
    if isinstance(value, str):
        return [value]
    if not _string_symbol(value):
        return None
    inner = value.get('__text_parts__')
    if isinstance(inner, list) and all(isinstance(part, str) or _string_symbol(part) for part in inner):
        return [deepcopy(part) for part in inner]
    return [deepcopy(value)]


def _digest(parts):
    canonical = json.dumps(parts, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def concat_text(left, right):
    """Concatenate String literals/symbols; any other input stays unknown."""
    left, right = _parts(left), _parts(right)
    if left is None or right is None:
        return U
    parts = []
    for part in left + right:
        if isinstance(part,str) and not part:
            continue
        if isinstance(part, str) and parts and isinstance(parts[-1], str):
            parts[-1] += part
        else:
            parts.append(part)
    if all(isinstance(part, str) for part in parts):
        return ''.join(parts)
    if len(parts)==1:return deepcopy(parts[0])
    composite = {'__symbol__': 'text-' + _digest(parts), '__type__': 'String', '__text_parts__': parts}
    lengths = [len(part.encode('utf-16-le',errors='surrogatepass'))//2 if isinstance(part,str) else part.get('__length__') for part in parts]
    if all(isinstance(length, int) and not isinstance(length, bool) for length in lengths):
        composite['__length__'] = sum(lengths)
    return composite


def _uuid_text(part):
    return (_string_symbol(part) and part.get('__uuid_text__') is True
            and isinstance(part.get('__length__'), int) and not isinstance(part.get('__length__'), bool)
            and part['__length__'] == 36 and '__text_parts__' not in part)


def _date_text(part):
    return _string_symbol(part) and part.get('__java_date_text__') is True and '__text_parts__' not in part


def _malformed(literal):
    return any(char.isspace() or char in '?#;' for char in literal) or _ENCODED_SLASH.search(literal) is not None


def _segment(parts):
    if not parts:
        return ''
    if len(parts) == 1:
        return parts[0]
    result = parts[0]
    for part in parts[1:]:
        result = concat_text(result, part)
    return result


def http_text_parts(value):
    """Scheme, hostname and path segments of a symbolic http(s) URL, else None."""
    parts = value.get('__text_parts__') if isinstance(value, dict) else None
    if not (_string_symbol(value) and isinstance(parts, list) and parts):
        return None
    head, tail = parts[0], parts[1:]
    if not isinstance(head, str) or not all(isinstance(part, str) or _uuid_text(part) or _date_text(part) for part in tail):
        return None
    match = _ABSOLUTE.fullmatch(head)
    if match is None or any(_malformed(part) for part in [head] + [p for p in tail if isinstance(p, str)]):
        return None
    try:
        hostname = urlsplit(head).hostname
    except ValueError:
        return None
    if not hostname:
        return None
    segments, current = [], []
    for part in [match.group(3)] + tail:
        if isinstance(part, str):
            for index, token in enumerate(part.split('/')):
                if index:
                    segments.append(current)
                    current = []
                if token:
                    current.append(token)
        else:
            current.append(deepcopy(part))
    segments.append(current)
    while segments and not segments[0]:
        segments.pop(0)
    while segments and not segments[-1]:
        segments.pop()
    return {'scheme': match.group(1).lower(), 'hostname': hostname,
            'segments': [_segment(segment) for segment in segments]}
