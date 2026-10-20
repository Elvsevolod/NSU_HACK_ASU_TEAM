"""Local startup fields for an explicitly annotated, no-arg Spring bean.

Startup is analyzed separately from scenario execution. Source startup with
remote/data effects or an explicit constructor stays outside this contract.
"""
from .state import U
from .bean_lifecycle import BeanLifecycle
from .heap_join import widen


def initialized_receiver(engine, mid):
    owner=engine.p.methods[mid]['owner'];meta=engine.p.nodes[owner]
    annotations={a['name'].rsplit('.',1)[-1] for a in meta.get('annotations',[])}
    if not annotations & {'Component','Service','Controller','RestController'}:return U
    methods=[target for target,m in engine.p.methods.items() if m['owner']==owner]
    callbacks=[target for target in methods if any(a['name'].rsplit('.',1)[-1]=='PostConstruct'
               for a in engine.p.methods[target].get('annotations',[]))]
    if len(callbacks)!=1 or engine.p.parameters(callbacks[0]) or any(engine.p.methods[t]['name']=='<init>' for t in methods):return U
    _,_,remote,data=engine.p.ix.closure(set(callbacks))
    if remote or data:return U
    unit=engine.p.ix.unit_of(mid);key=(unit,owner)
    if key in engine.state.bean_instances:return engine.state.bean_instances[key]
    from .engine import Engine,AlternativeRequired,AnalysisBoundary
    from .java_exceptions import JavaThrow
    from copy import deepcopy
    bootstrap=Engine(engine.p,deepcopy(engine.state));bootstrap.method=mid
    obj=BeanLifecycle(bootstrap,'source bean startup').allocate(owner,meta['fqn'],meta,{},lambda _:None,'source')
    try:
        bootstrap.initialize_instance(owner,obj,'source bean startup')
        bootstrap.invoke(callbacks[0],[],obj,'source bean startup')
        if bootstrap.approximate:raise AnalysisBoundary('unsupported local initializer')
    except (AlternativeRequired,AnalysisBoundary,JavaThrow):
        bootstrap.approximate=True
        widen(obj)
        engine.assume('local bean initialization is unresolved: '+owner)
        engine.warnings.add('local bean initialization is unresolved: '+owner)
    engine.state.bean_instances[key]=obj
    engine.effect_events.append({'model_version':'source-local-bean-startup/1','operation':'PostConstruct',
        'owner':owner,'callbacks':callbacks,'scenario_execution':False,'resource_writes':[],
        'complete':not bootstrap.approximate})
    return obj
