"""Bounded source Feign callbacks; bootstrap facts are separate from execution."""
from copy import deepcopy
from itertools import permutations
import json
import re

from .bean_properties import annotations,declaration
from .java_collections import JavaObject
from .native_arrays import JavaArray
from .project import text,keywords
from .generic_types import type_parts
from .request import normalized_headers
from .state import U
from .java_exceptions import JavaThrow
from .spring_client_config import field_declaration,direct_new


def boundary(message,reason):
    from .engine import AnalysisBoundary
    raise AnalysisBoundary('Feign source interceptor '+message+': '+reason,category='unsupported_semantics')


class JavaFeignTemplate(JavaObject):
    """Framework-owned mutable reference; application dictionaries cannot forge it."""
    def __init__(self,headers):
        super().__init__('feign.RequestTemplate',{'__headers__':normalized_headers(deepcopy(headers))},wire_fields=())


def template_operation(engine,obj,node,args,reason):
    if not isinstance(obj,JavaFeignTemplate):return False,U
    name=text(node.child_by_field_name('name'));values=obj.get('__headers__',U)
    if not isinstance(values,dict):boundary('template state was widened',reason)
    if name not in ('header','removeHeader') or not args:boundary('RequestTemplate operation is outside the header contract: '+name,reason)
    key=args[0]
    if key is None or key=='':raise JavaThrow({'__type__':'IllegalArgumentException'})
    if not isinstance(key,str) or not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+",key):boundary('header name is unresolved or outside the literal token contract',reason)
    key=key.lower();before=deepcopy(values.get(key,[]))
    if name=='removeHeader':
        if len(args)!=1:boundary('removeHeader overload is unresolved',reason)
        values.pop(key,None)
    else:
        incoming=list(args[1:])
        if incoming==[None]:
            arguments=[n for n in node.child_by_field_name('arguments').named_children if n.type not in ('line_comment','block_comment')]
            written=engine.source_type(arguments[1]);base,_=type_parts(written)
            if base.endswith('[]') and engine.standard_type(base[:-2],'java.lang.String'):
                raise JavaThrow({'__type__':'NullPointerException'})
            if any(engine.standard_type(base,fqn) for fqn in ('java.lang.Iterable','java.util.Collection','java.util.List','java.util.Set')):incoming=[]
            elif not engine.standard_type(base,'java.lang.String'):boundary('null header overload is unresolved',reason)
        if len(incoming)==1 and isinstance(incoming[0],(list,JavaArray)):
            collection=incoming[0]
            if getattr(collection,'opaque',False) or not getattr(collection,'order_known',True):boundary('header collection contents/order are unresolved',reason)
            incoming=list(collection)
        if any(value is not None and not isinstance(value,str) or isinstance(value,str) and any(c in value for c in '{}\r\n') for value in incoming):
            boundary('header values require finite literal strings',reason)
        if not incoming:values.pop(key,None)
        else:
            if before is U:boundary('existing header values are unresolved',reason)
            after=list(before)
            for value in incoming:
                if value is not None and value.strip() and value not in after:after.append(value)
            values[key]=after
    engine.effect_events.append({'model_version':'feign-request-template/1','operation':name,'method':engine.method,
        'callsite':reason,'header':key,'before':before,'after':deepcopy(values.get(key,[])),
        'resource_writes':[],'completions':['normal']})
    return True,obj


def native_annotation(engine,meta,fqn):
    return next((a for a in meta.get('annotations',[]) if engine.standard_type(a['name'],fqn,meta)),None)


def check_policy(engine,meta,reason):
    unsupported=('org.springframework.context.annotation.Scope','org.springframework.context.annotation.Lazy',
        'org.springframework.scheduling.annotation.Async','org.springframework.security.access.prepost.PreAuthorize',
        'org.springframework.security.access.prepost.PostAuthorize','org.springframework.cache.annotation.Cacheable')
    if any(native_annotation(engine,meta,fqn) for fqn in unsupported):boundary('bean scope/interception policy is not modeled',reason)
    for note in meta.get('annotations',[]):
        leaf=note['name'].rsplit('.',1)[-1]
        if leaf.startswith('Conditional') and any(engine.standard_type(note['name'],prefix+leaf,meta) for prefix in (
            'org.springframework.context.annotation.','org.springframework.boot.autoconfigure.condition.')):
            boundary('conditional bean registration is unresolved',reason)


def bean_name(engine,meta,reason):
    note=next((native_annotation(engine,meta,prefix+name) for prefix,name in (
        ('org.springframework.stereotype.','Component'),('org.springframework.stereotype.','Service'),
        ('org.springframework.context.annotation.','Configuration')) if native_annotation(engine,meta,prefix+name)),None)
    args=note.get('args','').strip('() ') if note else ''
    if args:
        try:value=json.loads(args.removeprefix('value=').strip())
        except ValueError:value=None
        if not isinstance(value,str):boundary('component bean name is unresolved',reason)
        if value:return value
    name=meta['fqn'].rsplit('.',1)[-1]
    return name if len(name)>1 and name[:2].isupper() else name[:1].lower()+name[1:]


