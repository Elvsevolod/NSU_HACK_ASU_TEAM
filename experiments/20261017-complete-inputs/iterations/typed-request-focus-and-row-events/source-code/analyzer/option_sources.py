"""Narrow source facts linking a DOM select control to AJAX response rows.

Only one accepted producer shape is proven: inside the success callback, a
single ascending loop over a direct response-path alias reads one literal field
per row into an option value and appends the option to a literal-ID document
element. Anything else is omitted rather than approximated.
"""
from tree_sitter import Language, Parser
import tree_sitter_javascript

from .project import text, walk
from .jsflow import definitions_before


FUNCTIONS = {'function_expression', 'function_declaration', 'method_definition', 'arrow_function'}
DECLARATIONS = {'variable_declaration', 'lexical_declaration'}
LABELS = ('innerText', 'textContent')
LABEL_FORBIDDEN = {'call_expression', 'new_expression', 'assignment_expression',
                   'augmented_assignment_expression', 'update_expression',
                   'function_expression', 'arrow_function'}


def _unwrapped(node):
    while node is not None and node.type in ('expression_statement', 'parenthesized_expression'):
        node = node.named_children[0] if node.named_children else None
    return node


def _expression(parser, source):
    if not source:
        return None
    root = parser.parse(('(' + source + ');').encode()).root_node
    return _unwrapped(root.named_children[0]) if root.named_children else None


def _identifier(node):
    return text(node) if node is not None and node.type == 'identifier' else None


def _string(node):
    if node is None or node.type != 'string':
        return None
    raw = text(node)
    return raw[1:-1] if len(raw) >= 2 and raw[0] in ('"', "'") and raw[-1] == raw[0] else None


def _response_path(node, response_name):
    parts = []
    while node is not None and node.type == 'member_expression':
        property_node = node.child_by_field_name('property')
        if property_node is None or property_node.type != 'property_identifier':
            return None
        parts.append(text(property_node))
        node = node.child_by_field_name('object')
    if _identifier(node) != response_name:
        return None
    return '.'.join([response_name, *reversed(parts)])


def _length_array(node):
    if node is None or node.type != 'member_expression':
        return None
    property_node = node.child_by_field_name('property')
    if property_node is None or property_node.type != 'property_identifier' or text(property_node) != 'length':
        return None
    return _identifier(node.child_by_field_name('object'))


def _loop_shape(loop):
    initializer = loop.child_by_field_name('initializer')
    condition = loop.child_by_field_name('condition')
    increment = loop.child_by_field_name('increment')
    if initializer is None or initializer.type not in DECLARATIONS or condition is None or increment is None:
        return None
    if any(child.type not in ('variable_declarator', 'comment') for child in initializer.named_children):
        return None
    declarators = [child for child in initializer.named_children if child.type == 'variable_declarator']
    if not declarators:
        return None
    index = _identifier(declarators[0].child_by_field_name('name'))
    if index is None or text(declarators[0].child_by_field_name('value')) != '0':
        return None
    array, bound = None, None
    if len(declarators) == 2:
        bound = _identifier(declarators[1].child_by_field_name('name'))
        array = _length_array(declarators[1].child_by_field_name('value'))
        if bound is None or array is None:
            return None
    elif len(declarators) != 1:
        return None
    if condition.type != 'binary_expression' or text(condition.child_by_field_name('operator')) != '<':
        return None
    if _identifier(condition.child_by_field_name('left')) != index:
        return None
    right = condition.child_by_field_name('right')
    if bound is not None:
        if _identifier(right) != bound:
            return None
    else:
        array = _length_array(right)
        if array is None:
            return None
    if increment.type != 'update_expression' or _identifier(increment.child_by_field_name('argument')) != index:
        return None
    if text(increment) not in (index + '++', '++' + index):
        return None
    return index, array, bound


def _document_call(node, method):
    if node is None or node.type != 'call_expression':
        return None
    function = node.child_by_field_name('function')
    arguments = node.child_by_field_name('arguments')
    if (function is None or function.type != 'member_expression'
            or text(function.child_by_field_name('object')) != 'document'
            or text(function.child_by_field_name('property')) != method
            or arguments is None or len(arguments.named_children) != 1):
        return None
    return arguments.named_children[0]


def _option_name(statement):
    if statement.type not in DECLARATIONS:
        return None
    if any(child.type not in ('variable_declarator', 'comment') for child in statement.named_children):
        return None
    declarators = [child for child in statement.named_children if child.type == 'variable_declarator']
    if len(declarators) != 1:
        return None
    name = _identifier(declarators[0].child_by_field_name('name'))
    if name is None or _string(_document_call(declarators[0].child_by_field_name('value'), 'createElement')) != 'option':
        return None
    return name


def _control_id(parser, source):
    return _string(_document_call(_expression(parser, source), 'getElementById'))


def _indexed(node, array, index):
    return (node is not None and node.type == 'subscript_expression'
            and _identifier(node.child_by_field_name('object')) == array
            and _identifier(node.child_by_field_name('index')) == index)


def _value_field(node, array, index):
    node = _unwrapped(node)
    if node is not None and node.type == 'subscript_expression' and _indexed(node.child_by_field_name('object'), array, index):
        return _string(node.child_by_field_name('index'))
    if node is not None and node.type == 'member_expression' and _indexed(node.child_by_field_name('object'), array, index):
        property_node = node.child_by_field_name('property')
        if property_node is not None and property_node.type == 'property_identifier':
            return text(property_node)
    return None


def _plain_label(node):
    return node is not None and all(
        descendant.type not in LABEL_FORBIDDEN
        and not (descendant.type == 'unary_expression'
                 and text(descendant.child_by_field_name('operator')) == 'delete')
        for descendant in walk(node))


