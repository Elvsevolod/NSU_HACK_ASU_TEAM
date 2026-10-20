"""Lower explicit filters through DTO mutators and source enum constants."""
import re
import calendar
from datetime import datetime
from baseline_nlp import ntoks
from .project import text, walk
from .provenance import entity_words
from .state import U
from .engine import Engine


def generated_omissions(project, mid):
    """Optional DTO identifiers whose null case generates a UUID in source."""
    cache = project.__dict__.setdefault('_generated_input_fields', {})
    if mid in cache:
        return cache[mid]
    result = {}
    roots = {project.resolve_type(p['type'], project.methods[mid]['module'], project.methods[mid]['file'])
             for p in project.http_parameters(mid) if p['kind'] == 'RequestBody'} - {None}
    reachable = project.__dict__.setdefault('_request_reachable', {})
    if mid not in reachable:
        reachable[mid] = project.ix.closure({mid})[0] | {mid}
    for method in reachable[mid]:
        node = project.ast.get(method)
        if node is None or 'randomUUID' not in text(node):
            continue
        meta = project.methods[method]
        names = {name for name, typ in project.parameters(method) if project.resolve_type(typ, meta['module'], meta['file']) in roots}
        for condition in walk(node):
            if condition.type != 'if_statement':
                continue
            test = condition.child_by_field_name('condition')
            raw = text(test).strip('() ')
            matched = re.fullmatch(r'(\w+)\.(?:get([A-Z]\w*)\(\)|(\w+))\s*(==|!=)\s*null', raw)
            if not matched or matched[1] not in names:
                continue
            field = matched[2][:1].lower() + matched[2][1:] if matched[2] else matched[3]
            branch = condition.child_by_field_name('consequence' if matched[4] == '==' else 'alternative')
            if not branch or not re.search(r'\bUUID\s*\.\s*randomUUID\s*\(', text(branch)):
                continue
            read = matched[1] + '.' + ('get' + matched[2] + '()' if matched[2] else matched[3])
            aliases = {text(local.child_by_field_name('name')) for local in walk(node)
                       if local.type == 'variable_declarator' and local.start_byte < condition.start_byte
                       and text(local.child_by_field_name('value')) == read}
            assignments = [item for item in walk(branch) if item.type == 'assignment_expression'
                           and (text(item.child_by_field_name('left')) in aliases
                                or text(item.child_by_field_name('left')) == matched[1] + '.' + field)
                           and re.search(r'\bUUID\s*\.\s*randomUUID\s*\(', text(item.child_by_field_name('right')))]
            if not assignments:
                continue
            if project.resolve_type('UUID', meta['module'], meta['file']) is not None:
                continue
            if 'java.util.UUID' not in project.sources[meta['file']].decode() and 'java.util.*' not in project.sources[meta['file']].decode():
                continue
            if any(field in project.type_fields.get(root, {}) and project.type_fields[root][field]['type'].split('.')[-1] in ('String', 'UUID') for root in roots):
                result[field] = method + ':' + str(condition.start_point.row + 1)
    cache[mid] = result
    return result


def enum_scalar_binding(project, mid, field, action):
    """Use an enum's numeric value only when source compares this input getter to it."""
    cache = project.__dict__.setdefault('_input_enum_evidence', {})
    cache_key = (mid, field)
    if cache_key not in cache:
        reachable = project.__dict__.setdefault('_request_reachable', {})
        if mid not in reachable:
            reachable[mid] = project.ix.closure({mid})[0] | {mid}
        getter = 'get' + field[:1].upper() + field[1:]
        evidence = []
        for method in reachable[mid]:
            node = project.ast.get(method)
            if node is None or getter not in text(node):
                continue
            for condition in walk(node):
                if condition.type != 'binary_expression' or not re.search(r'\b' + re.escape(getter) + r'\s*\(', text(condition)):
                    continue
                source = text(condition)
                refs = [project.enum_reference(text(child), method) for child in walk(condition) if child.type == 'field_access']
                owners = {ref.rsplit('.', 1)[0] for ref in refs if ref}
                for name, obj in project.enum_objects.items():
                    owner, member_name = name.rsplit('.', 1)
                    if owner in owners:
                        values = [v for key, v in obj.items() if not key.startswith('__') and isinstance(v, int) and not isinstance(v, bool)]
                        if len(values) == 1:
                            labels = [member_name, *(v for key, v in obj.items() if not key.startswith('__') and isinstance(v, str))]
                            evidence.append((values[0], name, labels, method))
        cache[cache_key] = evidence
    normalized = lambda s: re.sub('[^a-z0-9]', '', s.lower())
    matches = [(value, name, method) for value, name, labels, method in cache[cache_key]
               if any(len(normalized(label)) >= 4 and normalized(label) in normalized(action) for label in labels)]
    if len({repr(value) for value, _, _ in matches}) == 1:
        return matches[0]
    return None


