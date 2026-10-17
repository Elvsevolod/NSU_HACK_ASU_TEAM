"""Resolve response references by declared entity and explicit selection language."""
import re
from baseline_nlp import ntoks
from .state import U
from .project import text


def source_string(project, value):
    """Evaluate only source-proven pure toString/getter expressions for composite IDs."""
    active = set()

    def invoke(obj, tid, name):
        signature = (tid, name)
        if tid is None or signature in active:
            return U
        methods = [m for m in project.methods_of(tid, name) if not project.parameters(m)]
        if not methods:
            if name == 'name' and tid in project.enum_members and isinstance(obj, dict):
                return obj.get('__enum__', '').rsplit('.', 1)[-1] or U
            return U
        if len(methods) != 1:
            return U
        node = project.ast.get(methods[0])
        body = node.child_by_field_name('body') if node else None
        statements = [s for s in body.named_children if s.type not in ('line_comment', 'block_comment')] if body else []
        if len(statements) != 1 or statements[0].type != 'return_statement':
            return U
        active.add(signature)
        result = expression(statements[0].named_children[0], obj, tid)
        active.remove(signature)
        return result

    def expression(node, obj, tid):
        kind = node.type
        if kind == 'this':
            return obj
        if kind == 'identifier':
            return obj.get(text(node), U)
        if kind == 'field_access' and text(node.child_by_field_name('object')) == 'this':
            return obj.get(text(node.child_by_field_name('field')), U)
        if kind == 'string_literal':
            import json
            try:
                return json.loads(text(node))
            except ValueError:
                return U
        if kind == 'binary_expression' and text(node.child_by_field_name('operator')) == '+':
            left, right = expression(node.child_by_field_name('left'), obj, tid), expression(node.child_by_field_name('right'), obj, tid)
            if left is U or right is U or not isinstance(left, (str, int)) or not isinstance(right, (str, int)):
                return U
            return str(left) + str(right) if isinstance(left, str) or isinstance(right, str) else left + right
        if kind == 'method_invocation':
            args = node.child_by_field_name('arguments')
            if args and args.named_children:
                return U
            receiver = node.child_by_field_name('object')
            receiver_value = obj if receiver is None else expression(receiver, obj, tid)
            target = tid
            if receiver is not None and receiver.type == 'identifier':
                field = project.type_fields.get(tid, {}).get(text(receiver), {})
                target = project.resolve_type(field.get('type', ''), project.nodes[tid].get('module'), project.nodes[tid].get('file'))
            if not isinstance(receiver_value, dict):
                return U
            return invoke(receiver_value, target, text(node.child_by_field_name('name')))
        return U

    if not isinstance(value, dict):
        return U
    tid = project.resolve_type(value.get('__type__', ''), '')
    result = invoke(value, tid, 'toString')
    return result if isinstance(result, str) else U


def contains_unknown(value):
    if value is U:
        return True
    if isinstance(value, dict):
        return any(contains_unknown(v) for k, v in value.items() if not str(k).startswith('__') or k == '__json__')
    return isinstance(value, (list, tuple)) and any(contains_unknown(v) for v in value)


def entity_words(value):
    value = re.sub(r'(Controller|Service|Impl|Request|Response|Dto|Info|Entity)$', '', value.split('.')[-1], flags=re.I)
    return set(ntoks(value)) - {'get', 'find', 'query', 'lookup', 'read', 'create', 'new', 'id', 'key'}


