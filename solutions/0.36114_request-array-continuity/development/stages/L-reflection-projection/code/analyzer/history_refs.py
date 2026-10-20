"""Response ownership survives flattening, including empty collections."""
from dataclasses import dataclass, asdict
import re

from .java_collections import schema_type, semantic_view
from .state import U


def object_scope(project, item, obj):
    entry=item.get('entry')
    meta=project.methods.get(entry,{}) if isinstance(entry,str) else {}
    written=schema_type(obj)
    tid=project.resolve_type(written,meta.get('module',''),meta.get('file')) if isinstance(written,str) else None
    deployment=project.ix.unit_of(entry) if entry in project.methods else project.nodes.get(tid,{}).get('module','')
    return str(deployment),project.nodes.get(tid,{}).get('fqn',written),tid


def compatible_scope(project, mid, requested, item, obj=None, declared_type=None):
    """A same-named local schema disambiguates foreign services and forms."""
    from .provenance import entity_words
    target=project.methods[mid]
    local={tid for tid,node in project.nodes.items() if node.get('kind')=='type' and
           node.get('module')==target['module'] and entity_words(node.get('fqn',''))==set(requested)}
    if not local:return True
    if obj is not None:deployment,fqn,tid=object_scope(project,item,obj)
    else:
        meta=project.methods.get(item.get('entry'),{}) if isinstance(item.get('entry'),str) else {}
        tid=project.resolve_type(declared_type,meta.get('module',''),meta.get('file')) if declared_type else None
        deployment=project.ix.unit_of(item['entry']) if item.get('entry') in project.methods else ''
        fqn=project.nodes.get(tid,{}).get('fqn',declared_type)
    qualified={project.nodes[tid]['fqn'] for tid in local}
    if fqn not in qualified:return False
    # Equal simple names cannot establish cross-deployment identity. A fully
    # qualified common DTO may cross a proven source HTTP/UI boundary.
    return not deployment or deployment==str(project.ix.unit_of(mid)) or tid in local


@dataclass(frozen=True)
class ObjectRef:
    deployment: str
    qualified_type: str
    identity: tuple
    producer: str
    response_path: str
    position: int | None
    ui_scope: str | None = None


@dataclass(frozen=True)
class CollectionRef:
    deployment: str
    element_types: tuple
    producer: str
    response_path: str
    object_paths: tuple
    size: int
    complete: bool
    ui_scope: str | None = None


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
    if not isinstance(entry, str):entry = None
    meta = project.methods.get(entry, {})
    deployment = project.ix.unit_of(entry) if entry in project.methods else ''
    producer = str(item.get('step', index)) + ':' + (entry or 'unresolved')
    base = 'history[' + str(index) + '].result'
    observed = list(objects(item.get('result', U), base))
    refs = []
    for path, obj in observed:
        written = schema_type(obj)
        _, fqn, tid = object_scope(project,item,obj)
        ids = tuple((key, repr(obj.get(key, U))) for key, field in project.type_fields.get(tid, {}).items() if field.get('id'))
        positions = re.findall(r'\[(\d+)\]', path[len(base):])
        refs.append(ObjectRef(str(deployment), fqn, ids, producer, path,
                              int(positions[-1]) if positions else None,item.get('ui_scope')))
    written = meta.get('return_raw', '')
    declared = tuple(dict.fromkeys(project.nodes[tid]['fqn']
        for name in re.findall(r'[\w.$]+', written)
        if (tid := project.resolve_type(name, meta.get('module', '' ))) in project.type_fields))
    groups = []
    for path, values in containers(item.get('result', U), base):
        members = tuple(ref.response_path for ref in refs if re.fullmatch(r'\[\d+\]',ref.response_path[len(path):])
                        and ref.response_path.startswith(path+'['))
        types = tuple(dict.fromkeys(ref.qualified_type for ref in refs if ref.response_path in members))
        if not types:
            parents=[(parent,obj) for parent,obj in observed if path.startswith(parent+'.')]
            if parents:
                parent,obj=max(parents,key=lambda pair:len(pair[0]))
                _,_,owner=object_scope(project,item,obj)
                layout=None
                for name in re.findall(r'\.([\w$]+)',path[len(parent):]):
                    layout=project.type_fields.get(owner,{}).get(name)
                    if not layout:break
                    written=layout['type']
                    names=re.findall(r'[\w.$]+',written)
                    owner=project.resolve_type(names[-1],project.nodes[layout['declaring_type']]['module'],layout['file']) if names else None
                types=(project.nodes[owner]['fqn'],) if layout and owner else ()
            else:types=declared
        groups.append(CollectionRef(str(deployment), types, producer, path, members,
                                    len(values), not contains_unknown(values),item.get('ui_scope')))
    return {'objects': [asdict(ref) for ref in refs], 'collections': [asdict(ref) for ref in groups]}
