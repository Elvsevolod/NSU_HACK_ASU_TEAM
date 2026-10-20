"""Source Feign target and default EXPLODED named-parameter wire construction.

The template rules are checked against Feign 10.10.1 and 13.5. This does not
implement custom expanders, QueryMap, nondefault CollectionFormat or refresh.
The result still goes through ordinary URI lookup and server HTTP binding.
"""
import json
import re
from urllib.parse import quote,urlsplit
from baseline_closure import _split_args
from .project import text
from .state import U
from .request import MISSING,wire_text
from .symbolic_text import concat_text,_uuid_text
from .http_integral_text import integral_origin


def stop(message,reason,category='unsupported_semantics'):
    from .engine import AnalysisBoundary
    raise AnalysisBoundary('Feign '+message+': '+reason,category=category)


def resolved(engine,value,reason):
    """Resolve only the supplied environment of the calling deployment."""
    module=engine.p.methods[engine.method]['module']
    for _ in range(32):
        if '#{' in value:stop('destination expression is not modeled',reason)
        found=re.search(r'\$\{([^{}]+)\}',value)
        if not found:
            if '${' in value:stop('destination placeholder is malformed',reason)
            return value
        key,separator,default=found[1].partition(':')
        item=engine.p.configuration.value(module,key,default if separator else U)
        if item is U or isinstance(item,(dict,list)):stop('destination property is unresolved',reason)
        item=str(item).lower() if type(item) is bool else str(item)
        value=value[:found.start()]+item+value[found.end():]
    stop('destination placeholder expansion exceeds the supported bound',reason)


def destination(engine,annotation,reason):
    fields={}
    for part in _split_args(annotation.get('args','')):
        pair=re.fullmatch(r'([\w]+)\s*=\s*(.*)',part,re.S)
        key,value=(pair[1],pair[2]) if pair else ('value',part)
        if key not in ('name','value','path','url','contextId'):continue
        try:literal=json.loads(value)
        except ValueError:literal=None
        if key in fields or not isinstance(literal,str):stop('destination needs unique literal attributes',reason)
        fields[key]=resolved(engine,literal,reason)
    names={fields[key] for key in ('name','value') if fields.get(key)}
    if len(names)!=1:stop('destination aliases are absent or conflicting',reason)
    name=next(iter(names))
    if not re.fullmatch(r'[\w.-]+',name,re.ASCII):stop('client name is outside the supported syntax',reason)
    path=fields.get('path','').strip()
    if any(c in path for c in '?#{}%\\') or any(c.isspace() for c in path) or '//' in path:stop('destination path syntax is not modeled',reason)
    path=path.strip('/')
    url=fields.get('url','')
    if not url.strip():
        # Property-defined targets and their version/refresh policy are a
        # separate contract. A known override must never fall back to name.
        module=engine.p.methods[engine.method]['module'];context_id=fields.get('contextId') or name
        for prefix in ('spring.cloud.openfeign.client.config.','feign.client.config.'):
            for key in (context_id,'default'):
                configured=engine.p.configuration.raw(module,prefix+key+'.url',U)
                if configured is not U and configured is not None and str(configured).strip():
                    stop('property-defined target URL policy is not modeled',reason)
        url='http://'+name
    elif url!=url.strip():stop('destination URL whitespace is not modeled',reason)
    elif '://' not in url:url='http://'+url
    try:
        parsed=urlsplit(url);parsed.port  # Validate a literal port without dropping it.
    except ValueError:stop('destination URL is invalid',reason)
    if (parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username is not None or parsed.password is not None
            or any(c in url for c in '?#{}\\') or any(c.isspace() for c in url) or not url.isascii()
            or '//' in parsed.path):stop('destination URL policy is outside the supported scope',reason)
    if re.search(r'%(?![0-9A-Fa-f]{2})|%2f|%5c|%3b',parsed.path,re.I):stop('destination escaped path policy is not modeled',reason)
    # Target URL and FeignClient.path precede the method URI. Keep the scheme,
    # authority and port exactly; lookup uses the decoded resulting address.
    base=parsed.scheme+'://'+parsed.netloc+parsed.path.rstrip('/')
    if path:base+='/'+path
    return base,name


