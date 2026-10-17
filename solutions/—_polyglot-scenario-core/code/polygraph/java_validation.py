"""Field Bean Validation subset over IR values, with native Pydantic bounds.

Source getter/custom validators and custom groups remain explicit cutoffs.
Length measures Java UTF-16 code units, not Python Unicode code points.
"""
from functools import lru_cache
import re
from typing import Annotated

from pydantic import Field,TypeAdapter,ValidationError

from .values import Object,Raised,Symbol,unknown

PACKAGES={'javax.validation.constraints','jakarta.validation.constraints','org.hibernate.validator.constraints'}
SUPPORTED={'NotNull','Null','Length','Size','Min','Max','AssertTrue','AssertFalse','NotEmpty'}


def qualified(project,name,file):
    explicit=project.resolve_import(name,file)
    if explicit:return explicit
    if '.' in name:return name
    custom=project.adapters['java'].custom_constraints
    local=project.adapters['java'].package_names.get(file,'')
    local=(local+'.' if local else '')+name
    if local in custom:return local
    if name in {'Valid','Validated'}:
        candidates={package+'.'+name for package in project.import_wildcards[file] if package in {'javax.validation','jakarta.validation','org.springframework.validation.annotation'}}
        return candidates.pop() if len(candidates)==1 else ''
    candidates={package+'.'+name for package in project.import_wildcards[file] if package in PACKAGES}
    candidates|={package+'.'+name for package in project.import_wildcards[file] if package+'.'+name in custom}
    return candidates.pop() if len(candidates)==1 else ''


@lru_cache(maxsize=256)
def bounds(minimum,maximum):return TypeAdapter(Annotated[int,Field(ge=minimum,le=maximum)])


def literal(engine,raw,name,default,span):
    if name!='value' and not re.search(r'\b'+name+r'\s*=',raw):return default
    pattern=r'\b'+name+r'\s*=\s*([+-]?\d[\d_]*)[lL]?(?=\s*[,\)])' if name!='value' or 'value' in raw else r'^\(\s*([+-]?\d[\d_]*)[lL]?\s*\)$'
    found=re.search(pattern,raw)
    if not found:engine.unsupported('Nonliteral Bean Validation bound',span)
    return int(found[1].replace('_',''))


def reject(engine,field,constraint,span):
    engine.note('bean-validation','Source field fails a checked constraint',span,field=field,constraint=constraint)
    raise Raised('MethodArgumentNotValidException')


def constraint(engine,name,raw,value,typ,field,span):
    from .java_boxing import boxed,unbox
    if boxed(value):value=unbox(value)
    if 'groups' in raw:engine.unsupported('Custom Bean Validation groups',span)
    if name not in SUPPORTED:engine.unsupported('Bean Validation constraint '+name+' needs an additional contract',span)
    if name=='NotNull':
        if value is None:reject(engine,field,name,span)
        if unknown(value) and not isinstance(value,Symbol):engine.unsupported('Unknown nullability during Bean Validation',span)
        if isinstance(value,Symbol) and not value.nonnull:engine.unsupported('Unknown symbol nullability during Bean Validation',span)
        return
    if name=='Null':
        if unknown(value):engine.unsupported('Unknown value for a Null constraint',span)
        if value is not None:reject(engine,field,name,span)
        return
    if value is None:
        if name=='NotEmpty':reject(engine,field,name,span)
        return
    if unknown(value):engine.unsupported('Unknown value during Bean Validation',span)
    if name in {'AssertTrue','AssertFalse'}:
        if type(value) is not bool:engine.unsupported('Non-boolean assertion constraint',span)
        if value!=(name=='AssertTrue'):reject(engine,field,name,span)
        return
    if name in {'Length','Size','NotEmpty'}:
        raw_type=typ.split('<')[0].split('.')[-1]
        if raw_type not in {'String','CharSequence','List','Set','Collection','Map','Iterable'} and not typ.endswith('[]'):engine.unsupported('Constraint on an unmodeled sized Java type',span)
        if name=='Length' and not isinstance(value,str):engine.unsupported('Length constraint requires a CharSequence',span)
        if not isinstance(value,(str,list,tuple,dict)):engine.unsupported('Unmodeled sized Java value',span)
        measure=len(value.encode('utf-16-le',errors='surrogatepass'))//2 if isinstance(value,str) else len(value)
        minimum=1 if name=='NotEmpty' else literal(engine,raw,'min',0,span)
        maximum=2147483647 if name=='NotEmpty' else literal(engine,raw,'max',2147483647,span)
    else:
        if type(value) is not int:engine.unsupported('Non-integral Min/Max value',span)
        measure=value;limit=literal(engine,raw,'value',None,span)
        minimum,maximum=(limit,None) if name=='Min' else (None,limit)
    if minimum is not None and maximum is not None and (minimum<0 and name in {'Length','Size'} or maximum<minimum):engine.unsupported('Invalid Bean Validation bounds',span)
    try:bounds(minimum,maximum).validate_python(measure,strict=True)
    except ValidationError:reject(engine,field,name,span)


