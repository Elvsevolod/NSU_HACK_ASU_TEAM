"""Checker-only cart contract v3. Never imported by inference or request grounding."""
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit
import json
from evidence import equal

V=Path(__file__).resolve().parents[1]
INPUTS=V/'validation_inputs/shopping-cart'


def subset(wanted,actual):
    return isinstance(actual,dict) and all(k in actual and subset(v,actual[k]) for k,v in wanted.items()) if isinstance(wanted,dict) else equal(wanted,actual)


def rows_match(wanted,actual):
    if not isinstance(actual,list) or len(wanted)!=len(actual):return False
    used=set()
    for row in wanted:
        matches=[i for i,item in enumerate(actual) if i not in used and subset(row,item)]
        if len(matches)!=1:return False
        used.add(matches[0])
    return True


def expected_tables(n):
    result=json.loads((INPUTS/'checker-initial-rows-v2.json').read_text())
    if n>=2:
        next(r for r in result['payment-service.payments'] if r['id']==21)['status']='REFUNDED'
        next(r for r in result['order-service.orders'] if r['id']==11)['status']='PENDING'
    return result


def table_equal(expected,actual):
    return isinstance(actual,dict) and expected.keys()==actual.keys() and all(rows_match(expected[k],actual[k]) for k in expected)


