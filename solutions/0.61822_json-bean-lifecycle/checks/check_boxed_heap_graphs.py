"""Manual nonempty four-relation references for native boxed heap flow."""
import argparse,hashlib,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--code',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
assert not a.work.exists() and not a.output.exists();a.work.mkdir(parents=True)
sys.path[:0]=[str(a.code.resolve()),str(a.code.resolve()/'tests')]
from builders import build
from analyzer.project import Project
from analyzer.paths import run_paths
from analyzer.state import ScenarioState
cases=[
 ('typed-list-failure','List<Long> values=new ArrayList<Long>();List raw=values;raw.add(1);Long value=values.get(0);return negative();','',False),
 ('object-local','Object value=1L;if(((Long)value)==1L){return positive();}return negative();','',True),
 ('object-call-frame','Object value=identity(1L);if(((Long)value)==1L){return positive();}return negative();','Object identity(Object value){return value;}',True),
 ('widened-list-read','List<Long> values=new ArrayList<Long>();List raw=values;raw.add(1);Object value=values.get(0);if(((Integer)value)==1){return positive();}return negative();','',True)]
results=[]
for label,body,helper,positive in cases:
 sources={'Gateway.java':'''import java.util.*;import org.springframework.web.client.RestTemplate;
 class Gateway{RestTemplate rest;String entry(){before();'''+body+'}'+helper+'''
 String before(){return rest.getForObject("http://recorder/begin",String.class);}
 String positive(){return rest.getForObject("http://recorder/positive",String.class);}
 String negative(){return rest.getForObject("http://recorder/negative",String.class);}}''',
 'Recorder.java':'''import java.util.*;class Recorder{AuditStore audit;PositiveStore positive;NegativeStore negative;
 @GetMapping("/begin") String begin(){audit.findAll();return "ok";}
 @GetMapping("/positive") String positive(){positive.findAll();return "positive";}
 @GetMapping("/negative") String negative(){negative.findAll();return "negative";}}
 @Entity @Table(name="probe_audit") class Audit{@Id String id;}
 @Entity @Table(name="checked_snapshots") class Positive{@Id String id;}
 @Entity @Table(name="unexpected_snapshots") class Negative{@Id String id;}
 interface AuditStore extends JpaRepository<Audit,String>{List<Audit> findAll();}
 interface PositiveStore extends JpaRepository<Positive,String>{List<Positive> findAll();}
 interface NegativeStore extends JpaRepository<Negative,String>{List<Negative> findAll();}'''}
 work=a.work/label;project,db,ids=build(work,sources,rows={'probe_audit':[{'id':'a'}],
  'checked_snapshots':[{'id':'p'}],'unexpected_snapshots':[{'id':'n'}]})
 skeleton=project.skeleton
 for unit in ('gateway','recorder'):skeleton['nodes']['module:'+unit]={'kind':'module','name':unit,'deployment_units':[unit]}
 for node in skeleton['nodes'].values():
  if node.get('file'):node['module']='gateway' if node['file']=='Gateway.java' else 'recorder'
 (work/'skeleton.json').write_text(json.dumps(skeleton));project=Project(work/'skeleton.json',work)
 expected={('','executes',ids['Gateway.entry']),('','executes',ids['Gateway.before']),('','executes',ids['Recorder.begin']),
  (ids['Gateway.entry'],'calls',ids['Gateway.before']),(ids['Gateway.before'],'remote',ids['Recorder.begin']),
  (ids['Recorder.begin'],'data','res:table:service.probe_audit')}
 if positive:expected|={('','executes',ids['Gateway.positive']),('','executes',ids['Recorder.positive']),
  (ids['Gateway.entry'],'calls',ids['Gateway.positive']),(ids['Gateway.positive'],'remote',ids['Recorder.positive']),
  (ids['Recorder.positive'],'data','res:table:service.checked_snapshots')}
 if helper:expected|={('','executes',ids['Gateway.identity']),(ids['Gateway.entry'],'calls',ids['Gateway.identity'])}
 reference={'edges':sorted(expected),'outcome':'returned' if positive else 'uncaught application exception'}
 ref=work/'reference.json';ref.write_text(json.dumps(reference,indent=2)+'\n');sha=hashlib.sha256(ref.read_bytes()).hexdigest()
 paths=run_paths(project,ScenarioState(db),ids['Gateway.entry'],{},limit=16)
 found=set.union(*(x['engine'].edges for x in paths));outcomes={x['engine'].outcome for x in paths};relations={}
 for rel in ('executes','calls','remote','data'):
  want={e for e in expected if e[1]==rel};got={e for e in found if e[1]==rel}
  relations[rel]={'tp':len(want&got),'fp':len(got-want),'fn':len(want-got),'iou':len(want&got)/len(want|got) if want|got else None,'nonempty':bool(want|got)}
 assert hashlib.sha256(ref.read_bytes()).hexdigest()==sha
 results.append({'case':label,'passed':found==expected and outcomes=={reference['outcome']},'relations':relations,
  'reference_sha256':sha,'source_sha256':{n:hashlib.sha256(s.encode()).hexdigest() for n,s in sources.items()},
  'outcomes':sorted(outcomes),'paths':len(paths),'missing':sorted(expected-found),'extra':sorted(found-expected),
  'warnings':sorted(set.union(*(x['engine'].warnings for x in paths)))})
report={'passed':all(x['passed'] for x in results),'exact_graphs':sum(x['passed'] for x in results),'cases':results,
 'reference_fixed_before_prediction':True,'application_started':False,
 'scope':'Synthetic two-service native boxed state and refusal paths, not a complete independent real-application oracle'}
a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'exact_graphs':report['exact_graphs'],'total':len(results)}))
