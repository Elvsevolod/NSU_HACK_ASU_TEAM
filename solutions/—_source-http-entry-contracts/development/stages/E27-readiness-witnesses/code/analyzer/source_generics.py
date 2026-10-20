"""Source type substitution. No execution values participate in inference."""
import re
from .generic_types import type_parts,resolve,bind_parameters,inheritance_path

PRIMITIVES={'boolean','byte','short','char','int','long','float','double','void'}
BOXES={'boolean':'Boolean','byte':'Byte','short':'Short','char':'Character','int':'Integer',
       'long':'Long','float':'Float','double':'Double'}
NATIVE=('java.lang.String','java.lang.Object','java.lang.Number','java.lang.Class','java.lang.Void',
        'java.lang.Comparable','java.lang.Iterable','java.lang.Cloneable','java.io.Serializable',
        *(f'java.lang.{name}' for name in BOXES.values()),
        *(f'java.util.{name}' for name in ('List','ArrayList','LinkedList','Collection','Set','HashSet','Map','HashMap','LinkedHashMap','Iterator','Optional')),
        'java.util.Map.Entry','java.util.stream.Stream','java.util.Date','java.util.Calendar','java.util.UUID',
        'org.springframework.http.ResponseEntity','org.springframework.http.HttpEntity','org.springframework.http.HttpHeaders',
        'org.springframework.http.HttpStatus','org.springframework.http.HttpMethod',
        'javax.servlet.ServletRequest','javax.servlet.FilterChain','javax.servlet.http.HttpServletRequest','javax.servlet.http.HttpServletResponse',
        'org.springframework.security.authentication.AuthenticationManager',
        'org.springframework.security.core.Authentication','org.springframework.security.core.AuthenticationException',
        'io.jsonwebtoken.Claims','io.jsonwebtoken.JwtBuilder','io.jsonwebtoken.JwtParser','io.jsonwebtoken.Jws',
        'org.springframework.core.ParameterizedTypeReference','org.springframework.web.client.RestTemplate',
        'com.fasterxml.jackson.databind.ObjectMapper','com.fasterxml.jackson.databind.DeserializationFeature',
        'com.fasterxml.jackson.databind.JavaType','com.fasterxml.jackson.databind.type.TypeFactory',
        'com.fasterxml.jackson.core.type.TypeReference')


def environment(bindings,context):
    return {name:(written,context,{}) for name,written in bindings.items()}


def render(project,written,context,bindings,standard_type,variables=(),erase=False,active=()):
    """Materialize with declaration/use-site namespaces intact; reject captures."""
    written=re.sub(r'\s+','',written).replace('...','[]')
    key=(written,id(context),id(bindings),erase)
    if not written or key in active or len(active)>=64:return ''
    active=(*active,key)
    if written.endswith('[]'):
        component=render(project,written[:-2],context,bindings,standard_type,variables,erase,active)
        return component+'[]' if component else ''
    previous=(written,id(context),id(bindings))
    written,context,bindings=resolve(written,context,bindings)
    if (written,id(context),id(bindings))!=previous:
        # Bound arguments belong to their own source namespace, not to the
        # binder whose spelling they happened to replace.
        return render(project,written,context,bindings,standard_type,(),erase,active)
    base,arguments=type_parts(written)
    if not base or arguments is None or base in variables or '?' in written or '&' in written:return ''
    if base in PRIMITIVES:qualified=base
    else:
        owner=project.resolve_type(base,context['module'],context['file'])
        qualified=project.nodes[owner]['fqn'] if owner else ''
        if not qualified:
            qualified=next((name for name in NATIVE if standard_type(base,name,context)), '')
        if not qualified:
            if '.' in base:qualified=base
            else:
                cache=project.__dict__.setdefault('_source_generic_imports',{})
                file=context['file']
                if file not in cache:
                    cache[file]=[match[1] for node in project.trees[file].root_node.named_children if node.type=='import_declaration'
                        for match in [re.fullmatch(r'import\s+([\w.]+)\s*;',node.text.decode('utf-8'))] if match]
                imported=[name for name in cache[file] if name.rsplit('.',1)[-1]==base]
                if len(imported)==1:qualified=imported[0]
        if not qualified:return ''
    if not arguments or erase:return qualified
    parts=[render(project,arg,context,bindings,standard_type,variables,False,active) for arg in arguments]
    return qualified+'<'+','.join(parts)+'>' if all(parts) else ''


