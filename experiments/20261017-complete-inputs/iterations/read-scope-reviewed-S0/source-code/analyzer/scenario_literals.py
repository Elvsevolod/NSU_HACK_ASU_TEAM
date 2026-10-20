"""Explicit structured literals, restricted by declared source input fields."""
import re

from .nl_inputs import field_role, words
from .project import text, walk
from .provenance import entity_words
from .state import U
from .structured_literals import literal_value


def csv_fields(project, mid):
    """Only fields split by a literal delimiter inside their declaring DTO."""
    cache = project.__dict__.setdefault('_csv_inputs', {})
    if mid in cache:
        return cache[mid]
    roots = {project.resolve_type(p['type'], project.methods[mid]['module'], project.methods[mid]['file'])
             for p in project.http_parameters(mid) if p['kind'] == 'RequestBody'} - {None}
    result = {}
    for method, meta in project.methods.items():
        if meta['owner'] not in roots or method not in project.ast:
            continue
        for call in walk(project.ast[method]):
            if call.type != 'method_invocation' or text(call.child_by_field_name('name')) != 'split':
                continue
            receiver = call.child_by_field_name('object')
            field = text(receiver).removeprefix('this.')
            args = call.child_by_field_name('arguments')
            if field not in project.type_fields[meta['owner']] or args is None or len(args.named_children) != 1:
                continue
            if text(args.named_children[0]) != '\",\"':
                continue
            alias = meta['name'][3:] if meta['name'].startswith('get') else ''
            result[field] = {'delimiter': ',', 'label': alias, 'reference': method + ':' + str(call.start_point.row + 1)}
    cache[mid] = result
    return result


def field_labels(fields, field):
    """A unique ordered field-name projection may omit one interior word."""
    split = lambda name: re.findall(r'[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+', name)
    parts = split(field)
    labels = []
    for index in range(1, len(parts) - 1):
        candidate = [part.lower() for part in parts[:index] + parts[index + 1:]]
        owners = [name for name in fields if set(candidate) <= {part.lower() for part in split(name)}]
        if owners == [field]:
            labels.append(' '.join(candidate))
    return labels


def explicit_chain(project, mid, action):
    candidates = re.findall(r'\(([^()]*?(?:—|–|→|->)[^()]*)\)', action)
    for parameter in project.http_parameters(mid):
        if parameter['kind'] != 'RequestBody':
            continue
        label = re.sub(r'(?:Request|Dto|Info|Input)$', '', parameter['type'].split('.')[-1])
        parts = re.findall(r'[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+', label)
        phrase = r'[ _-]*'.join(map(re.escape, parts))
        if not phrase:
            continue
        found = re.search(r'\b' + phrase + r'\b\s+([^,;()]+?)(?=\s+(?:with|for|on)\b|$)', action, re.I)
        if found and re.search(r'—|–|→|->', found[1]):
            candidates.append(found[1])
    paths = {tuple(part.strip() for part in re.split(r'\s*(?:—|–|→|->)\s*', candidate)) for candidate in candidates}
    paths = [path for path in paths if len(path) >= 2 and all(re.fullmatch(r'[\w][\w .\'-]*', part) for part in path)]
    return paths[0] if len(paths) == 1 else None


def boolean_wire_fields(project, mid):
    """String parameters converted through java.lang.Boolean.parseBoolean."""
    cache = project.__dict__.setdefault('_boolean_wire_fields', {})
    if mid in cache:
        return cache[mid]
    result = {}
    node = project.ast.get(mid)
    meta = project.methods[mid]
    for call in walk(node) if node is not None else []:
        if call.type != 'method_invocation' or text(call.child_by_field_name('name')) != 'parseBoolean':
            continue
        receiver = text(call.child_by_field_name('object'))
        if receiver not in ('Boolean', 'java.lang.Boolean') or receiver == 'Boolean' and project.resolve_type('Boolean', meta['module'], meta['file']) is not None:
            continue
        args = call.child_by_field_name('arguments')
        if args is not None and len(args.named_children) == 1 and args.named_children[0].type == 'identifier':
            result[text(args.named_children[0])] = mid + ':' + str(call.start_point.row + 1)
    cache[mid] = result
    return result


def structured_bindings(project, mid, action):
    fields = project.request_fields(mid)
    output = {}
    for field, typ in fields.items():
        value, quote = literal_value(action, field, typ, field_labels(fields, field))
        if value is not U:
            output[field] = (value, 'action:declared-field-label', quote)
        if typ.split('.')[-1] != 'String' or 'time' not in words(field):
            continue
        role = words(field)
        label = r'(?:depart(?:ing|ure)?|start(?:\s+time)?)' if role & {'start', 'departure'} else r'(?:arriv(?:ing|al|e)|end(?:\s+time)?)' if role & {'end', 'arrival'} else None
        matches = list(re.finditer(r'\b' + label + r'\s+(?:at\s+)?((?:[01]\d|2[0-3]):[0-5]\d)\b', action, re.I)) if label else []
        if len({match[1] for match in matches}) == 1:
            output[field] = (matches[0][1], 'action:time-role-from-field', matches[0][0])
    collections = csv_fields(project, mid)
    for field, reference in boolean_wire_fields(project, mid).items():
        if fields.get(field, '').split('.')[-1] != 'String':
            continue
        parts = re.findall(r'[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+', field)
        if parts and parts[0].lower() in ('is', 'has'):
            parts = parts[1:]
        if not parts:
            continue
        phrase = r'\s+(?:(?:the|a|an)\s+)?'.join(map(re.escape, parts))
        matches = list(re.finditer(r'\b' + phrase + r'\b', action, re.I))
        values = {not bool(re.search(r'\b(?:no|not|without)\s*$', action[:match.start()], re.I)) for match in matches}
        if len(values) == 1:
            output[field] = ('true' if next(iter(values)) else 'false', reference, matches[0][0])
    for field, meta in collections.items():
        for typ in ('List<Integer>', 'List<Double>'):
            value, quote = literal_value(action, field, typ, (meta['label'],))
            if value is not U:
                output[field] = (','.join(map(str, value)), meta['reference'], quote)
                break
    chain = explicit_chain(project, mid, action)
    if chain:
        roles = {}
        for role in ('origin', 'destination', 'via'):
            matching = [field for field in fields if field_role(field) == role]
            if len(matching) == 1:
                roles[role] = matching[0]
        for role, value in [('origin', chain[0]), ('destination', chain[-1]), ('via', chain[1] if len(chain) == 3 else U)]:
            if role in roles and value is not U:
                output[roles[role]] = (value, 'action:explicit-chain', action)
        if 'origin' in roles and 'destination' in roles:
            shared = entity_words(roles['origin']) & entity_words(roles['destination'])
            shared -= {'start', 'end', 'source', 'destination', 'terminal', 'origin', 'name'}
            matching = [field for field, meta in collections.items() if shared & entity_words(meta['label'])]
            if len(matching) == 1:
                field = matching[0]
                output[field] = (','.join(chain), collections[field]['reference'], action)
    return output
