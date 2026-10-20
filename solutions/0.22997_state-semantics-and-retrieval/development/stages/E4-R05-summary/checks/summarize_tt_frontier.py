"""Checker-side full-step comparison and source-proven payment/producer frontier."""
import argparse,gzip,hashlib,json
from pathlib import Path
from collections import Counter
V=Path(__file__).resolve().parents[1]


def read(stage):return json.loads(gzip.decompress((V/'benchmark/stages'/stage/'analysis-report.json.gz').read_bytes()))
def edges(step):return {(e['source'],e['relation'],e['target']) for a in step['alternatives'] for e in a['edges']}
def witness(a):
    return {**{k:a.get(k) for k in ('entry','ui_site','parameters','bindings','request','requests','responses','outcome','result','selected_objects')},
        'before_unknown_tables':(a.get('state_before') or {}).get('unknown_tables'),
        'after_unknown_tables':(a.get('state_after') or {}).get('unknown_tables'),
        'path_conditions':a.get('path_conditions'),'last_source_events':a.get('events',[])[-8:],
        'call_effects':a.get('call_effects'),'operation_issues':a.get('operation_issues'),
        'unresolved':a.get('unresolved'),
        'limits':'Warning order is not chronology. Alternative ordinals are pointers only, not cross-run path identity.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();before=read('G01-parent30');after=read(a.stage);rows=[]
    for sid in before['scenarios']:
        left=before['scenarios'][sid]['steps'];right=after['scenarios'][sid]['steps'];assert [s['n'] for s in left]==[s['n'] for s in right]
        for b,c in zip(left,right):
            eb,ec=edges(b),edges(c);changed=eb!=ec
            models={e.get('model_version') for x in c['alternatives'] for e in x.get('call_effects',[])}
            if changed and 'unknown-foreach-boundary/1' in models:
                reason='Known-empty inference is declined at unknown foreach; affected heap remains unknown and the path stops explicitly. Edges beyond incomplete producer are not restored manually.'
            elif changed and 'native-map-removal/1' in models:
                reason='Known route ordering/element types and source-generated accessor contracts let the six-group removal filter execute. Additional source/remote/data observations appear before the remaining frontier.'
            elif changed:reason='Source/contract completion changed the observations of incomplete paths. Exact removed/added tuples and source events are provided; hidden edge correctness is unmeasured.'
            else:reason='Same observed per-step graph; value/state/completion witnesses are compared independently.'
            row={'scenario':sid,'n':c['n'],'action':c['action'],'graph_changed':changed,'explanation':reason,
                'outcomes_before':dict(Counter(x['outcome'] for x in b['alternatives'])),
                'outcomes_after':dict(Counter(x['outcome'] for x in c['alternatives'])),
                'relations':{rel:{'added':sorted(e for e in ec-eb if e[1]==rel),'removed':sorted(e for e in eb-ec if e[1]==rel)} for rel in ('executes','calls','remote','data')},
                'after_witnesses':[witness(x) for x in c['alternatives']]}
            rows.append(row)
    probe_path=V/'benchmark/overnight/G13/tt-generated-setter-consumer/probes.json';probes=json.loads(probe_path.read_text())
    probe_summaries=[]
    for case in probes['cases']:
        probe_summaries.append({'name':case['name'],'wire':case['wire'],'outcomes':dict(Counter(x['outcome'] for x in case['alternatives'])),
            'results':[x['result'] for x in case['alternatives']],
            'frontier_diagnostics':sorted({w for x in case['alternatives'] for w in x['warnings'] if any(t in w.lower() for t in ('outside','unresolved','unknown','unmodeled','not modeled'))}),
            'complete_trace':'benchmark/overnight/G13/tt-generated-setter-consumer/probes.json'})
    ui='tt-challenge/targets/trainticket/ts-ui-dashboard/static/assets/js/client_order_list.js'
    source=V.parents[1]/ui
    result={'schema':'TT-frontier/31','stage':a.stage,'steps_compared':len(rows),'steps':rows,
        'isolated_probes':probe_summaries,'full_NL_search_booking_payment_chain_passed':False,
        'payment_UI_source':{'path':ui,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'method':'payMyOrder','lines':[112,151],
            'fields':{'orderId':'that.orderId assigned from source button item.id','tripId':'that.tripId assigned from source button item.trainNumber',
                      'userId':'not sent by this UI function','price':'button argument stored on view; not serialized into info',
                      'Authorization':'Bearer plus source sessionStorage client_token; requires actual login/token producer'},
            'wire_keys':['orderId','tripId'],'no_payload_augmentation':True},
        'remaining':['Known search reaches native six-group filter, then source Set<Ticket> equality/hash and further distance/list consumer semantics remain bounded frontiers.',
            'S6 state already contains unknown station/train_type and other joined tables after earlier admin input/authentication boundaries; G02 observer records first invalidation and propagation.',
            'Later NL booking/payment steps have no complete known search/booking producer. Isolated payment success on declared initial rows does not establish a full scenario chain.',
            'Default scheduler still has incomplete paths; observed-union is an approximation, and hidden E/C/R/D IoU is unavailable.'],
        'comparison_method':'Exact E/C/R/D per step and full source/value witnesses; no alignment by alternative ordinal.',
        'targets_started':False,'oracle_read_by_inference':False}
    assert len(rows)==103
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'steps':len(rows),'changed':sum(r['graph_changed'] for r in rows),'full_NL_chain':False}))


if __name__=='__main__':main()
