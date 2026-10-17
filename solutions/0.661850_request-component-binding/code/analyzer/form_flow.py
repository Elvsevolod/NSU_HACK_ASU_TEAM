"""Source equations for simple Vue selectors; no implicit execution of events.

A selector may copy parameters into plain component data. Its helper calls must
be source-proven pure. Network, DOM, callbacks, computed writes and opaque calls
reject the projection instead of lending them a last-write-wins interpretation.
"""
from .project import text, walk
from .jsflow import definitions_before


FUNCTIONS = {'function_expression', 'function_declaration', 'arrow_function', 'method_definition'}
COMMENTS = {'comment'}
DATE_GETTERS = {'getDate', 'getMonth', 'getFullYear', 'getHours', 'getMinutes', 'getSeconds'}


def pairs(node):
    return {text(child.child_by_field_name('key')).strip('"\''): child.child_by_field_name('value')
            for child in node.named_children if child.type == 'pair'} if node is not None and node.type == 'object' else {}


def descendants(node):
    for child in node.named_children:
        yield child
        if child.type not in FUNCTIONS:
            yield from descendants(child)


def vue_form_flows(root):
    """One source summary per literal `new Vue({methods: ...})` component."""
    output = []
    shadowed_date = any(node.type in ('variable_declarator', 'function_declaration', 'class_declaration')
                        and text(node.child_by_field_name('name')) == 'Date' for node in walk(root))
    for creation in walk(root):
        if creation.type != 'new_expression' or text(creation.child_by_field_name('constructor')) != 'Vue':
            continue
        arguments = creation.child_by_field_name('arguments')
        if arguments is None or len(arguments.named_children) != 1:
            continue
        option_node = arguments.named_children[0]
        options = pairs(option_node)
        block = options.get('methods')
        if block is None or block.type != 'object':
            continue
        unsupported = (bool(set(options) & {'watch', 'computed', 'mixins', 'extends'})
                       or any(child.type not in ('pair','comment') for child in option_node.named_children))
        methods = {}
        for child in block.named_children:
            if child.type == 'comment':
                continue
            name = text(child.child_by_field_name('name')) if child.type == 'method_definition' else ''
            node = child if name else child.child_by_field_name('value') if child.type == 'pair' else None
            if child.type == 'pair':
                name = text(child.child_by_field_name('key')).strip('"\'')
            if not name or node is None or node.type not in ('method_definition', 'function_expression'):
                unsupported = True
                continue # Arrow functions have lexical this, not the component instance.
            parameters = node.child_by_field_name('parameters')
            names = [text(p) for p in parameters.named_children] if parameters is not None else []
            if parameters is None or any(p.type != 'identifier' for p in parameters.named_children):
                unsupported = True
                continue
            body = node.child_by_field_name('body')
            if body is None or body.type != 'statement_block':
                continue
            statements = [s for s in body.named_children if s.type not in COMMENTS]
            returns = [n for n in descendants(body) if n.type == 'return_statement']
            simple_returns = not returns or len(returns) == 1 and statements and returns[0] == statements[-1]
            definitions, _ = definitions_before(node, body.children[-1])
            methods[name] = {'name': name, 'parameters': names, 'node': node,
                             'definitions': definitions, 'returns': returns,
                             'simple_returns': bool(simple_returns)}
        writers = {}
        for name, method in methods.items():
            aliases = {'this','that'}
            assignments = [item for item in walk(method['node'])
                           if item.type in ('variable_declarator','assignment_expression')]
            for _ in range(len(assignments)):
                before = set(aliases)
                for item in assignments:
                    lhs = item.child_by_field_name('name') or item.child_by_field_name('left')
                    rhs = item.child_by_field_name('value') or item.child_by_field_name('right')
                    if lhs is not None and lhs.type == 'identifier' and text(rhs) in aliases:
                        aliases.add(text(lhs))
                if aliases == before:
                    break
            for item in walk(method['node']):
                if item.type not in ('assignment_expression', 'augmented_assignment_expression', 'update_expression'):
                    continue
                lhs = item.child_by_field_name('left') or item.child_by_field_name('argument')
                while lhs is not None and lhs.type in ('member_expression', 'subscript_expression'):
                    base = lhs.child_by_field_name('object')
                    if text(base) in aliases:
                        prop = lhs.child_by_field_name('property')
                        key = text(prop) if prop is not None else '*'
                        writers.setdefault(key, set()).add(name)
                        break
                    lhs = base
        pure, active = {}, set()

        def safe(name, allow_writes=False):
            signature = name, allow_writes
            if signature in pure:
                return pure[signature]
            method = methods.get(name)
            if (unsupported or method is None or signature in active or not method['simple_returns']
                    or any(child.type in ('async','get','set','*') for child in method['node'].children)):
                return False
            active.add(signature)
            node = method['node']
            body = node.child_by_field_name('body')
            local = set(method['parameters'])
            declarations = [n for n in descendants(body) if n.type == 'variable_declarator']
            local.update(text(n.child_by_field_name('name')) for n in declarations)
            dates = {text(n.child_by_field_name('name')) for n in declarations
                     if text(n.child_by_field_name('value')).startswith('new Date(')}
            aliases = {'this'} | {text(n.child_by_field_name('name')) for n in declarations
                                  if text(n.child_by_field_name('value')) == 'this'}
            names = [text(n.child_by_field_name('name')) for n in declarations] + method['parameters']
            valid = not ('Date' in local and dates) and len(names) == len(set(names))
            for item in descendants(body):
                kind = item.type
                if kind in FUNCTIONS or kind in ('for_statement', 'for_in_statement', 'while_statement', 'do_statement',
                                                'try_statement', 'throw_statement', 'switch_statement',
                                                'await_expression', 'yield_expression', 'update_expression',
                                                'augmented_assignment_expression'):
                    valid = False
                    break
                if kind == 'variable_declarator' and item.child_by_field_name('name').type != 'identifier':
                    valid = False
                    break
                if kind == 'assignment_expression':
                    lhs = item.child_by_field_name('left')
                    operator = item.child_by_field_name('operator')
                    if operator is not None and text(operator) != '=':
                        valid = False
                    elif lhs.type == 'identifier':
                        valid = text(lhs) in local and text(lhs) not in aliases
                    elif lhs.type == 'member_expression':
                        receiver = text(lhs.child_by_field_name('object'))
                        prop = lhs.child_by_field_name('property')
                        valid = allow_writes and receiver in aliases and prop.type == 'property_identifier'
                    else:
                        valid = False
                    if not valid:
                        break
                if kind == 'new_expression':
                    if (shadowed_date or 'Date' in local or text(item.child_by_field_name('constructor')) != 'Date'
                            or item.child_by_field_name('arguments').named_children):
                        valid = False
                        break
                if kind == 'call_expression':
                    function = item.child_by_field_name('function')
                    args = item.child_by_field_name('arguments')
                    fn = text(function)
                    if fn in ('parseInt', 'parseFloat', 'String', 'Number', 'Boolean') and fn not in local:
                        continue
                    if function is None or function.type != 'member_expression':
                        valid = False
                        break
                    receiver, prop = function.child_by_field_name('object'), text(function.child_by_field_name('property'))
                    if text(receiver) in aliases:
                        valid = prop not in writers and '*' not in writers and safe(prop) and args is not None
                    elif (prop in DATE_GETTERS and not args.named_children and not shadowed_date
                          and (text(receiver) in dates or text(receiver) == 'new Date()')):
                        valid = True
                    elif fn == 'console.log':
                        valid = True
                    else:
                        valid = False
                    if not valid:
                        break
            active.remove(signature)
            pure[signature] = valid
            return valid

        helpers = {}
        for name, method in methods.items():
            if safe(name) and len(method['returns']) == 1:
                returned = method['returns'][0]
                helpers[name] = {'parameters': method['parameters'], 'definitions': method['definitions'],
                                 'expression': text(returned.named_children[0]) if returned.named_children else 'undefined'}
        projectors = []
        for name, method in methods.items():
            if not safe(name, True):
                continue
            aliases = {'this'} | {key for key, value in method['definitions'].items() if value == 'this' and '.' not in key}
            fields = {key.split('.',1)[1]: expression for key, expression in method['definitions'].items()
                      if '.' in key and key.split('.',1)[0] in aliases and '.' not in key.split('.',1)[1]}
            if fields:
                projectors.append({'handler': name, 'parameters': method['parameters'], 'fields': fields,
                                   'aliases': sorted(aliases), 'definitions': method['definitions'],
                                   'source_line': method['node'].start_point.row + 1})
        output.append({'component_start': creation.start_byte, 'projectors': projectors, 'helpers': helpers,
                       'diagnostics':['Source Vue equations unavailable: unsupported component options or method declarations at line '+str(creation.start_point.row+1)] if unsupported else [],
                       'writers': {key: sorted(names) for key, names in writers.items()}})
    return output
