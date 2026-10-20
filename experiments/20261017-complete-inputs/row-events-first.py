"""Direct source facts for Vue ``v-for`` rows and click handlers.

Supported subset (anything else is omitted, never guessed):

* ``v-for`` with one bare alias or ``(alias, index)``, the ``in``/``of``
  keyword, and a collection written as a single plain ASCII JavaScript
  identifier: ``v-for="(item, index) in myRows"`` / ``v-for="row in rows"``.
  Any other collection expression (member access, call, filter, parenthesis,
  literal) is unsupported: its aliases shadow matching outer aliases and
  arguments bound to it produce no fact. A malformed attribute shadows every
  identifier it mentions, so outer aliases of the same name never leak.
* ``@click`` or ``v-on:click`` whose value is exactly one call to a direct
  identifier: ``edit(item.id, 7, 'x')``. Member callees, non-calls, malformed
  JavaScript and elements carrying both click attributes at once are omitted.
* Arguments: ``alias.property`` with one direct property of the row alias, or
  a JavaScript string / finite number / boolean / ``null`` literal. Strings
  use a strict small decoder; unsupported escapes (legacy octal, unknown
  escapes, lone surrogates, unpaired sign or any other expression) reject the
  whole event rather than fabricate a value.
* A fact is emitted only when every ``field`` argument resolves to the same
  ``(row alias, collection)`` pair and the nearest v-for binding of that alias
  is a direct-identifier collection. Literal-only calls, unknown aliases and
  arguments from different rows or collections produce no fact.

Facts are source facts only: they name the loop collection, the row alias,
the handler and its argument shapes. No row is selected and no event is
claimed to happen.

Conservative HTML handling: a mismatched end tag invalidates the whole
document, and ``row_events`` then returns no facts at all. HTML void elements
never remain on the scope stack. HTML entities are decoded by HTMLParser.
"""
import math
import re
import string
from html.parser import HTMLParser

import tree_sitter_javascript
from tree_sitter import Language, Parser

_BAD = object()
_MISSING = object()

_IDENTIFIER = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
_IDENTIFIER_TOKENS = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
_VFOR = re.compile(
    r'\s*(?:\(\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*(?:,\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*)?\)'
    r'|([A-Za-z_$][A-Za-z0-9_$]*))\s+(?:in|of)\s+(.+?)\s*\Z', re.S)
