"""Reconcile measured historical, ablation and observer facts; no answer generation."""
import json
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def main():
    out=V/'benchmark/overnight/G02/causal-ledger-v2';assert not out.exists();out.mkdir()
    read=lambda path:json.loads((V/path).read_text())
    old=read('benchmark/overnight/G02/historical-evidence/causal-ledger.json')
    events=read('benchmark/overnight/G02/causal-parent30/invalidations.json')['events']
    observer=read('benchmark/overnight/G02/causal-parent30/submission.json')['scenarios']['S6']
    baseline=read('benchmark/stages/G01-parent30/submission.json')['scenarios']['S6'];assert observer==baseline
    first={}
    for schema,table in [('ts_station','station'),('ts_train','train_type')]:
        i=next(i for i,e in enumerate(events) if e['kind']=='invalidate' and [schema,table] in e.get('new_unknown',[]))
        end=next(j for j in range(i+1,len(events)) if events[j]['kind']=='request_end')
        join=next((j for j in range(end+1,len(events)) if events[j]['kind']=='join_states' and [schema,table] in events[j].get('after_unknown',[])),None)
        first[table]={'first_invalidation_event':i,'invalidation':events[i],'containing_request_event':end,'request':events[end],
                      'first_following_join_event':join,'join':events[join] if join is not None else None,
                      'classification':'analysis-boundary fallback widens possible writable closure; not an observed datastore write'}
    ablation=read('benchmark/comparisons/G01-parent30--G02-bulk-contract-only.json')
    budget=read('benchmark/overnight/G02/isolated-order-completion-counters/results/results.json')
    result={**old,'schema':'S6-causal-ledger/2','observer_prediction_unchanged':True,'first_unknown_operations':first,
      'single_change_ablation':{'scope':'Only exact-arity standard Collection removeAll/retainAll consumer contract on immutable parent30; no unknown-loop/order/scheduler/budget changes.',
       'input':'development/stages/G02-bulk-contract-only/scope.json','comparison':'benchmark/comparisons/G01-parent30--G02-bulk-contract-only.json',
       'S6_steps':[row for row in ablation['steps'] if row['scenario']=='S6']},
      'isolated_budget_categories':{mode:{label:value['outcomes'] for label,value in variants.items()} for mode,variants in budget['cases'].items()},
      'paired_controls':['benchmark/overnight/G03/unknown-foreach-tests','benchmark/overnight/G04','benchmark/overnight/G02/isolated-order-completion-counters','benchmark/overnight/G06/residual-state-pilot-v5'],
      'interpretation':['Six historical union removals first occur at C1 step8, on incomplete paths; no hidden per-edge truth is known.',
        'Twelve step1 removals persist at step7; per-step eighteen is not union six.',
        'Primary station/train_type widening is addressable at observer events9/122; conservative fallback and join propagate it into later search inputs. Widening is distinct from SQL writes and from genuinely unknown authentication/input.',
        'Single-descriptor ablation changes search observations and removes additional step8 edges; it is not an isolated score fix.',
        'With correct HashSet membership unchanged, separate diagnostic reserves produce four returned/four thrown instead of two/two on commuting and effectful MREs. Two budget boundaries remain. Throwing callback case remains five thrown. No scheduler change accepted.',
        'G03 blocks opaque foreach from fabricated empty; G04 preserves bulk operand type. G13 additionally resolves default OrderColumn case/element kinds and source-generated accessor contracts; the live six-group filter is reached.',
        'All scenario values still come from source and declared inputs. No converter edge is restored manually.'],
      'remaining':['Default scheduler still shares order and completion reserve; negative G06 integration decision retained.',
        'Full TT producer chain still has unsupported custom Ticket equality/hash and additional arithmetic/consumer frontiers. G13 traces and final full103 comparisons record exact remaining states.',
        'The hidden S6 golden graph is unavailable; local evidence cannot label each removed edge correct/incorrect.']}
    (out/'causal-ledger.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    text='''# S6: measured causal ledger\n\nHistorical base→C1 first removes six union edges at search step8. Twelve step1 edges remain present at passenger-login step7. These are incomplete path observations, not hidden-gold judgements.\n\nThe observer preserves the exact parent30 S6 prediction. First unknown station is event9, request-end11; first unknown train_type is event122. Both start in Engine.run's AnalysisBoundary fallback of the corresponding admin write entry; the following joins carry unknown tables forward. No SQL write is established by these invalidation events. Authentication/input uncertainty and abstraction widening remain separate facts.\n\nA parent30 copy changing only removeAll/retainAll consumer descriptors has a separate full103 comparison. It does not recover the six historical converter edges. Correct HashSet membership remains unchanged in the separate-counter diagnostic: commuting/effectful cases expand two returned+two thrown to four+four, while still stopping two paths. This demonstrates budget coupling, without establishing that larger/separate reserves are a correct product fix.\n\nKnown/opaque iteration, bulk operand types, commuting versus effectful orders, throws, native arrays versus Lists and generated accessors have independent source fixtures. G13 fixes SQL OrderColumn lookup and preserves element kinds; a source-proven six-group live filter now executes. The remainder of the TT chain still needs custom object-set equality/hash and further value-flow semantics.\n\nExact tuples, source locations, constraints, observer event pointers, commands, statuses and immutable stage comparisons are in causal-ledger.json and linked run directories. No warning ordering or alternative numeric index is used as chronology or semantic path identity.\n'''
    (out/'causal-ledger.md').write_text(text)
    print(json.dumps({'observer_equal':True,'union_removed':len(old['union_removed']),'step1_retained_step7':len(old['step1_removed_but_retained_step7']),'first_events':{k:v['first_invalidation_event'] for k,v in first.items()}}))


if __name__=='__main__':main()
