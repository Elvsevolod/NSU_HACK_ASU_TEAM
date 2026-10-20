"""Bounded, cycle-safe call contexts that retain observed heap type evidence."""
from .state import U


def fingerprint(value):
    seen={};remaining=[4096]
    def visit(item,depth=0):
        remaining[0]-=1
        if remaining[0]<0 or depth>40:return ('context-budget',)
        if item is U:return ('unknown',)
        if item is None or type(item) in (str,int,float,bool):return (type(item).__name__,item)
        if isinstance(item,(dict,list,tuple,set)):
            key=id(item)
            if key in seen:return ('alias',seen[key])
            seen[key]=len(seen)
            if isinstance(item,dict):
                contents=tuple((visit(key,depth+1),visit(child,depth+1)) for key,child in sorted(item.items(),key=lambda pair:(type(pair[0]).__name__,str(pair[0]))))
            else:
                values=sorted(item,key=lambda v:(type(v).__name__,str(v))) if isinstance(item,set) else item
                contents=tuple(visit(child,depth+1) for child in values)
            attributes=getattr(item,'__dict__',{})
            # Allocation tokens are not data. Alias structure is captured above.
            metadata=tuple((name,visit(attributes[name],depth+1)) for name in
                ('kinds','component','opaque','fixed_size','flavor','structural_version','value_types',
                 '_native_field_kinds','_field_reference_types','_unchecked_generic_fields') if name in attributes)
            return (type(item).__name__,contents,metadata)
        if hasattr(item,'start_byte') and hasattr(item,'end_byte'):return ('source-node',item.type,item.start_byte,item.end_byte)
        return (type(item).__name__,str(item))
    return visit(value)
