"""Corrupt actual explicit/NL traces before normalization, never repair predictions."""
import argparse,hashlib,json
from copy import deepcopy
from pathlib import Path
from cart_evaluator_v4 import evaluate
from check_cart_profile import normalize_nl


def main():
    p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    assert not args.output.exists();args.output.mkdir(parents=True);rows=[]
    for profile in ('explicit','nl'):
        path=args.trace/(profile+'.json');original=json.loads(path.read_text())
        normalize=normalize_nl if profile=='nl' else lambda x:x
        assert evaluate(normalize(original))['passed'],profile+' positive must pass before mutation'
        names=['missing-step','duplicate-step','wrong-root-entry','wrong-bound-id','wrong-bound-type',
            'missing-server-body','wrong-server-total','wrong-remote-port','wrong-remote-entry','wrong-remote-argument',
            'missing-server-mapper','missing-server-total','missing-remote-edge','lost-status','swapped-response-ids',
            'foreign-row','write-after-refusal','ambiguous-handler','missing-state-before','lost-scope','wrong-body-id']
        if profile=='nl':names+=['lost-producer-binding','wrong-producer-reference','unresolved-producer']
        else:names+=['lost-producer','wrong-producer-id']
        for name in names:
            t=deepcopy(original);steps=t['steps'];a=steps[1]['alternatives'][0]
            key='state_after'
            if name=='missing-step':steps.pop(2)
            elif name=='duplicate-step':steps[2]['n']=2
            elif name=='wrong-root-entry':a['requests'][0]['entry']='method:order-service:OrderController#getById(Long)'
            elif name=='wrong-bound-id':a['requests'][0]['bound_arguments'][0]['value']=True
            elif name=='wrong-bound-type':a['requests'][0]['bound_arguments'][0]['declared_type']='java.lang.String'
            elif name=='missing-server-body':next(r for r in a['responses'] if r['request']==2).pop('body')
            elif name=='wrong-server-total':next(r for r in a['responses'] if r['request']==2)['body']['total']=0
            elif name=='wrong-remote-port':a['requests'][1]['request']['url']='http://localhost:8084/api/orders/11/revert-payment'
            elif name=='wrong-remote-entry':a['requests'][1]['entry']=a['requests'][0]['entry']
            elif name=='wrong-remote-argument':a['requests'][1]['bound_arguments'][0]['value']=12
            elif name.startswith('missing-server-'):
                target='OrderHttpMapper#' if name.endswith('mapper') else 'Order#total()'
                a['edges']=[e for e in a['edges'] if target not in (e['target'] if isinstance(e,dict) else e[2])]
            elif name=='missing-remote-edge':a['edges']=[e for e in a['edges'] if (e['relation'] if isinstance(e,dict) else e[1])!='remote']
            elif name=='lost-status':steps[4]['alternatives'][0]['responses'][-1]['status']=200
            elif name=='swapped-response-ids':a['responses'][0]['request'],a['responses'][1]['request']=a['responses'][1]['request'],a['responses'][0]['request']
            elif name=='foreign-row':a[key]['tables']['payment-service.payments'][2]['amount']=0
            elif name=='write-after-refusal':steps[4]['alternatives'][0]['data_operations']=deepcopy(a['data_operations'])
            elif name=='ambiguous-handler':steps[6]['alternatives']=[deepcopy(a)]
            elif name=='missing-state-before':
                if profile=='nl':steps[3]['alternatives'][0].pop('state_before')
                else:steps[3].pop('state_before')
            elif name=='lost-scope':t.pop('entry_boundary')
            elif name=='wrong-body-id':a['result']['id']=22
            elif name=='lost-producer-binding':a['bindings'].pop('id')
            elif name=='wrong-producer-reference':a['bindings']['id']['reference']='history[0].result[1].id'
            elif name=='unresolved-producer':a['bindings']['id']['resolved']=False
            elif name=='lost-producer':steps[1].pop('producer')
            elif name=='wrong-producer-id':steps[1]['producer']['payment_id']=22
            result=evaluate(normalize(t))
            rows.append({'profile':profile,'mutation':name,'rejected':not result['passed'],'errors':result['errors'],
                'mutated_trace_sha256':hashlib.sha256(json.dumps(t,sort_keys=True).encode()).hexdigest()})
    result={'passed':all(r['rejected'] for r in rows),'mutations':rows,
        'inputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.trace.glob('*.json')},
        'targets_started':False,'mutated_before_nl_normalization':True}
    (args.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'mutations':len(rows),'accepted_negatives':[r['mutation'] for r in rows if not r['rejected']]}))
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
