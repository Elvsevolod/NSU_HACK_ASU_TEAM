"""Local acceptance with explicit failed/unmeasured transfer cases, never hidden-score claims."""
import gzip,hashlib,json
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads((V/path).read_text())


def main():
    checks={}
    meta=read('benchmark/final/metadata.json');manifest=read('benchmark/final/code-sha256.json')
    checks['submission_matches']=sha(V/'submission.json')==meta['submission_sha256']
    checks['measured_code_matches']=all(sha(V/'code'/name)==digest for name,digest in manifest.items())
    checks['format_all_eight']=not read('benchmark/final/format-check.json')['errors']
    checks['protected_inputs_and_old_variants']=read('benchmark/protected-integrity.json')['passed']
    repeat=read('benchmark/repeated-analysis-final.json')
    checks['repeat_same_index_same_answer']=all(r['matches_expected'] and r['submission_sha256']==meta['submission_sha256'] for r in repeat['runs'])
    checks['all_103_compared']=read('benchmark/comparisons/base--'+meta['stage']+'.json')['steps_compared']==103
    checks['document_values_wire_args_state_diagnostics']=read('benchmark/document-journey/checks.json')['passed']
    checks['document_mutations_rejected']=read('benchmark/document-journey/mutation-checks.json')['passed']
    checks['actor_and_singleton_actual_http_boundaries']=read('benchmark/boundary-wires/checks.json')['passed']
    checks['ranking_and_global_budget_unchanged']=read('development/scope-check.json')['passed']
    for profile in ('main','additional'):
        checks['strict_piggy_'+profile]=read('benchmark/real-final/'+profile+'/checks.json')['passed']
        checks['strict_piggy_semantic_'+profile]=read('benchmark/real-final/'+profile+'/semantic-checks.json')['passed']
        checks['strict_piggy_negative_'+profile]=read('benchmark/real-final/'+profile+'/mutations/summary.json')['passed']
    checks['legacy_v2_source_state']=read('benchmark/legacy-final/checks.json')['passed']
    cart=read('benchmark/cart-transfer-final/checks.json')
    checks['new_real_profile_frozen_and_boundary_visible']=cart['evaluation_completed'] and cart['frozen_inputs_unchanged'] and cart['new_holdout_success'] is False and bool(cart['first_loss']['source_diagnostic'])
    audit=read('benchmark/final/analysis-report-offline-audit.json')
    checks['offline_no_references']=not any(audit[k] for k in ('blocked_network','blocked_processes','blocked_reference_reads'))
    stage_checks={}
    for path in sorted((V/'development/stages').iterdir()):
        if not path.is_dir():continue
        expected=json.loads((path/'code-sha256.json').read_text())
        stage_checks[path.name]=all(sha(path/'code'/name)==digest for name,digest in expected.items())
    checks['immutable_stage_snapshots']=all(stage_checks.values())
    report=json.loads(gzip.decompress((V/'benchmark/final/analysis-report.json.gz').read_bytes()))
    answer=read('submission.json');steps=0;witness=[]
    for sid,scenario in report['scenarios'].items():
        union=set()
        for step in scenario['steps']:
            steps+=1
            edges={tuple(e[k] for k in ('source','relation','target')) for a in step['alternatives'] for e in a['edges']}
            union.update(edges)
            witness.append({'scenario':sid,'step':step['n'],'entries':sorted({a['entry'] for a in step['alternatives']}),
                'alternatives':len(step['alternatives']),
                'relations':{kind:sum(e[1]==kind for e in edges) for kind in ('executes','calls','remote','data')},
                'requests_with_actual_arguments':sum('bound_arguments' in r for a in step['alternatives'] for r in a['requests']),
                'outcomes':sorted({a['outcome'] for a in step['alternatives']})})
        saved={tuple(e[k] for k in ('source','relation','target')) for e in answer['scenarios'][sid]['edges']}
        checks['report_submission_'+sid]=union==saved
    checks['exactly_103_steps']=steps==103
    result={'passed':all(checks.values()),'checks':checks,'stages':stage_checks,'step_witness':witness,
      'limits':['This is local bounded acceptance, not universal product completion or hidden-test quality',
        'The new cart source profile fails at a documented unsupported library boundary',
        'Train Ticket search/payment dependent NL chains remain partial; the next Map loop is outside the no-op proof',
        'Historical stage timings that mix serialization are not a fair analysis-time comparison'],
      'deepseek_used':False,'target_apps_started':False,'model_calls':0,'external_llm_api_calls':0}
    (V/'benchmark/final/witness-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'checks':checks}));assert result['passed']


if __name__=='__main__':main()
