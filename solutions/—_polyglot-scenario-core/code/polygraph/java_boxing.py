"""JDK scalar wrappers preserve runtime class and reference identity.

Only guaranteed cache identities are concretized. Equal values outside that
range do not prove reference inequality: a VM may extend its wrapper cache.
"""
from dataclasses import dataclass
import re

from .values import Object,TypeRef,Unknown,Raised,unknown,equal,integer,symbolic,binary

WRAPPERS={'Integer':'int','Long':'long','Byte':'byte','Short':'short','Boolean':'boolean'}
CLASSES={'java.lang.'+name:primitive for name,primitive in WRAPPERS.items()}
PRIMITIVES=set(WRAPPERS.values())|{'float','double','char'}


def short(typ):return typ.removeprefix('java.lang.')


def boxed(value):return isinstance(value,Object) and value.typ in CLASSES


def unbox(value):
    if value is None:raise Raised('NullPointerException')
    return value.fields.get('value',Unknown('Unknown boxed value')) if boxed(value) else value


def box(engine,value,origin,span,fresh=False):
    if value is None or boxed(value):return value
    raw=short(origin)
    primitive=WRAPPERS.get(raw,raw)
    name=next((name for name,kind in WRAPPERS.items() if kind==primitive),None)
    if name is None:engine.unsupported('Java boxing type is unresolved or unsupported: '+origin,span)
    if unknown(value):
        cache=primitive=='boolean' and symbolic(value)
        if not fresh and symbolic(value) and primitive!='boolean':
            cache=engine.condition(binary('>=',value,-128,'java',primitive),span) and engine.condition(binary('<=',value,127,'java',primitive),span)
        key=('java.lang.'+name,value)
        if cache and not fresh and key in engine.state.box_cache:return engine.state.box_cache[key]
        result=engine.state.new('java.lang.'+name,{'value':value,'fresh':fresh,'cache_guaranteed':cache and not fresh})
        if cache and not fresh:engine.state.box_cache[key]=result
        return result
    if primitive=='boolean':
        if type(value) is not bool:raise Raised('ClassCastException')
    else:
        if type(value) is not int:engine.unsupported('Non-integral Java boxing conversion',span)
        value=integer(value,primitive)
    typ='java.lang.'+name;cache=primitive=='boolean' or -128<=value<=127
    key=(typ,value)
    if not fresh and cache and key in engine.state.box_cache:return engine.state.box_cache[key]
    result=engine.state.new(typ,{'value':value,'fresh':fresh,'cache_guaranteed':cache and not fresh})
    if not fresh and cache:engine.state.box_cache[key]=result
    return result


def adapt(engine,value,typ,span,origin=''):
    raw=short(typ)
    if raw not in PRIMITIVES and engine.p.resolve_type(typ,engine.method.module if engine.method else '',span.file):return value
    if raw in WRAPPERS:
        if value is None or unknown(value):return value
        if boxed(value):
            if value.typ!='java.lang.'+raw:raise Raised('ClassCastException')
            return value
        return box(engine,value,raw,span)
    if raw in {'Double','Float','Character'}:
        if value is None or unknown(value):return value
        engine.unsupported('Additional Java scalar wrapper contract required: '+raw,span)
    if raw in PRIMITIVES:
        value=unbox(value)
        if unknown(value):return value
        if raw=='boolean':
            if type(value) is not bool:raise Raised('ClassCastException')
            return value
        if raw=='char':return value
        if type(value) not in {int,float}:raise Raised('ClassCastException')
        return integer(value,raw)
    if raw in {'Object','Number','Serializable','Comparable'} and type(value) in {int,bool,float}:
        return box(engine,value,origin,span)
    if raw in {'Object','Number','Serializable','Comparable'} and unknown(value) and short(origin) in PRIMITIVES:
        return box(engine,value,origin,span)
    return value


def argument(engine,value,typ,span):
    # At a generic library Object parameter, primitives are boxed and existing
    # references keep their class. Never infer Integer from the numeric value.
    if type(value) in {int,bool,float}:return box(engine,value,typ,span)
    return value


def reference_cast(engine,value,typ,span):
    if not typ or typ in {'Object','java.lang.Object'} or value is None:return value
    if unknown(value):engine.unsupported('Unknown functional-interface input cast',span)
    raw=short(typ)
    if raw in PRIMITIVES:typ=next((name for name,primitive in WRAPPERS.items() if primitive==raw),typ)
    source=engine.p.resolve_type(typ,engine.method.module if engine.method else '',span.file)
    if source:
        from .callbacks import compatible
        if not isinstance(value,Object) or not compatible(engine.p,value.typ,source):raise Raised('ClassCastException')
        return value
    raw=short(typ)
    if raw in WRAPPERS:
        if not boxed(value) or value.typ!='java.lang.'+raw:raise Raised('ClassCastException')
    elif raw=='String':
        if not isinstance(value,str):raise Raised('ClassCastException')
    elif raw in {'Number','Serializable','Comparable'}:
        target=('java.io.' if raw=='Serializable' else 'java.lang.')+raw
        if not isinstance(value,Object) or not engine.matches_type(value.typ,target):raise Raised('ClassCastException')
    else:engine.unsupported('Functional-interface input type needs a reference-cast contract: '+typ,span)
    return value


def equals(left,right):
    if not boxed(right) or left.typ!=right.typ:return False
    return equal(unbox(left),unbox(right))


@dataclass(frozen=True)
class MapKey:
    typ: str
    value: object


def map_key(engine,value,span):
    if boxed(value):
        scalar=unbox(value)
        if unknown(scalar):engine.unsupported('Unknown boxed Java map key',span)
        return MapKey(value.typ,scalar)
    if isinstance(value,Object) or unknown(value):engine.unsupported('Java map key needs a source hash/equality contract',span)
    return value


