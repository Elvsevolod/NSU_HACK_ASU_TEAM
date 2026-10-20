"""Bounded Spring REQUIRED/JPA unit of work; SQL events survive rollback.

Provider-dependent identifier strategies, nondefault propagation, custom flush
modes and association loading stay explicit limitations of this profile.
"""
from copy import deepcopy

from .state import U
from .java_collections import JavaRecord
from .java_exceptions import JavaThrow, assignable


class LazyRecord(JavaRecord):
    def __init__(self, declared, fields, wire_fields, resource, keys):
        super().__init__(declared, fields, wire_fields)
        self.resource, self.id_fields, self.loaded = resource, tuple(keys), False


def resource_key(database, resource):
    rows = database.rows(resource)
    found = [key for key, value in database.tables.items() if value is rows]
    return found[0] if len(found) == 1 else (database.schemas.get(resource.get('schema'), resource.get('schema')), resource['name'])


def transaction(engine, mid=None):
    mid = mid or engine.method
    unit = engine.p.ix.unit_of(mid)
    return engine.state.transactions.get(unit)


def begin(engine, mid, annotations):
    unit = engine.p.ix.unit_of(mid)
    if unit in engine.state.transactions:return False
    options = [annotation.get('args', '') for annotation in annotations if annotation['name'].rsplit('.',1)[-1] == 'Transactional']
    supported = all(option.strip() in ('', '()', '(readOnly=false)') for option in options)
    engine.state.transactions[unit] = {'base': engine.state.database.copy(), 'writes': set(),
        'pending': [], 'managed': {}, 'supported': supported, 'origin': mid,
        'base_assumptions': deepcopy(engine.state.resource_assumptions)}
    if not supported:
        engine.approximate = True
        engine.warnings.add('transaction options/provider policy outside REQUIRED default profile: '+mid)
    return True


def identity(engine, rid, record):
    keys = engine.p.id_fields.get(rid, [])
    values = tuple(repr(record.get(key,U)) for key in keys)
    return (rid, values) if keys and all(record.get(key,U) is not U for key in keys) else None


def manage(engine, rid, record):
    tx = transaction(engine)
    key = identity(engine, rid, record)
    if tx is None or key is None:return record
    if key in tx['managed']:return tx['managed'][key]['object']
    tx['managed'][key] = {'resource': rid, 'object': record, 'snapshot': deepcopy(dict(record))}
    return record


def cached(engine, rid, key_value):
    tx = transaction(engine)
    keys = engine.p.id_fields.get(rid, [])
    key = (rid, (repr(key_value),)) if len(keys)==1 else None
    return tx['managed'].get(key, {}).get('object', U) if tx else U


def sql(engine, operation, emitted_by=None):
    event = deepcopy(operation)
    event['sql_emitted'] = True
    event['transactional'] = transaction(engine) is not None
    event['emitted_by'] = emitted_by or event['source_site']
    guards, assumptions = engine.guard_stack, engine.execution_assumptions
    engine.guard_stack = [*guards, *event.pop('_guards', [])]
    engine.execution_assumptions = list(dict.fromkeys(assumptions + event.pop('_assumptions', [])))
    try:engine.add(event['method'], 'data', event['resource'], event['source_site'])
    finally:engine.guard_stack, engine.execution_assumptions = guards, assumptions
    engine.data_operations.append(event)


def queue(engine, operation):
    tx = transaction(engine)
    if tx is None:
        sql(engine, operation)
    else:
        tx['pending'].append({**deepcopy(operation), '_guards':deepcopy(engine.guard_stack),
                              '_assumptions':list(engine.execution_assumptions)})
        tx['writes'].add(resource_key(engine.state.database, engine.p.nodes[operation['resource']]))


