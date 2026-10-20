"""Checker-owned typed comparisons and finite, alias-preserving heap evidence."""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal


def equal(a,b):
    if type(a) is not type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return a==b


def payload(value):
    if isinstance(value,list):return [payload(child) for child in value]
    if isinstance(value,dict) and '__symbol__' in value:return deepcopy(value)
    if isinstance(value,dict):return {key:payload(child) for key,child in value.items() if key not in ('__type__','__http_entity__')}
    return value


def heap(state):
    """Object IDs are local traversal references, never process addresses."""
    seen={}
    def visit(value):
        if value is None or type(value) in (str,bool,int,float):return value
        if isinstance(value,Decimal):return {'$decimal':str(value)}
        if isinstance(value,datetime):return {'$instant':value.isoformat()}
        if isinstance(value,(dict,list,tuple)):
            if id(value) in seen:return {'$ref':seen[id(value)]}
            token='h'+str(len(seen)+1);seen[id(value)]=token
            fields={str(k):visit(v) for k,v in sorted(value.items(),key=lambda item:str(item[0]))} if isinstance(value,dict) else [visit(v) for v in value]
            attributes={k:visit(v) for k,v in sorted(getattr(value,'__dict__',{}).items())
                        if k in ('java_type','declared_type','wire_fields','source_owner','order_known','flavor','opaque','component')}
            return {'$id':token,'kind':type(value).__name__,'fields':fields,**({'attributes':attributes} if attributes else {})}
        from analyzer.state import U
        if value is U:return {'unknown':True}
        return {'unmeasured_type':type(value).__name__}
    return visit({'beans':state.bean_instances,'browser':state.browser,'actor_browsers':state.actor_browsers,
        'static_fields':state.static_fields,'class_initialization':state.class_initialization})


def delta(before,after):
    return {key:{'before':before.get(key,{'missing':True}),'after':after.get(key,{'missing':True})}
            for key in sorted(set(before)|set(after)) if not equal(before.get(key,{'missing':True}),after.get(key,{'missing':True}))}


def capture(engine,request,result):
    return {'wire':request.record(),'requests':deepcopy(engine.request_events),'result':deepcopy(result),
        'responses':deepcopy(engine.http_responses),'edges':sorted(engine.edges),'outcome':engine.outcome,
        'diagnostics':sorted(engine.warnings),'call_effects':deepcopy(engine.effect_events),
        'knowledge_losses':deepcopy(engine.loss_events),
        'data_operations':deepcopy(engine.data_operations),'state_after':deepcopy(engine.state.snapshot(full=True)),
        'heap_after':heap(engine.state)}


def chain(rows,label):
    result=[];previous={}
    for n,row in enumerate(rows,1):
        wire=row.get('wire',row.get('request',{})) or {};links=[]
        for field,binding in row.get('bindings',{}).items():
            if isinstance(binding,dict):links.append({'consumer_field':field,'source':binding.get('source'),'reference':binding.get('reference')})
        authorization=wire.get('headers',{}).get('authorization',[]) if isinstance(wire.get('headers'),dict) else []
        for header in authorization if isinstance(authorization,list) else []:
            if not isinstance(header,str) or not header.startswith('Bearer '):continue
            token=header[7:]
            for position in range(n-2,-1,-1):
                producer=rows[position].get('result')
                if isinstance(producer,dict) and equal(producer.get('token'),token):
                    links.append({'consumer_field':'headers.authorization','reference':'step '+str(position+1)+'.result.token',
                                  'evidence':'exact source-created token equality; source storage/header operations in the full trace'})
                    break
        state={'database':row.get('state_after',{}).get('tables'),
               'browser':row.get('state_after',{}).get('browser'),'beans_and_aliases':row.get('heap_after',{'unmeasured':True})}
        result.append({'step':row.get('n',n),'source_producers':links or [{'unmeasured_or_initial_context':True}],
          'preceding_step_result':rows[n-2].get('result') if n>1 else {'initial_context':True},
          'consumer_request':wire,'actual_arguments':[r.get('bound_arguments') for r in row.get('requests',[])],
          'result':row.get('result'),'state_delta':delta(previous,state),'per_step_edges':row.get('edges'),
          'diagnostics':row.get('diagnostics',row.get('unresolved',[])),
          'first_loss':next((item for item in row.get('diagnostics',row.get('unresolved',[]))
             if any(term in item.lower() for term in ('unknown','unresolved','unsupported','budget','not modeled'))),None)})
        previous=state
    return {'schema':'producer-consumer/1','case':label,'steps':result}


def trace_document(document):
    """Finite report view, with exact decimal/type/alias facts outside wire payloads."""
    from analyzer.__main__ import serial
    from analyzer.native_storage import JavaList
    metadata=[];active={};seen={}
    def visit(value,path):
        if isinstance(value,Decimal):
            metadata.append({'path':path,'kind':'java.math.BigDecimal','exact':str(value),'scale':-value.as_tuple().exponent})
            number=float(value)
            return number if Decimal(str(number))==value else {'$decimal':str(value)}
        if isinstance(value,(dict,list,tuple)):
            if id(value) in active:return {'$cycle_ref':active[id(value)]}
            if id(value) in seen:metadata.append({'path':path,'alias_of':seen[id(value)]})
            else:seen[id(value)]=path
            active[id(value)]=path
            if isinstance(value,JavaList):metadata.append({'path':path,'kind':type(value).__name__,'flavor':value.flavor,
                'element_kinds':list(value.kinds),'order_known':value.order_known,'unmodifiable':getattr(value,'unmodifiable',False),'opaque':value.opaque})
            try:
                return {str(k):visit(v,path+'/'+str(k)) for k,v in value.items()} if isinstance(value,dict) else [visit(v,path+'/'+str(i)) for i,v in enumerate(value)]
            finally:active.pop(id(value))
        if value is None or type(value) in (str,bool,int,float):return value
        return serial(value)
    result=visit(document,'$');result['semantic_value_metadata']=metadata
    return result
