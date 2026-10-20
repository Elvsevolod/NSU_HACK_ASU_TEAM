"""Cart v4: keep every v3 duty and validate complete legal producer orders."""
from copy import deepcopy
from itertools import permutations
from pathlib import Path
import json
from cart_evaluator_v3 import evaluate as evaluate_v3

V=Path(__file__).resolve().parents[1]


def wire(request):
    # Branch-specific source provenance is not an HTTP byte. It remains in the
    # raw trace and is checked through producer certificates by normalize_nl.
    return {k:deepcopy(v) for k,v in (request or {}).items() if k!='provenance'}


def evaluate(trace):
    projected=deepcopy(trace)
    for step in projected.get('steps',[]):
        if step.get('request'):step['request']=wire(step['request'])
        for alt in step.get('alternatives',[]):
            if alt.get('request'):alt['request']=wire(alt['request'])
            for event in alt.get('requests',[]):
                if event.get('request'):event['request']=wire(event['request'])
    result=evaluate_v3(projected);errors=result['errors']
    oracle=json.loads((V/'validation_inputs/shopping-cart/oracle-v3.json').read_text())
    expected={s['n']:s for s in oracle['steps']}
    orders=[]
    for step in trace.get('steps',[]):
        if step.get('n') not in (1,8):continue
        alts=step.get('alternatives',[]);wanted=expected[step['n']]['rows']
        legal=set(permutations(row['id'] for row in wanted))
        seen={tuple(row.get('id') for row in alt['result']) for alt in alts
              if isinstance(alt.get('result'),list) and all(isinstance(row,dict) for row in alt['result'])}
        if seen!=legal:errors.append(f"{step['n']}: all source-legal encounter orders required")
        if any(a.get('exploration',{}).get('complete') is not True for a in alts):
            errors.append(f"{step['n']}: producer/order exploration is not complete")
        orders.append({'step':step['n'],'legal':[list(x) for x in sorted(legal)],'observed':[list(x) for x in sorted(seen)],
            'reason':'PaymentJpaRepository.findByOrderId has no ORDER BY/Sort; two matching rows'})
    result.update(schema='cart-evaluation/4',passed=not errors,legal_orders=orders,
        inherited_obligations='all v3 required edges, executes, native arguments, state/refusal and server-body checks',
        metadata_delta='transport equality ignores only diagnostic provenance; per-branch producer certificates remain required by NL normalization')
    return result
