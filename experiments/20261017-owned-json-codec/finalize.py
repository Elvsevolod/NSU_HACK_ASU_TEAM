"""Completed aggregate evidence; no scenario-specific debugging or inference."""
from pathlib import Path
import collections,hashlib,json,shutil

ROOT=Path(__file__).resolve().parents[2]
EXP=Path(__file__).parent
V=ROOT/'solutions/0.66185_owned-json-codec'
P=ROOT/'solutions/0.66185_generic-type-substitution'
B=V/'benchmark'

def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def coverage(path):
    report=read(path);assert report['run_complete']
    steps=[step for scenario in report['scenarios'].values() for step in scenario['steps']]
    fields=[{msg.removeprefix('Unknown input: ') for alternative in step['alternatives']
             for msg in alternative['unresolved'] if msg.startswith('Unknown input: ')} for step in steps]
    issues=collections.Counter()
    for step in steps:issues.update({issue['kind'] for alternative in step['alternatives'] for issue in alternative['operation_issues']})
    return {'steps':len(steps),'unknown_steps_any_alternative':sum(map(bool,fields)),
        'unknown_step_fields':sum(map(len,fields)),'steps_without_request':sum(not step['alternatives'] for step in steps),
        'operation_issue_steps':dict(sorted(issues.items())),
        'all_scenarios_partial':all(s['analysis_status']!='complete_in_supported_model' for s in report['scenarios'].values()),
        'interpretation':'Propagation counts, not relation precision or independent defect counts'},report

summary=read(B/'summary.json');current,report=coverage(B/'analysis-report.json');parent,_=coverage(P/'benchmark/analysis-report.json')
assert read(B/'verification.json')['passed'] and read(B/'reproducibility.json')['passed']
assert '1067 passed' in (B/'tests.stdout.txt').read_text()
write(B/'coverage-summary.json',current)
write(B/'input-coverage.json',{'complete_measurement':True,'aggregate':current,'predictor_reads_this_file':False})
write(B/'comparison.json',{'parent_variant':18,'current_variant':19,'parent':read(P/'benchmark/summary.json'),
    'current':summary,'parent_inputs':parent,'current_inputs':current,
    'identical_full_submission':summary['submission_sha256']==read(P/'benchmark/summary.json')['submission_sha256'],
    'site_score':None,'universal_portability_proven':False})
panel=read(EXP/'panel-final-comparison.json')
assert panel['cases']==53 and panel['exact_edge_sets_before']==43 and panel['exact_edge_sets_after']==51
assert len(panel['changes'])==8 and len(panel['remaining_limits'])==2
write(B/'mechanism-comparison.json',panel)
shutil.copyfile(EXP/'panel18-final.json',B/'mechanism-baseline18.json')
shutil.copyfile(EXP/'panel19-final.json',B/'mechanism-candidate19.json')
for name,old in [('petclinic.json','petclinic.json'),('petclinic-body.json','petclinic-body-graph.json')]:
    a=read(EXP/name);b=read(P/'benchmark'/old);assert a['source_sha256']==b['source_sha256']
    if 'reference_sha256' in a:assert a['reference_sha256']==b['reference_sha256'] and a['passed']
    shutil.copyfile(EXP/name,B/old)
protected=read(EXP/'protected-manifest.json')
assert not any('—_polyglot-scenario-core' in name for name in protected)
changed=[name for name,digest in protected.items() if not (ROOT/name).is_file() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
assert not changed,changed
write(B/'protected-files.json',{'checked':len(protected),'changed':changed,
    'previous_inputs_and_variants_preserved':True,'parallel_variant_13_not_inspected_or_edited':True,
    'authorized_site_status_metadata_transition':'experiments/20261017-owned-json-codec/protected-site-status-18-transition.json'})
write(B/'deepseek-development.json',{'launcher':'~/.local/bin/opencode-deepseek','requested_model':'opencode/deepseek-v4.1-flash-free',
    'variant':'max','cli_version_checked':'1.19.3','new_API_attempt_in_variant19':False,
    'availability_evidence':'Frozen variant18 benchmark/deepseek-development.json: nonretryable403 FreeTierError before reply/edits',
    'provider_state_change_or_safe_fix_established':False,'reason_not_repeated':'No new availability evidence after nonretryable error; no busy retry',
    'substantive_reply_received':False,'delegated_edits':0,'review_completed':False,'new_runtime_edits_author':'Codex',
    'fallback_model_used':False,'runtime_model_calls':len(report['model_calls']),'inherited_reviewed_DeepSeek_SQL_change':True})
write(B/'code-review.json',{'runtime_diff_read':True,'frozen_parent':18,'tests_passed':1067,'new_tests':47,
    'new_independent_tests_against_frozen18':{'failed':32,'passed':15,'log':'experiments/20261017-owned-json-codec/independent-tests-baseline18.txt'},
    'inherited_test_files_changed':['tests/test_scalar_record_boundaries.py'],
    'test_change_reason':'Proven constructor-owned default codec now throws a known JsonMappingException bound for extra property. Stronger assertion requires abrupt completion and no approximation, rather than an unknown-policy warning.',
    'guards':['native exact constructor versus injected/source subclass/namesake','independent copy, aliases, caller-owned conservative joins',
      'unknown feature boolean, unsupported modules, escape and configuration after first use','primitive null versus boxed/reference null and omitted initializer',
      'checked read failure versus convertValue wrapper; namespace-correct catch and unknown exact exception subtype',
      'static enum constant value qualifier side effects and null receiver','business JSON metadata cannot forge a native codec',
      'unsupported setters/getters/annotations and incomplete payload projections never prove a codec failure',
      'version-dependent same-type convertValue aliases retained as unknown'],
    'limits':['Only two native Jackson2 DeserializationFeature flags; injected/custom/HTTP codec contexts remain unknown',
      'Full JavaBeans, custom codecs, JVM, generic casts and Map-view streams remain incomplete',
      'No full HTTP/security/Jackson execution oracle for a second real application; small panel is not representative portability evidence']})
write(V/'package-code-sha256.json',{'code/'+path.relative_to(V/'code').as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted((V/'code').rglob('*')) if path.is_file() and not {'__pycache__','.pytest_cache'}&set(path.parts) and path.suffix!='.pyc'})
print(json.dumps({'summary':summary,'coverage':current,'panel_exact':[43,51],'protected_files':len(protected)},ensure_ascii=False))
