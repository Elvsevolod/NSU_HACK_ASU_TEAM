"""Lazy sequential Java streams built with native CPython iterator primitives.

Source callbacks use the shared kernel. Unsupported collectors, interference,
parallelism and unspecified encounter order remain visible boundaries.
"""
from functools import reduce,partial
from itertools import islice
import re

from .values import FunctionRef,MethodRef,Object,Raised,TypeRef,unknown
from .models import NOT_HANDLED
from . import java_sets
from .java_boxing import argument as box_argument,boxed,unbox,reference_cast

STREAM='java.util.stream.Stream'


def construct(engine,typ,args,kwargs,span):
    base=re.sub(r'<.*>','',typ)
    qualified=engine.p.resolve_import(base,span.file) or base
    if qualified not in java_sets.TYPES:return NOT_HANDLED
    if kwargs:engine.unsupported('Java set constructor keyword arguments',span)
    result=java_sets.create(engine,java_sets.element(typ),qualified.endswith('.LinkedHashSet'))
    if not args:return result
    if len(args)==1 and boxed(args[0]):args=(unbox(args[0]),)
    if len(args)==1 and type(args[0]) is int:
        if args[0]<0:raise Raised('IllegalArgumentException')
        return result
    if len(args)!=1 or not isinstance(args[0],list):engine.unsupported('Java set constructor overload',span)
    for index,item in enumerate(args[0]):
        if index>=engine.loop_limit:engine.unsupported('Java set construction budget',span)
        java_sets.put(engine,result,item,span)
    return result


def new(engine,source,element_type='',ordered=True,operations=()):
    return engine.state.new(STREAM,{'source':source,'element_type':element_type,'ordered':ordered,'operations':operations,'used':False})


def callable_argument(engine,value,span):
    if value is None:raise Raised('NullPointerException')
    if not isinstance(value,(MethodRef,FunctionRef)):engine.unsupported('Stream callback needs a supported functional value',span)
    return value


def pipeline(engine,stream,span):
    source=stream.fields['source']
    empty=any(operation=='limit' and argument==0 for operation,argument in stream.fields['operations'])
    if not empty and not stream.fields['ordered'] and len(source)>1:engine.unsupported('Unordered Java stream needs an encounter-order/commutativity contract',span)
    original=tuple(id(value) for value in source)
    version=engine.state.mutation_version(source)
    def check():
        if id(source) in engine.state.tainted_containers or tuple(id(value) for value in source)!=original or version!=engine.state.mutation_version(source):
            engine.unsupported('Interference with Java stream source',span)
    def elements():
        for index,item in enumerate(source):
            check()
            if index>=engine.loop_limit:engine.unsupported('Java stream iteration budget',span)
            engine.tick(span)
            yield item
        check()
    def apply(callback,input_type,item,predicate=False,peek=False):
        item=reference_cast(engine,item,input_type,span)
        result=engine.invoke_callable(callback,(item,),span);check()
        return engine.condition(result,getattr(callback,'span',span)) if predicate else item if peek else box_argument(engine,result,getattr(callback,'return_type',''),span)
    values=elements()
    for operation,argument in stream.fields['operations']:
        if operation=='map':values=map(partial(apply,*argument),values)
        elif operation=='filter':values=filter(partial(apply,*argument,predicate=True),values)
        elif operation=='peek':values=map(partial(apply,*argument,peek=True),values)
        elif operation=='limit':values=islice(values,argument)
        elif operation=='skip':values=islice(values,argument,None)
    return values,check


