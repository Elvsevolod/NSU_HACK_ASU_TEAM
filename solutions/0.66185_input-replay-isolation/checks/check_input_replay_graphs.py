"""Visible four-relation graphs for branch-local request input ownership."""
import argparse,hashlib,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--code',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
assert not a.work.exists() and not a.output.exists();a.work.mkdir(parents=True)
sys.path[:0]=[str(a.code.resolve()),str(a.code.resolve()/'tests')]
from builders import build
from analyzer.project import Project
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from analyzer.java_collections import JavaRecord
from analyzer.__main__ import serial
results=[]
for label,body,modes,limit in [
 ('branch-write','if(flag){input.active=true;}if(input.active){return positive();}return negative();',['positive','negative'],8),
 ('prebranch-write','input.count=input.count+1;if(flag){}if(input.count==1){return positive();}return negative();',['positive'],8),
 ('conservative-restart','input.count=input.count+1;if(flag){}if(input.count==1){return positive();}return negative();',['positive'],1)]:
 sources={'Client.java':'''import org.springframework.web.client.RestTemplate;
 class Request{public boolean active=false;public int count=0;}class Client{RestTemplate rest;
 String entry(Request input,boolean flag){'''+body+'''}
 String positive(){return rest.getForObject("http://warehouse/positive",String.class);}
 String negative(){return rest.getForObject("http://warehouse/negative",String.class);}}''',
 'Warehouse.java':'''import java.util.*;class Warehouse{PositiveStore positive;NegativeStore negative;
 @GetMapping("/positive") String positive(){positive.findAll();return "positive";}
 @GetMapping("/negative") String negative(){negative.findAll();return "negative";}}
 @Entity @Table(name="positive_parts") class Positive{@Id String id;}
 @Entity @Table(name="negative_parts") class Negative{@Id String id;}
 interface PositiveStore extends JpaRepository<Positive,String>{List<Positive> findAll();}
 interface NegativeStore extends JpaRepository<Negative,String>{List<Negative> findAll();}'''}
 work=a.work/label;project,db,ids=build(work,sources,rows={'positive_parts':[{'id':'p'}],'negative_parts':[{'id':'n'}]})
 skeleton=project.skeleton
 for unit in ('client','warehouse'):skeleton['nodes']['module:'+unit]={'kind':'module','name':unit,'deployment_units':[unit]}
 for node in skeleton['nodes'].values():
  if node.get('file'):node['module']='client' if node['file']=='Client.java' else 'warehouse'
 (work/'skeleton.json').write_text(json.dumps(skeleton));project=Project(work/'skeleton.json',work)
 expected={('','executes',ids['Client.entry'])}
 for mode in modes:
  expected|={('','executes',ids['Client.'+mode]),('','executes',ids['Warehouse.'+mode]),
   (ids['Client.entry'],'calls',ids['Client.'+mode]),(ids['Client.'+mode],'remote',ids['Warehouse.'+mode]),
   (ids['Warehouse.'+mode],'data','res:table:service.'+mode+'_parts')}
 reference={'edges':sorted(expected),'results':sorted(modes),'input_after':{'active':False,'count':0}}
 ref=work/'reference.json';ref.write_text(json.dumps(reference,indent=2)+'\n');sha=hashlib.sha256(ref.read_bytes()).hexdigest()
 initial=JavaRecord('Request',{'__type__':'Request','active':False,'count':0},wire_fields={'active','count'})
 state=ScenarioState(db);paths=run_paths(project,state,ids['Client.entry'],{'input':initial,'flag':U},limit=limit)
 found=set.union(*(x['engine'].edges for x in paths));observed=sorted({x['result'] for x in paths});after={k:initial[k] for k in ('active','count')}
 relations={}
 for rel in ('executes','calls','remote','data'):
  want={e for e in expected if e[1]==rel};got={e for e in found if e[1]==rel}
  relations[rel]={'tp':len(want&got),'fp':len(got-want),'fn':len(want-got),'iou':len(want&got)/len(want|got) if want|got else None,'nonempty':bool(want|got)}
 correct=found==expected and observed==reference['results'] and after==reference['input_after']
 assert hashlib.sha256(ref.read_bytes()).hexdigest()==sha
 results.append({'case':label,'passed':correct,'relations':relations,'results':observed,'original_input_after':after,
  'paths':len(paths),'reference_sha256':sha,'source_sha256':{name:hashlib.sha256(s.encode()).hexdigest() for name,s in sources.items()},
  'missing':sorted(expected-found),'extra':sorted(found-expected)})
report={'passed':all(x['passed'] for x in results),'exact_graphs':sum(x['passed'] for x in results),'cases':results,
 'reference_fixed_before_prediction':True,'application_started':False,
 'scope':'Internal Java entry parameter snapshots, remote HTTP and independent tables',
 'limits':['Synthetic source-fixed component, not a real application or scenario understanding benchmark','The visible graph is the union of feasible flag values under the declared path budget']}
a.output.write_text(json.dumps(report,indent=2,default=serial)+'\n');print(json.dumps({'passed':report['passed'],'exact_graphs':report['exact_graphs'],'total':len(results)}))
