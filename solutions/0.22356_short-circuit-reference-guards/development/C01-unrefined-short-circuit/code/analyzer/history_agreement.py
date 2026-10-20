"""Strict agreement of complete observations, never of the first alternative."""
from copy import deepcopy
from decimal import Decimal
import hashlib,json,math
from .state import U
from .java_collections import JsonObject


def key(value,active=None,include_origins=False):
    active=set() if active is None else active
    if value is U:return None
    if value is None:return ('null',)
    if type(value) in (bool,int,str):return (type(value).__name__,value)
    if isinstance(value,Decimal) or type(value) is float:
        if type(value) is float and not math.isfinite(value):return None
        if isinstance(value,Decimal) and not value.is_finite():return None
        return ('number',str(Decimal(str(value)).normalize()))
    if type(value) is dict or isinstance(value,(list,tuple,JsonObject)):
        if id(value) in active:return None
        active=active|{id(value)}
        if value=={'unknown':True} or value=={'missing':True}:return None
        if isinstance(value,dict):
            if any(type(k) is not str for k in value):return None
            items=[(k,key(v,active,include_origins)) for k,v in sorted(value.items())]
            if any(v is None for _,v in items):return None
            return ('object',getattr(value,'origin_type',None) if include_origins else None,tuple(items))
        items=[key(v,active,include_origins) for v in value]
        if any(v is None for v in items):return None
        return ('array',getattr(value,'order_known',True) if include_origins else None,tuple(items))
    return None


def digest(value):
    typed=key(value)
    return hashlib.sha256(json.dumps(typed,ensure_ascii=True,separators=(',',':')).encode()).hexdigest() if typed is not None else None


def agree_completed(rows,select):
    if not rows or any(row.get('outcome')!='returned' or row.get('exploration',{}).get('complete') is not True for row in rows):return None
    values=[select(row) for row in rows]
    if any(value is None or value is U for value in values):return None
    keys=[key(value,include_origins=True) for value in values]
    if any(value is None for value in keys) or any(value!=keys[0] for value in keys[1:]):return None
    return {'value':deepcopy(values[0]),'alternatives':len(rows),'coverage':'all reachable enumerated outcomes',
        'conditions':[deepcopy(row.get('path_conditions',row.get('conditions',[]))) for row in rows]}


def observation(item):
    return digest({name:item.get(name) for name in ('result','selected_objects')})


def response_available(item):
    """Engine coverage is authoritative; bare legacy rows are supplied observations."""
    if 'outcome' in item and item['outcome']!='returned':return False
    if 'exploration' in item:
        coverage=item['exploration']
        if not isinstance(coverage,dict) or coverage.get('complete') is not True:return False
    return True