def call(engine,receiver,name,args,kwargs,span,receiver_type='',argument_types=()):
    if kwargs:return NOT_HANDLED
    if isinstance(receiver,TypeRef) and receiver.name=='java.util.stream.Collectors':
        if name in {'toList','toSet'} and not args:return engine.state.new('java.util.stream.Collector',{'kind':name})
        engine.unsupported('Java collector contract '+name,span)
    if isinstance(receiver,TypeRef) and receiver.name==STREAM:
        if name=='empty' and not args:return new(engine,[])
        if name=='of':
            if len(args)==1 and isinstance(args[0],list):engine.unsupported('Stream.of array/element overload is unresolved',span)
            return new(engine,[box_argument(engine,value,argument_types[index] if index<len(argument_types) else '',span) for index,value in enumerate(args)])
        engine.unsupported('Java stream factory '+name,span)
    if isinstance(receiver,Object) and receiver.typ in java_sets.TYPES:
        values,_=java_sets.fields(engine,receiver,span)
        if name=='stream' and not args:return new(engine,values,receiver.fields.get('element_type',''),receiver.typ.endswith('.LinkedHashSet'))
        if name in {'size','isEmpty'} and not args:return len(values) if name=='size' else not values
        if name in {'add','contains'} and len(args)==1:return java_sets.put(engine,receiver,box_argument(engine,args[0],argument_types[0] if argument_types else '',span),span,name=='contains')
        engine.unsupported('Java set operation '+name,span)
    if isinstance(receiver,list) and name in {'stream','parallelStream'} and not args:
        if name=='parallelStream':engine.unsupported('Parallel Java stream',span)
        return new(engine,receiver,java_sets.element(receiver_type))
    if not isinstance(receiver,Object) or receiver.typ!=STREAM:return NOT_HANDLED
    fields=receiver.fields
    if (type(fields.get('used')) is not bool or type(fields.get('ordered')) is not bool or
        not isinstance(fields.get('source'),list) or not isinstance(fields.get('operations'),tuple)):
        engine.unsupported('Java stream state is unknown',span)
    if fields['used']:raise Raised('IllegalStateException')
    if name in {'map','filter','peek'} and len(args)==1:
        callback=callable_argument(engine,args[0],span);fields['used']=True
        input_type=java_sets.element(receiver_type) or fields['element_type']
        element_type=callback.return_type if name=='map' and isinstance(callback,MethodRef) else fields['element_type']
        return new(engine,fields['source'],element_type,fields['ordered'],fields['operations']+((name,(callback,input_type)),))
    if name in {'limit','skip'} and len(args)==1:
        bound=unbox(args[0]) if boxed(args[0]) else args[0]
        if type(bound) is not int:engine.unsupported('Unknown Java stream slice bound',span)
        if bound<0:raise Raised('IllegalArgumentException')
        fields['used']=True
        return new(engine,fields['source'],fields['element_type'],fields['ordered'],fields['operations']+((name,bound),))
    if name=='count' and not args:
        if fields['operations']:engine.unsupported('Stream count may elide callbacks; JDK version-specific contract required',span)
        fields['used']=True;return len(fields['source'])
    terminal=name in {'collect','reduce','forEach','forEachOrdered','findFirst','anyMatch','allMatch','noneMatch'}
    if not terminal:engine.unsupported('Java stream operation '+name,span)
    if name=='collect' and not (len(args)==1 and isinstance(args[0],Object) and args[0].typ=='java.util.stream.Collector' and args[0].fields.get('kind') in {'toList','toSet'}):engine.unsupported('Java collector overload/state is unsupported',span)
    callback=None
    if name in {'forEach','forEachOrdered','anyMatch','allMatch','noneMatch'}:
        if len(args)!=1:engine.unsupported('Java stream terminal arity',span)
        callback=callable_argument(engine,args[0],span)
    if name=='reduce':
        if len(args)!=2:engine.unsupported('Java reduce overload',span)
        callback=callable_argument(engine,args[1],span)
    if name=='findFirst' and args:engine.unsupported('Java findFirst arity',span)
    fields['used']=True;values,check=pipeline(engine,receiver,span)
    if name=='collect':
        if args[0].fields['kind']=='toList':return list(values)
        result=java_sets.create(engine,fields['element_type'])
        for item in values:java_sets.put(engine,result,item,span);check()
        return result
    if name=='reduce':
        def accumulate(left,right):
            left=reference_cast(engine,left,fields['element_type'],span)
            right=reference_cast(engine,right,fields['element_type'],span)
            result=engine.invoke_callable(callback,(left,right),span);check();return box_argument(engine,result,getattr(callback,'return_type',''),span)
        initial=box_argument(engine,args[0],argument_types[0] if argument_types else '',span)
        return reduce(accumulate,values,initial)
    if name=='findFirst':
        sentinel=object();result=next(values,sentinel)
        if result is None:raise Raised('NullPointerException')
        return engine.state.new('java.util.Optional',{'present':result is not sentinel,'value':None if result is sentinel else result})
    for item in values:
        item=reference_cast(engine,item,java_sets.element(receiver_type) or fields['element_type'],span)
        result=engine.invoke_callable(callback,(item,),span);check()
        if name in {'forEach','forEachOrdered'}:continue
        matched=engine.condition(result,getattr(callback,'span',span))
        if matched and name in {'anyMatch','noneMatch'}:return name=='anyMatch'
        if not matched and name=='allMatch':return False
    return None if name in {'forEach','forEachOrdered'} else name!='anyMatch'
