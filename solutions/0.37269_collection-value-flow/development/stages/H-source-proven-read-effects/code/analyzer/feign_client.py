"""Spring Cloud OpenFeign source contract, with explicit HTTP boundaries."""
import re
from copy import deepcopy
from urllib.parse import quote

from .project import text
from .state import U
from .request import Request,MISSING
from .java_exceptions import JavaThrow
from .models import unwrap,http_entity


def operation(engine,node,args,reason):
    p=engine.p;caller=engine.method;meta=p.methods[caller]
    written=engine.source_type(node.child_by_field_name('object'))
    owner=p.resolve_type(written,meta['module'],meta['file'])
    annotation=next((a for a in p.nodes.get(owner,{}).get('annotations',[]) if a['name'].rsplit('.',1)[-1]=='FeignClient'),None)
    if annotation is None:return False,U
    from .engine import AnalysisBoundary
    name=text(node.child_by_field_name('name'))
    methods=[method for method in p.by_name.get(name,[]) if p.methods[method]['owner']==owner and len(p.parameters(method))==len(args)]
    if len(methods)!=1:raise AnalysisBoundary('Feign method signature is ambiguous: '+reason,category='unknown_target')
    method=methods[0];routes=[(verb,route) for mid,verb,route in p.client_routes if mid==method]
    if len(routes)!=1:raise AnalysisBoundary('Feign HTTP mapping is ambiguous: '+reason,category='unknown_target')
    host=re.search(r'(?:\b(?:name|value)\s*=\s*|^\(\s*)"([^"]+)"',annotation.get('args',''))
    if host is None:raise AnalysisBoundary('Feign client destination is not a source literal: '+reason,category='unsupported_semantics')
    verb,route=routes[0];parameters={parameter['name']:parameter for parameter in p.http_parameters(method)}
    path={};headers={};body=MISSING
    for (key,_),value in zip(p.parameters(method),args):
        parameter=parameters.get(key,{})
        kind=parameter.get('kind');wire_name=parameter.get('wire_name',key)
        if kind=='PathVariable':path[wire_name]=value
        elif kind=='RequestHeader':headers[wire_name]=value
        elif kind=='RequestParam':raise AnalysisBoundary('Feign query parameter contract is not yet modeled: '+reason,category='unsupported_semantics')
        elif body is MISSING:body=value
        else:raise AnalysisBoundary('Feign has multiple unannotated request bodies: '+reason,category='unsupported_semantics')
    segments=[]
    for segment in route:
        value=path.get(segment[1:-1].split(':',1)[0],U) if segment.startswith('{') else segment
        if not isinstance(value,(str,int)):raise AnalysisBoundary('Feign path value is unknown: '+reason,category='unknown_value')
        segments.append(quote(str(value),safe=''))
    url='http://'+host[1]+'/'+('/'.join(segments))
    mapping=' '.join(a.get('args','') for a in p.methods[method].get('annotations',[]))
    if 'APPLICATION_JSON_UTF8_VALUE' in mapping:headers['content-type']=['application/json;charset=UTF-8']
    elif 'APPLICATION_JSON_VALUE' in mapping:headers['content-type']=['application/json']
    unit=p.ix.unit_of(caller);session=U
    oauth=engine.state.context.get('client_oauth_contexts',{}).get(unit)
    interceptor=any('OAuth2FeignRequestInterceptor' in source.decode() and
        any(info['file']==file and p.ix.unit_of(mid)==unit for mid,info in p.methods.items()) for file,source in p.sources.items())
    if oauth and interceptor:
        session=oauth
        token=oauth.get('token',U)
        if isinstance(token,str):headers['authorization']=['Bearer '+token]
        else:headers['authorization']=U
    if body is not MISSING:body=engine.json_wire(body,reason)
    targets=sorted(p.ix.handlers_for(verb,segments,host[1]))
    if len(targets)!=1:raise AnalysisBoundary('Feign target handler is absent or ambiguous: '+reason,category='unknown_target')
    target=targets[0];request=Request.http(p.ix.unit_of(target),verb,url,headers,body,session=session,
        provenance={'source_callsite':reason,'client_method':method,'oauth_boundary':'supplied verified context' if session is not U else 'unknown'})
    def entered(request_id):
        if unit!=p.ix.unit_of(target):engine.add(caller,'remote',target,reason,{'target_request':request_id,'url':url,'method':verb})
    failed=False;request_index=len(engine.request_events)
    try:response,_=engine.http_invoke(target,lambda:engine.bind_request(target,request,reason),reason,request,entered)
    except JavaThrow as failure:
        failed=True;response={'__type__':'ResponseEntity','__http_entity__':True,'status':engine.server_error_status(target,failure),'body':U}
    status=response.get('status',U) if http_entity(response) else 200
    if status is U:raise AnalysisBoundary('Feign response status is unresolved: '+reason,category='unknown_value')
    if failed or status>=400:
        fallback=re.search(r'\bfallback\s*=\s*([\w.]+)\s*\.class',annotation.get('args',''))
        enabled=any(item['module']==meta['module'] and item['key']=='feign.hystrix.enabled' and str(item['value']).lower()=='true' for item in p.config)
        if fallback and enabled:
            tid=p.resolve_type(fallback[1],meta['module'],p.nodes[owner]['file'])
            callbacks=p.inherited_methods(tid,name,len(args))
            if len(callbacks)!=1:raise AnalysisBoundary('Feign fallback target is ambiguous: '+reason,category='unknown_target')
            from .heap_join import source_nodes
            from .source_generics import render as render_source_type
            callback=callbacks[0]
            memo={id(node):node for node in source_nodes(args)}
            engine.request_events[request_index]['fallback']={'entry':callback,'bound_arguments':[
                {'name':key,'declared_type':render_source_type(p,typ,p.methods[callback],{},engine.standard_type) or typ,
                 'value':deepcopy(value,memo)} for (key,typ),value in zip(p.parameters(callback),args)]}
            return True,engine.invoke(callbacks[0],args,reason='Feign Hystrix fallback callback at '+reason)
        raise JavaThrow({'__type__':'FeignException','status':status})
    if p.methods[method].get('return_raw')=='void':return True,None
    from .http_json import decode_response
    value=decode_response(p,engine.json_wire(unwrap(response),reason),p.methods[method].get('return_raw',''),p.methods[method],engine.standard_type,
        lambda issue:engine.json_issue(issue,reason))
    return True,value
