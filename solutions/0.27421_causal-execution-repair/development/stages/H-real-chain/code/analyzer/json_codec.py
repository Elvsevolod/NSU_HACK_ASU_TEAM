"""Observed operations on a constructor-owned Jackson 2 ObjectMapper."""
import json
import math
from .java_collections import JavaJsonMapper,JacksonFeature,JavaTypeFactory,JavaTypeToken,JsonText,JsonObject,JavaMap,JavaRecord
from .java_exceptions import JavaThrow
from .http_json import decode_response,type_parts
from .models import wire
from .heap_join import owned_objects,widen
from .state import U


def operation(mapper,name,args,issue):
    if name=='copy' and not args:
        result=JavaJsonMapper(mapper.flags)
        result.opaque=mapper.opaque
        return True,result
    if name=='isEnabled' and len(args)==1 and isinstance(args[0],JacksonFeature):
        result=mapper.flags.get(args[0].name,U) if not mapper.opaque else U
        if result is U:issue('JSON codec feature value is unresolved')
        return True,result
    if name in ('configure','enable','disable'):
        if name=='configure' and len(args)==2 and isinstance(args[0],JacksonFeature) and args[1] is None:
            raise JavaThrow({'__type__':'NullPointerException'})
        features=args[:1] if name=='configure' else args
        enabled=args[1] if name=='configure' and len(args)==2 else name=='enable' if name!='configure' else U
        valid=(len(args)==2 if name=='configure' else bool(args)) and all(isinstance(feature,JacksonFeature) and feature.name in mapper.defaults for feature in features)
        if not valid or mapper.used or mapper.opaque:
            mapper.invalidate()
            issue('JSON codec configuration after use or unsupported feature is unresolved')
        else:
            for feature in features:mapper.flags[feature.name]=enabled if type(enabled) is bool else U
            if type(enabled) is not bool:issue('JSON codec configuration value is unresolved')
        return True,mapper
    if name in ('hashCode','toString'):
        issue('JSON mapper Object operation is unresolved: '+name)
        return True,U
    if name not in ('writeValueAsString','readValue','convertValue','getTypeFactory','getClass','equals','hashCode','toString'):
        mapper.invalidate()
        issue('unsupported JSON codec operation may change configuration: '+name)
        return True,U
    return False,U


def conversion(mapper,name,args,project,standard_type,issue,lifecycle=None):
    if mapper.opaque:
        issue('JSON codec configuration is opaque')
        return U
    if name=='getTypeFactory' and not args:return JavaTypeFactory()
    mapper.used=True
    messages=[]
    def note(message):
        messages.append(message)
        issue(message)
    def serialize(value):return wire(value,note,project.json_model_limits,lifecycle.read if lifecycle else None)
    try:
        if name=='writeValueAsString' and len(args)==1:
            return JsonText(serialize(args[0]),not messages)
        if name not in ('readValue','convertValue') or len(args)!=2 or not isinstance(args[1],JavaTypeToken) or args[1].kind not in ('Class','JavaType','TypeReference'):
            issue('JSON mapper overload or target type is not modeled')
            return U
        token=args[1]
        if name=='convertValue':
            base,_=type_parts(token.written)
            target=project.resolve_type(base,token.context['module'],token.context['file'])
            ancestry=set()
            pending=[tid for tid,node in project.nodes.items() if node['kind']=='type' and isinstance(args[0],JavaRecord) and node['fqn']==args[0].declared_type]
            while pending:
                tid=pending.pop()
                if tid in ancestry:continue
                ancestry.add(tid);pending.extend(project.type_parents.get(tid,()))
            mutable=isinstance(args[0],(JavaMap,JavaRecord,list))
            possibly_same=(target is not None and target in ancestry or
                           isinstance(args[0],JavaMap) and any(standard_type(base,fqn,token.context) for fqn in ('java.util.Map','java.util.HashMap','java.util.LinkedHashMap')) or
                           mutable and standard_type(base,'java.lang.Object',token.context))
            if possibly_same:
                for value in list(owned_objects(args[0])):widen(value)
                issue('same-type convertValue aliasing depends on the unobserved Jackson version')
                return U
            payload=serialize(args[0]);exact=not messages
        elif isinstance(args[0],JsonText):
            payload,exact=args[0].payload,args[0].exact
        elif isinstance(args[0],str):
            try:
                def finite_number(written):
                    result=float(written)
                    if not math.isfinite(result):raise ValueError('nonfinite JSON number')
                    return result
                def invalid_constant(written):raise ValueError('nonstandard JSON constant')
                payload=json.loads(args[0],object_pairs_hook=JsonObject,parse_float=finite_number,parse_constant=invalid_constant)
                exact=True
            except (ValueError,RecursionError):
                issue('JSON text syntax or trailing-token policy is not modeled')
                return U
        else:
            issue('JSON text representation is not modeled')
            return U
        if not exact:issue('JSON payload projection is not proven complete for codec failures')
        return decode_response(project,payload,token.written,token.context,standard_type,issue,mapper.flags,exact,lifecycle)
    except JavaThrow as failure:
        if name=='convertValue':raise JavaThrow({'__type__':'java.lang.IllegalArgumentException'}) from None
        raise
