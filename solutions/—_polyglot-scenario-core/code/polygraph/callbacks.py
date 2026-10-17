"""Deferred source/library calls. References capture receivers, never run them.

An invocation uses the declaration's lexical owner for skeleton callsite IDs,
even when a stream escapes and another method later consumes it.
"""
from .values import FunctionRef,MethodRef,Object,Raised,TypeRef,unknown

# Bounded native instance signatures, not a short-name heuristic for any class.
INSTANCES={'String':{'length':0,'isEmpty':0,'trim':0,'hashCode':0,'equals':1},
           'java.lang.String':{'length':0,'isEmpty':0,'trim':0,'hashCode':0,'equals':1},
           'java.math.BigDecimal':{'add':1,'multiply':1,'subtract':1,'compareTo':1}}


def compatible(project,actual,expected,seen=frozenset()):
    if actual==expected:return True
    if actual in seen or actual not in project.types:return False
    info=project.types[actual]
    return any(compatible(project,project.resolve_type(parent,info.module,info.span.file),expected,seen|{actual}) for parent in info.parents)


def reference(engine,expr,receiver):
    name,owner,qualifier_type=expr.value
    if not owner:engine.unsupported('Method reference outside a source method requires an initialization contract',expr.span)
    if receiver is None:raise Raised('NullPointerException')
    if unknown(receiver):engine.unsupported('Method reference has an unresolved/null receiver',expr.span)
    result_type=expr.typ
    native=receiver.name if isinstance(receiver,TypeRef) else receiver.typ if isinstance(receiver,Object) else 'java.lang.String' if isinstance(receiver,str) else ''
    if not result_type and native in {'String','java.lang.String'}:result_type={'length':'int','hashCode':'int','isEmpty':'boolean','equals':'boolean','trim':'String'}.get(name,'')
    if not result_type and native.startswith('java.lang.'):
        result_type={'intValue':'int','longValue':'long','shortValue':'short','byteValue':'byte','booleanValue':'boolean','hashCode':'int','compareTo':'int','equals':'boolean','toString':'String','sum':'int' if native.endswith('.Integer') else 'long'}.get(name,'')
    return MethodRef(receiver,name,owner,expr.span,qualifier_type,result_type)


def invoke(engine,callback,args,span):
    if isinstance(callback,FunctionRef):return engine.source_call(callback.name,args,span=span)
    if not isinstance(callback,MethodRef):engine.unsupported('Unmodeled functional-interface callback',span)
    if len(engine.frames)>=engine.depth_limit:engine.unsupported('Callback nesting budget',span)
    origin=engine.p.methods[callback.owner];receiver=callback.receiver
    if id(receiver) in engine.state.tainted_containers:engine.unsupported('Captured callable receiver may have been mutated by opaque code',callback.span)
    engine.events.append({'kind':'callback-invoked','owner':origin.skeleton_id,'reference':callback.span,'consumer':span,'name':callback.name})
    engine.frames.append((origin,{}))
    try:
        if callback.name=='new':
            if not isinstance(receiver,TypeRef):engine.unsupported('Constructor reference qualifier is not a type',callback.span)
            return engine.create(receiver.name,args,span=callback.span)
        if isinstance(receiver,TypeRef):
            if receiver.name in engine.p.types:
                methods=engine.p.methods_of(receiver.name,callback.name)
                static=[m for m in methods if m.annotations.get('static') and len(m.params)==len(args)]
                instance=[m for m in methods if not m.annotations.get('static') and len(m.params)+1==len(args)]
                if len(static)+len(instance)!=1:engine.unsupported('Ambiguous method reference dispatch',callback.span)
                if static:return engine.source_call(static[0].key,args,span=callback.span)
                if args[0] is None:raise Raised('NullPointerException')
                if not isinstance(args[0],Object):engine.unsupported('Unbound source method reference needs a typed receiver',callback.span)
                if not compatible(engine.p,args[0].typ,receiver.name):raise Raised('ClassCastException')
                if instance[0].annotations.get('private'):
                    return engine.source_call(instance[0].key,args[1:],receiver=args[0],span=callback.span)
                return engine.call(args[0],callback.name,args[1:],{},callback.span,{})
            count=INSTANCES.get(receiver.name,{}).get(callback.name)
            from .java_boxing import CLASSES
            if receiver.name in CLASSES and callback.name in {'sum','compare','valueOf','parseInt','parseLong'}:
                return engine.call(receiver,callback.name,args,{},callback.span,{})
            if receiver.name in CLASSES:count={'intValue':0,'longValue':0,'shortValue':0,'byteValue':0,'booleanValue':0,'hashCode':0,'equals':1,'compareTo':1}.get(callback.name)
            if count is None or len(args)!=count+1:engine.unsupported('Native static/unbound method reference requires a signature contract',callback.span)
            if receiver.name in CLASSES and args[0] is not None:
                from .java_boxing import boxed
                if not boxed(args[0]) or args[0].typ!=receiver.name:raise Raised('ClassCastException')
            if receiver.name in {'String','java.lang.String'} and args[0] is not None and not isinstance(args[0],str):
                if unknown(args[0]):engine.unsupported('Unknown receiver for String method reference',callback.span)
                raise Raised('ClassCastException')
            return engine.call(args[0],callback.name,args[1:],{},callback.span,{})
        if callback.qualifier_type in engine.p.types:
            targets=[m for m in engine.p.methods_of(callback.qualifier_type,callback.name,len(args)) if m.annotations.get('private')]
            if len(targets)==1:return engine.source_call(targets[0].key,args,receiver=receiver,span=callback.span)
        return engine.call(receiver,callback.name,args,{},callback.span,{})
    finally:engine.frames.pop()
