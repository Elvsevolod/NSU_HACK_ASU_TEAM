"""A closed lexical slice for ordinary classic-script var bindings.

This adapter does not evaluate JavaScript or assume a callback was invoked.
Complex binding patterns and dynamic scope disable this slice with diagnostics.
"""
import json
import math
from .project import text, walk


FUNCTIONS = {'function_declaration','function_expression','arrow_function','method_definition',
             'generator_function_declaration','generator_function'}
DECLARATIONS = {'function_declaration','generator_function_declaration'}
PATTERNS = {'object_pattern','array_pattern','assignment_pattern','object_assignment_pattern','rest_pattern'}


def parent_function(node):
    node = node.parent
    while node is not None and node.type not in FUNCTIONS:
        node = node.parent
    return node


def scoped_nodes(node):
    if node is None:
        return
    yield node
    for child in node.named_children:
        if child.type in FUNCTIONS:
            yield child
        else:
            yield from scoped_nodes(child)


def name_of(node):
    return text(node) if node is not None and node.type == 'identifier' else None


def loop_binding(node, kind=None):
    if node.type != 'for_in_statement':
        return None
    declared = text(node.child_by_field_name('kind'))
    if declared not in ('var','let','const') or kind and declared != kind:
        return None
    return name_of(node.child_by_field_name('left'))


def literal_initializer(node):
    if node is None:
        return False
    if any(n.type in ('comment','escape_sequence') for n in walk(node)):
        return False
    if node.type in ('string','true','false','null'):
        return True
    if node.type == 'number':
        try:
            number = json.loads(text(node))
            return type(number) in (int,float) and math.isfinite(number) and abs(number) <= 9007199254740991
        except (ValueError,OverflowError):
            return False
    if node.type == 'parenthesized_expression':
        return len(node.named_children) == 1 and literal_initializer(node.named_children[0])
    if node.type == 'array':
        previous = '['
        for child in node.children[1:-1]:
            if child.type == ',':
                if previous in ('[',','):
                    return False
            elif not literal_initializer(child):
                return False
            previous = child.type
        return True
    if node.type == 'object':
        for pair in node.named_children:
            key,value = pair.child_by_field_name('key'),pair.child_by_field_name('value')
            if pair.type != 'pair' or key is None or key.type not in ('property_identifier','string','number') or not literal_initializer(value):
                return False
            if text(key).strip('\"\'') == '__proto__':
                return False
        return True
    return False