def registration_plan(engine,unit,client,registrations,reason):
    p=engine.p;cache=p.__dict__.setdefault('_feign_callback_registration',{});key=unit,client,registrations
    if key in cache:return cache[key]
    types=[(owner,meta) for owner,meta in p.nodes.items() if meta['kind']=='type' and unit in p.ix.units.get(meta.get('module'),())]
    boots=[(owner,meta) for owner,meta in types if native_annotation(engine,meta,'org.springframework.boot.autoconfigure.SpringBootApplication')]
    if len(boots)!=1:boundary('registration needs one source Boot application with default scanning',reason)
    boot,app=boots[0]
    check_policy(engine,app,reason)
    if native_annotation(engine,app,'org.springframework.boot.autoconfigure.SpringBootApplication').get('args','').strip('() '):
        boundary('custom Boot scanning/bootstrap options are not modeled',reason)
    enables=[]
    for owner,meta in types:
        if native_annotation(engine,meta,'org.springframework.context.annotation.ComponentScan') or native_annotation(engine,meta,'org.springframework.context.annotation.Import'):
            boundary('custom component scanning/imports are not modeled',reason)
        enabled=native_annotation(engine,meta,'org.springframework.cloud.openfeign.EnableFeignClients')
        if enabled:enables.append(enabled)
    if len(enables)!=1 or enables[0].get('args','').strip('() '):boundary('client scan/default configuration is unresolved',reason)
    client_note=native_annotation(engine,p.nodes[client],'org.springframework.cloud.openfeign.FeignClient')
    if re.search(r'\bconfiguration\s*=',client_note.get('args','')):boundary('custom client configuration is not modeled',reason)
    if any(row['module']==app['module'] and re.match(r'(?:spring\.cloud\.openfeign|feign)\.client\.config\.',row['key']) for row in p.config):
        boundary('configured client overrides are not modeled',reason)
    package=app['fqn'].rpartition('.')[0]
    inside=lambda meta:not package or meta['fqn'].startswith(package+'.')
    if not inside(p.nodes[client]):boundary('client is outside the proven default package scan',reason)
    rows=[];names=set()
    for registration in registrations:
        factory=p.methods.get(registration);owner=factory['owner'] if factory else registration
        meta=p.nodes[owner]
        if not inside(meta):continue
        check_policy(engine,meta,reason)
        if p.profile_status(owner) is U:boundary('bean profile is unresolved',reason)
        if factory:
            check_policy(engine,factory,reason)
            if owner!=boot and not native_annotation(engine,meta,'org.springframework.context.annotation.Configuration'):
                boundary('factory configuration registration is unresolved',reason)
            note=native_annotation(engine,factory,'org.springframework.context.annotation.Bean')
            allocation=direct_new(engine,registration)
            if (note is None or note.get('args','').strip('() ') or p.parameters(registration) or allocation is None or
                    allocation.child_by_field_name('arguments').named_children):boundary('factory needs an unambiguous no-arg direct source allocation',reason)
            owner=p.resolve_type(text(allocation.child_by_field_name('type')),factory['module'],factory['file'])
            if owner is None:boundary('factory implementation source is unavailable',reason)
            meta=p.nodes[owner]
            name=factory['name']
        else:name=bean_name(engine,meta,reason)
        if name in names:boundary('duplicate bean names require an overriding/registration contract',reason)
        names.add(name);check_policy(engine,meta,reason)
        methods=[mid for mid,m in p.methods.items() if m['owner']==owner]
        callbacks=[mid for mid in methods if p.methods[mid]['name']=='apply' and len(p.parameters(mid))==1 and not p.methods[mid].get('abstract')]
        if len(callbacks)!=1 or not engine.standard_type(p.parameters(callbacks[0])[0][1],'feign.RequestTemplate',p.methods[callbacks[0]]):
            boundary('apply signature/source is unresolved',reason)
        check_policy(engine,p.methods[callbacks[0]],reason)
        rows.append({'registration':registration,'owner':owner,'callback':callbacks[0],'configuration_module':app['module']})
    cache[key]=tuple(rows)
    return cache[key]


def injected_string(engine,module,written,reason):
    try:value=json.loads(written.strip('() ').removeprefix('value=').strip())
    except ValueError:value=None
    if not isinstance(value,str) or '#{' in value:boundary('@Value expression is outside the literal placeholder contract',reason)
    for _ in range(32):
        match=re.search(r'\$\{([^{}]+)\}',value)
        if not match:
            if '${' in value:boundary('@Value placeholder is unresolved',reason)
            return value
        key,separator,default=match[1].partition(':')
        item=engine.p.configuration.value(module,key,default if separator else U)
        if item is U or isinstance(item,(dict,list)):boundary('@Value property is unresolved: '+key,reason)
        item=str(item).lower() if type(item) is bool else str(item)
        value=value[:match.start()]+item+value[match.end():]
    boundary('@Value expansion budget exceeded',reason)


