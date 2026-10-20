"""Certify target-independent scalar removals over a known finite Map.

Only ignored remove/removeAll calls may change one unaliased native target.
Every actually reached source callback must be a proved field getter. A private
execution checks casts, guards, throws and unchanged non-target roots before
the ordinary interpreter executes one representative order with full events.
"""
from .bean_properties import generated_accessor
from .context_key import fingerprint
from .generic_types import type_parts
from .heap_join import clone_execution, owned_objects
from .java_collections import JavaMapView, JavaMapEntry
from .native_arrays import JavaArray
from .native_storage import JavaList
from .project import text, walk
from .source_conversions import declaration_erasure
from .state import U


def field_getter(engine, method):
    if engine.p.parameters(method):return False
    node=engine.p.ast.get(method)
    if node is None:
        meta=engine.p.methods[method]
        return bool(generated_accessor(engine.p,meta['owner'],meta['name'],0,engine.standard_type))
    body=node.child_by_field_name('body')
    statements=[n for n in body.named_children if n.type not in ('line_comment','block_comment')] if body else []
    if len(statements)!=1 or statements[0].type!='return_statement':return False
    values=statements[0].named_children
    if len(values)!=1:return False
    value=values[0]
    if value.type=='identifier':return True
    return (value.type=='field_access' and
            text(value.child_by_field_name('object'))=='this')


def complete_context(value):
    attributes=[{name:getattr(item,name) for name in ('order_known','order','mutation_version','uncertain_versions')
                 if hasattr(item,name)} for item in owned_objects(value)]
    context=fingerprint((value,attributes))
    def bounded(item):
        return item!=('context-budget',) and (not isinstance(item,tuple) or all(bounded(v) for v in item))
    return context if bounded(context) else None


