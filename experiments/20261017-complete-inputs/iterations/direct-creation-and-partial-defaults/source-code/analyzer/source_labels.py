"""Local aliases for request DTO fields, proven by getter chains in source.

For a handler mid, field_aliases() takes the declared @RequestBody types and
reports which local variable names are directly initialized (or directly
assigned) from a zero-argument getter whose receiver resolves to exactly one
of those DTO types. The getter suffix must match a field actually declared by
that DTO type (getFoo -> foo), and an explicit source accessor is honored only
when its body is a single return of that matching field. Names bound to more
than one type and bindings inside nested methods, classes or lambdas are
dropped: only the full local name and method:line evidence are recorded, and
unresolved or uncertain receivers contribute no facts.
"""
import re

from .project import text


def _getter_field(name):
    return name[3].lower() + name[4:] if re.fullmatch(r'get[A-Z]\w*', name) else None


def _arguments(invocation):
    arguments = invocation.child_by_field_name('arguments')
    return [child for child in arguments.named_children
            if child.type not in ('line_comment', 'block_comment')] if arguments else []


def _declared(project, tid):
    return project.type_fields.get(tid, {})


def _pure_accessor(project, mid, field):
    """A zero-arg explicit accessor whose only statement returns field (or this.field)."""
    node = project.ast.get(mid)
    if node is None or project.parameters(mid):
        return False
    body = node.child_by_field_name('body')
    statements = [child for child in body.named_children
                  if child.type not in ('line_comment', 'block_comment')] if body else []
    if len(statements) != 1 or statements[0].type != 'return_statement':
        return False
    returned = [child for child in statements[0].named_children
                if child.type not in ('line_comment', 'block_comment')]
    if len(returned) != 1:
        return False
    expression = returned[0]
    if expression.type == 'identifier':
        return text(expression) == field
    return (expression.type == 'field_access' and text(expression.child_by_field_name('field')) == field
            and text(expression.child_by_field_name('object')) == 'this')


def _accessor_ok(project, tid, method_name, field):
    """Explicit accessors must be pure; absent ones keep the declared-field convention."""
    explicit = [mid for mid in project.by_name.get(method_name, []) if project.methods[mid]['owner'] == tid]
    return not explicit or any(_pure_accessor(project, mid, field) for mid in explicit)


_NESTED_BODIES = frozenset({
    'class_declaration', 'interface_declaration', 'enum_declaration', 'record_declaration',
    'annotation_type_declaration', 'method_declaration', 'constructor_declaration',
    'lambda_expression', 'class_body'})


def _own_walk(node):
    """Walk a method body without descending into nested methods, classes or lambdas."""
    yield node
    for child in node.named_children:
        if child.type not in _NESTED_BODIES:
            yield from _own_walk(child)


def _scope(project, mid):
    """Unambiguous identifier -> (written type, file); plus parameter/local names.

    A name bound to more than one type (an inner block shadowing a field, for
    example) is dropped, so an uncertain receiver can never provide evidence.
    """
    node = project.ast.get(mid)
    if node is None:
        return {}, set()
    method = project.methods[mid]
    pairs, locals_ = {}, set()

    def bind(name, written, file, local):
        if not name:
            return
        pairs.setdefault(name, set()).add((written, file))
        if local:
            locals_.add(name)

    for name, field in project.type_fields.get(method['owner'], {}).items():
        bind(name, field['type'], field['file'], False)
    parameters = node.child_by_field_name('parameters')
    for parameter in parameters.named_children if parameters else []:
        if parameter.type == 'formal_parameter':
            bind(text(parameter.child_by_field_name('name')),
                 text(parameter.child_by_field_name('type')), method['file'], True)
    for declaration in _own_walk(node):
        if declaration.type != 'local_variable_declaration':
            continue
        written = text(declaration.child_by_field_name('type'))
        for variable in declaration.named_children:
            if variable.type == 'variable_declarator':
                bind(text(variable.child_by_field_name('name')), written, method['file'], True)
    scope = {name: next(iter(types)) for name, types in pairs.items() if len(types) == 1}
    return scope, {name for name in locals_ if name in scope}


