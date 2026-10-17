"""Aggregate only completed predictions; references stay outside the builder."""
from pathlib import Path
import collections,hashlib,json,shutil

ROOT=Path(__file__).resolve().parents[2]
EXP=Path(__file__).parent
V=ROOT/'solutions/—_generic-type-substitution'
P=ROOT/'solutions/—_backed-collection-views'
B=V/'benchmark'


def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def coverage(path):
    report=read(path);assert report['run_complete']
    steps=[step for scenario in report['scenarios'].values() for step in scenario['steps']]
    assert len(steps)==103
    fields=[{msg.removeprefix('Unknown input: ') for alternative in step['alternatives']
        for msg in alternative['unresolved'] if msg.startswith('Unknown input: ')} for step in steps]
    issues=collections.Counter()
    for step in steps:issues.update({issue['kind'] for alternative in step['alternatives'] for issue in alternative['operation_issues']})
    return {'steps':103,'unknown_steps_any_alternative':sum(map(bool,fields)),
        'unknown_step_fields':sum(map(len,fields)),'steps_without_request':sum(not step['alternatives'] for step in steps),
        'operation_issue_steps':dict(sorted(issues.items())),
        'all_scenarios_partial':all(s['analysis_status']!='complete_in_supported_model' for s in report['scenarios'].values()),
        'interpretation':'Repeated propagation coverage, not precision or independent defect count'},report


summary=read(B/'summary.json')
current,report=coverage(B/'analysis-report.json');parent,_=coverage(P/'benchmark/analysis-report.json')
assert read(B/'verification.json')['passed']
write(B/'coverage-summary.json',current)
write(B/'comparison.json',{'parent_variant':17,'current_variant':18,'parent':read(P/'benchmark/summary.json'),
    'current':summary,'parent_inputs':parent,'current_inputs':current,
    'identical_full_submission':summary['submission_sha256']==read(P/'benchmark/summary.json')['submission_sha256'],
    'site_score':None,'universal_portability_proven':False})
write(B/'input-coverage.json',{'complete_measurement':True,'aggregate':current,'predictor_reads_this_file':False,
    'unknown_fields':[{'scenario':sid,'step':step['n'],'fields':sorted({msg.removeprefix('Unknown input: ')
        for alternative in step['alternatives'] for msg in alternative['unresolved'] if msg.startswith('Unknown input: ')})}
        for sid,scenario in report['scenarios'].items() for step in scenario['steps']
        if any(msg.startswith('Unknown input: ') for alternative in step['alternatives'] for msg in alternative['unresolved'])]})

before=read(EXP/'panel17.json');after=read(EXP/'panel18-final.json')
assert len(before['cases'])==len(after['cases'])==45
changes=[];limits=[]
for a,b in zip(before['cases'],after['cases']):
    assert (a['name'],a['source_sha256'],a['reference_sha256'])==(b['name'],b['source_sha256'],b['reference_sha256'])
    assert a['reference_fixed_before_prediction'] and b['reference_fixed_before_prediction']
    changed={relation:[a['relations'][relation]['iou'],b['relations'][relation]['iou']]
             for relation in b['relations'] if a['relations'][relation]!=b['relations'][relation]}
    if changed:changes.append({'case':a['name'],'family':b['family'],'iou':changed})
    if b['missing'] or b['extra']:
        assert b['name'] in ('generic_shadowing_conservative','view_stream_limit') and b['warnings']
        limits.append({'case':b['name'],'missing':b['missing'],'extra':b['extra']})
assert len(limits)==2 and len(changes)==5
write(B/'mechanism-comparison.json',{'cases':45,'families':len(after['families']),
    'references_and_sources_equal':True,'exact_edge_sets_before':38,'exact_edge_sets_after':43,
    'changes':changes,'remaining_limits':limits,
    'limits':'Manual small mechanism fixtures, not representative accuracy; empty relations untested.'})
