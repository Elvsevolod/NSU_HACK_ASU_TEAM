"""Default Spring MVC outcomes with no selected source handler."""
import re

from .values import Object,Raised,Response,Unknown,unknown,wire

PARENTS={'IllegalArgumentException':'RuntimeException','NumberFormatException':'IllegalArgumentException',
         'ArithmeticException':'RuntimeException','NullPointerException':'RuntimeException','IllegalStateException':'RuntimeException',
         'IndexOutOfBoundsException':'RuntimeException','RuntimeException':'Exception','ServletException':'Exception',
         'HttpRequestMethodNotSupportedException':'ServletException','MethodArgumentNotValidException':'Exception',
         'Exception':'Throwable','Error':'Throwable'}
NATIVE={name:'java.lang.'+name for name in set(PARENTS)|{'Throwable'} if name not in {'ServletException','HttpRequestMethodNotSupportedException','MethodArgumentNotValidException'}}
NATIVE.update({'HttpRequestMethodNotSupportedException':'org.springframework.web.HttpRequestMethodNotSupportedException',
               'MethodArgumentNotValidException':'org.springframework.web.bind.MethodArgumentNotValidException',
               'ServletException':'javax.servlet.ServletException'})


def response_status(annotations):
    from .models import STATUSES
    if 'ResponseStatus' not in annotations:return 200
    raw=annotations['ResponseStatus'];found=re.search(r'\bHttpStatus\.([A-Z_]+)',raw)
    if found:return STATUSES.get(found[1],Unknown('Unsupported Spring HTTP status'))
    return 500 if not raw.strip('() ') else Unknown('Unresolved Spring response status')


def canonical(project,name,method=None,actual=False):
    if name in project.types:return name
    if actual and '.' not in name:return NATIVE.get(name,name)
    if method:
        imported=project.resolve_import(name,method.span.file)
        if imported:return project.resolve_type(imported,method.module,method.span.file) or imported
        owner=project.types.get(getattr(method,'owner',method.key))
        if owner:
            package=owner.key.split(':',1)[-1].rpartition('.')[0]
            local=method.module+':'+package+'.'+name if package else method.module+':'+name
            if local in project.types:return local
    return NATIVE.get(name,name)


def distance(project,actual,expected,method):
    target=canonical(project,expected,method);queue=[(canonical(project,actual,actual=True),0)];seen=set()
    while queue:
        current,depth=queue.pop(0)
        if current in seen:continue
        seen.add(current)
        if current==target:return depth
        if current in project.types:
            info=project.types[current]
            queue.extend((canonical(project,parent,info),depth+1) for parent in info.parents)
        else:
            parent=PARENTS.get(current.split('.')[-1]) if current in NATIVE.values() else None
            if parent:queue.append((canonical(project,parent,actual=True),depth+1))
    return None


def exception_handler(engine,exception,module,controller=None):
    choices=[]
    if exception.typ=='UnknownException' and any(m.module==module and 'ExceptionHandler' in m.annotations for m in engine.p.methods.values()):
        engine.unsupported('Unknown exception type may select source Spring advice',controller.span if controller else engine.p.methods[next(k for k,m in engine.p.methods.items() if m.module==module and 'ExceptionHandler' in m.annotations)].span)
    for info in engine.p.types.values():
        if info.module!=module or info.language!='java':continue
        local=controller is not None and controller.owner==info.key
        advice=set(info.annotations)&{'ControllerAdvice','RestControllerAdvice'}
        if not local and not advice:continue
        for key in info.methods:
            method=engine.p.methods[key]
            if 'ExceptionHandler' not in method.annotations:continue
            catches=re.findall(r'([\w.]+)\.class',method.annotations['ExceptionHandler']) or [p.typ for p in method.params]
            depths=[value for name in catches if (value:=distance(engine.p,exception.typ,name,method)) is not None]
            if not depths:continue
            enabled=engine.p.enabled(info)
            if enabled is False:continue
            if enabled is None or any(info.annotations[name].strip('() ') for name in advice):
                engine.unsupported('Conditional/scoped Spring exception advice',method.span)
            raw=info.annotations.get('Order','');found=re.fullmatch(r'\(?\s*([+-]?\d+)\s*\)?',raw)
            if raw and not found:engine.unsupported('Unresolved Spring advice ordering',method.span)
            choices.append(((0 if local else 1,int(found[1]) if found else 2147483647,min(depths)),method,info))
    if not choices:return None
    best=min(choice[0] for choice in choices);selected=[choice for choice in choices if choice[0]==best]
    if len(selected)!=1:engine.unsupported('Ambiguous Spring exception handler ordering',selected[0][1].span)
    return selected[0][1:]


def handle_exception(engine,exception,module,controller=None):
    selected=exception_handler(engine,exception,module,controller)
    if selected is None:return None
    method,info=selected
    outer=engine.frames;engine.frames=[]
    try:
        receiver=engine.create(info.key,span=info.span,bean=True)
        value=exception.value if isinstance(exception.value,Object) else engine.state.new(exception.typ,{'message':exception.value})
        if len(method.params)>1:engine.unsupported('Additional Spring exception-handler parameters',method.span)
        result=engine.execute_method(method.key,(value,) if method.params else (),receiver=receiver,span=method.span)
        if isinstance(result,Response):return result
        status=response_status({**info.annotations,**method.annotations})
        if unknown(status):engine.unsupported('Unresolved Spring exception-handler status',method.span)
        rest=set(info.annotations)&{'RestControllerAdvice','RestController','ResponseBody'} or 'ResponseBody' in method.annotations
        if result is not None and not rest:engine.unsupported('View-based Spring exception-handler result',method.span)
        return Response(wire(result),status)
    finally:engine.frames=outer


def no_handler(engine,module,path,verb,span):
    from .protocol import route_match
    endpoints=[e for e in engine.p.endpoints if e.module==module and e.framework=='spring']
    if not module or not endpoints or any(e.module==module and e.framework!='spring' for e in engine.p.endpoints):return None
    prefix=engine.p.configuration.context_path(module)
    status,headers=None,{}
    if not unknown(prefix) and prefix and path!=prefix and not path.startswith(prefix+'/'):
        status=404
    elif verb.upper() not in {'HEAD','OPTIONS'}:
        paths=[e for e in endpoints if route_match(path,e.path) is not None]
        if not paths or any(e.conditions.get('profile_unknown') or e.conditions.get('context_path_unknown') for e in paths):return None
        risks=[risk for risk in engine.p.framework_risks if risk['module']==module]
        if risks and not engine.context.get('assumptions',{}).get('framework_entry'):return None
        selected=exception_handler(engine,Raised('HttpRequestMethodNotSupportedException'),module)
        if selected is not None:return handle_exception(engine,Raised('HttpRequestMethodNotSupportedException'),module)
        custom=any(info.module==module and any(re.search(r'(?:HandlerExceptionResolver|ErrorController)\b',parent) for parent in info.parents) for info in engine.p.types.values())
        if custom:return None
        allowed={e.verb for e in paths if e.verb!='*'}
        if allowed and not any(e.verb=='*' for e in paths):status,headers=405,{'Allow':', '.join(sorted(allowed))}
    if status is None:return None
    engine.note('framework-error-body','Default routing status is known; the framework error payload is not reconstructed',span,status=status)
    engine.events.append({'kind':'framework-http-response','module':module,'path':path,'method':verb,'status':status,'reason':'servlet context boundary' if status==404 else 'source mapping HTTP method mismatch'})
    return Response(Unknown('framework error response body'),status,headers)