def _expr_type(project, expression, scope, module, file, owner):
    """Type id for an identifier, this, field access or zero-arg declared getter."""
    if expression is None:
        return None
    if expression.type == 'identifier':
        entry = scope.get(text(expression))
        return project.resolve_type(entry[0], module, entry[1]) if entry else None
    if expression.type == 'this':
        return owner
    if expression.type == 'field_access':
        base = _expr_type(project, expression.child_by_field_name('object'), scope, module, file, owner)
        field = _declared(project, base).get(text(expression.child_by_field_name('field')))
        return project.resolve_type(field['type'], module, field['file']) if field else None
    if expression.type == 'method_invocation':
        if _arguments(expression):
            return None
        call = text(expression.child_by_field_name('name'))
        name = _getter_field(call)
        receiver = expression.child_by_field_name('object')
        base = owner if receiver is None else _expr_type(project, receiver, scope, module, file, owner)
        field = _declared(project, base).get(name) if name and _accessor_ok(project, base, call, name) else None
        return project.resolve_type(field['type'], module, field['file']) if field else None
    return None


def _root_field(project, value, roots, scope, module, file, owner):
    """Declared root DTO field read by a direct zero-arg getter value, else None."""
    if value is None or value.type != 'method_invocation' or _arguments(value):
        return None
    call = text(value.child_by_field_name('name'))
    field = _getter_field(call)
    receiver = value.child_by_field_name('object')
    base = owner if receiver is None else _expr_type(project, receiver, scope, module, file, owner)
    return field if (field and base in roots and field in _declared(project, base)
                     and _accessor_ok(project, base, call, field)) else None


def _scan(project, roots):
    found = []
    for mid in sorted(project.methods):
        node = project.ast.get(mid)
        if node is None:
            continue
        method = project.methods[mid]
        scope, bindings = _scope(project, mid)
        for statement in _own_walk(node):
            pairs = []
            if statement.type == 'local_variable_declaration':
                pairs = [(text(variable.child_by_field_name('name')), variable.child_by_field_name('value'))
                         for variable in statement.named_children if variable.type == 'variable_declarator']
            elif statement.type == 'assignment_expression' and text(statement.child_by_field_name('operator')) == '=':
                left = statement.child_by_field_name('left')
                if left.type == 'identifier' and text(left) in bindings:
                    pairs = [(text(left), statement.child_by_field_name('right'))]
            for label, value in pairs:
                field = _root_field(project, value, roots, scope, method['module'], method['file'], method['owner'])
                if field:
                    found.append((field, label, mid, statement.start_point.row + 1))
    return list(dict.fromkeys(found))


def field_aliases(project, mid):
    """Field aliases for the @RequestBody declared types of mid.

    Returns {field: [{'label': local name, 'reference': 'source_mid:line'}]}.
    Every indexed source method is scanned for direct getter-chain evidence;
    the scan is shared between calls with the same root type set and results
    are cached per mid. Fields without proven aliases are omitted.
    """
    cache = project.__dict__.setdefault('_field_alias_cache', {})
    if mid in cache:
        return cache[mid]
    method = project.methods.get(mid)
    roots = set()
    if method:
        for parameter in project.http_parameters(mid):
            if parameter['kind'] != 'RequestBody':
                continue
            tid = project.resolve_type(parameter['type'], method['module'], method['file'])
            if project.type_fields.get(tid):
                roots.add(tid)
    result = {}
    if roots:
        scans = project.__dict__.setdefault('_field_alias_scan', {})
        key = tuple(sorted(roots))
        if key not in scans:
            scans[key] = _scan(project, roots)
        for field, label, source, line in scans[key]:
            result.setdefault(field, []).append({'label': label, 'reference': f'{source}:{line}'})
    cache[mid] = result
    return result
