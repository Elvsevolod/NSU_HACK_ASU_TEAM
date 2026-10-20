"""Version 3 regression evaluator; required edges remain an incomplete subset."""
import argparse,hashlib,json,re
from copy import deepcopy
from pathlib import Path
from cart_evaluator_v3 import evaluate
from evidence import equal
V=Path(__file__).resolve().parents[1]


def normalize_nl(trace):
    result={k:trace.get(k) for k in ('entry_boundary','security_evaluated')};result['steps']=[]
    journal=[]
    producer=None
    def value_at(reference):
        tokens=re.findall(r'[A-Za-z_]+|\d+',reference)
        if not tokens or tokens.pop(0)!='history':return None
        value=journal
        try:
            for token in tokens:value=value[int(token)] if isinstance(value,list) else value[token]
            return value
        except (KeyError,IndexError,TypeError,ValueError):return None
    for step in trace.get('steps',[]):
        alts=deepcopy(step.get('alternatives',[]));row={'n':step['n'],'alternatives':alts}
        for a in alts:
            a['edges']=[(e['source'],e['relation'],e['target']) if isinstance(e,dict) else e for e in a.get('edges',[])]
        if alts:
            first=alts[0]
            if step['n']==1 and isinstance(first.get('result'),list):
                approved=[item for item in first['result'] if isinstance(item,dict) and item.get('status')=='APPROVED']
                if len(approved)==1:producer=approved[0]
            for a in alts:
                if step['n'] in (2,3,4,5) and producer:
                    binding=a.get('bindings',{}).get('id',{})
                    actual=value_at(binding.get('reference',''))
                    expected=producer.get('orderId') if step['n']==4 else producer.get('id')
                    if binding.get('source')=='history' and binding.get('resolved') is True and type(actual) is int and equal(actual,expected) and equal(a.get('parameters',{}).get('id'),actual):
                        a['producer']={'producer_step':1,'payment_id':producer.get('id'),'order_id':producer.get('orderId'),'source':'actual root result','reference':binding['reference']}

            for name in ('request','state_before','state_after','producer'):
                values=[a.get(name) for a in alts]
                row[name]=values[0] if all(equal(values[0],v) for v in values[1:]) else {'unknown':True}
        else:
            row.update(state_before=step.get('state_before'),state_after=step.get('state_after'))
        result['steps'].append(row)
        journal.append({'result':alts[0].get('result'),'selected_objects':alts[0].get('selected_objects',[]) } if len(alts)==1 else {})
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();root=V/'validation_inputs/shopping-cart'
    frozen=json.loads((V/'development/cart-historical30/cart-freeze-v2.json').read_text())
    unchanged=all(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest for name,digest in frozen['files'].items())
    explicit=json.loads((a.trace/'explicit.json').read_text());nl=json.loads((a.trace/'nl.json').read_text())
    results={'explicit':evaluate(explicit),'nl':evaluate(normalize_nl(nl))}
    result={'schema':'cart-profile/3','passed':unchanged and all(r['passed'] for r in results.values()),
      'frozen_v1_inputs_unchanged':unchanged,'profiles':results,'new_holdout_success':False,'targets_started':False,
      'oracle_sha256':hashlib.sha256((root/'oracle-v3.json').read_bytes()).hexdigest(),
      'limits':['Required source-edge subset, not complete graph precision/IoU.','Cart is a tuned regression profile, not fresh holdout.','JWT/security/bootstrap are outside the explicit application boundary.']}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'failures':{k:len(r['errors']) for k,r in results.items()}}))
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
