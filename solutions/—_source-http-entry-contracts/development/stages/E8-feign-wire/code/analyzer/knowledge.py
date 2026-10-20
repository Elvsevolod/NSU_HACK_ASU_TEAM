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
    meta=engine.p.methods.get(engine.method,{})
    location={'file':meta.get('file'),'line':node.start_point.row+1 if node is not None else None,
        'end_line':node.end_point.row+1 if node is not None else None,'method':engine.method}
    key=(phase,cause,location['file'],location['line'],declared_type,
        tuple((g.get('condition'),str(g.get('value')),g.get('assumed')) for g in engine.guard_stack))
    if key in engine.loss_keys:return
    engine.loss_keys.add(key)
    if len(engine.loss_events)>=128:
        engine.loss_records_omitted+=1;return
    source=engine.p.sources.get(meta.get('file'),b'')
    event={'sequence':len(engine.loss_events)+1,'phase':phase,'cause':cause,'location':location,
        'source_sha256':hashlib.sha256(source).hexdigest() if source else None,
        'declared_type':declared_type or None,'runtime_kind':runtime_kind,
        'before':abstract(before),'after':abstract(after),'completion':completion,
        'guards':deepcopy(engine.guard_stack),'assumptions':list(engine.execution_assumptions),
        'prefix_event_count':len(engine.events),'prefix_edges':[list(e['edge']) for e in engine.events[-12:]],
        'actual_effect_count':len(engine.data_operations),'actual_effects':deepcopy(engine.data_operations[-4:]),
        'possible_write_footprint':list(possible_writes),'widened_locations':list(affected),
        'request_id':engine.request_events[-1].get('id') if engine.request_events else None,
        'producer_lineage':'request bound_arguments / request provenance and state history; see full step trace'}
    engine.loss_events.append(event)
