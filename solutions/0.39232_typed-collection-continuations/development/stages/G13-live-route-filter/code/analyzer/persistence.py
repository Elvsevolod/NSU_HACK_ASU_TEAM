"""Bounded Spring REQUIRED/JPA unit of work; SQL events survive rollback.

Provider-dependent identifier strategies, nondefault propagation, custom flush
modes and association loading stay explicit limitations of this profile.
"""
from copy import deepcopy

from .state import U
from .java_collections import JavaRecord
from .java_exceptions import JavaThrow, assignable
from .native_storage import JavaList


class LazyCollection(JavaList):
    def __init__(self,resource,foreign,key,value_column,order_column,origin,reason):
        super().__init__()
        self.resource,self.foreign,self.key=resource,foreign,deepcopy(key)
        self.value_column,self.order_column=value_column,order_column
        self.origin,self.reason,self.loaded=origin,reason,False


def primary_resources(engine,written):
    from .generic_types import type_parts
    meta=engine.p.methods[engine.method]
    owner=engine.p.resolve_type(written or '',meta['module'],meta['file'])
    cache=engine.p.__dict__.setdefault('_repository_primary_resources',{})
    if owner in cache:return cache[owner]
    pending,seen,resources=[owner],set(),set()
    while pending:
        current=pending.pop()
        if current is None or current in seen:continue
        seen.add(current);context=engine.p.nodes[current]
        for parent in engine.p.generic_parents.get(current,()):
            base,args=type_parts(parent)
            if base.rsplit('.',1)[-1] in ('JpaRepository','CrudRepository','MongoRepository') and args:
                entity=engine.p.resolve_type(args[0],context['module'],context.get('file'))
                resources.update(rid for rid,tid in engine.p.entities.items() if tid==entity)
            else:pending.append(engine.p.resolve_type(base,context['module'],context.get('file')))
    cache[owner]=frozenset(resources)
    return cache[owner]


def attach_collections(engine,rid,record,reason):
    from .generic_types import type_parts
    from .state import camel
    tid=engine.p.entities.get(rid)
    keys=engine.p.id_fields.get(rid,[])
    if len(keys)!=1:return record
    owner=engine.p.nodes[tid]
    descriptions={}
    for mapping in engine.p.collections.get(rid,[]):
        prop,table,foreign,*columns=mapping
        resources=[key for key,node in engine.p.nodes.items() if node.get('kind')=='data_resource' and node.get('name')==table and node.get('schema')==engine.p.nodes[rid].get('schema')]
        if len(resources)==1:descriptions[prop]=(resources[0],foreign,*(columns+[None,None])[:2])
    for prop,info in engine.p.type_fields.get(tid,{}).items():
        relation=info.get('orm_relation')
        if not relation:continue
        if relation['kind']=='OneToMany' and relation['mapped_by']:
            _,args=type_parts(info['type'])
            target=engine.p.resolve_type(args[0],owner['module'],info['file']) if args and len(args)==1 else None
            inverse=engine.p.type_fields.get(target,{}).get(relation['mapped_by'],{}).get('orm_relation') or {}
            resources=[key for key,value in engine.p.entities.items() if value==target]
            if len(resources)==1 and inverse.get('join_column'):
                descriptions[prop]=(resources[0],camel(inverse['join_column']),None,None)
        if prop not in descriptions:
            engine.approximate=True
            engine.assume('unmodeled ORM association loading: '+owner['fqn']+'.'+prop)
            engine.warnings.add('ORM association mapping/fetch outside the supported profile: '+owner['fqn']+'.'+prop)
            continue
        record[prop]=LazyCollection(*descriptions[prop][:2],record.get(keys[0],U),*descriptions[prop][2:],engine.method,reason)
        from .generic_types import type_parts
        _,arguments=type_parts(info['type'])
        record[prop].element_kind=engine.declared_kind(arguments[0],owner) if arguments and len(arguments)==1 else None
        if relation['fetch']=='EAGER':load_collection(engine,record[prop],reason)
    return record