_KEYWORD_COLLECTIONS = frozenset(('this', 'true', 'false', 'null'))
_VOID = frozenset(('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                   'link', 'meta', 'param', 'source', 'track', 'wbr'))
_ESCAPES = {'n': '\n', 't': '\t', 'r': '\r', 'b': '\b', 'f': '\f', 'v': '\v',
            '0': '\0', "'": "'", '"': '"', '\\': '\\', '/': '/', '`': '`'}
_HEXDIGITS = frozenset(string.hexdigits)


def _loop_scope(value):
    """Bindings declared by one v-for value: alias -> direct collection or None."""
    match = _VFOR.match(value)
    if match is None:
        return {alias: None for alias in _IDENTIFIER_TOKENS.findall(value)}
    row, index, bare = match.group(1), match.group(2), match.group(3)
    source = match.group(4)
    collection = source if _IDENTIFIER.fullmatch(source) and source not in _KEYWORD_COLLECTIONS else None
    bindings = {}
    for name, is_row in ((row, True), (index, False), (bare, True)):
        if name:
            bindings[name] = collection if is_row else None
    return bindings


def _string_literal(raw):
    if len(raw) < 2 or raw[0] not in ('"', "'") or raw[-1] != raw[0]:
        return _BAD
    body, out, index = raw[1:-1], [], 0
    while index < len(body):
        char = body[index]
        if char != '\\':
            if char in '\r\n':
                return _BAD
            out.append(char)
            index += 1
            continue
        index += 1
        if index >= len(body):
            return _BAD
        escape = body[index]
        index += 1
        if escape == '0' and index < len(body) and body[index].isdigit():
            return _BAD
        if escape in _ESCAPES:
            out.append(_ESCAPES[escape])
        elif escape == 'x':
            digits = body[index:index + 2]
            if len(digits) != 2 or any(d not in _HEXDIGITS for d in digits):
                return _BAD
            out.append(chr(int(digits, 16)))
            index += 2
        elif escape == 'u':
            if index < len(body) and body[index] == '{':
                end = body.find('}', index)
                code = body[index + 1:end] if end != -1 else ''
                if not code or len(code) > 8 or any(d not in _HEXDIGITS for d in code):
                    return _BAD
                value = int(code, 16)
                if value > 0x10FFFF or 0xD800 <= value <= 0xDFFF:
                    return _BAD
                out.append(chr(value))
                index = end + 1
            else:
                digits = body[index:index + 4]
                if len(digits) != 4 or any(d not in _HEXDIGITS for d in digits):
                    return _BAD
                value = int(digits, 16)
                if 0xD800 <= value <= 0xDFFF:
                    return _BAD
                out.append(chr(value))
                index += 4
        elif escape in '\r\n':
            if escape == '\r' and index < len(body) and body[index] == '\n':
                index += 1
        else:
            return _BAD
    return ''.join(out)


def _number_literal(raw):
    text = raw.replace('_', '')
    try:
        value = int(text, 0) if text[:2].lower() in ('0x', '0o', '0b') else float(text)
    except ValueError:
        return _BAD
    if isinstance(value, float):
        if not math.isfinite(value):
            return _BAD
        return int(value) if value.is_integer() else value
    return value


def _argument(node, raw):
    """(alias, {'field': name}) or (None, {'literal': value}) or _BAD."""
    if node.type == 'member_expression' and '?.' not in raw(node):
        obj, prop = node.child_by_field_name('object'), node.child_by_field_name('property')
        if obj is not None and obj.type == 'identifier' and prop is not None and prop.type == 'property_identifier':
            return raw(obj), {'field': raw(prop)}
        return _BAD
    if node.type == 'string':
        value = _string_literal(raw(node))
        return (None, {'literal': value}) if value is not _BAD else _BAD
    if node.type == 'number':
        value = _number_literal(raw(node))
        return (None, {'literal': value}) if value is not _BAD else _BAD
    if node.type == 'true':
        return None, {'literal': True}
    if node.type == 'false':
        return None, {'literal': False}
    if node.type == 'null':
        return None, {'literal': None}
    return _BAD


def _has_error(root):
    pending = [root]
    while pending:
        node = pending.pop()
        if node.type == 'ERROR' or getattr(node, 'is_missing', False):
            return True
        pending.extend(node.children)
    return False


def _decode_event(parser, expression):
    """Handler identifier and decoded argument list of one click value, or None."""
    source = ('(' + expression + ');').encode('utf-8')
    root = parser.parse(source).root_node
    if _has_error(root) or not root.named_children:
        return None
    node = root.named_children[0]
    if node.type != 'expression_statement' or not node.named_children:
        return None
    node = node.named_children[0]
    while node.type == 'parenthesized_expression' and node.named_children:
        node = node.named_children[0]
    if node.type != 'call_expression':
        return None
    function = node.child_by_field_name('function')
    if function is None or function.type != 'identifier':
        return None
    arguments = node.child_by_field_name('arguments')
    raw = lambda n: source[n.start_byte:n.end_byte].decode('utf-8')
    decoded = []
    for argument in arguments.named_children if arguments is not None else ():
        value = _argument(argument, raw)
        if value is _BAD:
            return None
        decoded.append(value)
    return raw(function), decoded


class _Rows(HTMLParser):
    """Collect direct click facts while tracking v-for alias scopes."""

    def __init__(self, parser):
        super().__init__(convert_charrefs=True)
        self._parser = parser
        self._frames = []
        self._facts = []
        self._valid = True

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        vfor = attributes.get('v-for')
        self._frames.append((tag, _loop_scope(vfor) if isinstance(vfor, str) else {}))
        clicks = []
        for name in ('@click', 'v-on:click'):
            value = attributes.get(name)
            if isinstance(value, str) and value.strip():
                clicks.append(value)
        if len(clicks) == 1:
            fact = self._event(clicks[0])
            if fact is not None:
                self._facts.append(fact)
        if tag in _VOID:
            self._frames.pop()

    def handle_endtag(self, tag):
        if tag in _VOID:
            return
        if self._frames and self._frames[-1][0] == tag:
            self._frames.pop()
        else:
            self._valid = False

    def _resolve(self, name):
        for _, bindings in reversed(self._frames):
            if name in bindings:
                return name, bindings[name]
        return _MISSING, None

    def _event(self, expression):
        decoded = _decode_event(self._parser, expression)
        if decoded is None:
            return None
        handler, arguments = decoded
        resolved = {self._resolve(alias) for alias, _ in arguments if alias is not None}
        if len(resolved) != 1:
            return None
        row, collection = resolved.pop()
        if collection is None:
            return None
        return {'collection': collection, 'row': row, 'handler': handler,
                'arguments': [argument for _, argument in arguments],
                'source_line': self.getpos()[0]}


def row_events(html):
    """Source facts for click handlers bound to v-for rows in one HTML string."""
    collector = _Rows(Parser(Language(tree_sitter_javascript.language())))
    collector.feed(html)
    collector.close()
    return collector._facts if collector._valid else []