shutil.copyfile(EXP/'panel17.json',B/'mechanism-baseline17.json')
shutil.copyfile(EXP/'panel18-final.json',B/'mechanism-candidate18.json')
selection=read(EXP/'petclinic.json');old_selection=read(P/'benchmark/petclinic.json')
assert selection['source_sha256']==old_selection['source_sha256']
shutil.copyfile(EXP/'petclinic.json',B/'petclinic.json')
a=read(EXP/'petclinic-body-corrected17.json');b=read(EXP/'petclinic-body-corrected18.json')
old=read(P/'benchmark/petclinic-body-graph.json')
assert a['passed'] and b['passed'] and a['source_sha256']==b['source_sha256']==old['source_sha256']
assert a['reference_sha256']==b['reference_sha256']==old['reference_sha256']
shutil.copyfile(EXP/'petclinic-body-corrected17.json',B/'petclinic-body-baseline17.json')
shutil.copyfile(EXP/'petclinic-body-corrected18.json',B/'petclinic-body-graph.json')
write(B/'petclinic-fixture-correction.json',{'changed':'Request JSON contains only id/name; removed unbranded internal __type__ marker from body.',
    'source_files_and_reference_edges_unchanged':True,'reference_sha256':b['reference_sha256'],
    'same_corrected_fixture_both_variants_passed':True,
    'invalid_initial_attempt_preserved_in_experiments':True,'full_http_graph_measured':False})

protected=read(EXP/'protected-manifest.json')
assert not any('—_polyglot-scenario-core' in name for name in protected)
changed=[name for name,digest in protected.items() if not (ROOT/name).is_file() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
assert not changed,changed
write(B/'protected-files.json',{'checked':len(protected),'changed':changed,
    'previous_inputs_and_variants_preserved':True,'parallel_variant_13_not_inspected_or_edited':True})

events=[json.loads(line) for line in (EXP/'deepseek-design.jsonl').read_text().splitlines() if line.strip()]
assert not any(e.get('type')=='text' for e in events)
write(B/'deepseek-development.json',{'launcher':'~/.local/bin/opencode-deepseek',
    'requested_model':'opencode/deepseek-v4.1-flash-free','variant':'max',
    'session_ids':sorted({e['sessionID'] for e in events if 'sessionID' in e}),
    'error_codes':[e.get('error',{}).get('data',{}).get('statusCode') for e in events if e.get('type')=='error'],
    'error_type':'FreeTierError','is_retryable':False,
    'provider_message':'Free tier can only be used from within OpenCode',
    'substantive_reply_received':False,'delegated_edits':0,'review_completed':False,
    'new_runtime_edits_author':'Codex','fallback_model_used':False,'reported_cost':None,
    'runtime_model_calls':len(report['model_calls']),'inherited_reviewed_DeepSeek_SQL_change':True})
write(B/'code-review.json',{'runtime_diff_read':True,'new_runtime_author':'Codex','frozen_parent':17,
    'tests_passed':1020,'inherited_test_files_changed':[],
    'guards':['declaration-owned nested bindings and imports','same-name class/method parameters and annotated parameters',
      'raw dependent/recursive/intersection bounds','generic arity, wildcard and source cycle diagnostics',
      'cache independence across instantiations and ordering','literal native annotation policy, comment/string/foreign-name rejection',
      'abstract/interface/nonstatic-member construction','primitive-null policy versus boxed/generic reference null'],
    'test_setup_corrections':['Qualified Map in the use-site descriptor instead of borrowing a schema file import; added negative test for the unqualified descriptor.',
      'Petclinic body now has real JSON id/name, not an unbranded internal type tag; both frozen17 and18 use the same corrected fixture with unchanged references.'],
    'limits':['Static substitution does not implement Java runtime checkcast or arbitrary boxed provenance',
      'Custom codecs, full JavaBeans and mapper/global settings are incomplete',
      'Source generic inheritance requires a unique acyclic path; wildcard/owner-generic contexts remain bounded',
      'View streams and the previous full JVM/framework/unknown-length heap limits remain open']})
write(V/'package-code-sha256.json',{'code/'+path.relative_to(V/'code').as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted((V/'code').rglob('*')) if path.is_file() and not {'__pycache__','.pytest_cache'}&set(path.parts) and path.suffix!='.pyc'})
print(json.dumps({'summary':summary,'coverage':current,'mechanism_changes':len(changes),'protected_files':len(protected)},ensure_ascii=False))