def validate(engine,key,value,span,active=frozenset()):
    if value is None:return
    if unknown(value):engine.unsupported('Unknown cascaded Bean Validation value',span)
    if (key,id(value)) in active:return
    active=active|{(key,id(value))}
    info=engine.p.types[key]
    if set(info.annotations)&{'GroupSequence','GroupSequenceProvider'}:engine.unsupported('Custom Bean Validation default sequence',info.span)
    if any(qualified(engine.p,name,info.span.file).rpartition('.')[0] in PACKAGES or qualified(engine.p,name,info.span.file) in engine.p.adapters['java'].custom_constraints for name in info.annotations.get('validation_annotations',{})):engine.unsupported('Class-level Bean Validation callback',info.span)
    for method_key in info.methods:
        method=engine.p.methods[method_key]
        if any(qualified(engine.p,name,info.span.file).rpartition('.')[0] in PACKAGES or qualified(engine.p,name,info.span.file) in engine.p.adapters['java'].custom_constraints or qualified(engine.p,name,info.span.file) in {'javax.validation.Valid','jakarta.validation.Valid'} for name in method.annotations.get('validation_annotations',{})):engine.unsupported('Getter-based Bean Validation requires a source callback contract',method.span)
    fields=value.fields if isinstance(value,Object) else value
    if not isinstance(fields,dict):engine.unsupported('Unmodeled bean value',span)
    if any('@' in typ for typ,_ in info.fields.values()):engine.unsupported('Type-use Bean Validation requires a container-element contract',info.span)
    for parent in info.parents:
        resolved=engine.p.resolve_type(parent,info.module,info.span.file)
        if resolved:
            if set(engine.p.types[resolved].fields)&set(info.fields):engine.unsupported('Shadowed Java validation fields',span)
            validate(engine,resolved,value,span,active)
    for field,annotations in info.annotations.get('field_annotations',{}).items():
        current=fields.get(field)
        typ=info.fields[field][0]
        for name,raw in annotations.items():
            full=qualified(engine.p,name,info.span.file)
            if full in engine.p.adapters['java'].custom_constraints:engine.unsupported('Custom field Bean Validation callback',info.span)
            if full.rpartition('.')[0] in PACKAGES:constraint(engine,name.split('.')[-1],raw,current,typ,field,info.span)
        if any(name.split('.')[-1]=='ConvertGroup' for name in annotations):engine.unsupported('Cascaded validation group conversion',span)
        if not any(qualified(engine.p,name,info.span.file) in {'javax.validation.Valid','jakarta.validation.Valid'} for name in annotations) or current is None:continue
        if unknown(current):engine.unsupported('Unknown cascaded field',span)
        inner=re.fullmatch(r'(?:[\w.]+)(?:<(.+)>)?',typ)
        if isinstance(current,(list,tuple)):
            child_type=inner[1] if inner and inner[1] else typ.removesuffix('[]')
            children=current
        elif isinstance(current,dict) and typ.split('<')[0].split('.')[-1]=='Map':
            child_type=inner[1].split(',')[-1].strip() if inner and inner[1] else '';children=current.values()
        else:child_type=typ;children=[current]
        resolved=engine.p.resolve_type(child_type,info.module,info.span.file)
        if resolved:
            for child in children:validate(engine,resolved,child,span,active)


def validate_parameter(engine,param,value,method):
    if any(qualified(engine.p,name,method.span.file).rpartition('.')[0] in PACKAGES or qualified(engine.p,name,method.span.file) in engine.p.adapters['java'].custom_constraints for name in param.annotations):engine.unsupported('Executable Bean Validation constraints require a method-validation contract',method.span)
    marker=next((name for name in param.annotations if name.split('.')[-1] in {'Valid','Validated'}),None)
    if marker is None:return
    if qualified(engine.p,marker,method.span.file) not in {'javax.validation.Valid','jakarta.validation.Valid','org.springframework.validation.annotation.Validated'}:return
    if marker.split('.')[-1]=='Validated' and param.annotations[marker].strip('() '):engine.unsupported('Custom validation group on Spring parameter',method.span)
    key=engine.p.resolve_type(param.typ,method.module,method.span.file)
    if key:validate(engine,key,value,method.span)
