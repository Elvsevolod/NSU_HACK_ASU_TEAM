"""Spring Data 2.x query wrappers, independent of query content knowledge."""
from .generic_types import type_parts
from .native_storage import JavaList
from .state import U


def unknown_result(engine, call):
    p=engine.p;meta=p.methods[engine.method]
    owner=p.resolve_type(call.get('receiver_type',''),meta['module'],meta['file'])
    pending=[owner];seen=set();supported=False
    while pending:
        current=pending.pop()
        if current is None or current in seen:continue
        seen.add(current);context=p.nodes[current]
        for written in p.generic_parents.get(current,()):
            base,_=type_parts(written)
            supported |= any(engine.standard_type(base,fqn,context) for fqn in (
                'org.springframework.data.jpa.repository.JpaRepository',
                'org.springframework.data.repository.CrudRepository'))
            pending.append(p.resolve_type(base,context['module'],context['file']))
    if not supported:return U
    declared=[(mid,m) for mid,m in p.methods.items() if m['owner']==owner and m['name']==call['callee']]
    if any(not m.get('abstract') for _,m in declared):return U
    written=declared[0][1].get('return_raw','') if len(declared)==1 else (
        'java.util.Optional' if call['callee']=='findById' else 'java.util.List' if call['callee']=='findAll' else '')
    base,_=type_parts(written)
    context=declared[0][1] if len(declared)==1 else p.nodes[owner]
    if engine.standard_type(base,'java.util.Optional',context):
        return {'__optional__':True,'optional':U,'__repository_presence__':U}
    shape=next((name for name in ('List','ArrayList','LinkedList','Collection','Set','HashSet')
        if engine.standard_type(base,'java.util.'+name,context)),None)
    if shape:
        result=JavaList();result.opaque=True;result.flavor=shape
        result.order_known=shape not in ('Set','HashSet','Collection')
        return result
    return U


def presence(engine, value, reason):
    known=value.get('__repository_presence__',U)
    if known is not U:return known
    if not engine.path_replay:return U
    label=reason+':repository-optional-presence'
    selected=engine.choose(label,[False,True])
    if selected is None:
        from .engine import CompletionRequired,AnalysisBoundary
        if not engine.allow_completion_splits:raise AnalysisBoundary('repository presence needs an isolated continuation: '+reason)
        raise CompletionRequired(str(engine.branch_index)+':'+label,[False,True])
    value['__repository_presence__']=selected
    if not selected:value['optional']=None
    return selected
