"""Resolve response references by declared entity and explicit selection language."""
import re
from baseline_nlp import ntoks
from .state import U


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


def history_value(project, mid, field, action, history):
    """Only typed matching owners qualify. Multiple objects remain ambiguous."""
    norm = lambda value: re.sub(r'[^a-z0-9]', '', value.lower())
    requested = entity_words(field)
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
    candidates, by_step, creations = {}, {}, {}
    for index, item in enumerate(history):
        for path, obj in objects(item.get('result', U), 'history[' + str(index) + '].result'):
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
            for key in keys:
                value = obj.get(key, U)
                if contains_unknown(value) or value is None:
                    continue
                identity = (obj['__type__'], key, repr(value))
                candidates[identity] = (path + '.' + key, value, index)
                by_step.setdefault(index, [])
                if identity not in by_step[index]:
                    by_step[index].append(identity)
                if owner == requested and re.search(r'\b(?:create|add|register|book|reserve|insert)\b', item.get('action', ''), re.I):
                    creations.setdefault(identity, index)
    identities = list(candidates)
    ordinal = re.search(r'\b(first|second|third|fourth)\b', action, re.I)
    wants_new = re.search(r'\b(?:newly|just|recently)\s+(?:created|added|registered|booked)|\b(?:new|latest)\b', action, re.I)
    if wants_new:
        created = [key for key in identities if key in creations]
        if created:
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