def parse(engine,value,primitive,span):
    if not isinstance(value,str):raise Raised('NumberFormatException')
    engine.operations+=len(value);engine.tick(span)
    if not re.fullmatch(r'[+-]?\d+',value):raise Raised('NumberFormatException')
    digits=value.lstrip('+-').lstrip('0') or '0'
    bits={'int':32,'long':64,'byte':8,'short':16}[primitive]
    if len(digits)>20:raise Raised('NumberFormatException')
    result=int(('-' if value.startswith('-') else '')+digits)
    if not -(1<<(bits-1))<=result<(1<<(bits-1)):raise Raised('NumberFormatException')
    return result


def decode_json(engine,value,typ,span,depth=0):
    name=short(typ)
    if depth>128:engine.unsupported('Java JSON decoding depth',span)
    if name in WRAPPERS or name in PRIMITIVES:
        primitive=WRAPPERS.get(name,name)
        if value is not None and not unknown(value):
            bits={'int':32,'long':64,'byte':8,'short':16}.get(primitive)
            if primitive=='boolean' and type(value) is not bool:engine.unsupported('Java JSON boolean coercion needs a codec contract',span)
            if bits and (type(value) is not int or not -(1<<(bits-1))<=value<(1<<(bits-1))):engine.unsupported('Java JSON integer range/coercion needs a codec contract',span)
        return adapt(engine,value,next((wrapper for wrapper,primitive in WRAPPERS.items() if primitive==name),name),span)
    if name!='Object':return value
    if type(value) is bool:return box(engine,value,'boolean',span)
    if type(value) is int:
        if -(1<<31)<=value<(1<<31):return box(engine,value,'int',span)
        if -(1<<63)<=value<(1<<63):return box(engine,value,'long',span)
        engine.unsupported('Untyped JSON number exceeds supported Java wrappers',span)
    if type(value) is float:engine.unsupported('Untyped JSON floating wrapper is unsupported',span)
    if isinstance(value,list):return [decode_json(engine,item,'Object',span,depth+1) for item in value]
    if isinstance(value,dict):return {key:decode_json(engine,item,'Object',span,depth+1) for key,item in value.items()}
    return value


def construct(engine,typ,args,kwargs,span,argument_types=()):
    from .models import NOT_HANDLED
    resolved=engine.p.resolve_import(typ,span.file) or typ
    name=short(resolved)
    if name not in WRAPPERS:return NOT_HANDLED
    if kwargs or len(args)!=1:engine.unsupported('Boxed constructor overload',span)
    value=args[0];primitive=WRAPPERS[name]
    if isinstance(value,str) and primitive!='boolean':value=parse(engine,value,primitive,span)
    elif primitive=='boolean' and isinstance(value,str):value=value.lower()=='true'
    elif value is None:
        hint=argument_types[0] if argument_types else ''
        if primitive=='boolean' and hint in {'String','java.lang.String','null'}:return box(engine,False,primitive,span,fresh=True)
        if hint in {'String','java.lang.String','null'}:raise Raised('NumberFormatException')
        if not hint:engine.unsupported('Null boxed constructor overload is ambiguous',span)
        raise Raised('NullPointerException')
    else:value=unbox(value)
    return box(engine,value,primitive,span,fresh=True)


def call(engine,receiver,name,args,kwargs,span,argument_types=()):
    from .models import NOT_HANDLED
    if boxed(receiver):
        value=unbox(receiver)
        if name=='equals' and len(args)==1:return equals(receiver,argument(engine,args[0],argument_types[0] if argument_types else '',span))
        if name=='toString' and not args:return Unknown('Unknown boxed string') if unknown(value) else str(value).lower() if type(value) is bool else str(value)
        if name=='hashCode' and not args:
            if unknown(value):return value
            return 1231 if value is True else 1237 if value is False else integer(value^(value>>32),'int') if receiver.typ=='java.lang.Long' else integer(value,'int')
        if name in {'intValue','longValue','shortValue','byteValue','booleanValue'} and not args:return adapt(engine,value,name.removesuffix('Value'),span)
        if name=='compareTo' and len(args)==1:
            other_box=argument(engine,args[0],argument_types[0] if argument_types else '',span)
            if other_box is None:raise Raised('NullPointerException')
            if not boxed(other_box) or receiver.typ!=other_box.typ:raise Raised('ClassCastException')
            other=unbox(other_box)
            if unknown(value) or unknown(other):return Unknown('Unknown boxed comparison','int')
            return (value>other)-(value<other)
        return NOT_HANDLED
    if not isinstance(receiver,TypeRef) or short(receiver.name) not in WRAPPERS:return NOT_HANDLED
    primitive=WRAPPERS[short(receiver.name)]
    if name in {'valueOf','parseInt','parseLong','parseByte','parseShort','parseBoolean'}:
        if kwargs or len(args)!=1:engine.unsupported('Boxed parse/valueOf overload',span)
        value=args[0]
        if primitive=='boolean':value=value is not None and isinstance(value,str) and value.lower()=='true' if isinstance(value,str) or value is None else unbox(value)
        elif isinstance(value,str):value=parse(engine,value,primitive,span)
        elif name!='valueOf':raise Raised('NumberFormatException')
        else:value=unbox(value)
        return box(engine,value,primitive,span) if name=='valueOf' else value
    if name in {'sum','compare'} and len(args)==2:
        left,right=(adapt(engine,value,primitive,span) for value in args)
        if unknown(left) or unknown(right):return Unknown('Unknown boxed arithmetic',primitive)
        return integer(left+right,primitive) if name=='sum' else (left>right)-(left<right)
    return NOT_HANDLED
