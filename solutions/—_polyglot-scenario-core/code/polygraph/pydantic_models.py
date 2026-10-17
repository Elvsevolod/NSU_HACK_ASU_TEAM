"""Native Pydantic schemas from bounded source facts, never target classes."""
import ast
import json
from contextvars import ContextVar
from copy import deepcopy
from datetime import date,datetime,timedelta
from decimal import Decimal
import types
from typing import Annotated,Any,Union,get_args,get_origin
from uuid import UUID

from pydantic import BaseModel,ConfigDict,EmailStr,Field,TypeAdapter,ValidationError,create_model

from .values import Object,Symbol,Text,Raised,unknown,wire,serial
from .native_contracts import check

ACTIVE_ENGINE=ContextVar('polygraph_pydantic_engine',default=None)


def factory_callback(project,expression,validate_default=False):
    from .definition_models import qualified
    target=qualified(project,expression) if expression.op=='call' else ''
    if target not in project.methods:
        target=project.lexical_modules.get(expression.span.file,'')+'.'+target if '.' not in target else ''
    method=project.methods.get(target)
    required_data=method is not None and len(method.params)==1 and method.params[0].default is None
    if required_data:
        def factory(validated_data):
            engine=ACTIVE_ENGINE.get()
            value=engine.execute_method(target,(normalize(validated_data),),span=expression.span)
            if validate_default and abstract(value):engine.unsupported('Native validation of an abstract factory result',expression.span)
            return value
    else:
        def factory():
            engine=ACTIVE_ENGINE.get();value=engine.value(expression,{})
            if validate_default and abstract(value):engine.unsupported('Native validation of an abstract factory result',expression.span)
            return value
    return factory


def lineage(project,key,seen=frozenset()):
    if key in seen:return []
    info=project.types[key];result=[]
    for parent in info.parents:
        resolved=project.resolve_type(parent,info.module,info.span.file)
        if resolved:result.extend(lineage(project,resolved,seen|{key}))
    return result+[info]


def typename(node):
    return node.id if isinstance(node,ast.Name) else typename(node.value)+'.'+node.attr if isinstance(node,ast.Attribute) else ''


def annotation(engine,text,info):
    def convert(node):
        if isinstance(node,ast.Constant) and node.value is None:return type(None)
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.BitOr):return Union[convert(node.left),convert(node.right)]
        if isinstance(node,ast.Subscript):
            base=typename(node.value).split('.')[-1]
            parts=node.slice.elts if isinstance(node.slice,ast.Tuple) else [node.slice]
            if base in {'Optional','Union'}:
                values=tuple(convert(value) for value in parts)
                return Union[values+(type(None),)] if base=='Optional' else Union[values]
            if base in {'list','List'}:return list[convert(parts[0])]
            if base in {'dict','Dict'}:return dict[convert(parts[0]),convert(parts[1])]
            raise ValueError('unsupported annotation '+text)
        raw=typename(node);qualified=engine.p.resolve_import(raw,info.span.file) or raw
        resolved=engine.p.resolve_type(raw,info.module,info.span.file)
        if resolved:return schema(engine,resolved)[0]
        builtin={'str':str,'int':int,'float':float,'bool':bool,'bytes':bytes,'Any':Any,'typing.Any':Any,
                 'uuid.UUID':UUID,'datetime.datetime':datetime,'datetime.date':date,'datetime.timedelta':timedelta,
                 'decimal.Decimal':Decimal,'pydantic.EmailStr':EmailStr}
        builtin.update({'builtins.'+name:value for name,value in list(builtin.items()) if '.' not in name})
        if qualified in builtin:return builtin[qualified]
        raise ValueError('unresolved annotation '+text)
    return convert(ast.parse(text,mode='eval').body)