def load_collection(engine,value,reason):
    if not isinstance(value,LazyCollection) or value.loaded:return value
    from .models import key_equal
    value.loaded=True
    resource=engine.p.nodes[value.resource]
    sql(engine,{'method':value.origin,'resource':value.resource,'operation':'association_load',
        'arguments':[value.key],'source_site':value.reason,'uncertain_write':False},reason)
    rows=engine.state.database.rows(resource)
    if rows is None:
        value.opaque=True
        engine.assume('association state is unknown: '+value.resource)
        return value
    selected=[]
    for row in rows:
        equal=key_equal(row.get(value.foreign,U),value.key)
        if equal is U:value.opaque=True
        if equal is True:selected.append(row)
    if value.order_column:
        column=engine.state.database.column_name(resource_key(engine.state.database,resource),value.order_column)
        positions=[row.get(column) for row in selected]
        if any(type(position) is not int for position in positions) or sorted(positions)!=list(range(len(selected))):value.opaque=True
        else:selected.sort(key=lambda row:row[column])
    for row in selected:
        item=row.get(value.value_column,U) if value.value_column else engine.p.materialize(engine.state.database,value.resource,row)
        kind=getattr(value,'element_kind',None)
        if kind=='String' and type(item) is not str or kind in ('Integer','Long','Short','Byte') and type(item) is not int:
            value.opaque=True
        value.append(deepcopy(item),kind)
    # An unordered multi-element collection has no proven iteration order.
    if len(value)>1 and value.order_column is None:
        value.order_known=False
        engine.assume('association iteration order is unobserved: '+value.resource)
    return value


class LazyRecord(JavaRecord):
    def __init__(self, declared, fields, wire_fields, resource, keys):
        super().__init__(declared, fields, wire_fields)
        self.resource, self.id_fields, self.loaded = resource, tuple(keys), False


def resource_key(database, resource):
    rows = database.rows(resource)
    found = [key for key, value in database.tables.raw_items() if value is rows]
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
        engine.assume('transaction options/provider policy outside REQUIRED default profile: '+mid)
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


def materialize_record(engine, entity, hydrated, reason):
    fields=engine.p.type_fields.get(entity,{})
    fqn=engine.p.nodes[entity]['fqn']
    record=JavaRecord(fqn,{'__type__':fqn},fields)
    record.source_owner=entity
    record._native_field_kinds={}
    for name,info in fields.items():
        typ=info['type']
        record[name]=False if typ=='boolean' else '\0' if typ=='char' else 0 if typ in ('byte','short','int','long','float','double') else None
        record._native_field_kinds[name]=engine.declared_kind(typ,engine.p.nodes[info['declaring_type']]) if typ in ('boolean','char','byte','short','int','long','float','double') else None
    constructors=[mid for mid in engine.p.methods_of(entity,'<init>')
                  if not engine.p.parameters(mid) and engine.p.ast.get(mid) is not None]
    if len(constructors)==1:
        record._pending_initializer=entity
        engine.invoke(constructors[0],[],record,'ORM constructor callback: '+reason,export_method=False)
    elif not constructors:
        engine.initialize_instance(entity,record,reason)
    else:
        engine.approximate=True
        engine.assume('ambiguous ORM constructor: '+fqn)
    # Hydration follows construction; its callbacks and failures remain events.
    record.update(deepcopy(hydrated))
    for name,info in fields.items():
        if name in record:
            record._native_field_kinds[name]=engine.declared_kind(info['type'],engine.p.nodes[info['declaring_type']])
    return record


def sql(engine, operation, emitted_by=None):
    event = deepcopy(operation)
    event['sql_emitted'] = engine.p.nodes[event['resource']].get('resource_kind')!='collection'
    event['datastore_event'] = True
    event['transactional'] = transaction(engine) is not None
    event['emitted_by'] = emitted_by or event['source_site']
    guards, assumptions = engine.guard_stack, engine.execution_assumptions
    engine.guard_stack = [*guards, *event.pop('_guards', [])]
    engine.execution_assumptions = list(dict.fromkeys(assumptions + event.pop('_assumptions', [])))
    from .event_values import witness
    try:engine.add(event['method'], 'data', event['resource'], event['source_site'],witness(event.get('arguments',[])))
    finally:engine.guard_stack, engine.execution_assumptions = guards, assumptions
    engine.data_operations.append(event)


