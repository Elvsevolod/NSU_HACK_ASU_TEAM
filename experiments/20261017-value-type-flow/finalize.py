"""Aggregate completed measurements only; never feed reference data to inference."""
from pathlib import Path
import collections,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2]
EXP=Path(__file__).parent
V=ROOT/'solutions/—_value-type-flow'
B=V/'benchmark'

def read(p):return json.loads(p.read_text())
def write(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def aggregate(path):
 r=read(path);assert r['run_complete'],'Do not measure a live checkpoint'
 steps=[s for sc in r['scenarios'].values() for s in sc['steps']];assert len(steps)==103
 fields=[{m.removeprefix('Unknown input: ') for a in s['alternatives'] for m in a['unresolved'] if m.startswith('Unknown input: ')} for s in steps]
 counter=collections.Counter()
 for s in steps:counter.update({issue['kind'] for a in s['alternatives'] for issue in a['operation_issues']})
 return {'steps':len(steps),'unknown_steps_any_alternative':sum(map(bool,fields)),
  'unknown_step_fields':sum(map(len,fields)),'steps_without_request':sum(not s['alternatives'] for s in steps),
  'operation_issue_steps':dict(sorted(counter.items())),
  'all_scenarios_partial':all(sc['analysis_status']!='complete_in_supported_model' for sc in r['scenarios'].values()),
  'interpretation':'Issue coverage counts repeated propagation, not precision or independent defects'},r

summary=read(B/'summary.json');assert summary['run_complete']
current,report=aggregate(B/'analysis-report.json')
parent,_=aggregate(ROOT/'solutions/—_http-json-collections/benchmark/analysis-report.json')
comparison={'parent_variant':15,'current_variant':16,'parent':read(ROOT/'solutions/—_http-json-collections/benchmark/summary.json'),
 'current':summary,'parent_inputs':parent,'current_inputs':current,
 'identical_full_submission':summary['submission_sha256']==read(ROOT/'solutions/—_http-json-collections/benchmark/summary.json')['submission_sha256'],
 'site_score':None,'universal_portability_proven':False}
write(B/'comparison.json',comparison);write(B/'coverage-summary.json',current)
write(B/'input-coverage.json',{'complete_measurement':True,'aggregate':current,
 'unknown_fields':[{'scenario':sid,'step':step['n'],'fields':sorted({m.removeprefix('Unknown input: ') for a in step['alternatives'] for m in a['unresolved'] if m.startswith('Unknown input: ')})}
  for sid,sc in report['scenarios'].items() for step in sc['steps'] if any(m.startswith('Unknown input: ') for a in step['alternatives'] for m in a['unresolved'])],
 'predictor_reads_this_file':False})
a=read(EXP/'baseline15-panel-v11.json');b=read(EXP/'candidate16-panel-v11.json')
assert len(a['cases'])==len(b['cases'])==27
changes=[]
for before,after in zip(a['cases'],b['cases']):
 assert before['source_sha256']==after['source_sha256'] and before['reference_sha256']==after['reference_sha256']
 if after['name']=='generic_shadowing_conservative':
  assert not after['missing'] and after['extra'] and after['warnings'] and all(o['approximate'] for o in after['outcomes'])
 else:assert not after['missing'] and not after['extra']
 diffs={rel:[before['relations'][rel]['iou'],after['relations'][rel]['iou']] for rel in before['relations'] if before['relations'][rel]!=after['relations'][rel]}
 if diffs:changes.append({'case':before['name'],'family':before['family'],'iou':diffs})
write(B/'mechanism-comparison.json',{'cases':27,'families':len(b['families']),'source_reference_hashes_equal':True,
 'all_candidate_relations_exact':False,'positive_cases_exact':26,'documented_generic_binding_limit_cases':1,'changes':changes,
 'limits':'Hand-selected small components; not a representative accuracy estimate. Empty relations untested.'})
for label in ('baseline15','candidate16'):shutil.copyfile(EXP/(label+'-panel-v11.json'),B/('mechanism-'+label+'.json'))
shutil.copyfile(EXP/'panel_v11.py',V/'checks/check_mechanisms_v11.py')
shutil.copyfile(ROOT/'solutions/—_http-json-collections/checks/missing-input-witness.json',V/'checks/missing-input-witness.json')
protected=read(EXP/'protected-manifest.json')
changed=[name for name,digest in protected.items() if not (ROOT/name).is_file() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
assert not changed,changed
write(B/'protected-files.json',{'checked':len(protected),'changed':changed,'previous_inputs_and_variants_preserved':True})
events=[json.loads(line) for line in (EXP/'deepseek-review.jsonl').read_text().splitlines() if line.strip()]
write(B/'deepseek-development.json',{'requested_model':'opencode/deepseek-v4.1-flash-free','variant':'max',
 'session_ids':sorted({e['sessionID'] for e in events if 'sessionID' in e}),
 'error_codes':[e.get('error',{}).get('data',{}).get('statusCode') for e in events if e.get('type')=='error'],
 'error_name':'FreeTierError','is_retryable':False,'substantive_reply_received':False,'delegated_edits':0,
 'new_runtime_edits_author':'Codex','parent_contains_previously_reviewed_DeepSeek_SQL_change':True,
 'fallback_model_used':False,'runtime_model_calls':len(report['model_calls'])})
write(V/'package-code-sha256.json',{'code/'+p.relative_to(V/'code').as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
 for p in sorted((V/'code').rglob('*')) if p.is_file() and not {'__pycache__','.pytest_cache'}&set(p.parts) and p.suffix!='.pyc'})
write(B/'verification-cache-check.json',read(EXP/'verification-cache-check.json'))
print(json.dumps({'summary':summary,'coverage':current,'changed_mechanism_families':len(changes)},ensure_ascii=False))