class ScriptVars:
    def __init__(self, root):
        self.root, self.bindings, self.program_names, self.diagnostics = root, {}, set(), []
        self._functions, self._blocks = {}, {}
        nodes = list(walk(root))
        declarations, disabled = {}, set()
        if root.has_error:
            disabled.add('JavaScript parse errors')
        for node in nodes:
            if node.type in PATTERNS:
                disabled.add('complex binding pattern at line '+str(node.start_point.row+1))
            if node.type in ('class','class_declaration'):
                disabled.add('class scope at line '+str(node.start_point.row+1))
            if node.type in ('import_statement','export_statement','import','with_statement'):
                disabled.add('module or dynamic scope at line '+str(node.start_point.row+1))
            if node.type in ('call_expression','new_expression'):
                callee = node.child_by_field_name('function') or node.child_by_field_name('constructor')
                if callee is not None and any(text(n) in ('eval','Function') and n.type in ('identifier','property_identifier') for n in walk(callee)):
                    disabled.add('dynamic evaluation at line '+str(node.start_point.row+1))
            name,kind = None,None
            if node.type == 'variable_declarator' and parent_function(node) is None:
                name = name_of(node.child_by_field_name('name'))
                if node.parent.type == 'variable_declaration':
                    kind = 'var'
                elif node.parent.parent == root:
                    kind = 'lexical'
            elif node.type in DECLARATIONS and parent_function(node) is None:
                name,kind = name_of(node.child_by_field_name('name')),'function'
            elif node.type == 'class_declaration' and parent_function(node) is None and node.parent == root:
                name,kind = name_of(node.child_by_field_name('name')),'class'
            elif parent_function(node) is None and loop_binding(node,'var'):
                name,kind = loop_binding(node,'var'),'loop var'
            if name and kind:
                self.program_names.add(name)
                declarations.setdefault(name,[]).append((kind,node))
        for name,records in declarations.items():
            if len(records) != 1:
                self.diagnostics.append('Ambiguous program binding '+name)
                if any(kind == 'lexical' for kind,_ in records):
                    disabled.add('conflicting program lexical declarations')
                continue
            kind,node = records[0]
            if kind == 'var' and node.parent.parent == root:
                value = node.child_by_field_name('value')
                self.bindings[name] = {'initializer':text(value) if value is not None else None,
                                       'line':node.start_point.row+1,'initializer_safe':False}
        prefix = True
        for statement in root.named_children:
            if statement.type in ('comment','empty_statement',*DECLARATIONS):
                continue
            if statement.type != 'variable_declaration':
                prefix = False
                continue
            for node in statement.named_children:
                if node.type != 'variable_declarator':
                    continue
                name,value = name_of(node.child_by_field_name('name')),node.child_by_field_name('value')
                safe = literal_initializer(value)
                if name in self.bindings:
                    self.bindings[name]['initializer_safe'] = prefix and safe
                prefix = prefix and (value is None or safe)
        if disabled:
            self.bindings = {}
            self.diagnostics.extend(sorted(disabled))

    @staticmethod
    def _key(node):
        return node.type,node.start_byte,node.end_byte

    def _function_names(self, node):
        key = self._key(node)
        if key in self._functions:
            return self._functions[key]
        parameters = node.child_by_field_name('parameters') or node.child_by_field_name('parameter')
        names = {text(n) for n in (parameters.named_children if parameters.type == 'formal_parameters' else [parameters])
                 if n is not None and n.type == 'identifier'} if parameters is not None else set()
        if node.type != 'arrow_function':
            names.add('arguments')
        if node.type in ('function_expression','generator_function'):
            name = name_of(node.child_by_field_name('name'))
            if name:
                names.add(name)
        for child in scoped_nodes(node.child_by_field_name('body')):
            if child.type in DECLARATIONS:
                names.add(name_of(child.child_by_field_name('name')))
            elif child.type == 'variable_declarator' and child.parent.type == 'variable_declaration':
                names.add(name_of(child.child_by_field_name('name')))
            elif loop_binding(child,'var'):
                names.add(loop_binding(child,'var'))
        names.discard(None)
        self._functions[key] = names
        return names

    def _block_names(self, node):
        key = self._key(node)
        if key not in self._blocks:
            children = [child for case in node.named_children for child in case.named_children] if node.type == 'switch_body' else node.named_children
            self._blocks[key] = {name_of(var.child_by_field_name('name')) for declaration in children
                                 if declaration.type == 'lexical_declaration' for var in declaration.named_children
                                 if var.type == 'variable_declarator'}
            self._blocks[key].discard(None)
        return self._blocks[key]

    def resolve(self, node, name=None):
        name = name or name_of(node)
        if name not in self.bindings:
            return None
        current = node
        while current is not None and current != self.root:
            if current.type in FUNCTIONS and name in self._function_names(current):
                return None
            if current.type in ('statement_block','switch_body') and name in self._block_names(current):
                return None
            if current.type == 'catch_clause' and name_of(current.child_by_field_name('parameter')) == name:
                return None
            if current.type == 'for_in_statement' and text(current.child_by_field_name('kind')) in ('let','const') and loop_binding(current) == name:
                return None
            if current.type == 'for_statement':
                initializer = current.child_by_field_name('initializer')
                if initializer is not None and initializer.type == 'lexical_declaration' and any(
                        name_of(n.child_by_field_name('name')) == name for n in initializer.named_children if n.type == 'variable_declarator'):
                    return None
            current = current.parent
        return name if current == self.root else None

    def write(self, node):
        if node.type != 'assignment_expression':
            return None
        left = node.child_by_field_name('left')
        return self.resolve(left) if left is not None and left.type == 'identifier' else None

    def function_shadow_names(self, node):
        names,current = set(),node
        while current is not None:
            if current.type in FUNCTIONS:
                names.update(self._function_names(current))
                for child in scoped_nodes(current.child_by_field_name('body')):
                    if child.type == 'variable_declarator':
                        names.add(name_of(child.child_by_field_name('name')))
                    elif child.type == 'catch_clause':
                        names.add(name_of(child.child_by_field_name('parameter')))
                    elif loop_binding(child):
                        names.add(loop_binding(child))
            current = current.parent
        names.discard(None)
        return names