def objects(value, path):
    if isinstance(value, dict):
        if value.get('__type__') and '__symbol__' not in value:
            yield path, value
        for key, child in value.items():
            if not str(key).startswith('__'):
                yield from objects(child, path + '.' + str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from objects(child, path + '[' + str(index) + ']')


def ordinal_for(action, requested):
    for candidate in re.finditer(r'\b(first|second|third|fourth)\b(?!-)', action, re.I):
        following = re.split(r'[,;()]|\b(?:for|with|without|on|of)\b', action[candidate.end():], 1, flags=re.I)[0]
        if requested & set(ntoks(following)[:4]):
            return candidate
    return None


def new_for(action, requested):
    for candidate in re.finditer(r'\b(?:(?:newly|just|recently)\s+(?:created|added|registered|booked)|new|latest)\b', action, re.I):
        following = re.split(r'[,;()]|\b(?:for|with|without|on|of)\b', action[candidate.end():], 1, flags=re.I)[0]
        if requested & set(ntoks(following)[:4]):
            return candidate
    return None


def history_value(project, mid, field, action, history, requested_entity=None, use_selection=True):
    """Only typed matching owners qualify. Multiple objects remain ambiguous."""
    norm = lambda value: re.sub(r'[^a-z0-9]', '', value.lower())
    requested = set(requested_entity) if requested_entity else entity_words(field[:-4] if field.endswith('Name') else field)
    if not requested:
        route_entities = set()
        names = {field, *(p['wire_name'] for p in project.http_parameters(mid) if p['name'] == field)}
        for handler, _, route in project.ix.handlers:
            if handler != mid:
                continue
            for index, segment in enumerate(route):
                if segment.strip('{}').split(':', 1)[0] in names and index > 0:
                    previous = route[index - 1]
                    if not previous.startswith('{'):
                        route_entities.add(tuple(sorted(entity_words(previous))))
        requested = set(next(iter(route_entities))) if len(route_entities) == 1 else entity_words(project.nodes[project.methods[mid]['owner']]['fqn'])
    candidates, by_step, creations, confirmed_creations = {}, {}, {}, {}
    for index, item in enumerate(history):
        observed = [*objects(item.get('result', U), 'history[' + str(index) + '].result'),
                    *objects(item.get('created_objects', []), 'history[' + str(index) + '].created_objects')]
        for path, obj in observed:
            owner = entity_words(obj['__type__'])
            tid = project.resolve_type(obj['__type__'], project.methods[mid]['module'])
            declared = project.type_fields.get(tid, {})
            ids = [k for k, meta in declared.items() if meta.get('id')]
            keys = [k for k in obj if norm(k) == norm(field)]
            named_reference = norm(field).endswith('id') and norm(field) != 'id' and any(k in declared for k in keys)
            if not named_reference and (not requested or not owner or not requested & owner):
                continue
            if norm(field) in ('key', 'id') and owner != requested:
                continue
            if not keys and owner == requested and (norm(field).endswith('id') or norm(field) in ('key', 'id')):
                keys = ids
            if not keys and owner == requested and field.endswith('Name') and 'name' in declared:
                from .nl_inputs import field_role, intermediate_field
                if field_role(field) is None and field != intermediate_field(project.request_fields(mid)):
                    keys = ['name']
            for key in keys:
                value = obj.get(key, U)
                if contains_unknown(value) or value is None:
                    continue
                rendered = source_string(project, value) if isinstance(value, dict) and '__symbol__' not in value else value
                canonical = rendered if rendered is not U else value
                identity = (tuple(sorted(owner)), repr(canonical))
                candidates[identity] = (path + '.' + key, value, index)
                by_step.setdefault(index, [])
                if identity not in by_step[index]:
                    by_step[index].append(identity)
                if owner == requested and ('.created_objects' in path or re.search(r'\b(?:create|add|register|book|reserve|insert)\b', item.get('action', ''), re.I)):
                    creations.setdefault(identity, index)
                if owner == requested and '.created_objects' in path:
                    confirmed_creations[identity] = index
    identities = list(candidates)
    ordinal = ordinal_for(action, requested)
    wants_new = new_for(action, requested)
    if use_selection and not ordinal and not wants_new and (norm(field).endswith('id') or norm(field) in ('key', 'id')):
        definite = any(requested <= set(ntoks(re.split(r'[,;()]|\b(?:for|with|without|on)\b', action[match.end():], 1, flags=re.I)[0])[:4])
                       for match in re.finditer(r'\b(?:the|this|same)\b', action, re.I))
        latest_creation = max(confirmed_creations.values(), default=-1) if definite else -1
        for index in range(len(history) - 1, -1, -1):
            if index < latest_creation:
                break
            selected = history[index].get('selected_objects', [])
            for position, item in enumerate(selected if isinstance(selected, list) else []):
                if item.get('entity') == sorted(requested) and item.get('value', U) is not U and not contains_unknown(item['value']):
                    return 'history[' + str(index) + '].selected_objects[' + str(position) + '].value', item['value']
        if definite and confirmed_creations:
            latest = max(confirmed_creations.values())
            created = [identity for identity, index in confirmed_creations.items() if index == latest]
            if len(created) == 1:
                return candidates[created[0]][:2]
    if wants_new:
        created = [key for key in identities if key in creations]
        if not created:
            return None
        newest = max(creations[key] for key in created)
        identities = sorted(created, key=lambda key: creations[key]) if ordinal else [key for key in created if creations[key] == newest]
    elif ordinal:
        # Use the latest collection's actual order, even after later single-object reads.
        collections = [keys for keys in by_step.values() if len(keys) > 1]
        if collections:
            identities = collections[-1]
    values = [candidates[key] for key in identities]
    if ordinal and values:
        ordered = values
        position = ('first', 'second', 'third', 'fourth').index(ordinal[1].lower())
        return ordered[position][:2] if position < len(ordered) else None
    if len(values) == 1:
        return values[0][:2]
    return None


def selected_field(project, field, params, history):
    """A value from a selected object needs a matching identifier in this request."""
    for index in range(len(history) - 1, -1, -1):
        selected = history[index].get('selected_objects', [])
        for position, item in enumerate(selected if isinstance(selected, list) else []):
            obj = item.get('object', {})
            tid = project.resolve_type(obj.get('__type__', ''), '') if isinstance(obj, dict) else None
            if field not in project.type_fields.get(tid, {}):
                continue
            linked = any(entity_words(key) == set(item.get('entity', [])) and value == item.get('value') for key, value in params.items())
            value = obj.get(field, U)
            if linked and value is not U and not contains_unknown(value):
                return 'history[' + str(index) + '].selected_objects[' + str(position) + '].object.' + field, value
    return None


def history_role_value(project, field, params, history):
    """Carry role values only from an object whose declared ID matches this request."""
    from .nl_inputs import field_role
    role = field_role(field)
    if role not in ('origin', 'destination', 'via') and field.lower() != 'date':
        return None
    identifiers = {key: value for key, value in params.items()
                   if key.lower().endswith('id') and value is not U and value is not None}
    if not identifiers:
        return None
    for index in range(len(history) - 1, -1, -1):
        previous = history[index].get('parameters', {})
        shared = identifiers.keys() & previous.keys()
        if shared and all(previous[key] == identifiers[key] for key in shared):
            values = [(key, value) for key, value in previous.items() if field_role(key) == role
                      and value is not None and value is not U and not contains_unknown(value)]
            if len({repr(value) for _, value in values}) == 1:
                return 'history[' + str(index) + '].parameters.' + values[0][0], values[0][1]
        matches = []
        for path, obj in objects(history[index].get('result', U), 'history[' + str(index) + '].result'):
            tid = project.resolve_type(obj['__type__'], '')
            declared = project.type_fields.get(tid, {})
            linked = False
            for key, expected in identifiers.items():
                value = obj.get(key, U) if key in declared else U
                if isinstance(value, dict) and '__symbol__' not in value:
                    value = source_string(project, value)
                if value is not U and value == expected:
                    linked = True
            if not linked:
                continue
            if field.lower() == 'date':
                filters = [(key, value) for key, value in previous.items() if field_role(key) == 'date'
                           and value is not None and value is not U and not contains_unknown(value)]
                if len({repr(value) for _, value in filters}) == 1:
                    return 'history[' + str(index) + '].parameters.' + filters[0][0], filters[0][1]
            for key in declared:
                value = obj.get(key, U)
                if field_role(key) == role and value is not U and value is not None and not contains_unknown(value):
                    matches.append((path + '.' + key, value))
        if matches:
            return matches[0] if len({repr(value) for _, value in matches}) == 1 else None
    return None
