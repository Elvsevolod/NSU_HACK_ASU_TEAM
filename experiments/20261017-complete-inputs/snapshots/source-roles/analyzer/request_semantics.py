"""Lower explicit filters through DTO mutators and source enum constants."""
import re
from baseline_nlp import ntoks
from .project import text, walk
from .provenance import entity_words
from .state import U
from .engine import Engine


def partial_url_parameters(frontend, mid, site, state):
    """Keep known path/query parts even when another expression is unknown."""
    expression = site['url']
    tree = frontend.parser.parse(('(' + expression + ');').encode())
    marker = '__unresolved_browser_value__'
    while marker in expression:
        marker += '_'

    def render(node):
        if node is None:
            return marker
        if node.type in ('parenthesized_expression', 'expression_statement') and node.named_children:
            return render(node.named_children[0])
        if node.type == 'binary_expression' and text(node.child_by_field_name('operator')) == '+':
            return render(node.child_by_field_name('left')) + render(node.child_by_field_name('right'))
        value = frontend.evaluate(text(node), state, definitions=site['definitions'])
        return str(value) if isinstance(value, (str, int, float)) and not isinstance(value, bool) else marker

    url = render(tree.root_node.named_children[0])
    values = Engine(frontend.project, state).path_parameters(mid, url)
    return {key: value for key, value in values.items() if not isinstance(value, str) or marker not in value}


def filter_bindings(project, mid, action):
    match = re.search(r'\bfilter(?:ed)?\b(?:\s+by)?\s+(.*)', action, re.I)
    if not match:
        return []
    phrase = match[1]
    words = set(ntoks(phrase))
    output = []
    for parameter in project.http_parameters(mid):
        if parameter['kind'] != 'RequestBody':
            continue
        tid = project.resolve_type(parameter['type'], project.methods[mid]['module'])
        fields = project.type_fields.get(tid, {})
        entity = entity_words(parameter['type'])
        candidates = []
        for method, meta in project.methods.items():
            if meta['owner'] != tid or meta['name'] == '<init>':
                continue
            node = project.ast.get(method)
            body = node.child_by_field_name('body') if node else None
            statements = [c for c in body.named_children if c.type not in ('line_comment', 'block_comment')] if body else []
            if not statements or any(s.type != 'expression_statement' for s in statements):
                continue
            assignments = []
            for statement in statements:
                expression = statement.named_children[0]
                if expression.type != 'assignment_expression' or text(expression.child_by_field_name('operator')) != '=':
                    break
                lhs = text(expression.child_by_field_name('left')).removeprefix('this.')
                rhs = text(expression.child_by_field_name('right'))
                if lhs not in fields:
                    break
                assignments.append((lhs, rhs))
            else:
                if not any(rhs == 'true' and fields[key]['type'] == 'boolean' for key, rhs in assignments):
                    continue
                params = dict(project.parameters(method))
                concepts = (set(ntoks(meta['name'] + ' ' + ' '.join(params)))
                            - {'enable', 'query', 'filter', 'target', 'start', 'end', 'time'})
                if not concepts & words:
                    continue
                bindings = []
                for key, rhs in assignments:
                    value, reference = U, method
                    if rhs in ('true', 'false'):
                        value = rhs == 'true'
                    elif rhs in params:
                        constants = []
                        for name, obj in project.enum_objects.items():
                            owner, member = name.rsplit('.', 1)
                            label = set(ntoks(member))
                            owner_words = set(ntoks(owner))
                            if not label or not label <= words or not owner_words & concepts or (entity and not owner_words & entity):
                                continue
                            scalars = [v for k, v in obj.items() if not k.startswith('__') and isinstance(v, int) and not isinstance(v, bool)]
                            if len(scalars) == 1:
                                constants.append((scalars[0], name))
                        if len({repr(v) for v, _ in constants}) == 1:
                            value, reference = constants[0]
                    bindings.append((key, value, reference, match[0]))
                candidates.append(bindings)
        if len(candidates) == 1:
            output.extend(candidates[0])
        elif len(candidates) > 1:
            ambiguous = {key: (key, U, reference, quote) for candidate in candidates
                         for key, _, reference, quote in candidate}
            output.extend(ambiguous.values())
    return output
