"""Bounded expression propagation within a JavaScript request's lexical scope."""
import json

from .project import text


FUNCTIONS = {'function_expression', 'function_declaration', 'method_definition', 'arrow_function'}


def definitions_before(scope, limit, initial=None):
    """Conditional writes become expressions, never the last visited branch's value.

    Only assignments are modeled here. Loops, exception handlers and computed
    property writes invalidate their affected values. Nested functions are separate.
    """
    values = dict(initial or {})
    uncertain = set()

    def assign(node, target, invalid=False):
        lhs = node.child_by_field_name('name') if node.type == 'variable_declarator' else node.child_by_field_name('left')
        rhs = node.child_by_field_name('value') if node.type == 'variable_declarator' else node.child_by_field_name('right')
        key = text(lhs)
        if not key:
            return
        if lhs.type == 'subscript_expression':
            owner = text(lhs.child_by_field_name('object'))
            uncertain.add(owner)
            for name in list(target):
                if name == owner or name.startswith(owner + '.'):
                    target[name] = 'undefined'
            return
        if lhs.type == 'identifier':
            for name in list(target):
                if name.startswith(key + '.'):
                    target.pop(name)
        elif lhs.type == 'member_expression':
            owner = text(lhs.child_by_field_name('object'))
            if target.get(owner, '').lstrip().startswith('{') and target[owner] != '{}':
                target[owner] = 'undefined'
                uncertain.add(owner)
        target[key] = 'undefined' if invalid else text(rhs) or 'undefined'

    def visit(node, target, invalid=False):
        if node is None or node.start_byte >= limit.start_byte or node.type in FUNCTIONS:
            return
        if node.type in ('variable_declarator', 'assignment_expression'):
            assign(node, target, invalid)
            return
        if node.type == 'if_statement' and not invalid:
            yes, no = node.child_by_field_name('consequence'), node.child_by_field_name('alternative')
            # The request itself establishes which enclosing branch was entered.
            for branch in (yes, no):
                if branch is not None and branch.start_byte <= limit.start_byte < branch.end_byte:
                    visit(branch, target)
                    return
            left, right = dict(target), dict(target)
            visit(yes, left)
            visit(no, right)
            condition = text(node.child_by_field_name('condition'))
            for key in left.keys() | right.keys():
                a, b = left.get(key, 'undefined'), right.get(key, 'undefined')
                target[key] = a if a == b else '(' + condition + '?(' + a + '):(' + b + '))'
            return
        invalid = invalid or node.type in {'for_statement', 'for_in_statement', 'while_statement',
                                          'do_statement', 'try_statement', 'catch_clause', 'switch_statement'}
        for child in node.named_children:
            visit(child, target, invalid)

    for child in scope.named_children:
        visit(child, values)
    # A new object plus property assignments can be read by URL guards as well as
    # by the request body. Object literals with later writes are handled by callers.
    for owner, expression in list(values.items()):
        if expression in ('new Object()', '{}') and owner not in uncertain:
            properties = {key[len(owner) + 1:]: value for key, value in values.items()
                          if key.startswith(owner + '.') and '.' not in key[len(owner) + 1:]}
            values[owner] = '{' + ','.join(json.dumps(key) + ':' + val for key, val in properties.items()) + '}'
    return values, uncertain


def url_cases(node, definitions, parse, active=()):
    """Return URL expressions with their branch guards, bounded by alias cycles."""
    if node is None:
        return []
    if node.type in ('parenthesized_expression', 'expression_statement'):
        return url_cases(node.named_children[0], definitions, parse, active) if node.named_children else []
    if node.type == 'identifier' and text(node) in definitions and text(node) not in active:
        name = text(node)
        return url_cases(parse(definitions[name]), definitions, parse, (*active, name))
    if node.type == 'ternary_expression':
        condition = text(node.child_by_field_name('condition'))
        output = []
        for branch, guard in [('consequence', condition), ('alternative', '!(' + condition + ')')]:
            for expression, conditions in url_cases(node.child_by_field_name(branch), definitions, parse, active):
                output.append((expression, [guard, *conditions]))
        return output
    return [(text(node), [])]
