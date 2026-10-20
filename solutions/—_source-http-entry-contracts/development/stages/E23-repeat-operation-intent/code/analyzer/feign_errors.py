"""Default error decoding retains a String's origin, never guessed error bytes."""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import re
from .feign_decoder import client_codec,transport_payload,native_subtype,boundary
from .java_collections import JavaObject
from .java_exceptions import JavaThrow,ExceptionBound
from .models import header_values
from .state import U


def scalar(value):
    if value is U:return {'unknown':True}
    if isinstance(value,datetime):return value.isoformat()
    if isinstance(value,Decimal):return str(value)
    raise TypeError('Unsupported error-message witness scalar: '+type(value).__name__)


def default_error(engine,method,target,response,status,request_index,reason):
    payload=transport_payload(engine,response,target,status,request_index,reason)
    client_codec(engine,method,reason)
    p=engine.p;unit=p.ix.unit_of(engine.method)
    for mid,meta in p.methods.items():
        if unit not in p.ix.units.get(meta['module'],()) or not p.enabled_type(meta['owner']):continue
        if any(engine.standard_type(a['name'],'org.springframework.context.annotation.Bean',meta)
               for a in meta.get('annotations',[])) and native_subtype(engine,meta.get('return_raw',''),'feign.codec.ErrorDecoder',meta):
            boundary(reason,'custom source ErrorDecoder is unresolved')
    for module,units in p.ix.units.items():
        if unit not in units:continue
        if any(re.fullmatch(r'(?:spring\.cloud\.openfeign|feign)\.client\.config\.[^.]+\.errorDecoder',row['key'])
               for row in p.configuration.entries.get(module,())):
            boundary(reason,'configured ErrorDecoder is unresolved')
    headers=header_values(response.get('headers',{}))
    if headers is U or any(key.lower()=='retry-after' for key in headers):
        boundary(reason,'response headers/Retry-After error policy is unresolved')
    event=engine.request_events[request_index]
    request={key:deepcopy(event['request'][key]) for key in ('deployment','method','url','path','query','query_complete')}
    facts={'model_version':'feign-default-error-message/1','request_id':event['id'],'status':status,
           'client_method':method,'request':request,'response_body':deepcopy(payload),
           'exact_text':False,'limits':['Version, reason phrase, charset and body-preview bytes are not materialized']}
    digest=hashlib.sha256(json.dumps(facts,sort_keys=True,ensure_ascii=True,default=scalar).encode()).hexdigest()[:20]
    message={'__symbol__':'feign-message-'+digest,'__type__':'String','__constraints__':['non_null'],
             '__feign_error_message__':facts}
    family=ExceptionBound('feign.FeignException')
    raise JavaThrow(JavaObject(family,{'__type__':family,'message':message,'status':status}))