def _writes_index(node, index):
    if node is None:
        return False
    for descendant in walk(node):
        if descendant.type == 'update_expression' and _identifier(descendant.child_by_field_name('argument')) == index:
            return True
        if descendant.type in ('assignment_expression', 'augmented_assignment_expression') \
                and text(descendant.child_by_field_name('left')) == index:
            return True
        if descendant.type == 'variable_declarator' and _identifier(descendant.child_by_field_name('name')) == index:
            return True
    return False


def _root_identifier(node):
    node = _unwrapped(node)
    while node is not None and node.type in ('member_expression', 'subscript_expression'):
        node = _unwrapped(node.child_by_field_name('object'))
    return _identifier(node)


def _mutates(node, names, response_name):
    if node.type == 'call_expression':
        function = _unwrapped(node.child_by_field_name('function'))
        if function is None or function.type != 'member_expression':
            return False
        target = _unwrapped(function.child_by_field_name('object'))
    elif node.type in ('assignment_expression', 'augmented_assignment_expression'):
        target = _unwrapped(node.child_by_field_name('left'))
        if target is None or target.type not in ('member_expression', 'subscript_expression'):
            return False
    elif node.type == 'update_expression':
        target = _unwrapped(node.child_by_field_name('argument'))
        if target is None or target.type not in ('member_expression', 'subscript_expression'):
            return False
    else:
        return False
    root = _root_identifier(target)
    return root in names or (response_name is not None and root == response_name)


def _mutated(success, boundary, after, names, response_name):
    stack = list(success.named_children)
    while stack:
        node = stack.pop()
        if node.type in FUNCTIONS:
            continue
        if (node.start_byte >= boundary if after else node.end_byte <= boundary) \
                and _mutates(node, names, response_name):
            return True
        stack.extend(node.named_children)
    return False


def _loops(scope):
    output, stack = [], list(scope.named_children)
    while stack:
        node = stack.pop()
        if node.type in FUNCTIONS:
            continue
        if node.type == 'for_statement':
            output.append(node)
            continue
        stack.extend(node.named_children)
    return sorted(output, key=lambda node: node.start_byte)


def _loop_fact(success, loop, response_name, parser):
    shape = _loop_shape(loop)
    if shape is None:
        return None
    index, array, bound = shape
    definitions, uncertain = definitions_before(success, loop)
    definition = definitions.get(array)
    if definition is None or array in uncertain:
        return None
    response_path = _response_path(_expression(parser, definition), response_name)
    if response_path is None:
        return None
    body = loop.child_by_field_name('body')
    statements = body.named_children if body is not None and body.type == 'statement_block' else [body] if body is not None else []
    option, control, control_receiver, value_field, value_writes, label_writes, append_line = None, None, None, None, 0, 0, None
    for statement in statements:
        if statement.type == 'comment':
            continue
        if statement.type in DECLARATIONS:
            name = _option_name(statement)
            if name is None or option is not None:
                return None
            option = name
            continue
        expression = statement.named_children[0] if statement.type == 'expression_statement' and statement.named_children else None
        if expression is None:
            return None
        if expression.type == 'assignment_expression':
            left = expression.child_by_field_name('left')
            if option is None or left.type != 'member_expression' or _identifier(left.child_by_field_name('object')) != option:
                return None
            property_name = text(left.child_by_field_name('property'))
            if property_name == 'value':
                field = _value_field(expression.child_by_field_name('right'), array, index)
                operator = expression.child_by_field_name('operator')
                if field is None or value_writes or (operator is not None and text(operator) != '='):
                    return None
                value_field, value_writes = field, value_writes + 1
            elif property_name in LABELS:
                if label_writes or not _plain_label(expression.child_by_field_name('right')):
                    return None
                label_writes += 1
            else:
                return None
            continue
        if expression.type == 'call_expression':
            function = expression.child_by_field_name('function')
            arguments = expression.child_by_field_name('arguments')
            receiver = _identifier(function.child_by_field_name('object')) if function is not None and function.type == 'member_expression' else None
            if (append_line is not None or option is None or receiver is None
                    or text(function.child_by_field_name('property')) != 'appendChild'
                    or arguments is None or len(arguments.named_children) != 1
                    or _identifier(arguments.named_children[0]) != option):
                return None
            control = _control_id(parser, None if receiver in uncertain else definitions.get(receiver))
            if control is None:
                return None
            control_receiver = receiver
            append_line = expression.start_point.row + 1
            continue
        return None
    if option is None or control is None or value_field is None or append_line is None or value_writes != 1 or label_writes != 1:
        return None
    if option in {index, array, bound, control_receiver} - {None}:
        return None
    if _mutated(success, loop.start_byte, False, {array}, response_name):
        return None
    if _mutated(success, loop.end_byte, True, {control_receiver}, None):
        return None
    if _writes_index(loop.child_by_field_name('condition'), index) or _writes_index(body, index):
        return None
    return {'control': control, 'value_field': value_field, 'response_path': response_path, 'source_line': append_line}


def option_sources(success, response_name):
    """Proven (control, value_field, response_path, source_line) option producers."""
    if success is None or success.type not in FUNCTIONS or not response_name:
        return []
    parameters = success.child_by_field_name('parameters')
    if parameters is None or response_name not in {text(child) for child in parameters.named_children}:
        return []
    parser = Parser(Language(tree_sitter_javascript.language()))
    output = []
    for loop in _loops(success):
        fact = _loop_fact(success, loop, response_name, parser)
        if fact is not None:
            output.append(fact)
    return output
