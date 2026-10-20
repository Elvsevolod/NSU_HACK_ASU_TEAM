"""Version 3 regression evaluator; required edges remain an incomplete subset."""
import argparse,hashlib,json,re
from copy import deepcopy
from pathlib import Path
from cart_evaluator_v4 import evaluate,wire
from evidence import equal
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from analyzer.history_agreement import agree_completed,observation
from analyzer.history_join import common_wire_bag
V=Path(__file__).resolve().parents[1]


def normalize_nl(trace):
    result={k:trace.get(k) for k in ('entry_boundary','security_evaluated')};result['steps']=[]
    result['normalization_schema']='cart-nl-order-aware/4'
    journal=[]
    producer=None
    def value_at(reference,certificate):
        tokens=re.findall(r'[A-Za-z_]+|\d+',reference)
        if not tokens or tokens.pop(0)!='history':return None
        try:
            source=journal[int(tokens.pop(0))]
            if not certificate or certificate.get('step')!=source['n'] or certificate.get('exploration',{}).get('complete') is not True:return None
            alts=source['alternatives']
            if not agree_completed(alts,lambda a:True):return None
            candidates=[a for a in alts if a.get('entry')==certificate.get('entry') and observation(a)==certificate.get('digest')]
            bag=common_wire_bag([a.get('result') for a in alts])
            if bag is not None and all(equal(alts[0].get('selected_objects',[]),a.get('selected_objects',[])) for a in alts[1:]):
                merged={'result':bag,'selected_objects':alts[0].get('selected_objects',[]),'entry':alts[0].get('entry')}
                if merged['entry']==certificate.get('entry') and observation(merged)==certificate.get('digest'):candidates.append(merged)
            values=[]
            for candidate in candidates:
                value=candidate
                for token in tokens:value=value[int(token)] if isinstance(value,list) else value[token]
                values.append(value)
            return values[0] if values and all(equal(values[0],v) for v in values[1:]) else None
        except (KeyError,IndexError,TypeError,ValueError):return None
    for step in trace.get('steps',[]):
        alts=deepcopy(step.get('alternatives',[]));row={'n':step['n'],'alternatives':alts}
        for a in alts:
            a['edges']=[(e['source'],e['relation'],e['target']) if isinstance(e,dict) else e for e in a.get('edges',[])]
            a.pop('producer',None)
        if alts:
            if step['n']==1:
                def selected(a):
                    approved=[item for item in a['result'] if isinstance(item,dict) and item.get('status')=='APPROVED'] if isinstance(a.get('result'),list) else []
                    if len(approved)!=1 or any(type(approved[0].get(k)) is not int for k in ('id','orderId')) or not isinstance(a.get('entry'),str):return None
                    return {'id':approved[0]['id'],'orderId':approved[0]['orderId'],'entry':a['entry']}
                agreement=agree_completed(alts,selected)
                producer=agreement['value'] if agreement else None
            for a in alts:
                if step['n'] in (2,3,4,5) and producer:
                    binding=a.get('bindings',{}).get('id',{})
                    actual=value_at(binding.get('reference',''),binding.get('producer_observation'))
                    expected=producer.get('orderId') if step['n']==4 else producer.get('id')
                    if binding.get('source')=='history' and binding.get('resolved') is True and type(actual) is int and equal(actual,expected) and equal(a.get('parameters',{}).get('id'),actual):
                        a['producer']={'producer_step':1,'payment_id':producer.get('id'),'order_id':producer.get('orderId'),'source':'actual root result','reference':binding['reference']}

            for name in ('request','state_before','state_after','producer'):
                values=[wire(a.get(name)) if name=='request' else a.get(name) for a in alts]
                row[name]=values[0] if all(equal(values[0],v) for v in values[1:]) else {'unknown':True}
            lineages=[a.get('producer') for a in alts]
            if all(isinstance(value,dict) and all(equal(value.get(k),lineages[0].get(k)) for k in ('producer_step','payment_id','order_id','source')) for value in lineages):
                row['producer']={k:lineages[0][k] for k in ('producer_step','payment_id','order_id','source')}
                row['producer']['reference_alternatives']=[value['reference'] for value in lineages]
        else:
            row.update(state_before=step.get('state_before'),state_after=step.get('state_after'))
        result['steps'].append(row)
        journal.append({'n':step['n'],'alternatives':alts})
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();root=V/'validation_inputs/shopping-cart'
    frozen=json.loads((V/'development/cart-historical30/cart-freeze-v2.json').read_text())
    unchanged=all(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest for name,digest in frozen['files'].items())
    explicit=json.loads((a.trace/'explicit.json').read_text());nl=json.loads((a.trace/'nl.json').read_text())
    results={'explicit':evaluate(explicit),'nl':evaluate(normalize_nl(nl))}
    result={'schema':'cart-profile/4','passed':unchanged and all(r['passed'] for r in results.values()),
      'frozen_v1_inputs_unchanged':unchanged,'profiles':results,'new_holdout_success':False,'targets_started':False,
      'oracle_sha256':hashlib.sha256((root/'oracle-v3.json').read_bytes()).hexdigest(),
      'limits':['Required source-edge subset, not complete graph precision/IoU.','Cart is a tuned regression profile, not fresh holdout.','JWT/security/bootstrap are outside the explicit application boundary.']}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'failures':{k:len(r['errors']) for k,r in results.items()}}))
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
