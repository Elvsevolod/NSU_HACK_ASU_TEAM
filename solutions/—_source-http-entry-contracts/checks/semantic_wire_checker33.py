"""Independent typed transport/SQL witnesses, never an inference input."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from urllib.parse import quote


def identity(value,bindings):
    return deepcopy(bindings.get(value['$identity'])) if isinstance(value,dict) and '$identity' in value else deepcopy(value)


def decimal(value):
    if type(value) in (str,int):return str(value)
    if type(value) is bool:return str(value).lower()
    if not isinstance(value,dict) or not value.get('__symbol__'):return None
    width={'byte':8,'Byte':8,'short':16,'Short':16,'int':32,'Integer':32,'long':64,'Long':64}.get(value.get('__type__','').removeprefix('java.lang.'))
    if width is None or 'non_null' not in value.get('__constraints__',[]):return None
    return {'__symbol__':value['__symbol__']+':decimal','__type__':'String','__constraints__':['non_null'],
        '__integral_text__':True,'__integral_bits__':width,'__integral_origin__':deepcopy(value)}


def text(parts):
    merged=[]
    for part in parts:
        if part=='':continue
        if isinstance(part,str) and merged and isinstance(merged[-1],str):merged[-1]+=part
        else:merged.append(part)
    if all(isinstance(part,str) for part in merged):return ''.join(merged)
    if len(merged)==1:return merged[0]
    digest=hashlib.sha256(json.dumps(merged,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()[:16]
    return {'__symbol__':'text-'+digest,'__type__':'String','__text_parts__':merged}


def text_match(parts,actual,bindings):
    values=[decimal(identity(part,bindings)) for part in parts]
    return None not in values and actual==text(values)


def observed_key(value):
    if value is None:return ('null',)
    if type(value) in (str,int,bool):return (type(value).__name__,value)
    if type(value) is float:return ('number',str(Decimal(str(value)).normalize()))
    if isinstance(value,dict):
        if value in ({'unknown':True},{'missing':True}):return None
        items=tuple((key,observed_key(child)) for key,child in sorted(value.items()))
        return None if any(child is None for _,child in items) else ('object',None,items)
    if isinstance(value,list):
        items=tuple(observed_key(child) for child in value)
        return None if None in items else ('array',None,items)
    return None


def observation(alternative):
    value=observed_key({key:alternative.get(key) for key in ('result','selected_objects')})
    return hashlib.sha256(json.dumps(value,ensure_ascii=True,separators=(',',':')).encode()).hexdigest() if value is not None else None


def request_matches(wanted,event,responses,bindings,match):
    actual=event.get('request')
    if not isinstance(actual,dict) or event.get('entry')!=wanted['target']:return False
    for key in ('deployment','method'):
        if actual.get(key)!=wanted[key]:return False
    path=[decimal(identity(part,bindings)) for part in wanted['path']]
    query={key:[decimal(identity(part,bindings)) for part in values] for key,values in wanted.get('query',{}).items()}
    if None in path or any(None in values for values in query.values()):return False
    if actual.get('path')!=path or actual.get('query')!=query or actual.get('query_complete') is not True:return False
    if actual.get('headers')!=wanted.get('headers',{}):return False
    if not match(wanted.get('body',{'missing':True}),actual.get('body'),bindings):return False
    if 'authority' in wanted:
        pieces=[wanted['authority']]
        for part in path:pieces.extend(['/',quote(part,safe='') if isinstance(part,str) else part])
        if query:
            first=True
            for key,values in query.items():
                for part in values:
                    pieces.extend([('?' if first else '&')+quote(key,safe='')+'=',quote(part,safe='') if isinstance(part,str) else part]);first=False
        if actual.get('url')!=text(pieces):return False
    reply=[row for row in responses if row.get('request')==event.get('id')]
    if len(reply)!=1 or reply[0].get('status')!=wanted['status']:return False
    if 'response_body' in wanted:
        wire=event.get('transport_response',{})
        if wire.get('request')!=event.get('id') or wire.get('status')!=wanted['status'] or not match(wanted['response_body'],wire.get('body'),bindings):return False
    bound={row['name']:row for row in event.get('bound_arguments',[])}
    for name,spec in wanted.get('bound',{}).items():
        row=bound.get(name,{})
        if row.get('declared_type')!=spec['declared_type'] or row.get('native_kind')!=spec['native_kind'] or not match(spec['value'],row.get('value'),bindings):return False
    return True


def operations_match(wanted,alternative,bindings,match):
    actual=alternative.get('data_operations',[])
    if len(wanted)!=len(actual):return False
    for expected,event in zip(wanted,actual):
        if event.get('sql_emitted') is not True or event.get('datastore_event') is not True or event.get('uncertain_write') is not False:return False
        if any(event.get(key)!=expected[key] for key in ('method','resource','operation','request_id','argument_kinds')):return False
        if not match(expected['arguments'],event.get('arguments'),bindings):return False
    return True


def history_matches(wanted,alternative,prior,bindings,match):
    outer=next((row for row in alternative.get('requests',[]) if row.get('id')==1),{})
    params={row['name']:row for row in outer.get('bound_arguments',[])}
    provenance=outer.get('request',{}).get('provenance',{}).get('bindings',{})
    for name,spec in wanted.get('history',{}).items():
        number=spec['step'];earlier=prior[number-1]['alternatives'] if 0<number<=len(prior) else []
        if not earlier or any(row.get('outcome')!='returned' or row.get('exploration',{}).get('complete') is not True for row in earlier):return False
        digests=[observation(row) for row in earlier]
        if not digests[0] or any(d!=digests[0] for d in digests):return False
        proof=provenance.get(name,{});seen=proof.get('producer_observation',{})
        if proof.get('source')!='history' or proof.get('resolved') is not True or proof.get('reference')!=spec['reference']:return False
        if seen.get('step')!=number or seen.get('entry')!=spec['entry'] or seen.get('digest')!=digests[0] or seen.get('exploration',{}).get('complete') is not True:return False
        bound=params.get(name,{})
        if bound.get('native_kind')!='Long' or not match(spec['value'],bound.get('value'),bindings):return False
    return True


def evaluate_wire(wanted,alternative,prior,bindings,match):
    requests=alternative.get('requests',[]);responses=alternative.get('responses',[])
    outer=wanted['outer'];remotes=wanted['remotes']
    request_order=(len(requests)==1+len(remotes) and [r.get('id') for r in requests]==list(range(1,len(requests)+1))
        and len(responses)==len(requests) and all(type(row.get('request')) is int for row in responses)
        and sorted(row['request'] for row in responses)==list(range(1,len(requests)+1)))
    outer_ok=request_order and request_matches(outer,requests[0],responses,bindings,match)
    remote_ok=request_order and all(request_matches(spec,event,responses,bindings,match) for spec,event in zip(remotes,requests[1:]))
    bound={row['name']:row for row in requests[0].get('bound_arguments',[])} if requests else {}
    kinds_ok=all(name in bound and bound[name].get('declared_type')==spec['declared_type'] and
        bound[name].get('native_kind')==spec['native_kind'] and match(spec['value'],bound[name].get('value'),bindings)
        for name,spec in wanted.get('bound',{}).items())
    remote_edges=all(spec['target'] is None or any(event.get('edge')=={'source':spec['source'],'relation':'remote','target':spec['target']}
        and event.get('values',{}).get('target_request')==row['id'] for event in alternative.get('events',[])) for spec,row in zip(remotes,requests[1:]))
    return {'outer_wire':outer_ok,'remote_wire_and_response':remote_ok and remote_edges,'native_binding':kinds_ok,
        'ordered_sql':operations_match(wanted['operations'],alternative,bindings,match),
        'history_origin':history_matches(wanted,alternative,prior,bindings,match),
        'error_message_origin':error_origins(alternative.get('result'),requests)}


def error_origins(value,requests):
    if isinstance(value,list):return all(error_origins(child,requests) for child in value)
    if not isinstance(value,dict):return True
    if '__feign_error_message__' not in value:return all(error_origins(child,requests) for child in value.values())
    fact=value['__feign_error_message__']
    event=next((row for row in requests if row.get('id')==fact.get('request_id')),None)
    if event is None:return False
    sent=event.get('request',{});reply=event.get('transport_response',{})
    if fact.get('request')!={key:sent.get(key) for key in ('deployment','method','url','path','query','query_complete')}:return False
    if fact.get('client_method')!=sent.get('provenance',{}).get('client_method'):return False
    if reply.get('status')!=fact.get('status') or reply.get('body')!=fact.get('response_body') or fact.get('status',0)<400:return False
    digest=hashlib.sha256(json.dumps(fact,sort_keys=True,ensure_ascii=True).encode()).hexdigest()[:20]
    return value.get('__symbol__')=='feign-message-'+digest
