"""Local export audit; never copies exports into the submission archive."""
import json
import os
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parent
sessions={
    'html-and-arguments': ('ses_eb7f2e361ffehHE6scB7mo1hI2',['html-strategy','html-row','row-arguments','creation-review']),
    'projection-review': ('ses_eb7d5a00fffeQPZ4rSxtTgHB2s',['projection-review','response-arrays']),
    'array-copy': ('ses_eb7c0622affenh3lXQmlgk1SnD',['response-arrays-small','response-arrays-repair']),
    'http-review': ('ses_eb7b5dc13ffeQ17R1aP3LpOvwt',['http-review']),
    'symbolic-text': ('ses_eb799fd21ffeIVT9y4sHajx6HG',['symbolic-text'])
}
result={}
for label,(session,logs) in sessions.items():
    output=root/(label+'-final-export.json')
    env={**os.environ,'OPENCODE_PERMISSION':json.dumps({'edit':'deny','bash':'deny','task':'deny','external_directory':'deny'})}
    with output.open('w') as out, output.with_suffix('.stderr.txt').open('w') as err:
        completed=subprocess.run([str(Path.home()/'.local/bin/opencode-deepseek'),'export',session],env=env,stdout=out,stderr=err,timeout=120)
    assert completed.returncode==0
    data=json.loads(output.read_text())
    messages=[m['info'] for m in data['messages'] if m['info']['role']=='assistant']
    events=[]
    for log in logs:
        events.extend(json.loads(line) for line in (root/(log+'.jsonl')).read_text().splitlines())
    skills=[e for e in events if e.get('part',{}).get('tool')=='skill' and e['part'].get('state',{}).get('status')=='completed'
            and e['part']['state'].get('input',{}).get('name')=='karpathy-guidelines']
    edits=[e for e in events if e.get('part',{}).get('tool') in ('write','edit','apply_patch') and e['part'].get('state',{}).get('status')=='completed']
    paths=sorted({e['part']['state'].get('input',{}).get('filePath','') for e in edits})
    result[label]={'session':session,'models':sorted({m['providerID']+'/'+m['modelID'] for m in messages}),
       'assistant_messages':len(messages),'reported_cost':sum(m.get('cost',0) for m in messages),
       'variant_from_runner':'max','native_skill_before_edits':not edits or bool(skills) and min(e['timestamp'] for e in skills)<min(e['timestamp'] for e in edits),
       'edited_paths':paths,'tool_errors':[{ 'tool':e['part']['tool'],'message':e['part']['state'].get('error','')[:300]}
         for e in events if e.get('part',{}).get('state',{}).get('status')=='error'],
       'runner_note':'all workers completed; length-limited attempts are retained; Codex independently repaired and tested delegated code and integration'}
    assert result[label]['models']==['opencode/deepseek-v4.1-flash-free']
    assert result[label]['native_skill_before_edits']
(root/'final-deepseek-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
