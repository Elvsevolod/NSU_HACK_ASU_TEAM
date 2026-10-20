"""Honest failed-transfer evaluation; required-edge subset is NOT a precision oracle."""
import argparse,hashlib,json
from pathlib import Path
from evidence import equal,chain
V=Path(__file__).resolve().parents[1]


def subset(expected,actual):
    if isinstance(expected,dict):return isinstance(actual,dict) and all(k in actual and subset(v,actual[k]) for k,v in expected.items())
    return equal(expected,actual)


def main():
    p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    assert not args.output.exists();root=V/'validation_inputs/shopping-cart'
    frozen=json.loads((V/'development/cart-freeze-v2.json').read_text())
    immutable=all(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest for name,digest in frozen['files'].items())
    oracle=json.loads((root/'oracle-v1.json').read_text());trace=json.loads((args.trace/'explicit.json').read_text());nl=json.loads((args.trace/'nl.json').read_text())
    results=[];actual=set();witness=[]
    for wanted,row in zip(oracle['steps'],trace['steps']):
        alternatives=row.get('alternatives',[])
        for a in alternatives:actual.update(tuple(e) for e in a['edges'])
        statuses=[a['responses'][-1].get('status') for a in alternatives if a.get('responses')]
        check={'n':wanted['n'],'status':all(equal(wanted['status'],s) for s in statuses) if 'status' in wanted and statuses else None,
               'producer_available':bool(alternatives) if wanted['n'] in (2,3,4,5) else None}
        if 'rows' in wanted:check['response_rows']=bool(alternatives) and all(isinstance(a['result'],list) and len(a['result'])==len(wanted['rows']) and
            all(any(subset(e,r) for r in a['result']) for e in wanted['rows']) for a in alternatives)
        if 'result_fields' in wanted:check['response_fields']=bool(alternatives) and all(subset(wanted['result_fields'],a['result']) for a in alternatives)
        if wanted.get('ambiguous'):
            proposals=nl['steps'][wanted['n']-1]['alternatives']
            check['no_arbitrary_unique_choice']=len({a['entry'] for a in proposals})!=1 or not proposals
        results.append(check)
        for a in alternatives:witness.append({'n':row['n'],'wire':row['request'],**a})
    required={tuple(e) for e in oracle['required_edges']};first=trace['steps'][0]['alternatives'][0]
    primary=next((message for message in first['warnings'] if message.startswith('unsupported stream operation:') and message.endswith(' toList')),None)
    result={'passed':False,'evaluation_completed':True,'frozen_inputs_unchanged':immutable,
       'new_holdout_success':False,'first_loss':{'kind':'unsupported Java Stream.toList terminal operation','source_diagnostic':primary,
           'producer':'PaymentPersistenceAdapter.findByOrderId','consequence':'controller receives unknown list; selected payment/order IDs cannot feed subsequent Requests'},
       'steps':results,'required_edge_recall_only':{relation:{'required':len([e for e in required if e[1]==relation]),
            'observed':len([e for e in required&actual if e[1]==relation]),'precision':None,'iou':None} for relation in ('executes','calls','remote','data')},
       'limits':['Frozen v1 oracle is a required-edge subset; full graph precision and IoU are unmeasured',
                 'Stream.toList, PATCH transport, java.time/Jackson and complete security/bootstrap are not claimed supported by this failed profile',
                 'No guessed response identifiers, tokens, success statuses or source-specific fixes were inserted'],
       'targets_started':False,'source_commit':oracle['source_commit']}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    args.output.with_name('cart-witnesses.json').write_text(json.dumps(chain(witness,'cart/failed-explicit-transfer'),indent=2)+'\n')
    assert immutable and primary and not result['new_holdout_success']


if __name__=='__main__':main()