def evaluate(trace):
    oracle=json.loads((INPUTS/'oracle-v3.json').read_text());errors=[];coverage=set()
    def require(condition,message):
        if not condition:errors.append(message)
    require(trace.get('entry_boundary')=='application_after_authentication' and trace.get('security_evaluated') is False,'declared post-authentication slice missing')
    steps=trace.get('steps',[])
    require([s.get('n') for s in steps]==list(range(1,9)),'exact unique steps 1..8 required')
    by_step={s.get('n'):s for s in steps}
    for want in oracle['steps']:
        n=want['n'];row=by_step.get(n,{})
        require(table_equal(expected_tables(max(1,n-1)),(row.get('state_before') or {}).get('tables')),f'{n}: state before differs')
        require(table_equal(expected_tables(n),(row.get('state_after') or {}).get('tables')),f'{n}: state after differs, including untouched rows')
        alternatives=row.get('alternatives',[])
        if want.get('ambiguous'):
            require(not alternatives,f'{n}: ambiguous action executed a handler')
            require(all(equal((row.get('state_before') or {}).get(key),(row.get('state_after') or {}).get(key)) for key in ('tables','database_rows','unknown_tables','browser','clock')),f'{n}: ambiguous action changed application state')
            continue
        require(bool(alternatives),f'{n}: no executed alternative')
        request=row.get('request') or {}
        require(request.get('deployment')==want['module'] and request.get('method')==want['method'] and request.get('url')==want['path'],f'{n}: actual root request differs')
        if n in (2,3,4,5):
            lineage=row.get('producer') or {}
            require(lineage.get('producer_step')==1 and type(lineage.get('producer_step')) is int and lineage.get('source')=='actual root result',f'{n}: producer provenance missing')
            require(type(lineage.get('payment_id')) is int and lineage.get('payment_id')==21 and type(lineage.get('order_id')) is int and lineage.get('order_id')==11,f'{n}: producer IDs/types differ')
        for i,a in enumerate(alternatives):
            label=f'{n}/{i}'
            require(a.get('outcome') in ('returned','HTTP error response'),label+': incomplete/exceptional analysis')
            events=a.get('requests',[]);responses=a.get('responses',[])
            roots=[e for e in events if e.get('id')==1]
            root=[r for r in responses if r.get('request')==1]
            require(len(roots)==1 and equal(roots[0].get('request'),request),label+': root request pairing differs')
            require(len(roots)==1 and roots[0].get('entry')==want['required_executes'][0],label+': root controller entry differs')
            require(len(roots)==1 and equal(roots[0].get('bound_arguments'),want['bound_arguments']),label+': root bound argument type/value differs')
            require(all(type(e.get('id')) is int for e in events) and len({e.get('id') for e in events})==len(events),label+': duplicate or wrongly typed request id')
            require(len(root)==1 and equal(root[0].get('status'),want['status']),label+': root response status/pairing differs')
            require(len({r.get('request') for r in responses})==len(responses) and all(type(r.get('request')) is int and r.get('request') in {e.get('id') for e in events} for r in responses),label+': duplicate/unpaired response')
            result=a.get('result')
            require(len(root)==1 and 'body' in root[0] and equal(root[0]['body'],result),label+': root body/result pairing differs')
            if 'rows' in want:require(rows_match(want['rows'],result),label+': response row bijection/typed fields differ')
            if 'result_fields' in want:require(subset(want['result_fields'],result),label+': response fields/types differ')
            if 'error_code' in want:require(isinstance(result,dict) and result.get('error_code',result.get('errorCode'))==want['error_code'],label+': error code missing/wrong')
            require(table_equal(expected_tables(n),a.get('state_after',{}).get('tables')),label+': alternative state differs')
            require(not a.get('state_after',{}).get('unknown_tables'),label+': unknown database state')
            edges={tuple(e) if not isinstance(e,dict) else (e['source'],e['relation'],e['target']) for e in a.get('edges',[])};coverage.update(edges)
            for target in want['required_executes']:require(any(e[1]=='executes' and e[2]==target for e in edges),label+': missing source execute '+target)
            obligations=[]
            for e in oracle['required_edges']:
                source,rel,target=e
                if n in (1,8) and ('getByOrder' in source or 'GetPaymentsByOrder' in source or 'findByOrderId' in source or 'PaymentPersistenceMapper#toDomain' in source):obligations.append(e)
                if n in (3,5,6) and rel=='data' and '#findById(' in source:obligations.append(e)
                if n==2 and not ('getByOrder' in source or 'GetPaymentsByOrder' in source or 'findByOrderId' in source or 'PaymentPersistenceMapper#toDomain' in source):obligations.append(e)
            for e in obligations:require(tuple(e) in edges,label+': missing per-step required edge '+str(e))
            remotes=[e for e in edges if e[1]=='remote']
            sent=[e for e in events if e.get('id')!=1]
            if n==2:
                expected=tuple(next(e for e in oracle['required_edges'] if e[1]=='remote'))
                require(expected in edges,label+': refund remote missing on this step')
                remote=want['remote']
                require(len(sent)==1,label+': exact one refund remote request required')
                if len(sent)==1:
                    event=sent[0];wire=event.get('request') or {}
                    require(event.get('entry')==remote['entry'] and equal(event.get('bound_arguments'),remote['bound_arguments']),label+': remote controller/typed arguments differ')
                    require(all(equal(wire.get(k),remote[k]) for k in ('deployment','method','url')),label+': remote deployment/address differs')
                    server=[r for r in responses if r.get('request')==event.get('id')]
                    require(len(server)==1 and equal(server[0].get('status'),remote['status']) and subset(remote['result_fields'],server[0].get('body')),label+': actual server response/body missing despite client Void')
            else:require(not remotes and not sent,label+': unexpected remote on this step')
            operations=a.get('data_operations',[])
            writes=[o for o in operations if o.get('datastore_event') and any(t in o.get('operation','').lower() for t in ('save','insert','update','delete','flush'))]
            if n!=2:require(not writes,label+': write after read/refusal')
            else:
                for table in want['writes']:require(any(o.get('resource','').endswith('.'+table) for o in writes),label+': required write missing '+table)
    required={tuple(e) for e in oracle['required_edges']}
    return {'schema':'cart-evaluation/3','passed':not errors,'errors':errors,
            'required_edge_subset':{rel:{'required':sum(e[1]==rel for e in required),'observed':sum(e[1]==rel for e in required&coverage),'precision':None,'iou':None} for rel in ('executes','calls','remote','data')},
            'scope':oracle['scope'],'new_holdout_success':False,'targets_started':False}
