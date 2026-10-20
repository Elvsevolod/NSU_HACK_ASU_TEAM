"""Bounded Java HashSet contracts, including source hashCode/equals effects."""
from functools import reduce
import re

from .values import Object,Raised,unknown,integer

TYPES={'java.util.HashSet','java.util.LinkedHashSet'}


def string_hash(text):
    raw=text.encode('utf-16-be',errors='surrogatepass')
    return reduce(lambda result,index:integer(31*result+int.from_bytes(raw[index:index+2],'big'),'int'),range(0,len(raw),2),0)


def hash_string(engine,text,span):
    engine.operations+=len(text);engine.tick(span)
    return string_hash(text)


def key(engine,item,element_type,span):
    if unknown(item):engine.unsupported('Unknown Java set hash/equality',span)
    if item is None:return 0
    from .java_boxing import boxed,call
    if boxed(item):
        result=call(engine,item,'hashCode',(),{},span)
        if type(result) is not int:engine.unsupported('Unknown boxed set hash',span)
        return result
    if isinstance(item,str):return hash_string(engine,item,span)
    if type(item) is bool:return 1231 if item else 1237
    if type(item) is int:
        engine.unsupported('Java set numeric boxing type is unresolved',span)
    if isinstance(item,Object) and item.typ in engine.p.types:
        hashes=engine.p.methods_of(item.typ,'hashCode',0);equals=engine.p.methods_of(item.typ,'equals',1)
        if len(hashes)==1:
            result=engine.source_call(hashes[0].key,receiver=item,span=span)
            if type(result) is not int:engine.unsupported('Source hashCode did not resolve to a concrete int',span)
            return integer(result,'int')
        if not hashes and not equals:return ('identity',item.identity)
    engine.unsupported('Java set hash contract is unavailable',span)


def equivalent(engine,left,right,span):
    from .java_boxing import boxed,equals
    if boxed(left):return engine.condition(equals(left,right),span)
    if isinstance(left,Object):
        if isinstance(right,Object) and left.identity==right.identity:return True
        methods=engine.p.methods_of(left.typ,'equals',1)
        if len(methods)==1:return engine.condition(engine.source_call(methods[0].key,(right,),receiver=left,span=span),span)
        return False
    return type(left) is type(right) and left==right


def fields(engine,collection,span):
    values=collection.fields.get('values');buckets=collection.fields.get('buckets')
    if not isinstance(values,list) or not isinstance(buckets,dict) or id(values) in engine.state.tainted_containers or id(buckets) in engine.state.tainted_containers:
        engine.unsupported('Java set state is unknown',span)
    return values,buckets


def put(engine,collection,item,span,contains=False):
    values,buckets=fields(engine,collection,span);version=engine.state.mutation_version(values)
    def check():
        current,_=fields(engine,collection,span)
        if current is not values or engine.state.mutation_version(values)!=version:engine.unsupported('Set interference during source hash/equality callback',span)
    hashed=key(engine,item,collection.fields.get('element_type',''),span);check()
    bucket=buckets.get(hashed,[])
    if len(bucket)>=8:engine.unsupported('Java HashMap tree/collision traversal needs a runtime contract',span)
    for previous in bucket:
        same=equivalent(engine,item,previous,span);check()
        if same:return True if contains else False
    if contains:return False
    buckets.setdefault(hashed,[]).append(item);values.append(item)
    engine.state.mutated(values)
    return True


def create(engine,element_type='',ordered=False):
    return engine.state.new('java.util.LinkedHashSet' if ordered else 'java.util.HashSet',{'values':[],'buckets':{},'element_type':element_type})


def element(typ):
    found=re.fullmatch(r'[\w.]+\s*<\s*([\w.]+)\s*>',typ)
    return found[1] if found else ''