def encode(value):
    # UriUtils.encode(value, UTF_8) skips a string only when every byte is
    # unreserved or '%' and at least one complete pct-escape occurs. Otherwise
    # the entire value is encoded, including previous percent signs.
    if re.fullmatch(r'[A-Za-z0-9._~%\-]*',value) and re.search(r'%[0-9A-Fa-f]{2}',value):return value
    return quote(value,safe='-._~')


def encode_literal(value):
    # Template literals preserve reserved characters and existing pct escapes.
    reserved=":/?#[]@!$&'()*+,;="
    result=[];offset=0
    for found in re.finditer(r'%[0-9A-Fa-f]{2}',value):
        result.extend((quote(value[offset:found.start()],safe=reserved),found[0]));offset=found.end()
    result.append(quote(value[offset:],safe=reserved))
    return ''.join(result)


def component(value,reason):
    if type(value) in (str,int,bool):return encode(wire_text(value)).replace('%2F','/')
    value=wire_text(value)
    if integral_origin(value) is not None or _uuid_text(value):return value
    stop('named value has no supported exact text expansion',reason,'unknown_value')


def annotations(node):
    mods=next((n for n in node.named_children if n.type=='modifiers'),None)
    return [n for n in mods.named_children if n.type in ('annotation','marker_annotation')] if mods else []


def parameter_name(engine,par,info,meta,reason):
    kind=info['kind']
    for node in annotations(par):
        written=text(node.child_by_field_name('name'))
        if any(engine.standard_type(written,fqn,meta) for fqn in (
                'org.springframework.cloud.openfeign.SpringQueryMap','org.springframework.web.bind.annotation.RequestPart',
                'org.springframework.web.bind.annotation.MatrixVariable','org.springframework.format.annotation.DateTimeFormat',
                'org.springframework.format.annotation.NumberFormat')):stop('parameter customization is not modeled',reason)
    if not kind:return info['wire_name']
    native=[node for node in annotations(par) if engine.standard_type(text(node.child_by_field_name('name')),
            'org.springframework.web.bind.annotation.'+kind,meta)]
    if len(native)!=1:stop('named parameter annotation identity is not proven',reason)
    aliases=[]
    for part in _split_args(text(native[0].child_by_field_name('arguments'))):
        pair=re.fullmatch(r'(\w+)\s*=\s*(.*)',part,re.S)
        key,raw=(pair[1],pair[2]) if pair else ('value',part)
        if key not in ('name','value'):continue
        try:alias=json.loads(raw)
        except ValueError:alias=None
        if not isinstance(alias,str):stop('parameter name is not a literal',reason)
        if alias:aliases.append(alias)
    if len(set(aliases))>1:stop('parameter name aliases conflict',reason)
    return aliases[0] if aliases else info['name']


def query_values(value,reason):
    if value is None:return []
    from .native_arrays import JavaArray
    if isinstance(value,JavaArray):stop('array query expansion is not modeled',reason)
    if isinstance(value,list):
        if getattr(value,'opaque',False) or not getattr(value,'order_known',True):stop('query collection membership/order is unresolved',reason)
        result=''
        for child in value:
            if child is None:continue
            child=component(child,reason)
            if not isinstance(child,str):
                # Preserve symbolic atoms without claiming the size/sign of a
                # generated number. Empty string atoms need the exact Feign
                # iterable expansion below and are handled as literal text.
                if result and result!=',':result=concat_text(result,',')
                result=concat_text(result,child)
            elif child=='':result=concat_text(result,',')
            else:
                if result and result!=',':result=concat_text(result,',')
                result=concat_text(result,child)
        if isinstance(result,str) and ',' in result:
            values=result.split(',')
            while values and values[-1]=='':values.pop()
            return values
        if not isinstance(result,str):
            # Each proven nonempty numeric/UUID atom has no commas. Split
            # only the literal separators, keeping the atoms and their order.
            chunks=result.get('__text_parts__',[result]);values=[];current=''
            for chunk in chunks:
                if isinstance(chunk,str):
                    for i,part in enumerate(chunk.split(',')):
                        if i:values.append(current);current=''
                        current=concat_text(current,part)
                else:current=concat_text(current,chunk)
            values.append(current)
            while values and values[-1]=='':values.pop()
            return values
        return [result]
    return [component(value,reason)]


