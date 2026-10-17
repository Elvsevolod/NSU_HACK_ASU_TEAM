"""Join conservative Java branches without disconnecting caller-owned objects."""
from copy import deepcopy
from .java_collections import JavaMap,JavaRecord,JavaMapView,JavaMapEntry,JavaMapIterator
from .state import U


def owned_objects(value,seen=None):
    seen=set() if seen is None else seen
    if not isinstance(value,(dict,list,tuple)) or id(value) in seen:return
    seen.add(id(value))
    if isinstance(value,(JavaMap,JavaRecord,JavaMapView,JavaMapEntry,JavaMapIterator)):yield value
    children=list(value.values()) if isinstance(value,dict) else list(value)
    if isinstance(value,(JavaMapView,JavaMapEntry)):children.append(value.backing)
    if isinstance(value,JavaMapIterator):children.append(value.view)
    for child in children:yield from owned_objects(child,seen)


def widen(value):
    if isinstance(value,JavaMap):value.invalidate()
    elif isinstance(value,JavaRecord):
        for key in value:
            if key!='__type__':value[key]=U
    elif isinstance(value,(JavaMapView,JavaMapEntry)):value.backing.invalidate()
    elif isinstance(value,JavaMapIterator):
        value.view.backing.invalidate();value.remaining=U;value.last=U;value.expected=None


def source_nodes(value,seen=None):
    seen=set() if seen is None else seen
    if id(value) in seen:return
    seen.add(id(value))
    if hasattr(value,'start_point') and hasattr(value,'type'):
        yield value;return
    children=list(value.values()) if isinstance(value,dict) else list(value) if isinstance(value,(list,tuple)) else []
    if isinstance(value,(JavaMapView,JavaMapEntry)):children.append(value.backing)
    if isinstance(value,JavaMapIterator):children.append(value.view)
    for child in children:
        yield from source_nodes(child,seen)


def clone_environment(value):
    memo={id(node):node for node in source_nodes(value)}
    return deepcopy(value,memo),memo


def join_environment(original,left,right,left_copies,right_copies,merge):
    memo={}
    joined=merge(left,right,memo=memo)
    originals=list(owned_objects(original))
    updates=[]
    for value in originals:
        key=id(value)
        if key in left_copies and key in right_copies:
            updates.append((value,merge(left_copies[key],right_copies[key],memo=memo)))
    # One possible object joining with several others creates a conditional
    # alias. A later mutation must not leave any overlapping view known.
    origins={}
    for pair,result in memo.items():
        for side,key in enumerate(pair):origins.setdefault((side,key),{})[id(result)]=result
    for group in origins.values():
        if len(group)>1:
            for value in group.values():widen(value)
    canonical={id(result):value for value,result in updates if isinstance(result,(JavaMap,JavaRecord,JavaMapView,JavaMapEntry,JavaMapIterator)) and type(value) is type(result)}
    canonical.update((id(node),node) for node in source_nodes(joined))
    for value,result in updates:
        if id(result) not in canonical:
            widen(value);continue
        fields={key:deepcopy(item,canonical) for key,item in result.items()}
        attributes={key:deepcopy(item,canonical) for key,item in result.__dict__.items()}
        value.clear();value.update(fields)
        value.__dict__.clear();value.__dict__.update(attributes)
    original.update(deepcopy(joined,canonical))