def schema(engine,key):
    check(engine,'pydantic',engine.p.types[key].span)
    cache=getattr(engine.p,'native_schemas',None)
    if cache is None:cache=engine.p.native_schemas={}
    cache_key=(key,json.dumps(serial(engine.context.get('globals',{})),sort_keys=True))
    if cache_key in cache:return cache[cache_key]
    if key in getattr(engine,'building_schemas',set()):engine.unsupported('recursive native schema',engine.p.types[key].span)
    if not hasattr(engine,'building_schemas'):engine.building_schemas=set()
    engine.building_schemas.add(key)
    info=engine.p.types[key];options={};factories=set();config={};declarations={}
    # Schema metadata belongs to application initialization. Runtime writes in
    # one scenario must not change a subsequently materialized native schema.
    from .kernel import Kernel
    metadata=Kernel(engine.p,context={'globals':deepcopy(engine.context.get('globals',{}))},smt=False)
    def initial_value(expression,binding):
        value=metadata.definition_value(expression,binding)
        if unknown(value):engine.unsupported('Pydantic schema initialization value is unresolved',expression.span)
        return value
    try:
        for parent in lineage(engine.p,key):
            declarations.update({name:parent for name in parent.fields})
            hooks={'__init__','model_post_init','__get_pydantic_core_schema__','__get_pydantic_json_schema__','__getattribute__','__getattr__'}
            if parent.annotations.get('field_options_unknown') or parent.annotations.get('model_config_unknown') or any(engine.p.methods[m].annotations.get('validation_hook') or engine.p.methods[m].name in hooks for m in parent.methods):
                engine.unsupported('Source Pydantic validators/serializers/configuration need an additional interpreter contract',parent.span)
            factories.update(parent.annotations.get('default_factories',[]))
            for field,values in parent.annotations.get('field_options',{}).items():
                options[field]={k:initial_value(v,'schema:'+key+':'+field+':'+str(k)) for k,v in values.items()}
            config.update({k:initial_value(v,'schema:'+key+':config:'+str(k)) for k,v in parent.annotations.get('model_config',{}).items()})
        if any(unknown(value) for values in options.values() for value in values.values()) or any(unknown(value) for value in config.values()):
            engine.unsupported('Pydantic schema options are unresolved',info.span)
        if any(config.get(flag) for flag in ['frozen','validate_assignment','from_attributes']):
            engine.unsupported('Pydantic instance lifecycle configuration needs an additional contract',info.span)
        fields={}
        for name,(typ,default) in engine.p.type_fields(key).items():
            if name.startswith('_'):continue
            value=... if default is None or name in factories else initial_value(default,'schema:'+key+':default:'+name)
            if unknown(value):engine.unsupported('Pydantic nonliteral field default is unresolved',info.span)
            field=Field(default_factory=factory_callback(engine.p,default,options.get(name,{}).get('validate_default',config.get('validate_default',False))),**options.get(name,{})) if name in factories else Field(default=value,**options.get(name,{}))
            fields[name]=(annotation(engine,typ,declarations[name]),field)
        native=create_model('Source_'+info.name,__config__=ConfigDict(**config),**fields)
        cache[cache_key]=(native,factories)
        return cache[cache_key]
    except (ValueError,TypeError) as exc:
        engine.unsupported('Pydantic schema outside supported facts: '+str(exc),info.span)
    finally:engine.building_schemas.discard(key)


def abstract(value,active=frozenset()):
    if unknown(value):return True
    if isinstance(value,Object):value=value.fields
    if isinstance(value,(dict,list,tuple)):
        if id(value) in active:return True
        return any(abstract(v,active|{id(value)}) for v in (value.values() if isinstance(value,dict) else value))
    return False


