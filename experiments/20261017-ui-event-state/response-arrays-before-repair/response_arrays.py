"""Forecast of canonical identity-copy loops: ``target[i] = source[i]``."""
import tree_sitter_javascript
from tree_sitter import Language, Parser

from .jsflow import definitions_before
from .project import text

PARSER = Parser(Language(tree_sitter_javascript.language()))


def _name(node):
    return text(node) if node is not None and node.type in ('identifier', 'property_identifier') else None


def _parse_expression(source):
    if not source:
        return None
    raw = source.encode('utf-8')
    root = PARSER.parse(raw).root_node
    if root.has_error or root.named_child_count != 1:
        return None
    expression = root.named_children[0]
    if (expression.start_byte, expression.end_byte) != (0, len(raw)):
        return None
    while expression.type == 'parenthesized_expression' and expression.named_children:
        expression = expression.named_children[0]
    return expression


def _simple_read(node):
    if node.type in ('identifier', 'this'):
        return True
    if node.type == 'member_expression':
        base = node.child_by_field_name('object')
        return base is not None and _name(node.child_by_field_name('property')) is not None and _simple_read(base)
    if node.type == 'subscript_expression':
        base, index = node.child_by_field_name('object'), node.child_by_field_name('index')
        return base is not None and index is not None and index.type == 'string' and _simple_read(base)
    return False


def _expand(source, aliases, used):
    value = (source or '').strip()
    seen = set()
    while value not in seen:
        seen.add(value)
        used.add(value)
        replacement = aliases.get(value)
        if replacement is None:
            return value
        value = replacement.strip()
    return None


def _source_read(source, aliases, used):
    expression = _parse_expression(_expand(source, aliases, used))
    if expression is None or expression.type == 'this' or not _simple_read(expression):
        return None
    return text(expression)


def _length_base(source, aliases, used):
    expression = _parse_expression(_expand(source, aliases, used))
    if expression is None or expression.type != 'member_expression':
        return None
    base = expression.child_by_field_name('object')
    if base is None or _name(expression.child_by_field_name('property')) != 'length' or not _simple_read(base):
        return None
    return text(base)


def summarize_array_copy(loop, scope, initial=None):
    if loop is None or loop.type != 'for_statement':
        return None
    initializer, condition = loop.child_by_field_name('initializer'), loop.child_by_field_name('condition')
    increment, body = loop.child_by_field_name('increment'), loop.child_by_field_name('body')
    if initializer is None or condition is None or increment is None or body is None:
        return None
    if initializer.type not in ('variable_declaration', 'lexical_declaration') or body.type != 'statement_block':
        return None
    declarators = [child for child in initializer.named_children if child.type == 'variable_declarator']
    if len(declarators) != 1:
        return None
    index_name = _name(declarators[0].child_by_field_name('name'))
    if index_name is None or text(declarators[0].child_by_field_name('value')) != '0':
        return None
    if condition.type != 'binary_expression' or text(condition.child_by_field_name('operator')) != '<':
        return None
    if _name(condition.child_by_field_name('left')) != index_name:
        return None
    if increment.type != 'update_expression' or text(increment) not in (index_name + '++', '++' + index_name):
        return None
    definitions, uncertain = definitions_before(scope, loop, initial)
    aliases = dict(initial or {})
    aliases.update(definitions)
    used = set()
    right = text(condition.child_by_field_name('right'))
    condition_source = _source_read(_length_base(right, aliases, used), aliases, used)
    if condition_source is None:
        return None
    statements = [child for child in body.named_children if child.type != 'comment']
    if len(statements) != 1 or statements[0].type != 'expression_statement':
        return None
    assignment = statements[0].named_children
    if (len(assignment) != 1 or assignment[0].type != 'assignment_expression'
            or text(assignment[0].child_by_field_name('operator')) != '='):
        return None
    assignment = assignment[0]
    target = assignment.child_by_field_name('left')
    source = assignment.child_by_field_name('right')
    if target is None or source is None:
        return None
    if target.type != 'subscript_expression' or source.type != 'subscript_expression':
        return None
    target_index, source_index = target.child_by_field_name('index'), source.child_by_field_name('index')
    if _name(target_index) != index_name or _name(source_index) != index_name:
        return None
    target_member = target.child_by_field_name('object')
    if target_member is None or target_member.type != 'member_expression':
        return None
    receiver = target_member.child_by_field_name('object')
    key = _name(target_member.child_by_field_name('property'))
    if receiver is None or key is None:
        return None
    if receiver.type != 'this' and _expand(text(receiver), aliases, used) != 'this':
        return None
    if _source_read(text(source.child_by_field_name('object')), aliases, used) != condition_source:
        return None
    target_text = text(target_member)
    initialized = next((name for name in (target_text, 'this.' + key)
                        if (definitions.get(name) or '').strip() == '[]'), None)
    if initialized is None:
        return None
    used.add(initialized)
    if used & uncertain:
        return None
    return {'key': key, 'expr': condition_source, 'target': target_text,
            'line': loop.start_point[0] + 1}
