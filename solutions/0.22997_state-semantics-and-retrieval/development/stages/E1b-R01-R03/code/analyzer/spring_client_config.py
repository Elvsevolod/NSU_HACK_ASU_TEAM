"""Bounded source-only @Bean constructor/field projection and local HTTP deployment.

Only unambiguous direct factory returns and immutable constructor assignments are
accepted. Environment absence and loopback deployment are explicit input facts.
This is not a Spring container/bootstrap implementation.
"""
from pathlib import Path
import re
from .project import text,walk,declaration_matches
from .state import U
from .native_storage import JavaHttpClient


def properties(project):
    cached=project.__dict__.get('_source_http_properties')
    if cached is not None:return cached
    roots={}
    for mid,meta in project.methods.items():
        parts=Path(meta['file']).parts
        if 'src' not in parts:continue
        prefix=Path(*parts[:parts.index('src')])
        roots.setdefault(prefix,set()).add(project.ix.unit_of(mid))
    result=[]
    for prefix,units in roots.items():
        if len(units)!=1:continue
        unit=next(iter(units))
        for path in sorted((project.root/prefix).glob('src/main/resources/application*.properties')):
            for n,line in enumerate(path.read_text().splitlines(),1):
                line=line.strip()
                if not line or line.startswith(('#','!')):continue
                match=re.fullmatch(r'([\w.-]+)\s*=\s*(.*)',line)
                if match and not line.endswith('\\'):
                    result.append({'unit':unit,'key':match[1],'value':match[2],'file':path.relative_to(project.root).as_posix(),'line':n,
                                   'profile':path.stem.removeprefix('application').removeprefix('-') or 'default'})
    project._source_http_properties=result
    return result


def property_value(engine,unit,key):
    context=engine.state.context
    overrides=context.get('deployment_properties',{}).get(unit,{})
    if key in overrides:return overrides[key]
    rows=[r for r in properties(engine.p) if r['unit']==unit and r['key']==key]
    active=context.get('active_profiles',['default'])
    rows=[r for r in rows if r['profile'] in active]
    if len({r['value'] for r in rows})!=1:return U
    value=rows[0]['value']
    match=re.fullmatch(r'\$\{([^}:]+)(?::(.*))?\}',value)
    if match:
        environment=context.get('deployment_environment',{}).get(unit,context.get('environment',{}))
        if match[1] in environment:value=environment[match[1]]
        elif context.get('environment_complete') is True:value=match[2] if match[2] is not None else U
        else:return U
    if not isinstance(value,str) or '${' in value or '#{' in value:return U
    engine.assume('source configuration under declared environment/profile: '+unit+' '+key)
    return value


def bean_methods(engine,unit,wanted):
    result=[]
    for mid,meta in engine.p.methods.items():
        if engine.p.ix.unit_of(mid)!=unit or not engine.p.enabled_type(meta['owner']):continue
        annotations=meta.get('annotations',[])
        if not any(a['name'].rsplit('.',1)[-1]=='Bean' and not a.get('args','').strip('() ') for a in annotations):continue
        if not any(a['name'].rsplit('.',1)[-1]=='Configuration' for a in engine.p.nodes[meta['owner']].get('annotations',[])):continue
        written=meta.get('return_raw','')
        tid=engine.p.resolve_type(written,meta['module'],meta['file'])
        actual=engine.p.nodes[tid]['fqn'] if tid else written
        if actual==wanted or engine.standard_type(written,wanted,meta):result.append(mid)
    return result


def direct_new(engine,mid):
    node=engine.p.ast.get(mid)
    body=node.child_by_field_name('body') if node else None
    statements=[c for c in body.named_children if c.type not in ('line_comment','block_comment')] if body else []
    if len(statements)!=1 or statements[0].type!='return_statement':return None
    value=statements[0].named_children[0]
    return value if value.type=='object_creation_expression' and not any(c.type=='class_body' for c in value.named_children) else None


