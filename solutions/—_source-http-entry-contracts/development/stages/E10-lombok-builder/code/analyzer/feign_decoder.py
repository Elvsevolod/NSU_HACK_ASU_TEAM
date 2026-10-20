"""Default Feign Spring decoder over the existing source JavaBean lifecycle.

No bean factory is executed here. Known custom codecs are boundaries; Boot
defaults are used only with a native Boot application in the calling unit.
"""
import re
from .state import U
from .http_json import decode_response
from .bean_lifecycle import BeanLifecycle
from .generic_types import type_parts
from .java_exceptions import JavaThrow,assignable


def boundary(reason,message):
    from .engine import AnalysisBoundary
    raise AnalysisBoundary('Feign response codec '+message+': '+reason,category='unsupported_semantics')


def native_subtype(engine,written,fqn,meta,seen=frozenset()):
    if engine.standard_type(written,fqn,meta):return True
    base,_=type_parts(written)
    owner=engine.p.resolve_type(base,meta['module'],meta['file'])
    if owner is None or owner in seen:return False
    return any(native_subtype(engine,parent,fqn,engine.p.nodes[owner],seen|{owner})
               for parent in engine.p.framework_types.get(owner,()))


def codec(engine,unit,reason,*,client=True):
    p=engine.p;cache=p.__dict__.setdefault('_feign_default_json_codec',{})
    key=(unit,client)
    if key in cache:
        value,error=cache[key]
        if error:boundary(reason,error)
        return value
    owners=[(owner,meta) for owner,meta in p.nodes.items() if meta['kind']=='type' and
            unit in p.ix.units.get(meta.get('module'),()) and p.enabled_type(owner)]
    boots=[a for _,meta in owners for a in meta.get('annotations',[])
           if engine.standard_type(a['name'],'org.springframework.boot.autoconfigure.SpringBootApplication',meta)]
    boot=bool(boots)
    custom_types=('com.fasterxml.jackson.databind.ObjectMapper','com.fasterxml.jackson.databind.Module',
        'org.springframework.http.converter.json.Jackson2ObjectMapperBuilder',
        'org.springframework.http.converter.HttpMessageConverter',
        'org.springframework.boot.autoconfigure.http.HttpMessageConverters',
        'org.springframework.boot.autoconfigure.jackson.Jackson2ObjectMapperBuilderCustomizer',
        'org.springframework.cloud.openfeign.support.HttpMessageConverterCustomizer')
    if client:custom_types+=('feign.codec.Decoder','feign.Feign.Builder','feign.Capability')
    error='has unobserved Boot bootstrap options' if any(a.get('args','').strip('() ') for a in boots) else None
    if client and any(engine.standard_type(a['name'],'org.springframework.cloud.openfeign.EnableFeignClients',meta)
            and re.search(r'\bdefaultConfiguration\s*=',a.get('args',''))
            for _,meta in owners for a in meta.get('annotations',[])):
        error='has unobserved default client configuration'
    from .source_configuration import matches
    for mid,meta in p.methods.items():
        if unit not in p.ix.units.get(meta['module'],()) or not p.enabled_type(meta['owner']):continue
        if not any(engine.standard_type(a['name'],'org.springframework.context.annotation.Bean',meta)
                   for a in meta.get('annotations',[])):continue
        disabled=False
        for a in meta.get('annotations',[]):
            if engine.standard_type(a['name'],'org.springframework.context.annotation.Profile',meta):
                expression=a.get('args','').strip('() "')
                disabled=matches(expression,p.configuration.profiles.get(meta['module'])) is False
        if disabled:continue
        written=meta.get('return_raw','')
        if engine.standard_type(written,'java.lang.Object',meta) or any(native_subtype(engine,written,fqn,meta) for fqn in custom_types):
            error='has a custom or opaque source bean '+mid;break
    flags={'FAIL_ON_UNKNOWN_PROPERTIES':False,'FAIL_ON_NULL_FOR_PRIMITIVES':False,'FAIL_ON_IGNORED_PROPERTIES':False} if boot else None
    accepted={'springjacksondeserialization'+key.lower().replace('_',''):key for key in (
        'FAIL_ON_UNKNOWN_PROPERTIES','FAIL_ON_NULL_FOR_PRIMITIVES','FAIL_ON_IGNORED_PROPERTIES')}
    values={}
    for module in {meta['module'] for _,meta in owners}:
        for row in p.configuration.entries.get(module,()):
            key=row['key']
            if client and re.fullmatch(r'(?:spring\.cloud\.openfeign|feign)\.client\.config\.[^.]+\.(?:decoder|responseInterceptor|capabilities)',key):
                error='has a configured client codec override'
            if not key.lower().startswith('spring.jackson.'):continue
            feature=accepted.get(re.sub('[^a-z0-9]','',key.lower()))
            if feature is None:error='has an unsupported Jackson configuration';continue
            observed=p.configuration.value(module,key,U)
            if isinstance(observed,str) and observed.lower() in ('true','false'):observed=observed.lower()=='true'
            if type(observed) is not bool:error='feature value is unresolved';continue
            if feature in values and values[feature] is not observed:error='feature aliases disagree'
            values[feature]=observed
    if values and flags is None:error='defaults for a non-Boot configuration are unobserved'
    if flags is not None:flags.update(values)
    cache[(unit,client)]=flags,error
    if error:boundary(reason,error)
    return flags


def decode(engine,payload,written,method,status,reason):
    p=engine.p;meta=p.methods[method];unit=p.ix.unit_of(engine.method)
    owner=p.nodes[meta['owner']]
    if any(engine.standard_type(a['name'],'org.springframework.cloud.openfeign.FeignClient',owner)
           and re.search(r'\bconfiguration\s*=',a.get('args','')) for a in owner.get('annotations',[])):
        boundary(reason,'has unobserved per-client configuration')
    flags=codec(engine,unit,reason);issues=[]
    def note(message):issues.append(message);engine.json_issue(message,reason)
    def body(typ):
        return decode_response(p,payload,typ,meta,engine.standard_type,note,codec=flags,
            lifecycle=BeanLifecycle(engine,reason,defaults_certain=flags is not None))
    base,arguments=type_parts(written)
    entity=any(engine.standard_type(base,fqn,meta) for fqn in ('org.springframework.http.ResponseEntity','org.springframework.http.HttpEntity'))
    try:
        if entity:
            if arguments is None or len(arguments)>1:boundary(reason,'HTTP entity generic type is unresolved')
            value={'__type__':'ResponseEntity','__http_entity__':True,'body':body(arguments[0]) if arguments else None,
                   'status':status,'headers':U}
        else:value=body(written)
    except JavaThrow as failure:
        from .engine import exception_type
        if assignable(exception_type(failure.value),'com.fasterxml.jackson.core.JsonProcessingException',p) is True:
            raise JavaThrow({'__type__':'feign.codec.DecodeException','status':status,'cause':failure.value}) from None
        raise
    if issues:boundary(reason,'conversion is not proved: '+issues[0])
    return value
