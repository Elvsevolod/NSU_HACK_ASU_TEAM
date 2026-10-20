"""Fixed four-relation source references for JSON callbacks and HTTP failures."""
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
 ('setter-constructor-transform',
  'Input input=new Input();input.name="alpha";String reply=rest.postForObject("http://recorder/item",input,String.class);if(reply.equals("ctor:ALPHA")){return positive();}return negative();',
  'String accept(@RequestBody Item input){return input.getName();}',
  'class Item{private String prefix;private String name;public Item(){prefix=prefix();}String prefix(){return "ctor:";}public void setName(String value){name=normalize(value);}String normalize(String value){return prefix+value.toUpperCase();}public String getName(){return name;}}',
  ['Recorder.accept','Item.prefix','Item.setName','Item.normalize','Item.getName'],
  [('Item.setName','Item.normalize'),('Recorder.accept','Item.getName')],True,True),
 ('computed-response-getter',
  'Reply reply=rest.getForObject("http://recorder/item",Reply.class);if(reply.count==2){return positive();}return negative();',
  'Item accept(){return new Item();}',
  'class Item{public int count=1;public int getCount(){return compute();}int compute(){return count+1;}}',
  ['Recorder.accept','Item.compute'],[],True,True),
 ('binding-setter-failure',
  'Input input=new Input();input.name="alpha";rest.postForObject("http://recorder/item",input,String.class);return positive();',
  'String accept(@RequestBody Item input){return input.getName();}',
  'class Item{private String name;public void setName(String value){throw new IllegalStateException();}public String getName(){return name;}}',
  ['Item.setName'],[],False,False),
 ('response-getter-failure',
  'Reply reply=rest.getForObject("http://recorder/item",Reply.class);return positive();',
  'Item accept(){return new Item();}',
  'class Item{public int getCount(){throw new IllegalStateException();}}',
  ['Recorder.accept'],[],True,False),
]
results=[]
for label,body,handler,bean,extra_methods,extra_calls,entered,positive in cases:
 verb='PostMapping' if '@RequestBody' in handler else 'GetMapping'
 sources={'Gateway.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.beans.factory.annotation.Autowired;
 class Gateway{@Autowired RestTemplate rest;String entry(){before();'''+body+'''}
 String before(){return rest.getForObject("http://recorder/begin",String.class);}
 String positive(){return rest.getForObject("http://recorder/positive",String.class);}
 String negative(){return rest.getForObject("http://recorder/negative",String.class);}}
 class Input{public String name;}class Reply{public int count;}''',
 'Recorder.java':'''import java.util.*;import org.springframework.web.bind.annotation.*;
 import org.springframework.beans.factory.annotation.Autowired;import org.springframework.data.jpa.repository.JpaRepository;import javax.persistence.*;
 class Recorder{@Autowired AuditStore audit;@Autowired PositiveStore positive;@Autowired NegativeStore negative;
 @GetMapping("/begin") String begin(){audit.findAll();return "ok";}
 @GetMapping("/positive") String positive(){positive.findAll();return "positive";}
 @GetMapping("/negative") String negative(){negative.findAll();return "negative";}
 @'''+verb+'("/item") '+handler+'}'+bean+'''
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
 expected|={('','executes',ids[name]) for name in extra_methods}
 expected|={(ids[left],'calls',ids[right]) for left,right in extra_calls}
 if entered:expected.add((ids['Gateway.entry'],'remote',ids['Recorder.accept']))
 if positive:expected|={('','executes',ids['Gateway.positive']),('','executes',ids['Recorder.positive']),
  (ids['Gateway.entry'],'calls',ids['Gateway.positive']),(ids['Gateway.positive'],'remote',ids['Recorder.positive']),
  (ids['Recorder.positive'],'data','res:table:service.checked_snapshots')}
 reference={'edges':sorted(expected),'result':'positive' if positive else 'unknown',
            'outcome':'returned' if positive else 'uncaught application exception'}
 ref=work/'reference.json';ref.write_text(json.dumps(reference,indent=2)+'\n');sha=hashlib.sha256(ref.read_bytes()).hexdigest()
 paths=run_paths(project,ScenarioState(db),ids['Gateway.entry'],{},limit=16)
 found=set.union(*(x['engine'].edges for x in paths));outcomes={x['engine'].outcome for x in paths};relations={}
 for relation in ('executes','calls','remote','data'):
  want={e for e in expected if e[1]==relation};got={e for e in found if e[1]==relation}
  relations[relation]={'tp':len(want&got),'fp':len(got-want),'fn':len(want-got),
   'iou':len(want&got)/len(want|got) if want|got else None,'nonempty':bool(want|got)}
 assert hashlib.sha256(ref.read_bytes()).hexdigest()==sha
 correct_result=not positive or all(x['result']=='positive' for x in paths)
 results.append({'case':label,'passed':found==expected and outcomes=={reference['outcome']} and correct_result,
  'relations':relations,'reference_sha256':sha,'source_sha256':{n:hashlib.sha256(s.encode()).hexdigest() for n,s in sources.items()},
  'outcomes':sorted(outcomes),'paths':len(paths),'missing':sorted(expected-found),'extra':sorted(found-expected),
  'warnings':sorted(set.union(*(x['engine'].warnings for x in paths)))})
report={'passed':all(x['passed'] for x in results),'exact_graphs':sum(x['passed'] for x in results),'cases':results,
 'reference_fixed_before_prediction':True,'application_started':False,
 'scope':'Synthetic JSON/HTTP source callbacks with four nonempty relation types; not a complete real-application oracle'}
a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'exact_graphs':report['exact_graphs'],'total':len(results)}))
if not report['passed']:raise SystemExit(1)
