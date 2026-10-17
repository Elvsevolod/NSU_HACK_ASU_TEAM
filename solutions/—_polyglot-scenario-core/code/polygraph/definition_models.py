"""Allowlisted declaration-time library factories, without app initialization."""

def source_defined(project,name):
    while name:
        if name in project.methods or name in project.types or name in project.globals:return True
        name=name.rpartition('.')[0]
    return False


def qualified(project,expr):
    if len(expr.bindings)==1 and not expr.bindings[0].startswith('local:'):
        return expr.bindings[0]
    receiver,_,_=expr.args
    if receiver is None:
        return project.resolve_import(expr.value,expr.span.file) or expr.value
    if receiver.op=='var':
        return (project.resolve_import(receiver.value,expr.span.file) or receiver.value)+'.'+expr.value
    return ''


def supported(engine,expr,seen=frozenset()):
    from .security_models import PURE_FACTORIES
    if expr.op in {'const','type'}:return True
    if expr.op=='var':
        imported=engine.p.resolve_import(expr.value,expr.span.file)
        key=imported or engine.p.lexical_modules.get(expr.span.file,'')+'.'+expr.value
        if key in engine.context.get('globals',{}):return True
        if key in PURE_FACTORIES and not source_defined(engine.p,key):return True
        return key not in seen and key in engine.p.globals and supported(engine,engine.p.globals[key],seen|{key})
    if expr.op=='call':
        key=qualified(engine.p,expr)
        if key not in PURE_FACTORIES or source_defined(engine.p,key):return False
        _,args,named=expr.args
        return all(supported(engine,value,seen) for value in args) and all(key is not None and supported(engine,value,seen) for key,value in named)
    if expr.op=='field':return supported(engine,expr.args[0],seen)
    if expr.op in {'bin','unary','format','list','dict'}:
        def safe(value):
            return supported(engine,value,seen) if hasattr(value,'op') else all(safe(v) for v in value) if isinstance(value,(tuple,list)) else True
        return safe(expr.args)
    return False
