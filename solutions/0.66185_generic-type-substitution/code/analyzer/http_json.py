"""Default JSON collection binding using declared response/property types.

This preserves the analyzer's DTO metadata; it is not a Jackson implementation.
Custom codecs, polymorphism and general Java runtime casts remain unresolved.
"""
from copy import deepcopy
from datetime import datetime
from .java_collections import JavaMap,JavaRecord,JsonObject,JsonText,raw_json_map
from .state import U
from .boxed_values import value_kind
from .models import uuid_value
from .java_exceptions import JavaThrow
from .generic_types import type_parts,resolve,bind_parameters,declaring_bindings


def decode_response(project,payload,response_type,meta,standard_type,unresolved):
    def fail(message):
        unresolved(message)
        return U
    def decode(value,written,context,bindings=None):
        if value is U:return value
        bindings={} if bindings is None else bindings
        written,context,bindings=resolve(written,context,bindings)
        base,arguments=type_parts(written)
        if value is None:
            if base in ('int','long','short','byte','char','boolean','double','float'):
                return fail('HTTP JSON null for a primitive needs a codec default/failure policy')
            return None
        if isinstance(value,JsonText):
            if standard_type(base,'java.lang.String',context) or standard_type(base,'java.lang.Object',context):return deepcopy(value)
            return fail('JSON text scalar is incompatible with the requested structured type')
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
            decoded={key:decode(child,typ,context,bindings) for key,child in value.items()}
            declared,declared_context,_=resolve(typ,context,bindings)
            hint='unresolved'
            for scalar in ('String','Integer','Long','Short','Byte','Character','Boolean','Float','Double'):
                if standard_type(declared,'java.lang.'+scalar,declared_context):hint=scalar;break
            return JavaMap(decoded,value_types={key:value_kind(child,hint) if hint!='unresolved' else
                           value_kind(child) if type(child) in (str,bool) else None for key,child in decoded.items()})
        list_type=base.rsplit('.',1)[-1]
        if list_type in ('List','ArrayList','LinkedList') and standard_type(base,'java.util.'+list_type,context):
            if not isinstance(value,list) or arguments is None or len(arguments)>1:
                return fail('HTTP collection shape or generic type is not modeled')
            return [decode(child,arguments[0] if arguments else 'java.lang.Object',context,bindings) for child in value]
        owner=project.resolve_type(base,context['module'],context['file'])
        if owner in project.enum_members:
            constants=[project.enum_objects[key] for key in project.enum_members[owner]]
            if any(not item.json_default for item in constants):return fail('custom enum JSON binding is not modeled')
            match=next((item for item in constants if item.enum_name==value),None) if isinstance(value,str) else None
            return deepcopy(match) if match is not None else fail('HTTP enum JSON value is not a supported constant name')
        if owner in project.type_fields and not isinstance(value,dict):
            return fail('HTTP DTO scalar coercion is not modeled')
        if owner in project.type_fields and isinstance(value,dict):
            if owner in project.json_construction_limits:
                return fail('HTTP JSON construction is not modeled: '+project.json_construction_limits[owner])
            for message in project.json_model_limits(project.nodes[owner]['fqn'],'deserialize'):unresolved(message)
            fields=project.type_fields[owner]
            if set(value)-fields.keys():
                policy=any(standard_type(name,'com.fasterxml.jackson.annotation.JsonIgnoreProperties',project.nodes[owner])
                           for name in project.json_ignore_unknown.get(owner,()))
                if not policy:return fail('undeclared JSON properties require an explicit JSON binding policy')
            local=bind_parameters(project,owner,arguments,context,bindings)
            if local is None:return fail('HTTP DTO generic argument count is not modeled')
            annotations=project.nodes[owner].get('annotations',[])
            if any(a['name'].split('.')[-1] in ('JsonDeserialize','JsonSerialize','JsonTypeInfo') for a in annotations):
                return fail('custom or polymorphic HTTP JSON binding is not modeled')
            result=deepcopy({key:item for key,item in value.items() if key in fields})
            if '__type__' not in project.type_fields[owner]:result['__type__']=project.nodes[owner]['fqn']
            if '__http_entity__' not in project.type_fields[owner]:result['__http_entity__']=False
            for field,info in project.type_fields[owner].items():
                if field not in value:continue
                declared=info['declaring_type']
                typ=info['type']
                field_bindings=declaring_bindings(project,owner,declared,local)
                if field_bindings is None:
                    result[field]=fail('HTTP generic property inheritance or substitution is not modeled')
                    continue
                result[field]=decode(value[field],typ,project.nodes[declared],field_bindings)
            return JavaRecord(project.nodes[owner]['fqn'],result,project.type_fields[owner])
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
