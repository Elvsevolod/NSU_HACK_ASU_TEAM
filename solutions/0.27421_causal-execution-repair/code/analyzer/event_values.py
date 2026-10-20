"""Compact observed argument facts; object shape never claims reference identity."""
from .state import U
from .java_collections import schema_type


def witness(values):
    result=[]
    for value in values:
        if value is U:fact={'kind':'unknown'}
        elif value is None or type(value) in (str,int,float,bool):fact={'kind':type(value).__name__,'value':value}
        elif isinstance(value,dict) and '__symbol__' in value:
            fact={'kind':'symbolic','type':value.get('__type__'),'symbol':value['__symbol__']}
        elif isinstance(value,dict):fact={'kind':'object','type':schema_type(value),'fields':[str(key) for key in value if not str(key).startswith('__')]}
        elif isinstance(value,list):fact={'kind':'collection','size':None if getattr(value,'opaque',False) else len(value)}
        else:fact={'kind':'opaque','type':type(value).__name__}
        result.append(fact)
    return {'version':'value-witness/1','arguments':result}
