"""Manual four-relation references for source type flow across HTTP and state."""
import argparse,hashlib,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--code',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
assert not a.work.exists() and not a.output.exists();a.work.mkdir(parents=True)
sys.path[:0]=[str(a.code.resolve()),str(a.code.resolve()/'tests')]
from builders import build
from analyzer.project import Project
from analyzer.paths import run_paths
from analyzer.state import ScenarioState
from analyzer.java_collections import JavaRecord,JavaMap
def record(typ,**fields):return JavaRecord(typ,{'__type__':typ,**fields},wire_fields=fields)
cases=[
 ('receiver-member','Box<Counter> box','if(box.getValue().count+1<0){return positive();}return negative();','',
  {'box':record('Box',value=record('Counter',id='seed',count=2147483647))},['Box.getValue'],False),
 ('method-result','Box<Counter> box','if(identity(box).getValue().count+1<0){return positive();}return negative();','<T>T identity(T value){return value;}',
  {'box':record('Box',value=record('Counter',id='seed',count=2147483647))},['Client.identity','Box.getValue'],False),
 ('deferred-state','Store<Long> store,List<Long> keys','if("known".equals(store.plan(keys).collect(Collectors.toList()).get(0))){return positive();}return negative();','',
  {'store':record('Store',values=JavaMap({})),'keys':[1]},['Store.plan'],False),
 ('typed-response','', '''Box<Counter> box=rest.exchange("http://warehouse/start",HttpMethod.GET,null,
    new ParameterizedTypeReference<Box<Counter>>(){}).getBody();
    if(box.getValue().count+1<0){return positive();}return negative();''','',{},['Box.getValue'],True)]
results=[]
for label,parameters,body,helpers,params,local_calls,response in cases:
 sources={'Client.java':'''import java.util.*;import java.util.stream.*;
 import org.springframework.web.client.RestTemplate;import org.springframework.http.HttpMethod;
 import org.springframework.core.ParameterizedTypeReference;
 class Box<T>{public T value;T getValue(){return value;}}
 class Store<K>{Map<K,String> values;Stream<String> plan(List<K> keys){
 return keys.stream().map(key->{values.put(key,"known");return values.get(key);});}}
 class Client{RestTemplate rest;String entry('''+parameters+'){'+body+'}'+helpers+'''
 String positive(){return rest.getForObject("http://warehouse/positive",String.class);}
 String negative(){return rest.getForObject("http://warehouse/negative",String.class);}}''',
 'Warehouse.java':'''import java.util.*;class Warehouse{PositiveStore positive;NegativeStore negative;CounterStore counters;
 @GetMapping("/positive") String positive(){positive.findAll();return "positive";}
 @GetMapping("/negative") String negative(){negative.findAll();return "negative";}
 @GetMapping("/start") Box<Counter> start(){Box<Counter> result=new Box<Counter>();
 result.value=counters.findById("seed").orElseThrow();return result;}}
 @Entity @Table(name="positive_parts") class Positive{@Id String id;}
 @Entity @Table(name="negative_parts") class Negative{@Id String id;}
 @Entity @Table(name="counter_rows") class Counter{@Id public String id;public int count;}
 interface PositiveStore extends JpaRepository<Positive,String>{List<Positive> findAll();}
 interface NegativeStore extends JpaRepository<Negative,String>{List<Negative> findAll();}
 interface CounterStore extends JpaRepository<Counter,String>{Optional<Counter> findById(String id);}'''}
 work=a.work/label;project,db,ids=build(work,sources,rows={'positive_parts':[{'id':'p'}],'negative_parts':[{'id':'n'}],
  'counter_rows':[{'id':'seed','count':2147483647}]})
 skeleton=project.skeleton
 for unit in ('client','warehouse'):skeleton['nodes']['module:'+unit]={'kind':'module','name':unit,'deployment_units':[unit]}
 for node in skeleton['nodes'].values():
  if node.get('file'):node['module']='client' if node['file']=='Client.java' else 'warehouse'
 (work/'skeleton.json').write_text(json.dumps(skeleton));project=Project(work/'skeleton.json',work)
 expected={('','executes',ids['Client.entry']),('','executes',ids['Client.positive']),('','executes',ids['Warehouse.positive']),
  (ids['Client.entry'],'calls',ids['Client.positive']),(ids['Client.positive'],'remote',ids['Warehouse.positive']),
  (ids['Warehouse.positive'],'data','res:table:service.positive_parts')}
 for name in local_calls:expected|={('','executes',ids[name]),(ids['Client.entry'],'calls',ids[name])}
 if response:expected|={('','executes',ids['Warehouse.start']),(ids['Client.entry'],'remote',ids['Warehouse.start']),
  (ids['Warehouse.start'],'data','res:table:service.counter_rows')}
 reference={'edges':sorted(expected),'result':'positive'}
 ref=work/'reference.json';ref.write_text(json.dumps(reference,indent=2)+'\n');sha=hashlib.sha256(ref.read_bytes()).hexdigest()
 paths=run_paths(project,ScenarioState(db),ids['Client.entry'],params,limit=16)
 found=set.union(*(x['engine'].edges for x in paths));observed=sorted({str(x['result']) for x in paths});relations={}
 for rel in ('executes','calls','remote','data'):
  want={e for e in expected if e[1]==rel};got={e for e in found if e[1]==rel}
  relations[rel]={'tp':len(want&got),'fp':len(got-want),'fn':len(want-got),'iou':len(want&got)/len(want|got) if want|got else None,'nonempty':bool(want|got)}
 correct=found==expected and observed==['positive']
 assert hashlib.sha256(ref.read_bytes()).hexdigest()==sha
 results.append({'case':label,'passed':correct,'relations':relations,'results':observed,'paths':len(paths),'reference_sha256':sha,
  'source_sha256':{name:hashlib.sha256(s.encode()).hexdigest() for name,s in sources.items()},
  'warnings':sorted(set.union(*(x['engine'].warnings for x in paths))),
  'missing':sorted(expected-found),'extra':sorted(found-expected)})
report={'passed':all(x['passed'] for x in results),'exact_graphs':sum(x['passed'] for x in results),'cases':results,
 'reference_fixed_before_prediction':True,'application_started':False,
 'scope':'Source generic member/method types and deferred/HTTP response state choose downstream calls and tables',
 'limits':['Synthetic two-service component, not a full real application oracle','References measure visible edge unions; JSON callback and framework warnings remain explicit']}
a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passed'],'exact_graphs':report['exact_graphs'],'total':len(results)}))
