"""Fixed source graphs: writes determine local, HTTP and table edges."""
import argparse,hashlib,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--code',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
assert not a.work.exists() and not a.output.exists();a.work.mkdir(parents=True)
sys.path[:0]=[str(a.code.resolve()),str(a.code.resolve()/'tests')]
from builders import build
from analyzer.project import Project
from analyzer.paths import run_paths
from analyzer.state import ScenarioState
from analyzer.java_collections import JavaRecord
cases=[
 ('field-postfix','int old=input.count++;if(old==0&&input.count==1){return positive();}return negative();','',[]),
 ('simple-receiver-order','target(input).count=rhs(input);if(input.visits==12){return positive();}return negative();',
  'Request target(Request x){x.visits=x.visits*10+1;return x;}int rhs(Request x){x.visits=x.visits*10+2;return 7;}',['target','rhs']),
 ('compound-receiver-once','target(input).count+=rhs(input);if(input.visits==1&&input.count==2){return positive();}return negative();',
  'Request target(Request x){x.visits=x.visits+1;return x;}int rhs(Request x){x.count=50;return 2;}',['target','rhs']),
 ('array-postfix','int[] values={0};int old=values[0]++;if(old==0&&values[0]==1){return positive();}return negative();','',[])]
results=[]
for label,body,helpers,helper_names in cases:
 sources={'Client.java':'''import org.springframework.web.client.RestTemplate;
 class Request{public int count;public int visits;}class Client{RestTemplate rest;
 String entry(Request input){'''+body+'}'+helpers+'''
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
 expected={('','executes',ids['Client.entry']),('','executes',ids['Client.positive']),('','executes',ids['Warehouse.positive']),
  (ids['Client.entry'],'calls',ids['Client.positive']),(ids['Client.positive'],'remote',ids['Warehouse.positive']),
  (ids['Warehouse.positive'],'data','res:table:service.positive_parts')}
 for name in helper_names:expected|={('','executes',ids['Client.'+name]),(ids['Client.entry'],'calls',ids['Client.'+name])}
 reference={'edges':sorted(expected),'result':'positive','input_after':{'count':0,'visits':0}}
 ref=work/'reference.json';ref.write_text(json.dumps(reference,indent=2)+'\n');sha=hashlib.sha256(ref.read_bytes()).hexdigest()
 initial=JavaRecord('Request',{'__type__':'Request','count':0,'visits':0},wire_fields={'count','visits'})
 paths=run_paths(project,ScenarioState(db),ids['Client.entry'],{'input':initial},limit=8)
 found=set.union(*(x['engine'].edges for x in paths));observed=sorted({str(x['result']) for x in paths});after={k:initial[k] for k in ('count','visits')}
 relations={}
 for rel in ('executes','calls','remote','data'):
  want={e for e in expected if e[1]==rel};got={e for e in found if e[1]==rel}
  relations[rel]={'tp':len(want&got),'fp':len(got-want),'fn':len(want-got),'iou':len(want&got)/len(want|got) if want|got else None,'nonempty':bool(want|got)}
 correct=found==expected and observed==['positive'] and after==reference['input_after']
 assert hashlib.sha256(ref.read_bytes()).hexdigest()==sha
 results.append({'case':label,'passed':correct,'relations':relations,'results':observed,'original_input_after':after,
  'paths':len(paths),'reference_sha256':sha,'source_sha256':{name:hashlib.sha256(s.encode()).hexdigest() for name,s in sources.items()},
  'warnings':sorted(set.union(*(x['engine'].warnings for x in paths))),
  'missing':sorted(expected-found),'extra':sorted(found-expected)})
report={'passed':all(x['passed'] for x in results),'exact_graphs':sum(x['passed'] for x in results),'cases':results,
 'reference_fixed_before_prediction':True,'application_started':False,
 'scope':'Java lvalue updates and assignment evaluation order determine calls to two HTTP handlers and tables',
 'limits':['Synthetic component graphs, not full applications or a scenario understanding benchmark','Reference arrays, static storage and arbitrary unsupported effects remain outside this check']}
a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passed'],'exact_graphs':report['exact_graphs'],'total':len(results)}))
