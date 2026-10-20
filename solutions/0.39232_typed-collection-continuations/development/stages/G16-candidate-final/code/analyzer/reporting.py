"""Finite diagnostic view of cyclic heaps. Never feeds execution or wire codecs."""


def finite_report(value,active=None,path='$'):
    active={} if active is None else active
    if not isinstance(value,(dict,list,tuple)):return value
    if id(value) in active:return {'$cycle_ref':active[id(value)]}
    active[id(value)]=path
    try:
        if isinstance(value,dict):
            children={k:finite_report(v,active,path+'/'+str(k)) for k,v in value.items()}
            return value if all(children[k] is v for k,v in value.items()) else children
        children=[finite_report(v,active,path+'/'+str(i)) for i,v in enumerate(value)]
        return value if all(a is b for a,b in zip(value,children)) else children
    finally:active.pop(id(value))