def queue(engine, operation):
    tx = transaction(engine)
    rid=operation['resource']
    tid=engine.p.entities.get(rid)
    generated=engine.p.generated_ids.get(rid)
    field=engine.p.type_fields.get(tid,{}).get(generated,{})
    if tx is None:
        sql(engine, operation)
    else:
        arguments=operation.get('arguments',[])
        new_identity=bool(arguments and isinstance(arguments[0],dict) and arguments[0].get(generated,U) in (None,U))
        if field.get('id_strategy')=='IDENTITY' and new_identity and operation['operation'].startswith(('save','insert')):
            engine.assume('IDENTITY insert timing uses the Hibernate-compatible active-transaction profile: '+operation['source_site'])
            sql(engine,operation)
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
        match = next((row for row in rows or [] if all(engine.p.materialize(engine.state.database,rid,row).get(key,U)==obj.get(key,U) for key in keys)), None)
        if match is not None:
            columns={field:column for column,field in engine.p.column_aliases.get(rid,{}).items()}
            fields=engine.p.type_fields.get(engine.p.entities.get(rid),{})
            for field in fields:
                value=obj.get(field,U)
                column=columns.get(field,field)
                match[column]=deepcopy(value)
                if field in match and field!=column:match[field]=deepcopy(value)
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
    rollback = tx.get('rollback_only',False)
    if failure is not None:
        typ = failure.get('__type__', U) if isinstance(failure, dict) else U
        from .java_exceptions import native_type
        typ = native_type(typ) if isinstance(typ,str) else typ
        runtime = assignable(typ, 'java.lang.RuntimeException', engine.p)
        error = assignable(typ, 'java.lang.Error', engine.p)
        failure_rollback = True if runtime is True or error is True else U if U in (runtime,error) else False
        rollback = True if rollback is True or failure_rollback is True else U if U in (rollback,failure_rollback) else False
    if not tx['supported'] or rollback is U:
        for operation in tx['pending']:engine.candidate_edges.add((operation['method'],'data',operation['resource']))
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
    if failure is None and rollback is True:
        raise JavaThrow({'__type__':'org.springframework.transaction.UnexpectedRollbackException'})


def nested_failure(engine,mid,failure):
    if failure is None:return
    tx=engine.state.transactions.get(engine.p.ix.unit_of(mid))
    if tx is None:return
    from .java_exceptions import native_type
    name=failure.get('__type__',U) if isinstance(failure,dict) else U
    typ=native_type(name) if isinstance(name,str) else U
    runtime=assignable(typ,'java.lang.RuntimeException',engine.p)
    error=assignable(typ,'java.lang.Error',engine.p)
    if runtime is True or error is True:tx['rollback_only']=True
    elif U in (runtime,error) and not tx.get('rollback_only'):tx['rollback_only']=U


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
        engine.assume('lazy entity contents are unknown: '+reason)
        record.loaded = True
        return
    matching = [engine.p.materialize(engine.state.database,record.resource,row) for row in rows]
    matching = [row for row in matching if all(row.get(key,U)==record.get(key,U) for key in record.id_fields)]
    if not matching:
        raise JavaThrow({'__type__':'jakarta.persistence.EntityNotFoundException'})
    entity=engine.p.entities[record.resource]
    hydrated=materialize_record(engine,entity,matching[0],reason)
    hydrated=attach_collections(engine,record.resource,hydrated,reason)
    record.update(deepcopy(hydrated)); record.loaded = True
    for name in ('source_owner','_native_field_kinds','_field_reference_types'):
        if hasattr(hydrated,name):setattr(record,name,deepcopy(getattr(hydrated,name)))
    tx = transaction(engine)
    if tx:
        key = identity(engine,record.resource,record)
        tx['managed'][key]['snapshot'] = deepcopy(dict(record))


