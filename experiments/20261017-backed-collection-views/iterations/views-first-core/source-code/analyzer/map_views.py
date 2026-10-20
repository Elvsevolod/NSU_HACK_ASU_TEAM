"""Native Map views retain their backing object; iteration order stays explicit."""
from .java_collections import JavaMapView,JavaMapEntry,JavaMapIterator
from .map_keys import key_spec,same_key
from .boxed_values import value_kind,boxed_equal
from .java_exceptions import JavaThrow
from .state import U


def unresolved(obj,kind,mutates=False):
    obj.last_issue=kind
    mapping=obj.view.backing if isinstance(obj,JavaMapIterator) else obj.backing
    if mutates:mapping.invalidate()
    return True,U


def iterator_next(iterator,choose=None):
    iterator.last_issue=None
    mapping=iterator.view.backing
    if iterator.expected is None:
        iterator.last=U
        return unresolved(iterator,'unknown_iterator_modification')[1]
    if iterator.expected!=mapping.structural_version:
        if any(iterator.expected<version<=mapping.structural_version for version in mapping.uncertain_versions):
            iterator.last=U
            return unresolved(iterator,'unknown_iterator_modification')[1]
        raise JavaThrow({'__type__':'ConcurrentModificationException'})
    if not isinstance(iterator.remaining,list):
        iterator.last=U
        return unresolved(iterator,'unknown_iterator_contents')[1]
    if not iterator.remaining:raise JavaThrow({'__type__':'NoSuchElementException'})
    if len(iterator.remaining)>1 and not isinstance(mapping.order,list):
        selected=choose('unordered-map-next',list(range(len(iterator.remaining)))) if choose else None
        if selected is None:
            iterator.remaining=U
            iterator.last=U
            return unresolved(iterator,'unordered_map_iteration')[1]
    else:selected=0
    key=iterator.remaining.pop(selected)
    slot=mapping.slot(key)
    if slot is U or slot is None:return unresolved(iterator,'unknown_iterator_contents')[1]
    iterator.last=key
    if iterator.view.kind=='keys':return slot['key']
    if iterator.view.kind=='values':return slot['value']
    return JavaMapEntry(mapping,key)


def view_library(name,obj,args,key_type,value_type,text_equal,choose=None):
    obj.last_issue=None
    if isinstance(obj,JavaMapIterator):
        mapping=obj.view.backing
        if name=='next' and not args:return True,iterator_next(obj,choose)
        if name=='hasNext' and not args:
            return (True,bool(obj.remaining)) if isinstance(obj.remaining,list) else unresolved(obj,'unknown_iterator_contents')
        if name=='remove' and not args:
            if obj.last is U or obj.expected is None:return unresolved(obj,'unknown_iterator_removal',True)
            if obj.last is None:raise JavaThrow({'__type__':'IllegalStateException'})
            if obj.expected!=mapping.structural_version:
                if any(obj.expected<version<=mapping.structural_version for version in mapping.uncertain_versions):
                    return unresolved(obj,'unknown_iterator_modification',True)
                raise JavaThrow({'__type__':'ConcurrentModificationException'})
            slot=mapping.slot(obj.last)
            if slot is U or slot is None:return unresolved(obj,'unknown_iterator_removal',True)
            mapping.remove(obj.last)
            obj.expected=mapping.structural_version;obj.last=None
            return True,None
        return unresolved(obj,'unsupported_iterator_operation',name not in ('equals','hashCode','toString','getClass'))
    mapping=obj.backing
    if isinstance(obj,JavaMapEntry):
        if obj.version!=mapping.mutation_version:
            return unresolved(obj,'entry_after_map_modification',name=='setValue')
        slot=mapping.slot(obj.key)
        if slot is U or slot is None:return unresolved(obj,'unknown_entry_mapping',name=='setValue')
        if name=='getKey' and not args:return True,slot['key']
        if name=='getValue' and not args:return True,slot['value']
        if name=='setValue' and len(args)==1:
            old=mapping.put(obj.key,args[0],value_kind(args[0],value_type))
            obj.version=mapping.mutation_version
            return True,old
        return unresolved(obj,'unsupported_entry_operation',name not in ('equals','hashCode','toString','getClass'))
    if name=='clear' and not args:mapping.clear_mappings();return True,None
    if name=='add' and len(args)==1:raise JavaThrow({'__type__':'UnsupportedOperationException'})
    if name=='iterator' and not args:return True,JavaMapIterator(obj)
    if not isinstance(mapping.mapping,dict):return unresolved(obj,'unknown_map_view_state',name in ('remove','removeAll','retainAll','removeIf'))
    entries=mapping.entries()
    if name=='size' and not args:return True,len(entries)
    if name=='isEmpty' and not args:return True,not entries
    if name in ('contains','remove') and len(args)==1:
        if obj.kind=='keys':
            key=key_spec(args[0],key_type)
            slot=mapping.slot(key) if key is not None else U
            if slot is U:return unresolved(obj,'unknown_view_key',name=='remove')
            found=slot is not None
            if name=='remove' and found:mapping.remove(key)
            return True,found
        if obj.kind=='values':
            kind=value_kind(args[0],value_type)
            matches=[boxed_equal(args[0],entry['value'],kind,entry.get('value_kind'),text_equal) for entry in entries]
        elif isinstance(args[0],JavaMapEntry):
            other=args[0];slot=other.backing.slot(other.key)
            if other.version!=other.backing.mutation_version or slot is U or slot is None:
                return unresolved(obj,'unknown_entry_equality',name=='remove')
            matches=[False if same_key(entry,other.key) is False else U if same_key(entry,other.key) is U else
                     boxed_equal(slot['value'],entry['value'],slot.get('value_kind'),entry.get('value_kind'),text_equal) for entry in entries]
        else:return unresolved(obj,'unsupported_entry_equality',name=='remove')
        if name=='contains':return (True,True) if True in matches else unresolved(obj,'unknown_view_value_equality') if U in matches else (True,False)
        if U in matches:return unresolved(obj,'unknown_view_value_equality',True)
        indices=[index for index,match in enumerate(matches) if match]
        if not indices:return True,False
        if len(indices)>1 and not isinstance(mapping.order,list):
            index=choose('unordered-value-remove',indices) if choose else None
            if index is None:return unresolved(obj,'unordered_view_removal',True)
        else:index=indices[0]
        mapping.remove(entries[index])
        return True,True
    return unresolved(obj,'unsupported_map_view_operation',name not in ('equals','hashCode','toString','getClass','stream','parallelStream','spliterator','toArray'))
