"""Prove only native Map loops whose pure guards are false for every member.

This evaluator never invokes source code and never writes the execution heap.
An unsupported expression rejects the proof; ordinary replay then handles it.
"""
from .java_collections import JavaMap,JavaMapView,JavaMapEntry,JavaRecord
from .generic_types import type_parts
from .map_keys import key_spec
from .project import text
from .state import U
from .reference_types import collection_compatibility


class OutsideProof(Exception):pass


def prove(engine,node,view,env):
    if not isinstance(view,JavaMapView):return False
    source=view.backing
    if source.flavor not in ('HashMap','LinkedHashMap') or not isinstance(source.mapping,dict):return False
    entries=source.entries()
    if len(entries)>64:return False
    written=text(node.child_by_field_name('type'));base,parameters=type_parts(written)
    def fits(value,kind,typ):
        typ,_=type_parts(typ)
        if value is U:return False
        if value is None:return typ not in ('boolean','byte','short','int','long','char','float','double')
        if engine.standard_type(typ,'java.lang.Object'):return True
        scalar=engine.native_scalar_type(typ)
        if scalar:return scalar==kind
        compatibility=collection_compatibility(engine,value,typ)
        if compatibility is not None:return compatibility
        return isinstance(value,JavaRecord) and engine.record_proves_type(value,typ)
    entry_type=engine.standard_type(base,'java.util.Map.Entry') or base=='Map.Entry' and engine.standard_type('Map','java.util.Map')
    if view.kind=='entries' and (not entry_type or parameters is None or len(parameters)!=2):return False
    body=node.child_by_field_name('body')
    statements=[c for c in body.named_children if c.type not in ('line_comment','block_comment')] if body.type=='block' else [body]
    guards=[]
    def expression(n,local):
        if n is None:raise OutsideProof()
        kind,raw=n.type,text(n)
        if kind=='identifier':
            if raw in local:return local[raw]
            value=env.get(raw,U)
            if isinstance(value,JavaMap) and value.flavor in ('HashMap','LinkedHashMap') and isinstance(value.mapping,dict):return value,None
            raise OutsideProof()
        if kind=='null_literal':return None,None
        if kind in ('true','false'):return kind=='true','Boolean'
        if kind=='parenthesized_expression':return expression(n.named_children[0],local)
        if kind=='unary_expression' and raw.startswith('!'):
            value,_=expression(n.named_children[-1],local)
            if type(value) is not bool:raise OutsideProof()
            return not value,'Boolean'
        if kind=='binary_expression':
            op=text(n.child_by_field_name('operator'))
            left,_=expression(n.child_by_field_name('left'),local)
            if op in ('&&','||'):
                if type(left) is not bool:raise OutsideProof()
                if left==(op=='||'):return left,'Boolean'
                right,_=expression(n.child_by_field_name('right'),local)
                if type(right) is not bool:raise OutsideProof()
                return right,'Boolean'
            right,_=expression(n.child_by_field_name('right'),local)
            if op not in ('==','!=') or left is U or right is U:raise OutsideProof()
            if left is None or right is None:equal=left is None and right is None
            elif type(left) is bool and type(right) is bool:equal=left==right
            else:raise OutsideProof()
            return equal if op=='==' else not equal,'Boolean'
        if kind=='method_invocation':
            receiver,_=expression(n.child_by_field_name('object'),local)
            name=text(n.child_by_field_name('name'));args=n.child_by_field_name('arguments').named_children
            if isinstance(receiver,JavaMapEntry) and not args and name in ('getKey','getValue'):
                slot=receiver.backing.slot(receiver.key)
                if slot is U or slot is None:raise OutsideProof()
                return (slot['key'],slot['kind']) if name=='getKey' else (slot['value'],slot.get('value_kind'))
            if isinstance(receiver,JavaMap) and len(args)==1 and name in ('get','containsKey'):
                value,kind=expression(args[0],local)
                key=key_spec(value,kind)
                if key is None:raise OutsideProof()
                slot=receiver.slot(key)
                if slot is U:raise OutsideProof()
                if name=='containsKey':return slot is not None,'Boolean'
                return (None,None) if slot is None else (slot['value'],slot.get('value_kind'))
        raise OutsideProof()
    try:
        for entry in entries:
            if view.kind=='entries':
                if not fits(entry['key'],entry['kind'],parameters[0]) or not fits(entry['value'],entry.get('value_kind'),parameters[1]):return False
                item=JavaMapEntry(source,entry);actual=None
            else:
                item=entry['key'] if view.kind=='keys' else entry['value']
                actual=entry['kind'] if view.kind=='keys' else entry.get('value_kind')
                if not fits(item,actual,written):return False
            local={text(node.child_by_field_name('name')):(item,actual)}
            for statement in statements:
                if statement.type=='local_variable_declaration':
                    declared=text(statement.child_by_field_name('type'))
                    for variable in statement.named_children:
                        if variable.type!='variable_declarator':continue
                        value,kind=expression(variable.child_by_field_name('value'),local)
                        if not fits(value,kind,declared):raise OutsideProof()
                        local[text(variable.child_by_field_name('name'))]=value,kind
                elif statement.type=='if_statement' and statement.child_by_field_name('alternative') is None:
                    value,_=expression(statement.child_by_field_name('condition'),local)
                    if value is not False:raise OutsideProof()
                    guards.append({'line':statement.start_point.row+1,'key':entry['key'],'condition':text(statement.child_by_field_name('condition')),'value':False})
                else:raise OutsideProof()
    except OutsideProof:return False
    if entries and not guards:return False
    engine.effect_events.append({'model_version':'native-map-noop/1','operation':'foreach',
        'callsite':engine.method+':'+str(node.start_point.row+1),'iterations':len(entries),
        'guards':guards,'heap_roots':[],'resource_writes':[],'global_footprint':'none',
        'callbacks':[],'completions':['normal']})
    return True