def normalize(value):
    if isinstance(value,UUID):return str(value)
    if isinstance(value,dict):return {k:normalize(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [normalize(v) for v in value]
    if hasattr(value,'model_dump'):return normalize(value.model_dump())
    return value


def proven_symbol(value,typ,metadata):
    if metadata:return False
    types_=get_args(typ) if get_origin(typ) in {Union,types.UnionType} else (typ,)
    if isinstance(value,Text):return str in types_ or Any in types_
    if not isinstance(value,Symbol):return False
    if not value.nonnull and type(None) not in types_:return False
    short=value.typ.split('.')[-1]
    return Any in types_ or UUID in types_ and short=='UUID' or str in types_ and short in {'str','String'} or int in types_ and value.sort in {'int','bv32','bv64'} or bool in types_ and value.sort=='bool'


def validated(engine,key,data,response=False):
    native,_=schema(engine,key)
    if not isinstance(data,dict):raise Raised('ResponseValidationError' if response else 'RequestValidationError')
    if not abstract(data):
        token=ACTIVE_ENGINE.set(engine)
        try:
            result=native.model_validate(data)
            values={name:normalize(getattr(result,name)) for name in native.model_fields}
            if result.model_extra:values.update(normalize(result.model_extra))
            return values,result.model_fields_set,result
        except ValidationError as exc:
            raise Raised('ResponseValidationError' if response else 'RequestValidationError',exc.errors(include_url=False)) from None
        finally:ACTIVE_ENGINE.reset(token)
    result={};provided=set()
    def nested(annotation):
        return isinstance(annotation,type) and issubclass(annotation,BaseModel) or any(nested(part) for part in get_args(annotation))
    if any(nested(field.annotation) for field in native.model_fields.values()):
        engine.unsupported('Nested native schemas with abstract input values',engine.p.types[key].span)
    if any(key in native.model_config for key in ['validate_by_alias','validate_by_name','populate_by_name']):
        engine.unsupported('Custom alias policy with abstract input values',engine.p.types[key].span)
    consumed=set()
    for name,field in native.model_fields.items():
        alias=field.validation_alias or field.alias or name
        if not isinstance(alias,str):engine.unsupported('Complex validation alias with abstract values',engine.p.types[key].span)
        source=alias if alias in data else name if native.model_config.get('populate_by_name') and name in data else None
        if source is None:
            if field.is_required():raise Raised('ResponseValidationError' if response else 'RequestValidationError')
            token=ACTIVE_ENGINE.set(engine)
            try:result[name]=normalize(field.get_default(call_default_factory=True,validated_data=result))
            finally:ACTIVE_ENGINE.reset(token)
            continue
        provided.add(name);value=data[source]
        consumed.add(source)
        if unknown(value) and proven_symbol(value,field.annotation,field.metadata):result[name]=value;continue
        if abstract(value):engine.unsupported('Native validation of a constrained/unknown abstract field',engine.p.types[key].span)
        try:result[name]=normalize(TypeAdapter(Annotated[field.annotation,field]).validate_python(value))
        except ValidationError as exc:raise Raised('ResponseValidationError' if response else 'RequestValidationError',exc.errors(include_url=False)) from None
    extra=set(data)-consumed
    if extra and native.model_config.get('extra')=='forbid':raise Raised('ResponseValidationError' if response else 'RequestValidationError')
    if native.model_config.get('extra')=='allow':
        result.update({name:data[name] for name in extra});provided.update(extra)
    return result,provided,None


def bind_body(engine,key,value,span):
    values,provided,_=validated(engine,key,value)
    obj=engine.create(key,kwargs=values,span=span)
    obj.provided=set(provided)
    return obj


def project_response(engine,value,key,flags,span):
    native,_=schema(engine,key)
    if isinstance(value,Object):
        if value.typ==key:
            data=dict(value.fields)
            for name,field in native.model_fields.items():
                alias=field.validation_alias or field.alias
                if name in data and alias is not None:
                    if not isinstance(alias,str):engine.unsupported('Complex source-model response alias',span)
                    data[alias]=data.pop(name)
        else:
            names={name for name in native.model_fields}|{field.alias for field in native.model_fields.values() if isinstance(field.alias,str)}
            data={name:field for name,field in value.fields.items() if name in names}
    else:data=value
    values,provided,instance=validated(engine,key,data,response=True)
    if isinstance(value,Object) and value.typ==key:
        provided=set(value.provided)
        if instance is not None:
            fields={name:getattr(instance,name) for name in native.model_fields}
            instance=native.model_construct(_fields_set=provided,**fields,**(instance.model_extra or {}))
    if instance is not None and not abstract(values):
        return instance.model_dump(mode='json',by_alias=flags.get('response_model_by_alias',True),
                                   exclude_none=bool(flags.get('response_model_exclude_none')),
                                   exclude_defaults=bool(flags.get('response_model_exclude_defaults')),
                                   exclude_unset=bool(flags.get('response_model_exclude_unset')))
    output={}
    for name,field in native.model_fields.items():
        value=values[name]
        if field.exclude or flags.get('response_model_exclude_none') and value is None or flags.get('response_model_exclude_unset') and name not in provided:continue
        if flags.get('response_model_exclude_defaults') and not field.is_required() and value==field.default:continue
        alias=field.serialization_alias or field.alias or name
        output[alias if flags.get('response_model_by_alias',True) else name]=wire(value)
    if native.model_config.get('extra')=='allow':
        output.update({name:wire(value) for name,value in values.items() if name not in native.model_fields and not (flags.get('response_model_exclude_none') and value is None)})
    return output
