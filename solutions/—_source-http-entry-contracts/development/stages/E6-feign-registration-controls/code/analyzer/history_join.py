"""Join equal JSON response multisets without merging fields of different rows.

This is only a history/wire value join. It never compares Java objects for Set
membership, sorts a database answer, or proves an encounter order/ordinal.
"""
from collections import defaultdict
from copy import deepcopy
from .native_storage import JavaList
from .history_agreement import key
from .heap_join import mutable_ids


def common_wire_bag(values):
    if not values or any(not isinstance(value,list) or getattr(value,'opaque',False) for value in values):return None
    groups=[]
    for value in values:
        seen=set()
        def unique_tree(item):
            if not isinstance(item,(dict,list)):return True
            if id(item) in seen:return False
            seen.add(id(item))
            return all(unique_tree(v) for v in (item.values() if isinstance(item,dict) else item))
        if not unique_tree(value):return None
        grouped=defaultdict(list)
        for item in value:
            token=key(item,include_origins=True)
            if token is None:return None
            grouped[token].append(item)
        groups.append(grouped)
    shape={token:len(items) for token,items in groups[0].items()}
    if any({token:len(items) for token,items in group.items()}!=shape for group in groups[1:]):return None
    # A canonical diagnostic storage order is explicitly unknown to consumers.
    # Duplicate JSON values keep their multiplicities; no Java identity is used.
    result=JavaList([deepcopy(item) for token in sorted(shape,key=repr) for item in groups[0][token]])
    result.order_known=len(result)<=1
    result.history_order_proof='equal complete response multisets; canonical storage is not encounter order'
    return result


def merge_item(left,right,merge,live_left=(),live_right=()):
    result=merge(left,right)
    if not isinstance(left,dict) or not isinstance(right,dict) or not isinstance(result,dict):return result
    if any(item.get('outcome')!='returned' or item.get('exploration',{}).get('complete') is not True for item in (left,right)):return result
    a,b=left.get('result'),right.get('result')
    if mutable_ids(a)&mutable_ids(live_left) or mutable_ids(b)&mutable_ids(live_right):return result
    bag=common_wire_bag([a,b])
    if bag is not None:
        result['result']=bag
        # Positions refer to old concrete observations; rebuild them lazily
        # from the joined typed JSON value before any future selection.
        result.pop('response_refs',None)
        result['history_order_join']={'kind':'complete-wire-multiset','ordinal_known':len(bag)<=1}
    return result
