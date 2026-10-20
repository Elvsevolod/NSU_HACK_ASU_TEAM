"""Version31 acceptance: actual positive cart plus bounded TT frontier and regressions."""
import gzip,hashlib,json
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(path):return json.loads((V/path).read_text())


def main():
    meta=read('benchmark/final/metadata.json');manifest=read('benchmark/final/code-sha256.json');checks={}
    actual={p.relative_to(V/'code').as_posix():sha(p) for p in (V/'code').rglob('*') if p.is_file() and not {'__pycache__','.pytest_cache'}&set(p.parts)}
    checks['exact_measured_code_manifest']=actual==manifest
    checks['submission_matches']=sha(V/'submission.json')==meta['submission_sha256']
    checks['format_all_eight']=not read('benchmark/final/format-check.json')['errors']
    checks['protected_inputs_and_old_variants']=read('benchmark/protected-integrity.json')['passed']
    repeat=read('benchmark/repeated-analysis-final.json')
    checks['prepared_exact_prediction_and_typed_witnesses']=repeat['passed'] and all(r['submission_sha256']==meta['submission_sha256'] for r in repeat['runs'])
    checks['prepared_report_only_delta']=read('benchmark/prepared-report-only-delta.json')['passed']
    checks['all_103_compared']=read('benchmark/comparisons/G01-parent30--'+meta['stage']+'.json')['steps_compared']==103
    checks['preceding_stage_compared']=read('benchmark/comparisons/G13-live-route-filter--'+meta['stage']+'.json')['steps_compared']==103
    checks['scope_rank_budget_and_no_default_G06']=read('development/scope-check.json')['passed']
    checks['S6_causal_observer_preserves_prediction']=read('benchmark/overnight/G02/causal-ledger-v2/causal-ledger.json')['observer_prediction_unchanged']
    root='benchmark/regressions-final/'
    checks['all_independent_commands_succeeded']=read(root+'results.json')['passed']
    for profile in ('main','additional'):
        for name in ('checks.json','semantic-checks.json','mutations/summary.json'):
            checks[profile+'/'+name]=read(root+profile+'/'+name)['passed']
    for name in ('legacy/checks.json','document/checks.json','document/mutation-checks.json','boundary-wires/checks.json','cart/checks.json','cart/mutations/summary.json'):
        checks[name]=read(root+name)['passed']
    unit=read('benchmark/overnight/G14/exact-final-all-unit-checkers/run.json')
    checks['unit_and_checker_actual_exit']=unit['returncode']==0 and not unit['timed_out'] and unit['code_hashes']==manifest
    audit=read('benchmark/final/analysis-report-offline-audit.json')
    checks['offline_observed_no_reference_network_process_reads']=not any(audit[k] for k in ('blocked_network','blocked_processes','blocked_reference_reads'))
    checks['fresh_holdout_honestly_not_run']=read('benchmark/holdout-availability.json')['status']=='not_run'
    stages={}
    for path in sorted((V/'development/stages').iterdir()):
        expected=json.loads((path/'code-sha256.json').read_text())
        stages[path.name]=all(sha(path/'code'/n)==d for n,d in expected.items())
    checks['stage_snapshots_unchanged']=all(stages.values())
    report=json.loads(gzip.decompress((V/'benchmark/final/analysis-report.json.gz').read_bytes()));answer=read('submission.json');steps=[];proofs=[]
    for sid,scenario in report['scenarios'].items():
        union=set()
        for step in scenario['steps']:
            edges={tuple(e[k] for k in ('source','relation','target')) for alt in step['alternatives'] for e in alt['edges']};union.update(edges)
            steps.append({'scenario':sid,'step':step['n'],'alternatives':len(step['alternatives']),
                'relations':{k:sum(e[1]==k for e in edges) for k in ('executes','calls','remote','data')},
                'outcomes':sorted({a['outcome'] for a in step['alternatives']})})
            proofs.extend(e for a in step['alternatives'] for e in a['call_effects'] if e.get('model_version')=='native-map-removal/1')
        saved={tuple(e[k] for k in ('source','relation','target')) for e in answer['scenarios'][sid]['edges']}
        checks['report_matches_submission_'+sid]=union==saved
    checks['exactly_103_steps']=len(steps)==103
    checks['live_six_group_filter_observed']=any(e.get('iterations')==6 and 'result_values' in e for e in proofs)
    frontier=read('benchmark/tt-frontier.json');checks['TT_frontier_and_UI_wire_visible']=frontier['steps_compared']==103 and frontier['full_NL_search_booking_payment_chain_passed'] is False and frontier['payment_UI_source']['wire_keys']==['orderId','tripId']
    cart_oracle=read('validation_inputs/shopping-cart/oracle-v3.json')
    result={'schema':'final-acceptance/31','passed':all(checks.values()),'checks':checks,'stages':stages,'steps':steps,
        'cart_per_step_executes_obligations':sum(len(s.get('required_executes',[])) for s in cart_oracle['steps']),
        'limits':['TT full search→booking→payment NL chain remains incomplete at documented source/unknown-state boundaries.',
            'Cart is a tuned real-source regression in an explicit application-after-authentication slice; security/JWT is unmeasured.',
            'Cart/Piggy required edges are incomplete subsets, not full graph precision/IoU. Document/inventory MREs have exact source oracles.',
            'No genuinely fresh complete real-application holdout package was available. G06 is a rejected integration experiment.',
            'Local acceptance does not imply universal Java/Spring/JVM support or hidden-test correctness.'],
        'deepseek_used':False,'target_apps_started':False,'model_calls':0,'external_llm_api_calls':0}
    (V/'benchmark/final/witness-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'checks':checks}));assert result['passed']


if __name__=='__main__':main()