def flush(engine, reason):
    tx = transaction(engine)
    if tx is None:return
    # Dirty checking is against the managed instance, not a detached wire copy.
    for item in tx['managed'].values():
        obj, rid = item['object'], item['resource']
        if isinstance(obj, LazyRecord) and not obj.loaded:continue
        if dict(obj) == item['snapshot']:continue
        rows = engine.state.database.rows(engine.p.nodes[rid])
        keys = engine.p.id_fields.get(rid, [])
        match = next((row for row in rows or [] if all(row.get(key,U)==obj.get(key,U) for key in keys)), None)
        if match is not None:
            match.update(deepcopy(dict(obj)))
        tx['writes'].add(resource_key(engine.state.database, engine.p.nodes[rid]))
        if not any(op['resource']==rid and op['operation'].startswith(('save','insert')) for op in tx['pending']):
            tx['pending'].append({'method': engine.method, 'resource': rid, 'operation': 'dirty_update',
                'arguments': [deepcopy(obj)], 'source_site': reason, 'uncertain_write': bool(engine.uncertain)})
        item['snapshot'] = deepcopy(dict(obj))
    for operation in tx['pending']:sql(engine, operation, reason)
    tx['pending'].clear()


def end(engine, mid, failure):
    unit = engine.p.ix.unit_of(mid)
    tx = engine.state.transactions[unit]
    rollback = False
    if failure is not None:
        typ = failure.get('__type__', U) if isinstance(failure, dict) else U
        from .java_exceptions import native_type
        typ = native_type(typ) if isinstance(typ,str) else typ
        runtime = assignable(typ, 'java.lang.RuntimeException', engine.p)
        error = assignable(typ, 'java.lang.Error', engine.p)
        rollback = True if runtime is True or error is True else U if U in (runtime,error) else False
    if not tx['supported'] or rollback is U:
        for key in tx['writes']:engine.state.database.unknown_tables.add(key)
        engine.approximate = True
        engine.warnings.add('transaction rollback/commit is unknown; touched tables widened: '+mid)
    elif rollback:
        for key in tx['writes']:
            if key in tx['base'].tables:engine.state.database.tables[key] = deepcopy(tx['base'].tables[key])
            else:engine.state.database.tables.pop(key, None)
            if key in tx['base'].unknown_tables:engine.state.database.unknown_tables.add(key)
            else:engine.state.database.unknown_tables.discard(key)
        for rid in list(engine.state.resource_assumptions):
            if resource_key(engine.state.database,engine.p.nodes[rid]) in tx['writes']:
                if rid in tx['base_assumptions']:engine.state.resource_assumptions[rid]=tx['base_assumptions'][rid]
                else:engine.state.resource_assumptions.pop(rid,None)
    else:
        flush(engine, 'transaction commit at '+mid)
    engine.persistence_events.append({'method':mid,'model_version':'spring-required-jpa/1',
        'outcome':'unknown' if not tx['supported'] or rollback is U else 'rollback' if rollback else 'commit',
        'tables':sorted('.'.join(key) for key in tx['writes'])})
    del engine.state.transactions[unit]


def lazy(engine, rid, value):
    entity = engine.p.entities.get(rid)
    keys = engine.p.id_fields.get(rid, [])
    if not entity or len(keys)!=1:return U
    record = LazyRecord(engine.p.nodes[entity]['fqn'], {'__type__':engine.p.nodes[entity]['fqn'],keys[0]:deepcopy(value)},
                        engine.p.type_fields.get(entity,{}), rid, keys)
    return manage(engine,rid,record)


def load(engine, record, field, reason):
    if not isinstance(record, LazyRecord) or record.loaded or field in record.id_fields:return
    rows = engine.state.database.rows(engine.p.nodes[record.resource])
    sql(engine, {'method':engine.method,'resource':record.resource,'operation':'lazy_load',
        'arguments':[record.get(key,U) for key in record.id_fields], 'source_site':reason,'uncertain_write':False})
    if rows is None:
        engine.execution_assumptions.append('lazy entity contents are unknown: '+reason)
        record.loaded = True
        return
    matching = [engine.p.materialize(engine.state.database,record.resource,row) for row in rows]
    matching = [row for row in matching if all(row.get(key,U)==record.get(key,U) for key in record.id_fields)]
    if not matching:
        raise JavaThrow({'__type__':'jakarta.persistence.EntityNotFoundException'})
    record.update(deepcopy(matching[0])); record.loaded = True
    tx = transaction(engine)
    if tx:
        key = identity(engine,record.resource,record)
        tx['managed'][key]['snapshot'] = deepcopy(dict(record))