def member_scope(project,receiver,declared,context):
    base,arguments=type_parts(receiver)
    owner=project.resolve_type(base,context['module'],context['file'])
    if owner is None:return None
    path=inheritance_path(project,owner,declared)
    if path is None:return None
    bindings=bind_parameters(project,owner,arguments,context,{})
    if bindings is None:return None
    raw=bool(project.type_variables.get(owner) and not arguments)
    current=owner
    for parent,written in path:
        _,args=type_parts(written)
        raw=bool(project.type_variables.get(parent) and (raw or not args))
        bindings=bind_parameters(project,parent,[] if raw else args,project.nodes[current],bindings)
        if bindings is None:return None
        current=parent
    return bindings,raw


def member_type(project,receiver,declared,written,context,standard_type):
    scope=member_scope(project,receiver,declared,context)
    if scope is None:return ''
    bindings,raw=scope
    return render(project,written,project.nodes[declared],bindings,standard_type,erase=raw)


def method_variables(project,target):
    cache=project.__dict__.setdefault('_source_method_variables',{})
    if target not in cache:
        source=project.ast.get(target)
        params=source.child_by_field_name('type_parameters') if source is not None else None
        found={}
        for parameter in params.named_children if params else []:
            name=next((c for c in parameter.named_children if c.type=='type_identifier'),None)
            bound=next((c for c in parameter.named_children if c.type=='type_bound'),None)
            if name is not None:found[name.text.decode('utf-8')]=bound.named_children[0].text.decode('utf-8') if bound is not None and bound.named_children else 'java.lang.Object'
        cache[target]=found
    return cache[target]


def call_context(project,target,receiver,context,argument_types,explicit,standard_type,static=False):
    meta=project.methods[target];owner=meta['owner'];variables=method_variables(project,target)
    scope=member_scope(project,receiver,owner,context) if not static else None
    bindings,raw=scope if scope is not None else ({},False)
    if scope is None and not static:
        bindings={name:('',meta,{}) for name in project.type_variables.get(owner,{})}
    class_bindings=dict(bindings)
    # A method binder is distinct from an identically spelled class binder.
    bindings={name:value for name,value in bindings.items() if name not in variables}
    inferred={};conflicts=set()
    def infer(formal,actual):
        formal=re.sub(r'\s+','',formal)
        if not actual:return
        if formal in variables:
            actual='java.lang.'+BOXES[actual] if actual in BOXES else actual
            if formal in inferred and inferred[formal]!=actual:conflicts.add(formal)
            else:inferred[formal]=actual
            return
        if formal.endswith('[]'):
            if actual.endswith('[]') and actual[:-2] not in PRIMITIVES:infer(formal[:-2],actual[:-2])
            return
        fbase,fargs=type_parts(formal);abase,aargs=type_parts(actual)
        if not fargs or aargs is None:return
        qualified=render(project,fbase,meta,bindings,standard_type,variables)
        if qualified!=abase:
            declared=project.resolve_type(qualified,meta['module'],meta['file'])
            projected=member_scope(project,actual,declared,context) if declared else None
            if projected is None or projected[1]:return
            mapped,_=projected
            aargs=[render(project,name,project.nodes[declared],mapped,standard_type) for name in project.type_variables.get(declared,{})]
        if len(fargs)==len(aargs):
            for left,right in zip(fargs,aargs):infer(left,right)
    if explicit is not None:
        if len(explicit)==len(variables):inferred.update(zip(variables,explicit))
        else:conflicts.update(variables)
    else:
        for (_,formal),actual in zip(project.parameters(target),argument_types):infer(formal,actual)
    for name,bound in variables.items():
        if name in inferred and name not in conflicts:bindings[name]=(inferred[name],context,{})
        elif explicit is None:bindings[name]=(bound,meta,bindings)
        else:bindings[name]=('',context,{})
    flat={name:render(project,name,meta,bindings,standard_type) for name in bindings}
    if scope is None and not static:
        # Missing receiver parameterization cannot capture a class variable
        # from an unrelated target or from the shape of a runtime record.
        for name in project.type_variables.get(owner,{}):
            if name not in variables:flat[name]=''
    class_names=list(project.type_variables.get(owner,{}))
    args=[render(project,name,project.nodes[owner],class_bindings,standard_type) for name in class_names]
    self_type=project.nodes[owner]['fqn']
    # The body is compiled in the generic declaration, even when the caller
    # sees an erased raw member. Preserve declaration bounds inside that body.
    if scope is not None and class_names and all(args):self_type+='<'+','.join(args)+'>'
    result=render(project,meta.get('return_raw',''),meta,bindings,standard_type,erase=raw and not static)
    return flat,self_type,result