def request_parts(engine,owner,method,args,annotation,reason):
    p=engine.p;meta=p.methods[method]
    mappings=('RequestMapping','GetMapping','PostMapping','PutMapping','DeleteMapping','PatchMapping')
    def native_mapping(a,item):
        return any(engine.standard_type(a['name'],'org.springframework.web.bind.annotation.'+kind,item) for kind in mappings)
    if not any(native_mapping(a,meta) for a in meta.get('annotations',[])):
        stop('method HTTP annotation identity is not proven',reason)
    for item in [p.nodes[owner],meta]:
        for a in item.get('annotations',[]):
            if native_mapping(a,item) and re.search(r'\b(?:headers|params)\s*=',a.get('args','')):
                stop('mapping header/query conditions are not modeled',reason)
            if engine.standard_type(a['name'],'org.springframework.cloud.openfeign.CollectionFormat',item):
                values=_split_args(a.get('args',''));raw=re.sub(r'^\s*value\s*=\s*','',values[0]) if len(values)==1 else ''
                match=re.fullmatch(r'([\w.]+)\.EXPLODED',raw)
                if match is None or not engine.standard_type(match[1],'feign.CollectionFormat',item):
                    stop('nondefault collection format is not modeled',reason)
    base,name=destination(engine,annotation,reason)
    routes=[(verb,route) for mid,verb,route in p.client_routes if mid==method]
    if len(routes)!=1:stop('HTTP mapping is ambiguous',reason,'unknown_target')
    verb,route=routes[0];path={};headers={};body=MISSING;query=[];seen=set()
    node=p.ast.get(method)
    if node is None:stop('parameter source is absent',reason,'unknown_target')
    nodes=[n for n in node.child_by_field_name('parameters').named_children if n.type=='formal_parameter']
    infos=p.http_parameters(method)
    if len(nodes)!=len(args) or len(infos)!=len(args):stop('parameter source signature is incomplete',reason,'unknown_target')
    for info,par,value in zip(infos,nodes,args):
        key=parameter_name(engine,par,info,meta,reason);kind=info['kind']
        if kind in ('PathVariable','RequestHeader','RequestParam'):
            if key in seen:stop('shared named template variable is not modeled',reason)
            seen.add(key)
        if kind=='PathVariable':path[key]=value
        elif kind=='RequestHeader':
            if value is not None:headers[key]=value
        elif kind=='RequestParam':
            if any(c in key for c in '{}'):stop('query name templates are not modeled',reason)
            for expanded in query_values(value,reason):query.append((encode(encode_literal(key)),expanded))
        elif body is MISSING:body=value
        else:stop('multiple unannotated request bodies are not modeled',reason)
    url=base
    for segment in route:
        if segment.startswith('{') and segment.endswith('}'):
            if ':' in segment:stop('path expression patterns are not modeled',reason)
            value=path.get(segment[1:-1].split(':',1)[0],U)
            part=component(value,reason)
        else:
            if any(c in segment for c in '?#{}\\'):stop('method URI template syntax is not modeled',reason)
            part=encode_literal(segment)
        url=concat_text(concat_text(url,'/'),part)
    for i,(key,value) in enumerate(query):
        url=concat_text(concat_text(url,('?' if i==0 else '&')+key+'='),value)
    address=engine.request_address(url)
    if not address or address['segments'] is None or not address['query_complete'] or any(v is U for values in address['query'].values() for v in values):
        stop('resolved URI layout or escaping is not modeled',reason)
    return verb,url,address,headers,body,{'client_name':name,'target_policy':'source annotation/name and supplied caller configuration',
                                      'query_format':'EXPLODED','uri_encoding':'Feign UriUtils finite values'}
