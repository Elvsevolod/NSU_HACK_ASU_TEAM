"""Bounded expression propagation within a JavaScript request's lexical scope."""
import json
from tree_sitter import Language, Parser
import tree_sitter_javascript

from .project import text


FUNCTIONS = {'function_expression', 'function_declaration', 'method_definition', 'arrow_function'}


def definitions_before(scope, limit, initial=None):
    """Conditional writes become expressions, never the last visited branch's value.

    Only assignments are modeled here. Loops, exception handlers and computed
    property writes invalidate their affected values. Nested functions are separate.
    """
    values = dict(initial or {})
    uncertain = set()
    parser = Parser(Language(tree_sitter_javascript.language()))

    def owner_of(name, target):
        seen = set()
        while name not in seen and target.get(name) in target:
            seen.add(name)
            name = target[name]
        return name

    def object_expression(owner, target):
        if target.get(owner) not in ('new Object()', '{}'):
            return target.get(owner, 'undefined')
        props = {name[len(owner) + 1:]: value for name, value in target.items()
                 if name.startswith(owner + '.') and '.' not in name[len(owner) + 1:]}
        return '{' + ','.join(json.dumps(key) + ':' + value for key, value in props.items()) + '}'

    def freeze(node, target):
        """Scalar reads use the value at this program point, not a later assignment."""
        if node is None:
            return 'undefined'
        if node.type == 'identifier' and text(node) in target:
            owner = owner_of(text(node), target)
            prior = target[owner]
            if prior.startswith(('{', '[')) or prior == 'new Object()':
                return text(node)  # object aliases retain identity until invalidated
            return '(' + prior + ')'
        if node.type == 'member_expression':
            base = node.child_by_field_name('object')
            if base is not None and base.type == 'identifier':
                owner = owner_of(text(base), target)
                key = owner + '.' + text(node.child_by_field_name('property'))
                if key in target:
                    return '(' + target[key] + ')'
        if node.type in FUNCTIONS:
            return text(node)
        # JSON.stringify snapshots an object; a later mutation cannot change it.
        if node.type == 'call_expression' and text(node.child_by_field_name('function')) == 'JSON.stringify':
            args = node.child_by_field_name('arguments')
            if args and len(args.named_children) == 1 and args.named_children[0].type == 'identifier':
                owner = owner_of(text(args.named_children[0]), target)
                return 'JSON.stringify(' + object_expression(owner, target) + ')'
        raw = node.text
        changes = [(c.start_byte - node.start_byte, c.end_byte - node.start_byte, freeze(c, target).encode())
                   for c in node.named_children]
        for start, end, replacement in reversed(changes):
            raw = raw[:start] + replacement + raw[end:]
        return raw.decode()

    def invalidate_aliases(owner, target):
        for key, expression in list(target.items()):
            if key == owner or key.startswith(owner + '.'):
                continue
            tree = parser.parse(('(' + expression + ');').encode())
            stack = [tree.root_node]
            while stack:
                node = stack.pop()
                if node.type == 'identifier' and text(node) == owner:
                    target[key] = 'undefined'
                    break
                stack.extend(node.named_children)

    def invalidate_object(owner, target):
        uncertain.add(owner)
        for key in list(target):
            if key == owner or key.startswith(owner + '.'):
                target[key] = 'undefined'

    def invalidate_calls(node, target):
        if node is None or node.type in FUNCTIONS:
            return
        if node.type == 'call_expression':
            fn = text(node.child_by_field_name('function'))
            pure = fn == 'JSON.stringify' or fn.startswith('console.')
            if not pure:
                args = node.child_by_field_name('arguments')
                for arg in args.named_children if args else []:
                    if arg.type == 'identifier':
                        owner = owner_of(text(arg), target)
                        if target.get(owner, '').startswith(('{', '[', 'new ')):
                            invalidate_object(owner, target)
                function = node.child_by_field_name('function')
                receiver = function.child_by_field_name('object') if function and function.type == 'member_expression' else None
                if receiver is not None and receiver.type == 'identifier':
                    owner = owner_of(text(receiver), target)
                    if target.get(owner, '').startswith(('{', '[')):
                        invalidate_object(owner, target)
        for child in node.named_children:
            invalidate_calls(child, target)

    def assign(node, target, invalid=False):
        lhs = node.child_by_field_name('name') if node.type == 'variable_declarator' else node.child_by_field_name('left')
        rhs = node.child_by_field_name('value') if node.type == 'variable_declarator' else node.child_by_field_name('right')
        key = text(lhs)
        if not key:
            return
        if lhs.type == 'subscript_expression':
            owner = owner_of(text(lhs.child_by_field_name('object')), target)
            uncertain.add(owner)
            for name in list(target):
                if name == owner or name.startswith(owner + '.'):
                    target[name] = 'undefined'
            return
        invalidate_calls(rhs, target)
        frozen = freeze(rhs, target)
        if lhs.type == 'identifier':
            if key in target:
                invalidate_aliases(key, target)
            for name in list(target):
                if name.startswith(key + '.'):
                    target.pop(name)
        elif lhs.type == 'member_expression' and lhs.child_by_field_name('object').type == 'identifier':
            owner = owner_of(text(lhs.child_by_field_name('object')), target)
            key = owner + '.' + text(lhs.child_by_field_name('property'))
        operator = node.child_by_field_name('operator')
        if operator is not None and text(operator) != '=':
            invalid = True
        if rhs is not None and rhs.type == 'object' and not invalid:
            target[key] = '{}'
            for child in rhs.named_children:
                prop = child.child_by_field_name('key') if child.type == 'pair' else None
                if prop is None or prop.type not in ('property_identifier', 'string', 'number'):
                    target[key] = 'undefined'
                    uncertain.add(key)
                    return
                name = text(prop).strip('"\'')
                target[key + '.' + name] = freeze(child.child_by_field_name('value'), target)
        else:
            target[key] = 'undefined' if invalid else frozen

    def visit(node, target, invalid=False):
        if node is None or node.start_byte >= limit.start_byte or node.type in FUNCTIONS:
            return
        if node.type in ('variable_declarator', 'assignment_expression', 'augmented_assignment_expression'):
            assign(node, target, invalid)
            return
        if node.type == 'call_expression':
            invalidate_calls(node, target)
            return
        if node.type == 'statement_block':
            scoped = {text(var.child_by_field_name('name')) for child in node.named_children if child.type == 'lexical_declaration'
                      for var in child.named_children if var.type == 'variable_declarator'}
            prior = {key: value for key, value in target.items() if any(key == name or key.startswith(name + '.') for name in scoped)}
            objects = {key for key in scoped if target.get(key, '').startswith(('{', '[', 'new '))}
            for key in objects:
                invalidate_aliases(key, target)
            for key in prior:
                target.pop(key)
            for child in node.named_children:
                visit(child, target, invalid)
            if not node.start_byte <= limit.start_byte < node.end_byte:
                for key in list(target):
                    if any(key == name or key.startswith(name + '.') for name in scoped):
                        target.pop(key)
                target.update(prior)
                for key in objects:
                    invalidate_object(key, target)
            return
        if node.type == 'update_expression':
            argument = node.child_by_field_name('argument')
            if argument is not None:
                target[text(argument)] = 'undefined'
            return
        if node.type == 'if_statement' and not invalid:
            yes, no = node.child_by_field_name('consequence'), node.child_by_field_name('alternative')
            # The request itself establishes which enclosing branch was entered.
            for branch in (yes, no):
                if branch is not None and branch.start_byte <= limit.start_byte < branch.end_byte:
                    visit(branch, target)
                    return
            condition = freeze(node.child_by_field_name('condition'), target)
            left, right = dict(target), dict(target)
            visit(yes, left)
            visit(no, right)
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
