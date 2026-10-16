"""Experimental graph projection, separate from source execution and state.

The task does not expressly exclude handwritten field-only constructors. This
policy tests a labeling hypothesis suggested by website feedback; it must not
change the source model or be treated as a confirmed runtime execution rule.
"""
from .project import text


def field_only_constructor(node):
    if node is None or node.type != 'constructor_declaration':
        return False
    params = node.child_by_field_name('parameters')
    names = {text(p.child_by_field_name('name')) for p in params.named_children
             if p.type == 'formal_parameter'} if params else set()
    body = node.child_by_field_name('body')
    if not names or body is None:
        return False
    owner_body = node.parent
    owner = owner_body.parent
    if owner.type != 'class_declaration' or owner.child_by_field_name('superclass'):
        return False
    fields = set()
    for child in owner_body.named_children:
        # Instance initialization may do additional work outside the ctor body.
        if child.type == 'block':
            return False
        if child.type != 'field_declaration':
            continue
        modifiers = next((text(n) for n in child.named_children if n.type == 'modifiers'), '')
        for var in child.named_children:
            if var.type != 'variable_declarator':
                continue
            if 'static' not in modifiers.split() and var.child_by_field_name('value'):
                return False
            if not any(word in modifiers.split() for word in ('static', 'volatile')):
                fields.add(text(var.child_by_field_name('name')))
    used = set()
    for statement in body.named_children:
        if statement.type in ('line_comment', 'block_comment'):
            continue
        if statement.type != 'expression_statement' or len(statement.named_children) != 1:
            return False
        assignment = statement.named_children[0]
        if assignment.type != 'assignment_expression' or text(assignment.child_by_field_name('operator')) != '=':
            return False
        lhs, rhs = assignment.child_by_field_name('left'), assignment.child_by_field_name('right')
        if (lhs.type != 'field_access' or text(lhs.child_by_field_name('object')) != 'this'
                or text(lhs.child_by_field_name('field')) not in fields
                or rhs.type != 'identifier' or text(rhs) not in names):
            return False
        used.add(text(rhs))
    return used == names


def project_edges(project, edges, policy):
    if policy == 'explicit':
        return edges, set()
    if policy != 'field-only':
        raise ValueError('Unknown constructor policy: ' + policy)
    candidates = {target for _, relation, target in edges
                  if relation == 'executes' and field_only_constructor(project.ast.get(target))}
    # Defensive: never suppress a constructor that has observable graph activity.
    outgoing = {source for source, relation, _ in edges if relation != 'executes'}
    candidates -= outgoing
    removed = {edge for edge in edges if edge[1] in ('executes', 'calls') and edge[2] in candidates}
    return edges - removed, removed
