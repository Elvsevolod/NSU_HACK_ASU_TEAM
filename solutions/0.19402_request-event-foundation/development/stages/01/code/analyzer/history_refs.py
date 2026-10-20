"""Response ownership survives flattening, including empty collections."""
from dataclasses import dataclass, asdict
import re

from .java_collections import schema_type, semantic_view
from .state import U


@dataclass(frozen=True)
class ObjectRef:
    deployment: str
    qualified_type: str
    identity: tuple
    producer: str
    response_path: str
    position: int | None


@dataclass(frozen=True)
class CollectionRef:
    deployment: str
    element_types: tuple
    producer: str
    response_path: str
    object_paths: tuple
    size: int
    complete: bool


def containers(value, path, active=None):
    active = set() if active is None else active
    value = semantic_view(value)
    if not isinstance(value, (dict, list)) or id(value) in active:
        return
    active = active | {id(value)}
    if isinstance(value, list):
        yield path, value
        for index, child in enumerate(value):
            yield from containers(child, path + '[' + str(index) + ']', active)
    else:
        for key, child in value.items():
            if not str(key).startswith('__'):
                yield from containers(child, path + '.' + str(key), active)


def references(project, item, index):
    from .provenance import objects, contains_unknown
    entry = item.get('entry')
    meta = project.methods.get(entry, {})
    deployment = project.ix.unit_of(entry) if entry in project.methods else ''
    producer = str(item.get('step', index)) + ':' + (entry or 'unresolved')
    base = 'history[' + str(index) + '].result'
    observed = list(objects(item.get('result', U), base))
    refs = []
    for path, obj in observed:
        written = schema_type(obj)
        tid = project.resolve_type(written, meta.get('module', ''))
        fqn = project.nodes.get(tid, {}).get('fqn', written)
        ids = tuple((key, repr(obj.get(key, U))) for key, field in project.type_fields.get(tid, {}).items() if field.get('id'))
        positions = re.findall(r'\[(\d+)\]', path[len(base):])
        refs.append(ObjectRef(str(deployment), fqn, ids, producer, path,
                              int(positions[-1]) if positions else None))
    written = meta.get('return_raw', '')
    declared = tuple(dict.fromkeys(project.nodes[tid]['fqn']
        for name in re.findall(r'[\w.$]+', written)
        if (tid := project.resolve_type(name, meta.get('module', '' ))) in project.type_fields))
    groups = []
    for path, values in containers(item.get('result', U), base):
        members = tuple(ref.response_path for ref in refs if ref.response_path.startswith(path + '['))
        types = tuple(dict.fromkeys(ref.qualified_type for ref in refs if ref.response_path in members)) or declared
        groups.append(CollectionRef(str(deployment), types, producer, path, members,
                                    len(values), not contains_unknown(values)))
    return {'objects': [asdict(ref) for ref in refs], 'collections': [asdict(ref) for ref in groups]}