def instance(engine,unit,row,reason):
    p=engine.p;owner=row['owner'];meta=p.nodes[owner];key=('feign-interceptor',unit,row['registration'])
    if key in engine.state.bean_instances:
        value=engine.state.bean_instances[key]
        if not isinstance(value,JavaObject) or value.java_type!=meta['fqn']:boundary('bean state/identity is unresolved after join',reason)
        return value
    methods=[mid for mid,m in p.methods.items() if m['owner']==owner]
    if any(p.methods[mid]['name']=='<init>' or native_annotation(engine,p.methods[mid],'javax.annotation.PostConstruct') or
           native_annotation(engine,p.methods[mid],'jakarta.annotation.PostConstruct') for mid in methods):boundary('source constructor/startup callback is not modeled',reason)
    if p.type_parents.get(owner) or any(not any(engine.standard_type(parent,fqn,meta) for fqn in
            ('feign.RequestInterceptor','java.lang.Object','java.io.Serializable')) for parent in p.framework_types.get(owner,())):
        boundary('bean inheritance/storage requires a separate startup contract',reason)
    if native_annotation(engine,meta,'org.springframework.context.annotation.Scope') or native_annotation(engine,meta,'org.springframework.context.annotation.Lazy'):
        boundary('bean scope/lazy initialization is not modeled',reason)
    if any(native_annotation(engine,meta,'lombok.'+name) for name in ('Data','Value','RequiredArgsConstructor','AllArgsConstructor','Builder')):
        boundary('generated bean constructor policy is not modeled',reason)
    node=declaration(p,owner);body=node.child_by_field_name('body') if node is not None else None
    if body is None or any(child.type=='block' for child in body.named_children):boundary('instance initializer is not modeled',reason)
    value=JavaObject(meta['fqn'],{'__type__':meta['fqn'],'__http_entity__':False},wire_fields=p.type_fields.get(owner,{}))
    value.source_owner=owner;value._native_field_kinds={}
    for name,info in p.type_fields.get(owner,{}).items():
        field=field_declaration(engine,info['declaring_type'],name)
        entries=annotations(field) if field is not None else []
        policy=[args for note,args in entries if engine.standard_type(note,'org.springframework.beans.factory.annotation.Value',meta)]
        if any(any(engine.standard_type(note,fqn,meta) for fqn in ('org.springframework.beans.factory.annotation.Autowired','javax.inject.Inject','jakarta.inject.Inject','javax.annotation.Resource','jakarta.annotation.Resource')) for note,_ in entries):
            boundary('bean dependency injection is outside the supported field contract',reason)
        if policy:
            if len(policy)!=1 or not engine.standard_type(info['type'],'java.lang.String',meta):boundary('@Value field type is not supported',reason)
            item=injected_string(engine,row['configuration_module'],policy[0],reason);kind='String'
        else:
            if info['has_initializer'] and info['default'] is U or field is not None and 'final' in keywords(field) and not info['has_initializer']:
                boundary('field initialization is unresolved: '+name,reason)
            item=deepcopy(info['default']);kind=info.get('default_kind')
            if item is U:
                typ=info['type'];item=False if typ=='boolean' else '\0' if typ=='char' else 0.0 if typ in ('float','double') else 0 if typ in ('byte','short','int','long') else None
                kind=engine.declared_kind(typ,meta)
        value[name]=item;value._native_field_kinds[name]=kind
    engine.state.bean_instances[key]=value
    engine.effect_events.append({'model_version':'source-feign-bean/1','registration':row['registration'],'owner':owner,
        'operation':'post-startup field projection','scenario_execution':False,'resource_writes':[],'scope':'default scan, implicit no-arg bean, literal/@Value fields'})
    return value


def apply(engine,unit,client,registrations,headers,reason):
    if not registrations:return headers
    rows=registration_plan(engine,unit,client,registrations,reason)
    if len(rows)>4:boundary('callback ordering exceeds the bounded permutation contract',reason)
    order=list(range(len(rows)))
    if len(order)>1:
        order=engine.choose(reason+':Feign RequestInterceptor order',list(permutations(order)))
        if order is None:boundary('callback order budget is exhausted; no arbitrary order selected',reason)
    template=JavaFeignTemplate(headers)
    for index in order:
        row=rows[index];receiver=instance(engine,unit,row,reason)
        event={'method':row['callback'],'role':'Feign RequestInterceptor','registration':row['registration'],
            'reason':reason,'outcome':'started','projection':'exported source callback'}
        engine.semantic_callbacks.append(event)
        try:
            engine.invoke(row['callback'],[template],receiver,reason='Feign source interceptor callback: '+reason)
            event['outcome']='returned'
        except JavaThrow:
            event['outcome']='threw';raise
    result=template.get('__headers__',U)
    if not isinstance(result,dict):boundary('outgoing headers are unresolved after callback',reason)
    return {key:value for key,value in result.items() if value is U or value}
