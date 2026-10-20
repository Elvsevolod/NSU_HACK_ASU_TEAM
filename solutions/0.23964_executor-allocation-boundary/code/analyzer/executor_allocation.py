"""Allocation only. No executor, thread, or callback is run by this contract."""
from .java_collections import JavaObject
from .java_exceptions import JavaThrow
from .state import U
from .project import text

POOL='java.util.concurrent.ThreadPoolExecutor'
FACTORY='org.springframework.scheduling.concurrent.CustomizableThreadFactory'


def source_factory(engine,value):
    if not isinstance(value,JavaObject):return False
    if value.java_type==FACTORY and not getattr(value,'source_owner',None):return True
    pending=[getattr(value,'source_owner',None)];seen=set()
    while pending:
        owner=pending.pop()
        if owner is None or owner in seen:continue
        seen.add(owner)
        if any(engine.standard_type(parent,'java.util.concurrent.ThreadFactory',engine.p.nodes[owner])
               for parent in engine.p.framework_types.get(owner,())):return True
        pending.extend(engine.p.type_parents.get(owner,()))
    return False


def operation(engine,node,name,obj,args,env,targets,reason):
    from .engine import AnalysisBoundary
    if targets:return False,U
    owner=text(node.child_by_field_name('object'))
    constructor=text(node.child_by_field_name('type'))
    if name=='<init>' and engine.standard_type(constructor,FACTORY):
        if len(args)>1 or args and args[0] is not U and args[0] is not None and not isinstance(args[0],str):
            raise AnalysisBoundary('ThreadFactory constructor overload is unresolved: '+reason,category='unsupported_semantics')
        return True,JavaObject(FACTORY,{'threadNamePrefix':args[0] if args else U})
    if name=='newFixedThreadPool' and owner not in env and engine.standard_type(owner,'java.util.concurrent.Executors'):
        if len(args) not in (1,2) or type(args[0]) is not int or not -(2**31)<=args[0]<2**31:
            raise AnalysisBoundary('fixed thread pool size/overload is unresolved: '+reason,category='unsupported_semantics')
        if args[0]<=0:raise JavaThrow({'__type__':'IllegalArgumentException'})
        if len(args)==2:
            if args[1] is None:raise JavaThrow({'__type__':'NullPointerException'})
            if not source_factory(engine,args[1]):
                raise AnalysisBoundary('fixed thread pool factory allocation is unresolved: '+reason,category='unsupported_semantics')
        engine.effect_events.append({'model_version':'executor-allocation/1','operation':name,'callsite':reason,
            'resource_writes':[],'heap_roots':[],'callbacks':[],'completions':['normal'],
            'scope':'allocation only; JVM resource/security failures outside model; no task/ThreadFactory callback'})
        return True,JavaObject(POOL,{'threadFactory':args[1] if len(args)==2 else U})
    if isinstance(obj,JavaObject) and obj.java_type==POOL and not getattr(obj,'source_owner',None):
        raise AnalysisBoundary('executor operation requires unsupported task/lifecycle semantics: '+reason,category='unsupported_semantics')
    return False,U
