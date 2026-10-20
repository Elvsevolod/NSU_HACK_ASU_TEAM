"""Passive causal loss records, separate from observed program effects."""
from copy import deepcopy
import hashlib
from .state import U


def abstract(value):
    if value is U:return {'knowledge':'unknown'}
    if value is None or type(value) in (bool,int,float):return {'knowledge':'constant','value':value}
    if type(value) is str:return {'knowledge':'constant','value':value[:160],'truncated':len(value)>160}
    if isinstance(value,list):return {'knowledge':'collection','carrier':type(value).__name__,
        'cardinality':None if getattr(value,'opaque',False) else len(value),
        'order_known':getattr(value,'order_known',None),'kinds':getattr(value,'kinds',[])[:16]}
    if isinstance(value,dict):return {'knowledge':'object','carrier':type(value).__name__,
        'type':getattr(value,'declared_type',value.get('__type__')),'fields':sorted(map(str,value))[:24]}
    return {'knowledge':'unrendered','carrier':type(value).__name__}


def type_qualifier(engine,node,env):
    from .project import text
    current=node
    while current.parent is not None and current.parent.type=='field_access' and current.parent.child_by_field_name('object')==current:
        current=current.parent
    parent=current.parent
    if parent is None or parent.type!='method_invocation' or parent.child_by_field_name('object')!=current:return False
    root=text(current).split('.')[0]
    meta=engine.p.methods.get(engine.method,{})
    return root not in env and root not in engine.variable_types and root not in engine.p.type_fields.get(meta.get('owner'),{})


def record(engine,phase,cause,node=None,before=U,after=U,declared_type='',runtime_kind=None,
           affected=(),possible_writes=(),completion='unresolved'):
    source_mid=engine.method
    if node is None and engine.boundary_frames:
        source_mid,node,_=engine.boundary_frames[-1]
    meta=engine.p.methods.get(source_mid,{})
    location={'file':meta.get('file'),'line':node.start_point.row+1 if node is not None else None,
        'end_line':node.end_point.row+1 if node is not None else None,'method':source_mid}
    key=(phase,cause,location['file'],location['line'],declared_type,
        tuple((g.get('condition'),str(g.get('value')),g.get('assumed')) for g in engine.guard_stack))
    if key in engine.loss_keys:return
    engine.loss_keys.add(key)
    if len(engine.loss_events)>=128:
        engine.loss_records_omitted+=1;return
    source=engine.p.sources.get(meta.get('file'),b'')
    request_id=(engine.filter_frames[-1]['request_id'] if engine.filter_frames else
        next((r['id'] for r in reversed(engine.request_events) if r['entry']==source_mid),None))
    request_index=next((i for i,r in enumerate(engine.request_events) if r['id']==request_id),None)
    request_event=engine.request_events[request_index] if request_index is not None else {}
    request=request_event.get('request') or {}
    from .resource_effects import proven_read
    reads=[{'resource':op['resource'],'operation':op['operation'],'request_id':op.get('request_id'),
        'data_operation_index':i} for i,op in enumerate(engine.data_operations)
        if op.get('source_site') in engine.p.nodes and proven_read(engine.p,op['source_site'])]
    invocation=node
    while invocation is not None and invocation.type!='method_invocation':invocation=invocation.parent
    callsite=engine.p.site(source_mid,invocation) if invocation is not None else None
    event={'sequence':len(engine.loss_events)+1,'phase':phase,'cause':cause,'location':location,
        'callsite':callsite,
        'source_sha256':hashlib.sha256(source).hexdigest() if source else None,
        'declared_type':declared_type or None,'runtime_kind':runtime_kind,
        'before':abstract(before),'after':abstract(after),'completion':completion,
        'guards':deepcopy(engine.guard_stack),'assumptions':list(engine.execution_assumptions),
        'prefix_event_count':len(engine.events),'prefix_edges':[list(e['edge']) for e in engine.events[-12:]],
        'actual_effect_count':len(engine.data_operations),'actual_effects':deepcopy(engine.data_operations[-4:]),
        'read_locations':reads,'read_locations_scope':'source-proven repository reads in executed SQL prefix; all accesses remain in data_operations',
        'possible_write_footprint':list(possible_writes),'widened_locations':list(affected),
        'request_id':request_id,'producer_lineage':{
            'entry':request_event.get('entry'),
            'request_event_reference':'requests['+str(request_index)+']' if request_index is not None else None,
            'bound_arguments_reference':'requests['+str(request_index)+'].bound_arguments' if request_index is not None else None,
            'provenance':deepcopy(request.get('provenance')),
            'history_length':len(engine.state.history) if engine.state is not None else 0}}
    engine.loss_events.append(event)
