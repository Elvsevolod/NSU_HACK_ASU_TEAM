"""Completed aggregate measurements, never a source of predictor inputs."""
from pathlib import Path
import collections,hashlib,json,shutil

ROOT=Path(__file__).resolve().parents[2]
EXP=Path(__file__).parent
V=ROOT/'solutions/—_backed-collection-views'
P=ROOT/'solutions/—_value-type-flow'
B=V/'benchmark'


def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def coverage(path):
    report=read(path)
    assert report['run_complete']
    steps=[step for scenario in report['scenarios'].values() for step in scenario['steps']]
    assert len(steps)==103
    fields=[{msg.removeprefix('Unknown input: ') for alternative in step['alternatives']
             for msg in alternative['unresolved'] if msg.startswith('Unknown input: ')} for step in steps]
    issues=collections.Counter()
    for step in steps:issues.update({issue['kind'] for alternative in step['alternatives'] for issue in alternative['operation_issues']})
    return {'steps':len(steps),'unknown_steps_any_alternative':sum(map(bool,fields)),
            'unknown_step_fields':sum(map(len,fields)),
            'steps_without_request':sum(not step['alternatives'] for step in steps),
            'operation_issue_steps':dict(sorted(issues.items())),
            'all_scenarios_partial':all(s['analysis_status']!='complete_in_supported_model' for s in report['scenarios'].values()),
            'interpretation':'Repeated propagation coverage, not precision or independent defect count'},report


summary=read(B/'summary.json')
current,report=coverage(B/'analysis-report.json')
parent,_=coverage(P/'benchmark/analysis-report.json')
assert read(B/'verification.json')['passed']
write(B/'coverage-summary.json',current)
write(B/'comparison.json',{'parent_variant':16,'current_variant':17,'parent':read(P/'benchmark/summary.json'),
    'current':summary,'parent_inputs':parent,'current_inputs':current,
    'identical_full_submission':summary['submission_sha256']==read(P/'benchmark/summary.json')['submission_sha256'],
    'site_score':None,'universal_portability_proven':False})
write(B/'input-coverage.json',{'complete_measurement':True,'aggregate':current,'predictor_reads_this_file':False,
    'unknown_fields':[{'scenario':sid,'step':step['n'],'fields':sorted({msg.removeprefix('Unknown input: ')
        for alternative in step['alternatives'] for msg in alternative['unresolved'] if msg.startswith('Unknown input: ')})}
        for sid,scenario in report['scenarios'].items() for step in scenario['steps']
        if any(msg.startswith('Unknown input: ') for alternative in step['alternatives'] for msg in alternative['unresolved'])]})

before=read(EXP/'panel16.json');after=read(EXP/'panel17-final.json')
assert len(before['cases'])==len(after['cases'])==38
changes=[]
limits=[]
for a,b in zip(before['cases'],after['cases']):
    assert (a['name'],a['source_sha256'],a['reference_sha256'])==(b['name'],b['source_sha256'],b['reference_sha256'])
    assert a['reference_fixed_before_prediction'] and b['reference_fixed_before_prediction']
    changed={relation:[a['relations'][relation]['iou'],b['relations'][relation]['iou']]
             for relation in b['relations'] if a['relations'][relation]!=b['relations'][relation]}
    if changed:changes.append({'case':a['name'],'family':b['family'],'iou':changed})
    if b['missing'] or b['extra']:
        assert b['name'] in ('generic_shadowing_conservative','view_stream_limit') and b['warnings']
        limits.append({'case':b['name'],'missing':b['missing'],'extra':b['extra']})
assert len(limits)==2 and len(changes)==9
write(B/'mechanism-comparison.json',{'cases':38,'families':len(after['families']),
    'references_and_sources_equal':True,'exact_edge_sets_before':sum(not c['missing'] and not c['extra'] for c in before['cases']),
    'exact_edge_sets_after':36,'changes':changes,'remaining_limits':limits,
    'limits':'Manual small mechanism fixtures, not representative accuracy; empty relations untested. Unordered Map reference permits either first key.'})
