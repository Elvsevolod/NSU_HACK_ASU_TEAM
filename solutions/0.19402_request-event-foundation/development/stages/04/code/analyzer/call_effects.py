"""Versioned conservative effects for calls without an executable source model."""
from dataclasses import dataclass
import re

from .state import U
from .java_collections import JavaMap, JavaJsonMapper, JavaRecord, is_symbolic
from .java_exceptions import JavaThrow, ExceptionBound


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
        methods = [mid for mid, meta in project.methods.items() if meta['owner'] == current]
        if methods:
            resources.update(target for _, target in project.ix.closure(set(methods))[3])
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
    else:
        for key in value:
            if not str(key).startswith('__'):value[key] = U


def apply_unknown(engine, name, receiver, args, env, declared, reason):
    meta = engine.p.methods[engine.method]
    owner = engine.p.resolve_type(declared, meta['module'], meta['file']) if declared else None
    resources = source_resources(engine.p, owner)
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
    engine.effect_events.append({'callsite': reason, 'operation': name, 'declared_receiver': declared,
        'model_version': effect.model_version, 'heap_roots': list(effect.heap_writes),
        'resource_writes': resources, 'global_footprint': 'unresolved' if resources is None else 'source_dependencies',
        'callbacks': callbacks, 'completions': effect.completions})
    if callbacks:
        engine.warnings.add('opaque callback dispatch/count/arguments remain unresolved: '+reason)
    if engine.path_replay:
        completion = engine.choose(reason+':opaque-completion', list(effect.completions))
        if completion == 'throw':
            raise JavaThrow({'__type__': ExceptionBound('java.lang.Throwable')})
        if completion is None:
            engine.warnings.add('opaque normal/throw joined at path budget: '+reason)
    else:
        engine.warnings.add('opaque throw alternative requires path replay: '+reason)
    return effect.value
