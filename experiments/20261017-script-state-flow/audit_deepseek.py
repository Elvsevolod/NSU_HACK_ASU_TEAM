import json,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
sessions=['ses_eb730b67effe8rk9Bh69ehFmpH','ses_eb71fc6ccffeBYVMqjApklF6R6','ses_eb71250a1ffeohyipZPyoIUjp2']
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
for name in ['global-review','script-vars','script-vars-small','scope-review','flow-review']:
 rows=[json.loads(line) for line in (root/(name+'.jsonl')).read_text().splitlines() if line.strip()]
 edits=[r for r in rows if r.get('part',{}).get('tool') in ('edit','write','apply_patch') and r['part'].get('state',{}).get('status')=='completed']
 assert not edits
 logs[name]={'events':len(rows),'sessions':sorted({r['sessionID'] for r in rows if 'sessionID' in r}),
  'completed_edits':0,'finishes':[r['part']['reason'] for r in rows if r.get('type')=='step_finish'],
  'tool_errors':[{'tool':r['part']['tool'],'error':r['part']['state'].get('error','')[:200]} for r in rows if r.get('part',{}).get('state',{}).get('status')=='error']}
logs['script-vars']['completion']='reason=length, 32000 reasoning, no implementation'
logs['script-vars-small']['completion']='reason=length, 32000 reasoning, no implementation'
logs['flow-review']['completion']='no response/events within900s; own process group terminated by bounded runner, returncode -15; not completed review'
report={'sessions':result,'logs':logs,'all_new_runtime_and_test_code_by':'Codex','accepted_finding':'prototype-changing __proto__ cannot be a safe object-literal initializer; independently reproduced and fixed',
 'rejected_findings':['block-function collision already disabled binding','named-function-expression own-name shadow already blocked'],
 'permissions':'read-only consultations; implementation attempt limited to two files but no edits; shell/task/external_directory denied','published_or_uploaded':False}
(root/'final-deepseek-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
