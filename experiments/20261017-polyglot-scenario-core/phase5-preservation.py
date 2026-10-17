from pathlib import Path
import json,hashlib
root=Path('/Users/vsevolod/Desktop/NSU_HACK_ASU_TEAM');exp=root/'experiments/20261017-polyglot-scenario-core';v=root/'solutions/—_polyglot-scenario-core'
before=json.loads((exp/'protected-before.json').read_text());changed=[];missing=[];unchanged=0;renamed=0;groups={}
for old,digest in before.items():
 current=old.replace('solutions/—_dom-state-flow/','solutions/0.748530_dom-state-flow/',1);renamed+=current!=old
 path=root/current
 if not path.exists():missing.append({'old':old,'current':current});continue
 after=hashlib.sha256(path.read_bytes()).hexdigest()
 if after==digest:unchanged+=1
 else:changed.append({'old':old,'current':current,'before':digest,'now':after})
 group=old.split('/')[0];groups.setdefault(group,{'files':0,'unchanged':0})
 groups[group]['files']+=1;groups[group]['unchanged']+=after==digest
result={'baseline_files':len(before),'unchanged_under_path_mapping':unchanged,'renamed_files':renamed,'path_mapping':{'solutions/—_dom-state-flow/':'solutions/0.748530_dom-state-flow/'},'missing_after_mapping':missing,'changed':changed,'groups':groups,'interpretation':'This task edited only variant 13 and its registry text. Existing variant 12 was renamed and edited concurrently by another chat; those bytes are preserved without restoration. New variants created in other chats are not included in the original baseline.'}
assert not missing
assert groups['tt-challenge']['files']==groups['tt-challenge']['unchanged']
assert groups['sample']['files']==groups['sample']['unchanged']
assert all(item['old']=='solutions/README.md' or item['old'].startswith('solutions/—_dom-state-flow/') for item in changed)
(exp/'protected-phase5.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(v/'development/protected-inputs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({key:result[key] for key in ['baseline_files','unchanged_under_path_mapping','renamed_files','groups']}))