def enum_ordinal_binding(project, mid, field, action):
    """An explicit ordinal type choice needs an unfiltered source enum listing."""
    choice = re.search(r'\b(first|second|third|fourth)\s+(?:available\s+)?(?:type|kind|option)\b', action, re.I)
    if not choice:
        return None
    concepts = set(ntoks(field)) - {'type', 'kind', 'mode', 'option'}
    before = set(ntoks(re.split(r'[,;]', action[:choice.start()])[-1])[-7:])
    if not concepts or not concepts <= before:
        return None
    cache = project.__dict__.setdefault('_ordinal_enum_listings', {})
    output = []
    position = ('first', 'second', 'third', 'fourth').index(choice[1].lower())
    for tid, members in project.enum_members.items():
        if entity_words(project.nodes[tid]['fqn']) - {'type', 'kind', 'mode', 'option'} != concepts or position >= len(members):
            continue
        values = [project.enum_objects.get(member, {}) for member in members]
        numeric = {key for key, value in values[0].items() if not key.startswith('__') and isinstance(value, int) and not isinstance(value, bool)} if values else set()
        if len(numeric) != 1:
            continue
        key = next(iter(numeric))
        if not all(type(value.get(key)) is int for value in values):
            continue
        if tid not in cache:
            proof = None
            name = project.nodes[tid]['fqn'].split('.')[-1]
            getter = 'get' + key[:1].upper() + key[1:]
            for method, meta in project.methods.items():
                node = project.ast.get(method)
                source = text(node)
                if project.resolve_type(name, meta['module'], meta['file']) != tid or not re.search(r'\b' + re.escape(name) + r'\s*\.\s*values\s*\(', source) or re.search(r'\b(?:sort|reverse|sorted)\s*\(', source):
                    continue
                for loop in walk(node):
                    if loop.type != 'enhanced_for_statement' or not re.fullmatch(re.escape(name) + r'\s*\.\s*values\s*\(\s*\)', text(loop.child_by_field_name('value'))):
                        continue
                    body = loop.child_by_field_name('body')
                    if any(child.type in ('if_statement', 'switch_expression', 'continue_statement', 'break_statement', 'return_statement') for child in walk(body)):
                        continue
                    item = text(loop.child_by_field_name('name'))
                    calls = [child for child in walk(body) if child.type == 'method_invocation']
                    def argument(call):
                        args = call.child_by_field_name('arguments')
                        return text(args.named_children[0]) if args is not None and len(args.named_children) == 1 else ''
                    direct = any(text(call.child_by_field_name('name')) == 'add'
                                 and argument(call) == item for call in calls)
                    projected = any(text(call.child_by_field_name('name')) == 'set' + key[:1].upper() + key[1:]
                                    and re.fullmatch(re.escape(item) + r'\.' + getter + r'\(\)', argument(call)) for call in calls)
                    if direct or projected:
                        proof = method + ':' + str(loop.start_point.row + 1)
                        break
                if proof:
                    break
            cache[tid] = proof
        if cache[tid]:
            output.append((values[position][key], members[position], cache[tid]))
    return output[0] if len(output) == 1 else None


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


def date_interval(phrase, clock=None):
    if re.search(r'\btoday\b', phrase, re.I) and isinstance(clock, datetime):
        return clock.replace(hour=0, minute=0, second=0, microsecond=0), clock.replace(hour=23, minute=59, second=59, microsecond=0)
    months = {name.lower(): index for index, name in enumerate(calendar.month_name) if name}
    names = '|'.join(months)
    found = re.search(r'\b(' + names + r')\s*(?:[—–-]|through|to)\s*(' + names + r')\s+(\d{4})\b', phrase, re.I)
    if found:
        start, end, year = months[found[1].lower()], months[found[2].lower()], int(found[3])
        if start <= end:
            return datetime(year, start, 1), datetime(year, end, calendar.monthrange(year, end)[1], 23, 59, 59)
    return None


def filter_bindings(project, mid, action, clock=None):
    match = re.search(r'\bfilter(?:ed)?\b(?:\s+by)?\s+(.*)', action, re.I)
    if not match:
        return []
    phrase = match[1]
    canonical = lambda word: {'bought': 'purchase', 'buy': 'purchase', 'statu': 'state', 'status': 'state'}.get(word, word)
    words = {canonical(word) for word in ntoks(phrase)}
    interval = date_interval(phrase, clock)
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
                concepts = {canonical(word) for word in concepts}
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
                            enum_type = obj.get('__enum_type__')
                            owner_name = project.nodes[enum_type]['fqn'] if enum_type else owner
                            owner_words = {canonical(word) for word in ntoks(owner_name.split('.')[-1])}
                            if not label or not label <= words or not owner_words & concepts or (entity and not owner_words & entity):
                                continue
                            scalars = [v for k, v in obj.items() if not k.startswith('__') and isinstance(v, int) and not isinstance(v, bool)]
                            if len(scalars) == 1:
                                constants.append((scalars[0], name, len(owner_words - concepts - entity)))
                        if constants:
                            specificity = min(score for _, _, score in constants)
                            constants = [(value, name) for value, name, score in constants if score == specificity]
                        if len({repr(v) for v, _ in constants}) == 1:
                            value, reference = constants[0]
                        elif interval and 'date' in concepts:
                            boundary = set(ntoks(rhs))
                            endpoint = interval[0] if 'start' in boundary else interval[1] if 'end' in boundary else None
                            if endpoint is not None:
                                value = Engine.coerce(endpoint.isoformat(sep=' '), params[rhs])
                                if re.search(r'\btoday\b', phrase, re.I):
                                    reference += ':context.clock'
                    bindings.append((key, value, reference, match[0]))
                candidates.append((len(concepts & words), bindings))
        if candidates:
            best = max(score for score, _ in candidates)
            candidates = [bindings for score, bindings in candidates if score == best]
        if len(candidates) == 1:
            output.extend(candidates[0])
        elif len(candidates) > 1:
            ambiguous = {key: (key, U, reference, quote) for candidate in candidates
                         for key, _, reference, quote in candidate}
            output.extend(ambiguous.values())
    return output
