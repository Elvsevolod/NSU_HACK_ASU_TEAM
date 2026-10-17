import json,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
sessions=['ses_eb6f94d7bffemBx9NDig7Fba6n','ses_eb6dcd0baffe2SC2Z99o3vwHF4']
result={}
for session in sessions:
 path=root/(session+'-export.json')
 env={**os.environ,'OPENCODE_PERMISSION':json.dumps({'edit':'deny','bash':'deny','task':'deny','external_directory':'deny'})}
 with path.open('w') as out,path.with_suffix('.stderr.txt').open('w') as err:
  completed=subprocess.run([str(Path.home()/'.local/bin/opencode-deepseek'),'export',session],env=env,stdout=out,stderr=err,timeout=60)
 assert completed.returncode==0
 data=json.loads(path.read_text());messages=[m['info'] for m in data['messages'] if m['info']['role']=='assistant']
 models=sorted({m['providerID']+'/'+m['modelID'] for m in messages})
 assert models==['opencode/deepseek-v4.1-flash-free'],models
 result[session]={'models':models,'reported_cost':sum(m.get('cost',0) for m in messages),'assistant_messages':len(messages),'variant_from_runner':'max'}
logs={}
for name in ['map-review','dispatch-review','sql-parentheses','dispatch-boundaries-review']:
 rows=[json.loads(line) for line in (root/(name+'.jsonl')).read_text().splitlines() if line.strip()]
 edits=[r for r in rows if r.get('part',{}).get('tool') in ('edit','write','apply_patch') and r['part'].get('state',{}).get('status')=='completed']
 logs[name]={'events':len(rows),'completed_edits':len(edits),'sessions':sorted({r['sessionID'] for r in rows if 'sessionID' in r}),
   'finishes':[r['part']['reason'] for r in rows if r.get('type')=='step_finish'],
   'provider_errors':[{'type':r.get('type'),'status_code':r.get('error',{}).get('data',{}).get('statusCode')} for r in rows if r.get('type')=='error']}
assert logs['map-review']['completed_edits']==0 and logs['dispatch-review']['completed_edits']==0
report={'sessions':result,'logs':logs,
 'accepted_delegated_implementation':'Only the balanced parenthesis SQL RHS parser change in analyzer/project.py and tests/test_query_parentheses.py; whole diff and extra AND/NULL regressions independently verified',
 'accepted_review_findings':['Annotation strings must not be parsed as Java keyword modifiers','Map shallow copy, collection typing, cycles and state joins require independent tests'],
 'rejected_review_findings':['Foreign wildcard imports do not legally displace java.lang unambiguously','A source generic superclass can be overridden by the substituted signature','Fully qualified Integer already supported'],
 'all_other_new_code_by':'Codex',
 'unavailable_review':'Fresh dispatch-boundaries-review failed HTTP403 FreeTierError (non-retryable); no completed review, no paid fallback',
 'permissions':'read-only consultations; SQL edit permission restricted to the two accepted files; shell/task/external_directory denied',
 'published_or_uploaded':False}
(root/'final-deepseek-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
