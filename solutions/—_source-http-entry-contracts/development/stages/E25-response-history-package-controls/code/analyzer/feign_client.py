"""Spring Cloud OpenFeign source contract, with explicit HTTP boundaries."""
import re
from copy import deepcopy

from .project import text
from .state import U
from .request import Request,MISSING
from .java_exceptions import JavaThrow
from .models import http_entity


def source_interceptors(engine,unit):
    """Potential source beans require effects/registration modeling before dispatch."""
    p=engine.p;cache=p.__dict__.setdefault('_feign_source_interceptors',{})
    if unit in cache:return cache[unit]
    def interceptor(written,context,seen=frozenset()):
        if engine.standard_type(written,'feign.RequestInterceptor',context):return True
        owner=p.resolve_type(written,context['module'],context['file'])
        if owner is None or owner in seen:return False
        return any(interceptor(parent,p.nodes[owner],seen|{owner}) for parent in p.framework_types.get(owner,()))
    def annotation(meta,fqn):
        return any(engine.standard_type(a['name'],fqn,meta) for a in meta.get('annotations',[]))
    def oauth_factory(mid,meta):
        node=p.ast.get(mid);body=node.child_by_field_name('body') if node is not None else None
        statements=body.named_children if body is not None else []
        if len(statements)!=1 or statements[0].type!='return_statement' or len(statements[0].named_children)!=1:return False
        value=statements[0].named_children[0]
        return value.type=='object_creation_expression' and engine.standard_type(text(value.child_by_field_name('type')),
            'org.springframework.cloud.security.oauth2.client.feign.OAuth2FeignRequestInterceptor',meta)
    beans=[];oauth=[]
    for owner,meta in p.nodes.items():
        if meta['kind']!='type' or unit not in p.ix.units.get(meta.get('module'),()) or not p.enabled_type(owner):continue
        if interceptor(meta['fqn'],meta) and any(annotation(meta,prefix+name) for prefix,name in (
            ('org.springframework.stereotype.','Component'),('org.springframework.stereotype.','Service'),
            ('org.springframework.context.annotation.','Configuration'))):beans.append(owner)
    for mid,meta in p.methods.items():
        if p.ix.unit_of(mid)!=unit or not p.enabled_type(meta['owner']) or not annotation(meta,'org.springframework.context.annotation.Bean'):continue
        known=oauth_factory(mid,meta)
        if known or interceptor(meta.get('return_raw',''),meta):beans.append(mid)
        if known:oauth.append(mid)
    cache[unit]=tuple(sorted(beans)),tuple(sorted(oauth))
    return cache[unit]


def operation(engine,node,args,reason):
    p=engine.p;caller=engine.method;meta=p.methods[caller]
    written=engine.source_type(node.child_by_field_name('object'))
    owner=p.resolve_type(written,meta['module'],meta['file'])
    annotation=next((a for a in p.nodes.get(owner,{}).get('annotations',[])
        if engine.standard_type(a['name'],'org.springframework.cloud.openfeign.FeignClient',p.nodes[owner])),None)
    if annotation is None:return False,U
    from .engine import AnalysisBoundary
    name=text(node.child_by_field_name('name'))
    methods=[method for method in p.by_name.get(name,[]) if p.methods[method]['owner']==owner and len(p.parameters(method))==len(args)]
    if len(methods)!=1:raise AnalysisBoundary('Feign method signature is ambiguous: '+reason,category='unknown_target')
    method=methods[0]
    from .feign_wire import request_parts
    verb,url,address,headers,body,wire_provenance=request_parts(engine,owner,method,args,annotation,reason)
    mapping=' '.join(a.get('args','') for a in p.methods[method].get('annotations',[]))
    if 'APPLICATION_JSON_UTF8_VALUE' in mapping:headers['content-type']=['application/json;charset=UTF-8']
    elif 'APPLICATION_JSON_VALUE' in mapping:headers['content-type']=['application/json']
    unit=p.ix.unit_of(caller);session=U
    oauth=engine.state.context.get('client_oauth_contexts',{}).get(unit)
    interceptors,oauth_factories=source_interceptors(engine,unit)
    if oauth and oauth_factories:
        session=oauth
        token=oauth.get('token',U)
        if isinstance(token,str):headers['authorization']=['Bearer '+token]
        else:headers['authorization']=U
    if body is not MISSING:body=engine.json_wire(body,reason)
    interceptors=tuple(mid for mid in interceptors if not oauth or mid not in oauth_factories)
    if interceptors:
        if oauth and oauth_factories:
            raise AnalysisBoundary('Feign mixed source/OAuth2 interceptor ordering is not modeled: '+reason,category='unsupported_semantics')
        from .feign_interceptors import apply as apply_interceptors
        headers=apply_interceptors(engine,unit,owner,interceptors,headers,reason)
    from .spring_client_config import local_targets
    targets=local_targets(engine,verb,address)
    if targets is None:targets=p.ix.handlers_for(verb,address['segments'],address['hostname'])
    targets=sorted(mid for mid in targets if p.enabled_type(p.methods[mid]['owner']))
    if len(targets)!=1:raise AnalysisBoundary('Feign target handler is absent or ambiguous: '+reason,category='unknown_target')
    target=targets[0];request=Request.http(p.ix.unit_of(target),verb,url,headers,body,session=session,
        provenance={'source_callsite':reason,'client_method':method,'wire_contract':wire_provenance,
                    'oauth_boundary':'supplied verified context' if session is not U else 'unknown'})
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
        from .feign_errors import default_error
        default_error(engine,method,target,response,status,request_index,reason)
    if p.methods[method].get('return_raw')=='void':return True,None
    from .feign_decoder import decode,transport_payload
    payload=transport_payload(engine,response,target,status,request_index,reason)
    value=decode(engine,payload,p.methods[method].get('return_raw',''),method,status,reason)
    return True,value