def certify(engine,node,view,env):
    if not isinstance(view,JavaMapView) or view.kind!='entries':return False
    source=view.backing
    if source.flavor not in ('HashMap','LinkedHashMap') or not isinstance(source.mapping,dict):return False
    entries=source.entries()
    if not 1<=len(entries)<=64:return False
    written=text(node.child_by_field_name('type'));base,parameters=type_parts(written)
    if not (engine.standard_type(base,'java.util.Map.Entry') or
            base=='Map.Entry' and engine.standard_type('Map','java.util.Map')):return False
    if not parameters or len(parameters)!=2:return False
    body=node.child_by_field_name('body');nodes=list(walk(body))
    forbidden={'assignment_expression','update_expression','return_statement','throw_statement',
               'break_statement','continue_statement','try_statement','try_with_resources_statement',
               'object_creation_expression','lambda_expression','method_reference','synchronized_statement',
               'for_statement','while_statement','do_statement'}
    if any(n.type in forbidden for n in nodes):return False
    mutators={'put','putAll','add','addAll','remove','removeAll','retainAll','clear','set',
              'sort','replaceAll','compute','computeIfAbsent','computeIfPresent','merge'}
    removals=[]
    for call in (n for n in nodes if n.type=='method_invocation'):
        name=text(call.child_by_field_name('name'))
        if name not in mutators:continue
        receiver=call.child_by_field_name('object');args=call.child_by_field_name('arguments')
        if (name not in ('remove','removeAll') or receiver is None or receiver.type!='identifier' or
                call.parent.type!='expression_statement' or len(args.named_children)!=1):return False
        removals.append((text(receiver),name))
    targets={name for name,_ in removals}
    if len(targets)!=1:return False
    target_name=next(iter(targets));target=env.get(target_name,U)
    if (not isinstance(target,JavaList) or isinstance(target,JavaArray) or target.opaque or
            target.fixed_size is not False or getattr(target,'unmodifiable',False) or engine.opaque(target)):return False
    scalar_kinds={'String','Integer','Long','Short','Byte','Character','Boolean'}
    if any(value is U or value is not None and kind not in scalar_kinds
           for value,kind in zip(target,target.kinds)):return False
    if any(name=='remove' for _,name in removals) and target.flavor!='HashSet':return False
    others={name:value for name,value in env.items() if name!=target_name}
    roots=(others,engine.state.bean_instances,engine.state.browser,engine.state.actor_browsers,
           engine.state.history,engine.state.transactions,engine.params)
    if any(value is target for value in owned_objects(roots)):return False
    for identifier in (n for n in nodes if n.type=='identifier' and text(n)==target_name):
        parent=identifier.parent
        if (parent.type!='method_invocation' or parent.child_by_field_name('object')!=identifier or
                text(parent.child_by_field_name('name')) not in ('remove','removeAll')):return False
    before=complete_context(others)
    if before is None:return False
    state_before=complete_context((engine.state.bean_instances,engine.state.transactions))
    if state_before is None:return False
    from .engine import Engine,AnalysisBoundary,AlternativeRequired
    from .java_exceptions import JavaThrow
    (state,owned,copied_view),_=clone_execution(engine.state,env,view)
    probe=Engine(engine.p,state,conservative=True,constraints=engine.use_constraints)
    probe.method=engine.method;probe.variable_types=dict(engine.variable_types)
    probe.source_bindings=dict(engine.source_bindings);probe.receiver_type=engine.receiver_type
    loop_name=text(node.child_by_field_name('name'))
    try:
        with probe.binding_scope(owned,[loop_name]):
            probe.variable_types[loop_name]=written
            for slot in copied_view.backing.entries():
                item=JavaMapEntry(copied_view.backing,slot)
                item=probe.reference_check(item,None,declaration_erasure(probe,written),'commuting map entry')
                if item is U:return False
                owned.set_value(loop_name,item,None)
                _,control=probe.execute(body,owned)
                if control is not None:return False
    except (JavaThrow,AnalysisBoundary,AlternativeRequired,TypeError,ValueError,KeyError,IndexError,AttributeError):
        return False
    if (probe.approximate or probe.warnings or probe.execution_assumptions or probe.data_operations or
            probe.request_events or probe.persistence_events or probe.state.database.unknown_tables!=engine.state.database.unknown_tables):return False
    callbacks={target for _,relation,target in probe.edges if relation=='executes'}
    if any(not field_getter(engine,method) for method in callbacks):return False
    getter_sites={event['callsite'] for event in probe.events if event['edge'][1]=='calls'}
    observers={'get','getKey','getValue','contains','indexOf','lastIndexOf','size','isEmpty','equals'}
    for call in (n for n in nodes if n.type=='method_invocation'):
        if text(call.child_by_field_name('name')) in observers|{'remove','removeAll'}:continue
        if engine.p.site(engine.method,call) not in getter_sites:return False
    after=complete_context({name:value for name,value in owned.items() if name!=target_name})
    if before!=after:return False
    if state_before!=complete_context((probe.state.bean_instances,probe.state.transactions)):return False
    result=owned[target_name]
    if result.opaque:return False
    # Only removal is permitted; this is also checked by the ordinary native
    # mutators. Do not deduce equality of Java boxed values from Python payloads.
    from .boxed_values import boxed_equal
    if any(not any(boxed_equal(value,old,kind,old_kind,lambda a,b:a==b) is True
                   for old,old_kind in zip(target,target.kinds))
           for value,kind in zip(result,result.kinds)):return False
    engine.effect_events.append({'model_version':'native-map-removal/1','operation':'foreach',
        'callsite':engine.method+':'+str(node.start_point.row+1),'iterations':len(entries),
        'heap_roots':[target_name],'resource_writes':[],'global_footprint':'one native removal target',
        'callbacks':sorted(callbacks),'completions':['normal'],
        'read_roots':sorted(others),'target_flavor':target.flavor,
        'guards':probe.conditions,
        'certification_source_invocations':probe.calls,
        'proof':'target is not read or aliased; guards read unchanged roots; actual callbacks are field getters; private execution has no throws/unknowns; scalar removals commute',
        'representative_order':'internal enumeration after commutativity proof; no source encounter order asserted'})
    return True
