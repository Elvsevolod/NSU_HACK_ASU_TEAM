"""Bounded JSON lifecycle on unmodified pinned PiggyMetrics Account source."""
import argparse,hashlib,json,re,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--code',type=Path,required=True);p.add_argument('--repository',type=Path,required=True)
p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
assert not a.work.exists() and not a.output.exists();a.work.mkdir(parents=True)
sys.path[:0]=[str(a.code.resolve()),str(a.code.resolve()/'tests')]
from builders import build
from analyzer.project import Project
from analyzer.paths import run_paths
from analyzer.state import ScenarioState
sources={p.relative_to(a.repository).as_posix():p.read_text() for p in sorted((a.repository/'account-service/src/main/java').rglob('*.java')) if p.name!='package-info.java'}
hashes={name:hashlib.sha256(source.encode()).hexdigest() for name,source in sources.items()}
sources['Probe.java']='''import com.piggymetrics.account.domain.Account;import com.fasterxml.jackson.databind.ObjectMapper;
 class Probe{String entry(){ObjectMapper mapper=new ObjectMapper();
 Account original=mapper.readValue("{\\"name\\":\\"Ada\\",\\"note\\":\\"initial\\"}",Account.class);
 Account copy=mapper.readValue(mapper.writeValueAsString(original),Account.class);
 copy.setNote("edited");return original.getNote()+":"+copy.getNote()+":"+copy.getName();}}'''
project,db,ids=build(a.work/'inputs',sources,module='account-json')
for node in project.skeleton['nodes'].values():
 if node['kind']=='type':
  package=re.search(r'^package\s+([\w.]+)\s*;',sources[node['file']],re.M)
  if package:node['fqn']=package[1]+'.'+node['fqn']
(a.work/'inputs/skeleton.json').write_text(json.dumps(project.skeleton))
expected={('','executes',ids['Probe.entry'])}
expected|={('','executes',ids['Account.set'+name]) for name in ('Name','LastSeen','Incomes','Expenses','Saving','Note')}
for method in ('setNote','getNote','getName'):
 expected.add(('','executes',ids['Account.'+method]));expected.add((ids['Probe.entry'],'calls',ids['Account.'+method]))
reference={'edges':sorted(expected),'result':'initial:edited:Ada',
 'scope':'Default Jackson2 Account JSON copy isolation; direct getters and reflection setters, supplied input values'}
ref=a.work/'reference.json';ref.write_text(json.dumps(reference,indent=2)+'\n');sha=hashlib.sha256(ref.read_bytes()).hexdigest()
project=Project(a.work/'inputs/skeleton.json',a.work/'inputs')
paths=run_paths(project,ScenarioState(db),ids['Probe.entry'],{},limit=16)
found=set.union(*(o['engine'].edges for o in paths))
relations={}
for relation in ('executes','calls','remote','data'):
 wanted={e for e in expected if e[1]==relation};actual={e for e in found if e[1]==relation}
 relations[relation]={'tp':len(wanted&actual),'fp':len(actual-wanted),'fn':len(wanted-actual),
  'nonempty':bool(wanted|actual),'iou':len(wanted&actual)/len(wanted|actual) if wanted|actual else None}
report={'passed':found==expected and all(o['result']==reference['result'] for o in paths),'relations':relations,
 'observed_results':[o['result'] for o in paths],'missing':sorted(expected-found),'extra':sorted(found-expected),
 'paths':len(paths),'warnings':sorted(set.union(*(o['engine'].warnings for o in paths))),
 'source_sha256':hashes,'source_files':len(hashes),'reference_sha256':sha,'reference_fixed_before_prediction':True,
 'repository':'https://github.com/sqshq/piggymetrics','commit':'6bb2cf9ddbca980b664d3edbb6ff775d75369278',
 'application_started':False,'limits':['Bounded DTO lifecycle with supplied values; no full real-application graph oracle',
  'No remote or database execution in this probe; empty relation types have no measured accuracy',
  'Jackson2 defaults; legacy Jackson1 annotation introspection and application codec configuration not claimed',
  'Skeleton supplied by source-only validation adapter']}
assert hashlib.sha256(ref.read_bytes()).hexdigest()==sha
a.output.write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps({'passed':report['passed'],'source_files':len(hashes),'relations':relations}))
if not report['passed']:raise SystemExit(1)
