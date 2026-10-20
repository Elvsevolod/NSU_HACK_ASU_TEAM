"""Default JSON collection binding using declared response/property types.

This preserves the analyzer's DTO metadata; it is not a Jackson implementation.
Custom codecs, polymorphism and general Java runtime casts remain unresolved.
"""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from .java_collections import JavaMap,JavaRecord,JsonObject,JsonText,raw_json_map
from .state import U
from .boxed_values import value_kind,json_value_kind
from .models import uuid_value
from .java_exceptions import JavaThrow,ExceptionBound
from .generic_types import type_parts,resolve,bind_parameters,declaring_bindings
from .source_generics import render,member_scope
from .native_storage import JavaList
from .native_arrays import JavaArray


def decode_response(project,payload,response_type,meta,standard_type,unresolved,codec=None,certain=True,lifecycle=None):
    def fail(message):
        unresolved(message)
        return U
    def decoded_kind(value,written,context,bindings):
        resolved=render(project,written,context,bindings,standard_type)
        aliases={'int':'Integer','long':'Long','short':'Short','byte':'Byte','char':'Character',
                 'boolean':'Boolean','float':'Float','double':'Double'}
        hint=aliases.get(resolved)
        if hint is None:
            hint=next((name for name in ('String','Integer','Long','Short','Byte','Character','Boolean','Float','Double')
                       if standard_type(resolved,'java.lang.'+name,context)),None)
        return value_kind(value,hint) if hint else json_value_kind(value)
    def decode(value,written,context,bindings=None,certain=certain):
        if value is U:return value
        bindings={} if bindings is None else bindings
        written,context,bindings=resolve(written,context,bindings)
        base,arguments=type_parts(written)
        if value is None:
            if base in ('int','long','short','byte','char','boolean','double','float'):
                policy=codec.get('FAIL_ON_NULL_FOR_PRIMITIVES',U) if codec is not None and certain else U
                if policy is False:return False if base=='boolean' else '\0' if base=='char' else 0.0 if base in ('float','double') else 0
                if policy is True:
                    raise JavaThrow({'__type__':ExceptionBound('com.fasterxml.jackson.databind.JsonMappingException')})
                return fail('HTTP JSON null for a primitive needs a codec default/failure policy')
            return None
        if written.endswith('[]'):
            element=written[:-2]
            component=render(project,element,context,bindings,standard_type)
            if not component:return fail('HTTP array component type is unresolved: '+written)
            if component in ('byte','char') and isinstance(value,str):
                return fail('HTTP byte/char array text representation requires a supported specialized codec')
            if not isinstance(value,list):
                unwrap=codec.get('ACCEPT_SINGLE_VALUE_AS_ARRAY',U) if codec is not None and certain else U
                if unwrap is False:
                    raise JavaThrow({'__type__':ExceptionBound('com.fasterxml.jackson.databind.JsonMappingException')})
                if unwrap is True:value=[value]
                else:return fail('HTTP array scalar coercion requires a supported codec policy')
            decoded=[decode(child,element,context,bindings,certain) for child in value]
            result=JavaArray(decoded,component,[decoded_kind(child,element,context,bindings) for child in decoded])
            result.order_known=getattr(value,'order_known',True)
            if hasattr(value,'repository_order'):result.repository_order=deepcopy(value.repository_order)
            return result
        if isinstance(value,JsonText):
            if standard_type(base,'java.lang.String',context) or standard_type(base,'java.lang.Object',context):return deepcopy(value)
            return fail('JSON text scalar is incompatible with the requested structured type')
        if standard_type(base,'java.math.BigDecimal',context) and type(value) in (int,Decimal):return Decimal(value)
        if standard_type(base,'java.util.UUID',context):
            try:result=uuid_value(value)
            except JavaThrow:result=U
            return result if result is not U else fail('HTTP UUID text conversion is not modeled for this value')
        if isinstance(value,dict) and not isinstance(value,JsonObject) and '__symbol__' in value:
            aliases={'Integer':'int','Long':'long','Double':'double','Float':'float','Boolean':'boolean'}
            scalar=value.get('__type__','').rsplit('.',1)[-1]
            wanted=base.rsplit('.',1)[-1]
            primitive=base in ('int','long','double','float','boolean')
            native=wanted in ('String','Integer','Long','Double','Float','Boolean') and standard_type(base,'java.lang.'+wanted,context)
            if (primitive or native) and aliases.get(scalar,scalar)==aliases.get(wanted,wanted):return deepcopy(value)
            if scalar in ('String','int','long','double','float','boolean') and standard_type(base,'java.lang.Object',context):return deepcopy(value)
            return fail('opaque HTTP value has an unresolved declared scalar type')
        if standard_type(base,'java.lang.Object',context):
            return raw_json_map(value,unresolved)
        map_type=base.rsplit('.',1)[-1]
        if map_type in ('Map','HashMap','LinkedHashMap') and standard_type(base,'java.util.'+map_type,context):
            if not isinstance(value,dict) or '__type__' in value and not isinstance(value,JsonObject) or any(type(key) is not str for key in value):
                return fail('HTTP Map value is not an unambiguous JSON object')
            key,key_context,_=resolve(arguments[0],context,bindings) if arguments else ('java.lang.String',context,{})
            if arguments is None or arguments and (len(arguments)!=2 or not standard_type(key,'java.lang.String',key_context)):
                return fail('HTTP Map key or generic type is not modeled')
            typ=arguments[1] if arguments else 'java.lang.Object'
            decoded={key:decode(child,typ,context,bindings,certain) for key,child in value.items()}
            declared,declared_context,_=resolve(typ,context,bindings)
            hint='unresolved'
            for scalar in ('String','Integer','Long','Short','Byte','Character','Boolean','Float','Double'):
                if standard_type(declared,'java.lang.'+scalar,declared_context):hint=scalar;break
            return JavaMap(decoded,value_types={key:value_kind(child,hint) if hint!='unresolved' else
                           json_value_kind(child) for key,child in decoded.items()})
        list_type=base.rsplit('.',1)[-1]
        if list_type in ('List','ArrayList','LinkedList') and standard_type(base,'java.util.'+list_type,context):
            if not isinstance(value,list) or arguments is None or len(arguments)>1:
                return fail('HTTP collection shape or generic type is not modeled')
            element=arguments[0] if arguments else 'java.lang.Object'
            decoded=[decode(child,element,context,bindings,certain) for child in value]
            result=JavaList(decoded,[decoded_kind(child,element,context,bindings) for child in decoded])
            result.order_known=getattr(value,'order_known',True)
            if hasattr(value,'repository_order'):result.repository_order=deepcopy(value.repository_order)
            return result
        owner=project.resolve_type(base,context['module'],context['file'])
        if owner in project.enum_members:
            constants=[project.enum_objects[key] for key in project.enum_members[owner]]
            if any(not item.json_default for item in constants):return fail('custom enum JSON binding is not modeled')
            match=next((item for item in constants if item.enum_name==value),None) if isinstance(value,str) else None
            return deepcopy(match) if match is not None else fail('HTTP enum JSON value is not a supported constant name')
        if owner in project.type_fields and not isinstance(value,dict):
            return fail('HTTP DTO scalar coercion is not modeled')
        if owner in project.type_fields and isinstance(value,dict):
            if lifecycle is not None:
                return lifecycle.decode(value,written,owner,context,bindings,codec,certain,decode,decoded_kind,unresolved)
            if owner in project.json_construction_limits:
                return fail('HTTP JSON construction is not modeled: '+project.json_construction_limits[owner])
            limits=project.json_model_limits(project.nodes[owner]['fqn'],'deserialize')
            for message in limits:unresolved(message)
            certain=certain and not limits
            fields=project.type_fields[owner]
            if set(value)-fields.keys():
                policy=any(standard_type(name,'com.fasterxml.jackson.annotation.JsonIgnoreProperties',project.nodes[owner])
                           for name in project.json_ignore_unknown.get(owner,()))
                if not policy:
                    flag=codec.get('FAIL_ON_UNKNOWN_PROPERTIES',U) if codec is not None and certain else U
                    if flag is True:raise JavaThrow({'__type__':ExceptionBound('com.fasterxml.jackson.databind.JsonMappingException')})
                    if flag is not False:return fail('undeclared JSON properties require an explicit JSON binding policy')
            local=bind_parameters(project,owner,arguments,context,bindings)
            if local is None:return fail('HTTP DTO generic argument count is not modeled')
            annotations=project.nodes[owner].get('annotations',[])
            if any(a['name'].split('.')[-1] in ('JsonDeserialize','JsonSerialize','JsonTypeInfo') for a in annotations):
                return fail('custom or polymorphic HTTP JSON binding is not modeled')
            result=deepcopy({key:item for key,item in value.items() if key in fields})
            if '__type__' not in project.type_fields[owner]:result['__type__']=project.nodes[owner]['fqn']
            if '__http_entity__' not in project.type_fields[owner]:result['__http_entity__']=False
            for field,info in project.type_fields[owner].items():
                if field not in value:
                    if codec is not None and certain:
                        default=info['default']
                        if default is U and not info['has_initializer']:
                            default=False if info['type']=='boolean' else '\0' if info['type']=='char' else 0.0 if info['type'] in ('float','double') else 0 if info['type'] in ('int','long','short','byte') else None
                        result[field]=deepcopy(default)
                        if default is U:unresolved('JSON property initializer is not modeled')
                    continue
                declared=info['declaring_type']
                typ=info['type']
                field_bindings=declaring_bindings(project,owner,declared,local)
                if field_bindings is None:
                    result[field]=fail('HTTP generic property inheritance or substitution is not modeled')
                    continue
                result[field]=decode(value[field],typ,project.nodes[declared],field_bindings,certain)
            record=JavaRecord(project.nodes[owner]['fqn'],result,project.type_fields[owner])
            record.source_owner=owner
            record._native_field_kinds={}
            record._field_reference_types={}
            record._unchecked_generic_fields=set()
            for field,info in fields.items():
                declared=info['declaring_type']
                field_bindings=declaring_bindings(project,owner,declared,local)
                scope=member_scope(project,written,declared,context)
                if scope is not None and scope[1]:record._unchecked_generic_fields.add(field)
                rendered=render(project,info['type'],project.nodes[declared],field_bindings or {},standard_type)
                if scope is not None and not scope[1]:record._field_reference_types[field]=rendered
                record._native_field_kinds[field]=(decoded_kind(result.get(field,U),info['type'],project.nodes[declared],field_bindings or {})
                    if field in value else info.get('default_kind'))
            return record
        if isinstance(value,(dict,list)):
            return fail('HTTP JSON binding structured value has an unsupported declared type: '+written)
        simple=base.rsplit('.',1)[-1]
        scalars={'String':str,'Boolean':bool,'boolean':bool,'Integer':int,'int':int,
                 'Long':int,'long':int,'Byte':int,'byte':int,'Short':int,'short':int,
                 'Double':float,'double':float}
        native=base in ('boolean','int','long','byte','short','double') or simple in scalars and standard_type(base,'java.lang.'+simple,context)
        if native:
            expected=scalars[simple]
            if expected is float and type(value) in (int,float):return float(value)
            if type(value) is not expected:return fail('HTTP scalar coercion is not modeled: '+written)
            if expected is int:
                bits={'Integer':32,'int':32,'Long':64,'long':64,'Byte':8,'byte':8,'Short':16,'short':16}[simple]
                if not -(1<<(bits-1))<=value<(1<<(bits-1)):return fail('HTTP integer range conversion is not modeled')
            return value
        if standard_type(base,'java.util.Date',context) and isinstance(value,datetime):return value
        return fail('HTTP scalar declared type is not modeled: '+written)
    return decode(payload,response_type,meta)
