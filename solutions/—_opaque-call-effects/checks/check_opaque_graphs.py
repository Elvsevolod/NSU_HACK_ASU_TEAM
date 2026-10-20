"""Source-fixed continuation graphs across an explicitly opaque library call.

The oracle is the union of visible normal/mutated/exceptional continuations,
not a claim to know arbitrary calls inside the missing dependency.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

parser=argparse.ArgumentParser()
parser.add_argument('--code',type=Path,required=True)
parser.add_argument('--work',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
assert not args.work.exists()
args.work.mkdir(parents=True)
sys.path[:0]=[str(args.code.resolve()),str(args.code.resolve()/'tests')]
from builders import build
from analyzer.project import Project
from analyzer.paths import run_paths
from analyzer.state import ScenarioState
from analyzer.__main__ import serial

reports=[]
for label,call,opaque in [('mutable-argument','vendor.Plugin.mutate(item);',True),
                          ('name-is-not-a-model','vendor.Plugin.info(item);',True),
                          ('known-source-contract','new Helper().mutate(item);',False)]:
    sources={
      'Caller.java':'''import org.springframework.web.client.RestTemplate;
        class Item{boolean active=false;}class Helper{void mutate(Item item){item.active=true;}}
        class Caller{RestTemplate rest;String entry(){Item item=new Item();before();try{
          '''+call+'''if(item.active){return positive();}return negative();
        }catch(RuntimeException failure){return caught();}finally{cleanup();}}
        void before(){}void cleanup(){}String caught(){return "caught";}
        String positive(){return rest.getForObject("http://warehouse/positive",String.class);}
        String negative(){return rest.getForObject("http://warehouse/negative",String.class);}}''',
      'Warehouse.java':'''import java.util.*;class Warehouse{Store store;
        @GetMapping("/positive") String positive(){store.findAll();return "positive";}
        @GetMapping("/negative") String negative(){store.findAll();return "negative";}}
        @Entity @Table(name="parts") class Part{@Id String id;}
        interface Store extends JpaRepository<Part,String>{List<Part> findAll();}'''}
    work=args.work/label
    project,db,ids=build(work,sources,rows={'parts':[{'id':'initial'}]})
    skeleton=project.skeleton
    for unit in ('client','warehouse'):
        skeleton['nodes']['module:'+unit]={'kind':'module','name':unit,'deployment_units':[unit]}
    for node in skeleton['nodes'].values():
        if node.get('file'):node['module']='client' if node['file']=='Caller.java' else 'warehouse'
    (work/'skeleton.json').write_text(json.dumps(skeleton))
    methods=['Caller.entry','Caller.before','Caller.cleanup','Caller.positive','Warehouse.positive']
    calls=[('Caller.entry',name) for name in ('Caller.before','Caller.cleanup','Caller.positive')]
    remote=[('Caller.positive','Warehouse.positive')]
    data=['Warehouse.positive']
    if opaque:
        methods+=['Caller.negative','Warehouse.negative','Caller.caught']
        calls += [('Caller.entry',name) for name in ('Caller.negative','Caller.caught')]
        remote.append(('Caller.negative','Warehouse.negative'));data.append('Warehouse.negative')
    else:
        methods.append('Helper.mutate');calls.append(('Caller.entry','Helper.mutate'))
    expected={('', 'executes',ids[name]) for name in methods}
    expected|={(ids[a],'calls',ids[b]) for a,b in calls}
    expected|={(ids[a],'remote',ids[b]) for a,b in remote}
    expected|={(ids[a],'data','res:table:service.parts') for a in data}
    reference={'edges':sorted(expected),'returns':['caught','negative','positive'] if opaque else ['positive'],
               'may_fail_uncaught':opaque,'database_snapshot_unknown':opaque}
    reference_path=work/'reference.json'
    reference_path.write_text(json.dumps(reference,indent=2)+'\n')
    digest=hashlib.sha256(reference_path.read_bytes()).hexdigest()
    project=Project(work/'skeleton.json',work)
    initial=ScenarioState(db)
    paths=run_paths(project,initial,ids['Caller.entry'],{},limit=16)
    found=set.union(*(p['engine'].edges for p in paths))
    returns=sorted({p['result'] for p in paths if p['engine'].outcome=='returned'})
    failures=any(p['engine'].outcome=='uncaught application exception' for p in paths)
    unknown=all(('service','parts') in p['state'].database.unknown_tables for p in paths)
    relations={}
    for relation in ('executes','calls','remote','data'):
        wanted={e for e in expected if e[1]==relation};actual={e for e in found if e[1]==relation}
        relations[relation]={'tp':len(actual&wanted),'fp':len(actual-wanted),'fn':len(wanted-actual),
            'iou':len(actual&wanted)/len(actual|wanted) if actual|wanted else None,'nonempty':bool(actual|wanted)}
    correct=found==expected and returns==reference['returns'] and failures==opaque and unknown==opaque
    assert not initial.database.unknown_tables and db.tables[('service','parts')]==[{'id':'initial'}]
    assert hashlib.sha256(reference_path.read_bytes()).hexdigest()==digest
    reports.append({'case':label,'passed':correct,'relations':relations,'returns':returns,'uncaught_possible':failures,
        'database_snapshot_unknown':unknown,'initial_state_preserved':True,'reference_sha256':digest,
        'source_sha256':{name:hashlib.sha256(source.encode()).hexdigest() for name,source in sources.items()},
        'missing':sorted(expected-found),'extra':sorted(found-expected),'paths':len(paths),
        'opaque_effects':sum(len(getattr(p['engine'],'opaque_effects',[])) for p in paths)})
report={'passed':all(r['passed'] for r in reports),'exact_graphs':sum(r['passed'] for r in reports),
        'cases':reports,'reference_fixed_before_prediction':True,'application_started':False,
        'scope':'Visible continuation graphs under an opaque effect contract; no invented dependency-internal edges',
        'limits':['Small synthetic Java/Spring graph; not an independent real-project accuracy score',
                  'An opaque dependency may have further unobserved effects/calls outside the supplied skeleton',
                  'Four relation kinds are nonempty; exceptional coverage requires the stated path budget']}
args.output.write_text(json.dumps(report,indent=2,default=serial)+'\n')
print(json.dumps({'passed':report['passed'],'exact_graphs':report['exact_graphs'],'total':len(reports)}))