def storage_record(engine,rid,record,check_children=True):
    """Known SQL columns for enum/association entities; graph objects stay managed.

    New or changed aggregate children require a separate cascade-write model.
    Unchanged existing children are checked, not declared physically updated.
    """
    from .java_collections import JavaEnumValue
    from .state import camel
    from .generic_types import type_parts
    from .engine import AnalysisBoundary
    entity=engine.p.entities.get(rid);fields=engine.p.type_fields.get(entity,{})
    if any((info.get('orm_relation') or {}).get('kind')=='ElementCollection' for info in fields.values()):return record
    if not any(info.get('orm_relation') or info.get('enum_string') for info in fields.values()):return record
    key=resource_key(engine.state.database,engine.p.nodes[rid])
    columns=engine.state.database.columns.get(key)
    if columns is None:raise AnalysisBoundary('ORM physical columns are unknown: '+rid,category='unsupported_semantics')
    aliases=engine.p.column_aliases.get(rid,{})
    result={}
    for column in columns:
        name=aliases.get(column,column);value=record.get(name,record.get(column,U));info=fields.get(name,{})
        if isinstance(value,JavaEnumValue):
            if not info.get('enum_string'):raise AnalysisBoundary('ORM enum storage strategy is unresolved: '+rid+'.'+name,category='unsupported_semantics')
            value=value.enum_name
        if value is U:
            related=[(prop,data) for prop,data in fields.items() if data.get('orm_relation') and data['orm_relation'].get('join_column') and camel(data['orm_relation']['join_column'])==column]
            if len(related)==1:
                prop,data=related[0];target=engine.p.resolve_type(data['type'],engine.p.nodes[entity]['module'],data['file'])
                ids=[n for n,i in engine.p.type_fields.get(target,{}).items() if i.get('id')]
                owner=record.get(prop)
                value=owner.get(ids[0],U) if len(ids)==1 and isinstance(owner,dict) else U
        result[column]=deepcopy(value)
    if check_children:
        for name,info in fields.items():
            relation=info.get('orm_relation')
            if not relation or relation['kind']!='OneToMany':continue
            children=record.get(name,U)
            if not isinstance(children,list) or getattr(children,'opaque',False):
                raise AnalysisBoundary('ORM aggregate membership is unknown: '+rid+'.'+name,category='unsupported_semantics')
            _,types=type_parts(info['type']);meta=engine.p.nodes[entity]
            target=engine.p.resolve_type(types[0],meta['module'],info['file']) if types and len(types)==1 else None
            resources=[resource for resource,owner in engine.p.entities.items() if owner==target]
            if len(resources)!=1:raise AnalysisBoundary('ORM aggregate child table is unresolved: '+rid+'.'+name,category='unsupported_semantics')
            child_resource=resources[0];rows=engine.state.database.rows(engine.p.nodes[child_resource]);ids=engine.p.id_fields.get(child_resource,[])
            inverse=engine.p.type_fields.get(target,{}).get(relation.get('mapped_by'),{}).get('orm_relation') or {}
            parent_ids=engine.p.id_fields.get(rid,[])
            foreign=camel(inverse['join_column']) if inverse.get('join_column') else None
            if rows is None or len(parent_ids)!=1 or not foreign or record.get(parent_ids[0],U) is U:
                raise AnalysisBoundary('ORM aggregate existing membership is unresolved: '+rid+'.'+name,category='unsupported_semantics')
            associated=[row for row in rows if row.get(foreign,U)==record[parent_ids[0]]]
            if len(associated)!=len(children):raise AnalysisBoundary('ORM aggregate membership changed: '+rid+'.'+name,category='unsupported_semantics')
            for child in children:
                matches=[row for row in rows or [] if isinstance(child,dict) and ids and all(row.get(i,U) is not U and row.get(i)==child.get(i,U) for i in ids)]
                original=engine.p.materialize(engine.state.database,child_resource,matches[0]) if len(matches)==1 else None
                if original is None or storage_record(engine,child_resource,child,False)!=storage_record(engine,child_resource,original,False):
                    raise AnalysisBoundary('new/changed ORM aggregate child needs cascade-write semantics: '+rid+'.'+name,category='unsupported_semantics')
    return result