def client_bean(engine,unit):
    if any(node.get('kind')=='call_site' and node.get('callee') in ('setRequestFactory','setInterceptors','setMessageConverters') and
           node.get('method') in engine.p.methods and engine.p.ix.unit_of(node['method'])==unit for node in engine.p.nodes.values()):return U
    candidates=bean_methods(engine,unit,'org.springframework.web.client.RestTemplate')
    if len(candidates)!=1:return U
    mid=candidates[0];meta=engine.p.methods[mid];allocation=direct_new(engine,mid)
    if allocation is None or engine.p.parameters(mid) or not engine.standard_type(text(allocation.child_by_field_name('type')),'org.springframework.web.client.RestTemplate',meta):return U
    arguments=allocation.child_by_field_name('arguments').named_children
    if not arguments:factory='SimpleClientHttpRequestFactory'
    elif len(arguments)==1 and arguments[0].type=='object_creation_expression' and not arguments[0].child_by_field_name('arguments').named_children:
        written=text(arguments[0].child_by_field_name('type'))
        factory=next((name for name in ('HttpComponentsClientHttpRequestFactory','SimpleClientHttpRequestFactory') if engine.standard_type(written,'org.springframework.http.client.'+name,meta)),None)
        if factory is None:return U
    else:return U
    return JavaHttpClient(factory=factory,source=mid,location=meta['file']+':'+str(allocation.start_point.row+1))


def field_declaration(engine,owner,name):
    meta=engine.p.nodes[owner];tree=engine.p.trees[meta['file']]
    declaration=next((n for n in walk(tree.root_node) if n.type=='class_declaration' and declaration_matches(n,meta['fqn'])),None)
    if declaration is None:return None
    return next((field for field in declaration.child_by_field_name('body').named_children if field.type=='field_declaration' and
                 any(text(v.child_by_field_name('name'))==name for v in field.named_children if v.type=='variable_declarator')),None)


def projected_field(engine,info):
    owner=info['declaring_type'];meta=engine.p.nodes[owner];unit=engine.p.ix.unit_of(engine.method)
    name=next((n for n,item in engine.p.type_fields[owner].items() if item is info),None)
    field=field_declaration(engine,owner,name)
    if field is None or 'final' not in text(field).split():return U
    constructors=[mid for mid,m in engine.p.methods.items() if m['owner']==owner and m['name']=='<init>']
    factories=bean_methods(engine,unit,meta['fqn'])
    if len(constructors)!=1 or len(factories)!=1:return U
    ctor=constructors[0];node=engine.p.ast.get(ctor)
    statements=[c for c in node.child_by_field_name('body').named_children if c.type not in ('line_comment','block_comment')]
    if any(c.type!='expression_statement' or len(c.named_children)!=1 or c.named_children[0].type!='assignment_expression' for c in statements):return U
    assignments=[n for n in walk(node.child_by_field_name('body')) if n.type=='assignment_expression']
    matching=[a for a in assignments if text(a.child_by_field_name('left'))=='this.'+name and text(a.child_by_field_name('operator'))=='=']
    if len(matching)!=1:return U
    parameter=text(matching[0].child_by_field_name('right'));parameters=engine.p.parameters(ctor)
    positions=[i for i,(n,_) in enumerate(parameters) if n==parameter]
    if len(positions)!=1:return U
    factory=factories[0];factory_meta=engine.p.methods[factory];allocation=direct_new(engine,factory)
    if allocation is None:return U
    arguments=allocation.child_by_field_name('arguments').named_children
    if len(arguments)!=len(parameters):return U
    expression=arguments[positions[0]]
    if expression.type!='identifier':return U
    binding=text(expression)
    declared=dict(engine.p.parameters(factory)).get(binding)
    if declared and engine.standard_type(declared,'org.springframework.web.client.RestTemplate',factory_meta):
        return client_bean(engine,unit)
    config_owner=factory_meta['owner'];config_field=field_declaration(engine,config_owner,binding)
    if config_field is None:return U
    match=re.search(r'@(?:[\w.]+\.)?Value\s*\(\s*"\$\{([\w.-]+)\}"\s*\)',text(config_field))
    return property_value(engine,unit,match[1]) if match else U


def local_targets(engine,verb,address):
    if engine.state.context.get('loopback_deployment') is not True or address.get('hostname') not in ('localhost','127.0.0.1','::1') or address.get('port') is None:return None
    units=set()
    for unit in {engine.p.ix.unit_of(mid) for mid in engine.p.methods}:
        port=property_value(engine,unit,'server.port')
        if isinstance(port,str) and port.isdigit() and int(port)==address['port']:units.add(unit)
    if len(units)!=1:return []
    engine.assume('declared local deployment maps loopback port to one source application')
    return sorted(engine.p.ix.handlers_for(verb,address['segments'],next(iter(units))))
