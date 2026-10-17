"""Click handler arguments for one Vue row scope, without HTML or DOM input.

``decode_row_event`` parses one click expression and returns the row owner
plus decoded arguments, or ``None`` when anything is unsupported or
ambiguous. The caller supplies the visible identifier scopes; identifiers
are never resolved here.

Accepted argument shapes (everything else rejects the whole event):

* ``row.property`` / ``row.property.chain``: static member chain rooted in
  an identifier bound to a ``row`` scope -> ``{'field': 'property.chain'}``.
* the whole ``row`` identifier -> ``{'object': True}``.
* the whole ``index`` identifier -> ``{'index': True}``.
* JavaScript string / finite safe number / boolean / null literals decoded
  by the strict decoders of ``row_events`` -> ``{'literal': value}``.

Rejected: unbound or shadowed identifiers, member chains rooted anywhere
else, computed subscripts, calls, spreads, assignments and other side
effects, optional chains, optional calls, template strings, malformed
JavaScript and more than one program statement.

At least one ``row``/``index`` argument is required, and every non-literal
argument must resolve to the same ``scope`` id; different scopes reject the
event even when collection and row alias match. A ``None`` scope entry or a
missing key shadows the identifier.
"""
import tree_sitter_javascript
from tree_sitter import Language, Parser

from .row_events import _BAD, _has_error, _number_literal, _string_literal

_PARSER = Parser(Language(tree_sitter_javascript.language()))


def _scope_entry(scopes, name, kinds):
    entry = scopes.get(name)
    if not isinstance(entry, dict) or entry.get('kind') not in kinds:
        return None
    if entry.get('scope') is None:
        return None
    return entry


def _argument(node, raw, source, scopes):
    if node.type == 'identifier':
        entry = _scope_entry(scopes, raw(node), ('row', 'index'))
        if entry is None:
            return _BAD
        if entry['kind'] == 'index':
            return 'index', entry
        return 'row', (), entry
    if node.type == 'member_expression':
        parts, current = [], node
        while current.type == 'member_expression':
            obj = current.child_by_field_name('object')
            prop = current.child_by_field_name('property')
            if obj is None or prop is None or prop.type != 'property_identifier':
                return _BAD
            between = source[obj.end_byte:prop.start_byte].decode('utf-8', 'replace')
            if between.strip() != '.':
                return _BAD
            parts.append(raw(prop))
            current = obj
        if current.type != 'identifier' or not parts:
            return _BAD
        entry = _scope_entry(scopes, raw(current), ('row',))
        if entry is None:
            return _BAD
        parts.reverse()
        return 'row', tuple(parts), entry
    if node.type == 'string':
        value = _string_literal(raw(node))
        return ('literal', value) if value is not _BAD else _BAD
    if node.type == 'number':
        value = _number_literal(raw(node))
        return ('literal', value) if value is not _BAD else _BAD
    if node.type == 'true':
        return 'literal', True
    if node.type == 'false':
        return 'literal', False
    if node.type == 'null':
        return 'literal', None
    return _BAD


def decode_row_event(expression, scopes):
    """Decoded click facts for one expression, or ``None`` when rejected."""
    source = ('(' + expression + ');').encode('utf-8')
    root = _PARSER.parse(source).root_node
    if _has_error(root) or len(root.named_children) != 1:
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
    arguments = node.child_by_field_name('arguments')
    if function is None or function.type != 'identifier' or arguments is None:
        return None
    between = source[function.end_byte:arguments.start_byte].decode('utf-8', 'replace')
    if between.strip():
        return None

    def raw(node):
        return source[node.start_byte:node.end_byte].decode('utf-8')

    result, scope_ids, owner = [], set(), None
    for argument in arguments.named_children:
        value = _argument(argument, raw, source, scopes)
        if value is _BAD:
            return None
        if value[0] == 'literal':
            result.append({'literal': value[1]})
            continue
        if value[0] == 'index':
            result.append({'index': True})
        elif value[1]:
            result.append({'field': '.'.join(value[1])})
        else:
            result.append({'object': True})
        scope_ids.add(value[-1]['scope'])
        owner = value[-1]
    if len(scope_ids) != 1:
        return None
    return {'collection': owner['collection'], 'row': owner['row'],
            'handler': raw(function), 'arguments': result}
