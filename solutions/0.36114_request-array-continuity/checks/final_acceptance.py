"""Post-hoc regression witnesses. Scenario coordinates never enter inference."""
import gzip
import hashlib
import json
from pathlib import Path

VARIANT=Path(__file__).resolve().parents[1]
ROOT=VARIANT.parents[1]


def key(edge):return tuple(edge[k] for k in ('source','relation','target'))


def main():
    final=VARIANT/'benchmark/final'
    report=json.loads(gzip.decompress((final/'analysis-report.json.gz').read_bytes()))
    answer=json.loads((VARIANT/'submission.json').read_text())
    counts={};steps=[]
    for sid,scenario in report['scenarios'].items():
        observed={key(edge) for step in scenario['steps'] for alternative in step['alternatives'] for edge in alternative['edges']}
        expected={key(edge) for edge in answer['scenarios'][sid]['edges']}
        assert observed==expected,sid
        counts[sid]={kind:sum(edge[1]==kind for edge in expected) for kind in ('executes','calls','remote','data')}
        for step in scenario['steps']:
            steps.append({'scenario':sid,'step':step['n'],'action':step['action'],
                'entries':sorted({a['entry'] for a in step['alternatives']}),
                'outcomes':sorted({a['outcome'] for a in step['alternatives']})})
    payments=[]
    for sid,n in [('S1',10),('S2',8),('S2',13),('S3',12),('S3',13),('S5',10),('S6',13),('S7',6)]:
        step=report['scenarios'][sid]['steps'][n-1]
        assert step['alternatives']
        for row in step['alternatives']:
            assert row['entry'].endswith('InsidePaymentController#pay(inside_payment.entity.PaymentInfo,org.springframework.http.HttpHeaders)')
        payments.append({'scenario':sid,'step':n,'action':step['action'],
            'alternatives':[{k:a[k] for k in ('entry','ui_site','request','requests','result','outcome')} for a in step['alternatives']]})
    record_checks={}
    for sid,n,suffix in [('S1',13,'#findByOrderId('),('S1',14,'#findAssuranceByOrderId('),('S7',11,'#findByOrderId('),('S6',14,'AdminOrderController#getAllOrders(')]:
        alts=report['scenarios'][sid]['steps'][n-1]['alternatives']
        assert alts and all(suffix in a['entry'] for a in alts),(sid,n)
        record_checks[sid+'/'+str(n)]=sorted({a['entry'] for a in alts})
    partial=report['scenarios']['S0']['steps'][4]['alternatives']
    assert partial
    for alternative in partial:
        args=alternative['requests'][0]['bound_arguments']
        dto=next(a['value'] for a in args if a['name']=='qi')
        assert dto['state']==1 and dto['enableStateQuery'] is True
    gold=json.loads((ROOT/'tt-challenge/gold/S0.json').read_text())
    block=gold['scenarios']['S0']
    golden={('scenario:S0','executes',method) for method in block['methods']}
    golden.update((source,relation,target) for relation in ('calls','remote','data') for source,target in block[relation])
    actual={key(edge) for edge in answer['scenarios']['S0']['edges']}
    difference={kind:{'fp':sorted(e for e in actual-golden if e[1]==kind),
                      'fn':sorted(e for e in golden-actual if e[1]==kind)} for kind in counts['S0']}
    (final/'S0-errors.json').write_text(json.dumps(difference,indent=2)+'\n')
    (final/'payment-request-witnesses.json').write_text(json.dumps(payments,ensure_ascii=True,indent=2)+'\n')
    result={'passed':True,'steps':len(steps),'per_scenario_relations':counts,'entry_overview':steps,
        'all_step_graph_unions_match_submission':True,'public_payment_entries':8,
        'preserved_related_reads_and_admin':record_checks,'partial_dto_explicit_fields_preserved':True,
        'submission_sha256':hashlib.sha256((VARIANT/'submission.json').read_bytes()).hexdigest(),
        'limits':['TT assertions cover handler and value regressions, not hidden graph correctness',
            'Remaining TT search/list ambiguity and missing client storage are reported as unresolved',
            'Public payment entry correctness alone does not prove successful payment for an NL-created order']}
    (final/'witness-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('entry_overview','per_scenario_relations')}))


if __name__=='__main__':main()
