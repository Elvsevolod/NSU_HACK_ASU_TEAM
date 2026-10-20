"""Versioned conservative effects for calls without an executable source model."""
from dataclasses import dataclass
import re

from .state import U
from .java_collections import JavaMap, JavaJsonMapper, JavaRecord, is_symbolic
from .java_exceptions import JavaThrow, ExceptionBound
from .native_storage import JavaList


@dataclass(frozen=True)
class CallEffects:
    model_version: str
    value: object
    heap_writes: tuple
    resources: tuple | None
    callbacks: tuple
    completions: tuple = ('normal', 'throw')


def source_resources(project, owner):
    if owner is None:
        return None
    pending, seen, resources = [owner], set(), set()
    while pending:
        current = pending.pop()
        if current in seen:continue
        seen.add(current)
        methods = [mid for mid, meta in project.methods.items() if meta['owner'] == current and not meta.get('analysis_context')]
        if methods:
            from .resource_effects import possible_writes
            closure=project.ix.closure(set(methods))
            resources.update(possible_writes(project,closure[0],closure[3]))
        meta = project.nodes[current]
        for field in project.type_fields.get(current, {}).values():
            target = project.resolve_type(field['type'], meta.get('module'), field.get('file'))
            if target:pending.append(target)
        for parent in project.generic_parents.get(current, ()):
            match = re.search(r'(?:JpaRepository|CrudRepository|MongoRepository)\s*<\s*([\w.]+)', parent)
            if match:
                entity = project.resolve_type(match[1], meta.get('module'), meta.get('file'))
                resources.update(rid for rid, tid in project.entities.items() if tid == entity)
    return tuple(sorted(resources))


def invalidate(value, opaque, seen=None):
    seen = set() if seen is None else seen
    if not isinstance(value, (dict, list, tuple)) or id(value) in seen or is_symbolic(value):
        return
    seen.add(id(value))
    if getattr(value,'unmodifiable',False):
        invalidate(value.backing,opaque,seen)
        return
    if isinstance(value, tuple):
        # Callback closures are reachable mutable memory even before dispatch.
        for child in value:invalidate(child, opaque, seen)
        return
    children = list(value.values()) if isinstance(value, dict) else list(value)
    for child in children:invalidate(child, opaque, seen)
    if isinstance(value, (JavaMap, JavaJsonMapper)):
        value.invalidate()
    elif isinstance(value, list):
        opaque.append(value)
        value[:] = [U] * len(value)
        if isinstance(value,JavaList):value.opaque=True
    else:
        for key in value:
            if not str(key).startswith('__'):value[key] = U


def apply_unknown(engine, name, receiver, args, env, declared, reason):
    meta = engine.p.methods[engine.method]
    owner = engine.p.resolve_type(declared, meta['module'], meta['file']) if declared else None
    resources = source_resources(engine.p, owner)
    engine.loss('unsupported','opaque call may change reachable heap/global state: '+name,
        before={'receiver_type':declared},possible_writes=resources or (),completion='normal_or_throw')
    roots = [receiver, *args, env.get('this', U)]
    for value in roots:invalidate(value, engine.opaque_heap)
    callbacks = tuple(index for index, value in enumerate(args)
                      if isinstance(value, tuple) and value and value[0] == 'lambda')
    effect = CallEffects('opaque-java-call/1', U, tuple(range(len(roots))), resources, callbacks)
    for rid in resources or ():
        rows = engine.state.database.rows(engine.p.nodes[rid])
        if rows is not None:engine.state.database.invalidate(rows)
    assumption = 'opaque call effects: ' + reason
    if resources is None:
        message='unresolved external resource/global footprint: '+reason
        if message not in engine.state.unscoped_state_assumptions:engine.state.unscoped_state_assumptions.append(message)
    elif resources:
        for rid in resources:
            existing=engine.state.resource_assumptions.setdefault(rid, [])
            if assumption not in existing:existing.append(assumption)
    engine.assume(assumption)
    candidates=[mid for mid in engine.p.by_name.get(name,[]) if owner and engine.p.methods[mid]['owner']==owner]
    category='unknown_target' if len(candidates)>1 else 'unknown_receiver' if receiver is U and not declared else 'unsupported_semantics'
    engine.operation_issues[(category,name)]+=1
    engine.effect_events.append({'callsite': reason, 'operation': name, 'declared_receiver': declared,
        'uncertainty_class':category,
        'model_version': effect.model_version, 'heap_roots': list(effect.heap_writes),
        'resource_writes': resources, 'global_footprint': 'unresolved' if resources is None else 'source_dependencies',
        'callbacks': callbacks, 'completions': effect.completions})
    for index in callbacks:
        callback=args[index]
        parameters=callback[1].child_by_field_name('parameters')
        count=1 if parameters is not None and parameters.type=='identifier' else len(parameters.named_children) if parameters is not None else 0
        def invoke_callback(selected, owned, values):
            if selected:engine.callback_value(values[0],[U]*count)
            return U,None
        selected=engine.choose(reason+':opaque-callback-'+str(index),[False,True]) if engine.path_replay else None
        if selected is None:
            value,control=engine.fork_join([False,True],env,[callback],invoke_callback)
            if control=='throw':raise JavaThrow(value)
        elif selected:engine.callback_value(callback,[U]*count)
        # One execution exposes source events; arbitrary repetition cannot retain
        # a concrete captured heap or imply a precise invocation count.
        invalidate(callback,engine.opaque_heap)
        engine.warnings.add('opaque callback count/arguments are unknown; zero/may-execute alternatives retained: '+reason)
    if engine.path_replay:
        completion = engine.choose(reason+':opaque-completion', list(effect.completions))
        if completion == 'throw':
            raise JavaThrow({'__type__': ExceptionBound('java.lang.Throwable')})
        if completion is None:
            from .engine import CompletionRequired,AnalysisBoundary
            if not engine.allow_completion_splits:raise AnalysisBoundary('opaque completion requires another isolated continuation: '+reason)
            raise CompletionRequired(str(engine.branch_index)+':'+reason+':opaque-completion',list(effect.completions))
    else:
        engine.warnings.add('opaque throw alternative requires path replay: '+reason)
    return effect.value
