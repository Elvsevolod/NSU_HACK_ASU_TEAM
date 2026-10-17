"""Default JSON collection binding using declared response/property types.

This preserves the analyzer's DTO metadata; it is not a Jackson implementation.
Custom codecs, polymorphism and generic inheritance remain unresolved.
"""
from copy import deepcopy
import re
from datetime import datetime
from .java_collections import JavaMap,raw_json_map
from .state import U


def type_parts(written):
    written=re.sub(r'\s+','',written)
    if '<' not in written:return written,[]
    base,tail=written.split('<',1)
    if not tail.endswith('>'):return base,None
    result,start,depth=[],0,0
    for index,char in enumerate(tail[:-1]):
        if char=='<':depth+=1
        elif char=='>':depth-=1
        elif char==',' and depth==0:result.append(tail[start:index]);start=index+1
    result.append(tail[start:-1])
    return base,result if depth==0 else None


def decode_response(project,payload,response_type,meta,standard_type,unresolved):
    def fail(message):
        unresolved(message)
        return U
    def decode(value,written,context):
        if value is U or value is None:return value
        base,arguments=type_parts(written)
        if isinstance(value,dict) and '__symbol__' in value:
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
            if not isinstance(value,dict) or '__type__' in value or any(type(key) is not str for key in value):
                return fail('HTTP Map value is not an unambiguous JSON object')
            if arguments is None or arguments and (len(arguments)!=2 or not standard_type(arguments[0],'java.lang.String',context)):
                return fail('HTTP Map key or generic type is not modeled')
            typ=arguments[1] if arguments else 'java.lang.Object'
            return JavaMap({key:decode(child,typ,context) for key,child in value.items()})
        list_type=base.rsplit('.',1)[-1]
        if list_type in ('List','ArrayList','LinkedList') and standard_type(base,'java.util.'+list_type,context):
            if not isinstance(value,list) or arguments is None or len(arguments)>1:
                return fail('HTTP collection shape or generic type is not modeled')
            return [decode(child,arguments[0] if arguments else 'java.lang.Object',context) for child in value]
        owner=project.resolve_type(base,context['module'],context['file'])
        if owner in project.type_fields and not isinstance(value,dict):
            return fail('HTTP DTO scalar coercion is not modeled')
        if owner in project.type_fields and isinstance(value,dict):
            if arguments:return fail('HTTP parameterized DTO binding is not modeled')
            annotations=project.nodes[owner].get('annotations',[])
            if any(a['name'].split('.')[-1] in ('JsonDeserialize','JsonSerialize','JsonTypeInfo') for a in annotations):
                return fail('custom or polymorphic HTTP JSON binding is not modeled')
            if '__type__' in project.type_fields[owner]:
                return fail('HTTP DTO business field conflicts with abstract type metadata')
            result=deepcopy(value)
            result.update(__type__=project.nodes[owner]['fqn'],__http_entity__=False)
            for field,info in project.type_fields[owner].items():
                if field not in value:continue
                declared=info['declaring_type']
                typ=info['type']
                variables=project.type_variables.get(declared,{})
                used=set(re.findall(r'[\w.]+',typ)) & variables.keys()
                if used:
                    if declared!=owner or any(variables[name] is None for name in used):
                        result[field]=fail('HTTP generic property substitution is not modeled')
                        continue
                    typ=re.sub(r'\b\w+\b',lambda match:variables[match[0]] if match[0] in used else match[0],typ)
                result[field]=decode(value[field],typ,project.nodes[declared])
            return result
        if isinstance(value,(dict,list)):
            return fail('HTTP structured value has an unsupported declared type: '+written)
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