shutil.copyfile(EXP/'panel16.json',B/'mechanism-baseline16.json')
shutil.copyfile(EXP/'panel17-final.json',B/'mechanism-candidate17.json')
for name in ('petclinic.json','petclinic-body-graph.json'):
    observed=read(EXP/name);original=read(P/'benchmark'/name)
    assert observed['source_sha256']==original['source_sha256']
    shutil.copyfile(EXP/name,B/name)

protected=read(EXP/'protected-manifest.json')
assert not any('—_polyglot-scenario-core' in name for name in protected),'Parallel work is outside this manifest'
changed=[name for name,digest in protected.items() if not (ROOT/name).is_file() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
assert not changed,changed
write(B/'protected-files.json',{'checked':len(protected),'changed':changed,
    'previous_inputs_and_variants_preserved':True,'parallel_variant_13_not_inspected_or_edited':True})

attempts=[]
for name in ('deepseek-review','deepseek-followup','deepseek-tests'):
    events=[json.loads(line) for line in (EXP/(name+'.jsonl')).read_text().splitlines() if line.strip()]
    native_tools=[event['part'] for event in events if event.get('type')=='tool_use']
    first=native_tools[0] if native_tools else None
    attempts.append({'name':name,'session_ids':sorted({event['sessionID'] for event in events if 'sessionID' in event}),
        'text_events':sum(event.get('type')=='text' for event in events),
        'finish_reasons':[e['part'].get('reason') for e in events if e.get('type')=='step_finish'],
        'error_codes':[e.get('error',{}).get('data',{}).get('statusCode') for e in events if e.get('type')=='error'],
        'first_native_tool':first.get('tool') if first else None,
        'first_tool_input':first.get('state',{}).get('input') if first else None,
        'reported_cost':sum(e['part'].get('cost',0) for e in events if e.get('type')=='step_finish')})
assert not (V/'code/tests/test_map_view_extra_cases.py').exists()
write(B/'deepseek-development.json',{'launcher':'~/.local/bin/opencode-deepseek','requested_model':'opencode/deepseek-v4.1-flash-free',
    'variant':'max','attempts':attempts,'substantive_reply_received':False,'delegated_edits':0,
    'review_completed':False,'new_runtime_edits_author':'Codex','fallback_model_used':False,
    'inherited_reviewed_DeepSeek_SQL_change':True,'runtime_model_calls':len(report['model_calls'])})
write(B/'code-review.json',{'runtime_diff_read':True,'new_runtime_author':'Codex','frozen_parent':16,
    'independent_tests_passed':972,'test_changes':{
      'test_operation_diagnostics.py':'Unsupported keySet boundary changed to unsupported spliterator because keySet is now supported; category assertion remains strict.',
      'test_map_view_json.py':'Unknown HTTP read uses conservative Engine; a direct Engine intentionally asks for path alternatives otherwise.',
      'test_map_view_boundaries.py':'Corrected test spelling to the existing unsupported_map_mutation category.'},
    'guards':['native ownership, JSON forgery and copied backing','Integer/Long and Character/String equality',
      'unknown order and duplicate-value removals','iterator failures and unsupported mutation recovery',
      'heap aliases, caller writes and JSON-ignored fields','copy early break, colliding keys, dependent writes and generic pollution'],
    'unresolved_boundaries':['View streams and codecs','Generic reference casts: mismatch diagnosed, exact Java cast timing not claimed',
      'Full object equality callbacks and floating boxing','Plain-list unknown-length heap joins','Full JVM/framework execution']})
write(V/'package-code-sha256.json',{'code/'+p.relative_to(V/'code').as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted((V/'code').rglob('*')) if p.is_file() and not {'__pycache__','.pytest_cache'}&set(p.parts) and p.suffix!='.pyc'})
print(json.dumps({'summary':summary,'coverage':current,'mechanism_changes':len(changes),'protected_files':len(protected)},ensure_ascii=False))
