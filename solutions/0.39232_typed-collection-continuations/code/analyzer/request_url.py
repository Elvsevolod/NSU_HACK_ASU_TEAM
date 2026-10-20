"""Independent URI components, with explicit completeness of the query.

Opaque text is never assumed delimiter-free. Only proven UUID/date text can
occupy a path segment; an opaque query suffix does not erase the known path.
Query occurrences stay ordered and repeated names are retained.
"""
from copy import deepcopy
import re
from urllib.parse import urlsplit, unquote, unquote_plus, quote

from .state import U
from .symbolic_text import concat_text, _uuid_text, _date_text


def request_address(value):
    parts = [value] if isinstance(value, str) else value.get('__text_parts__') if type(value) is dict else None
    if not isinstance(parts, list) or not parts or not isinstance(parts[0], str):
        return None
    marker = '__uri_atom_'
    while any(marker in part for part in parts if isinstance(part, str)):
        marker += '_'
    atoms, rendered, unsafe = {}, '', None
    for part in parts:
        if isinstance(part, str):
            rendered += part
        else:
            token = marker + str(len(atoms)) + '__'
            atoms[token] = deepcopy(part)
            if unsafe is None and not (_uuid_text(part) or _date_text(part) or
                                       type(part) is dict and part.get('__uri_query_value__')):
                unsafe = len(rendered)
            rendered += token
    # Literal fragments (including their opaque suffix) do not travel to HTTP.
    fragment = rendered.find('#')
    if fragment >= 0 and (unsafe is None or fragment < unsafe):
        rendered = rendered[:fragment]
        unsafe = None
    query_complete = unsafe is None
    path_complete = unsafe is None or '?' in rendered[:unsafe]
    if unsafe is not None:
        rendered = rendered[:unsafe]
    try:
        parsed = urlsplit(rendered)
        host = parsed.hostname
        port = parsed.port
        if parsed.scheme and parsed.scheme not in ('http', 'https'):
            return None
        if parsed.netloc and (not host or marker in parsed.netloc):
            return None
        if not parsed.netloc and not rendered.startswith('/'):
            return None
    except ValueError:
        return None

    def decode(raw, query=False):
        # A malformed escape is not evidence for a concrete server value.
        if re.search(r'%(?![0-9a-fA-F]{2})', raw):
            return U
        result = ''
        for piece in re.split('(' + re.escape(marker) + r'\d+__)', raw):
            if piece in atoms:
                decoded = U if atoms[piece].get('__uri_query_value__') else atoms[piece]
            else:
                try:
                    decoded = (unquote_plus if query else unquote)(piece, errors='strict')
                except UnicodeError:
                    return U
            result = concat_text(result, decoded)
        return result

    segments = parsed.path.strip('/').split('/') if parsed.path.strip('/') else []
    # Matrix parameters and encoded separators depend on servlet/path policy.
    if not path_complete or ';' in parsed.path or '\\' in parsed.path or re.search(r'%2f|%5c|%3b', parsed.path, re.I):
        segments = None
    else:
        segments = [decode(segment) for segment in segments]
        if any(segment is U for segment in segments):
            segments = None
    query = {}
    tokens = parsed.query.split('&') if parsed.query else []
    for i, token in enumerate(tokens):
        if not token:
            continue
        name, _, raw = token.partition('=')
        name = decode(name, True)
        if not isinstance(name, str):
            query_complete = False
            continue
        item = U if unsafe is not None and i == len(tokens)-1 else decode(raw, True)
        query.setdefault(name, []).append(item)
    return {'scheme':parsed.scheme or None,'hostname': host,'port':port, 'segments': segments, 'query': query,
            'query_complete': query_complete}


def client_template(url, lookup, unknown):
    if isinstance(url,str):
        return _client_template(url,lookup,unknown)
    parts=url.get('__text_parts__') if type(url) is dict else None
    if not isinstance(parts,list):return U
    marker='__client_uri_atom_'
    while any(marker in part for part in parts if isinstance(part,str)):marker+='_'
    atoms={};rendered=''
    for part in parts:
        if isinstance(part,str):rendered+=part
        else:
            token=marker+str(len(atoms))+'__';atoms[token]=part;rendered+=token
    expanded=_client_template(rendered,lookup,unknown)
    chunks=[expanded] if isinstance(expanded,str) else expanded.get('__text_parts__') if type(expanded) is dict else None
    if chunks is None:return U
    result=''
    for chunk in chunks:
        if isinstance(chunk,str):
            for piece in re.split('('+re.escape(marker)+r'\d+__)',chunk):
                result=concat_text(result,atoms.get(piece,piece))
        else:result=concat_text(result,chunk)
    return result


def _client_template(url, lookup, unknown):
    """Default RestTemplate String overload (URI_COMPONENT, parsePath=true).

    Template structure is parsed before expansion. Known variables are encoded
    within their component, including percent literals. Unknown query values
    cannot introduce new parameter names; unknown path values stay unresolved
    because encoded separators may be rejected by the server.
    """
    try:
        parsed = urlsplit(url)
        if not parsed.hostname or parsed.scheme not in ('http', 'https') or '{' in parsed.netloc:
            return U
    except ValueError:
        return U

    def component(raw, safe, query=False):
        result, offset = '', 0
        for match in re.finditer(r'\{([A-Za-z_]\w*)\}', raw):
            result = concat_text(result, quote(raw[offset:match.start()], safe=safe))
            value = lookup(match[1])
            if type(value) is bool:
                value = str(value).lower()
            if type(value) is int:
                value = str(value)
            if isinstance(value, str):
                value = quote(value, safe=safe)
            elif not _uuid_text(value):
                value = unknown()
                if query:
                    value['__uri_query_value__'] = True
            result = concat_text(result, value)
            offset = match.end()
        return concat_text(result, quote(raw[offset:], safe=safe))

    # These are RFC 3986 component characters, not application-specific routes.
    path_safe = ":@!$&'()*+,;="
    query_safe = ":@!$'()*+,;/?"
    result = parsed.scheme + '://' + parsed.netloc
    for i, segment in enumerate(parsed.path.split('/')):
        result = concat_text(result, '/' if i else '')
        result = concat_text(result, component(segment, path_safe))
    if '?' in url.split('#', 1)[0]:
        result = concat_text(result, '?')
        for i, pair in enumerate(parsed.query.split('&')):
            name, separator, value = pair.partition('=')
            result = concat_text(result, '&' if i else '')
            result = concat_text(result, component(name, query_safe))
            if separator:
                result = concat_text(result, '=')
                result = concat_text(result, component(value, query_safe, True))
    # Fragments are expanded/validated by the client but not sent in HTTP.
    if parsed.fragment:component(parsed.fragment, query_safe)
    return result
