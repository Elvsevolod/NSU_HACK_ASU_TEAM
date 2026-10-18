"""Independent stateful warehouse HTTP journeys, with predeclared graph oracles.

Run the exact same source/reference against either frozen parent or candidate.
Small synthetic components complement public-project checks, not replace them.
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
from analyzer.state import ScenarioState
from analyzer.paths import run_paths
from analyzer.__main__ import serial

results=[]
for label,query,success in [('repeated-query','quantity=2&tag=fragile&tag=cold',True),
                            ('missing','tag=fragile&tag=cold',False),
                            ('overflow','quantity=2147483648&tag=fragile&tag=cold',False),
                            ('malformed','quantity=broken&tag=fragile&tag=cold',False)]:
    sources={
      'Caller.java':'''import java.util.UUID;import org.springframework.web.client.RestTemplate;
        class Caller {RestTemplate rest;String start(){String id=UUID.randomUUID().toString();try{
          rest.postForObject("http://warehouse/holds/"+id+"?'''+query+'''",null,String.class);
          return rest.getForObject("http://warehouse/holds/"+id,String.class);
        }catch(HttpClientErrorException e){return rejected();}}
        String rejected(){return "rejected";}}''',
      'Api.java':'''import java.util.*;class Api {Store store;
        @PostMapping("/holds/{key}") String reserve(@PathVariable String key,@RequestParam int quantity,@RequestParam List<String> tag){
          if(tag.size()!=2 || !tag.get(0).equals("fragile") || !tag.get(1).equals("cold")){return wrong();}
          Hold hold=new Hold();hold.id=key;hold.quantity=quantity;store.save(hold);return "saved";}
        @GetMapping("/holds/{key}") String read(@PathVariable String key){Hold hold=store.findById(key);if(hold==null){return wrong();}return "found:"+hold.quantity;}
        String wrong(){return "wrong";}}
        @Entity @Table(name="holds") class Hold {@Id String id;int quantity;}
        interface Store extends JpaRepository<Hold,String>{Hold save(Hold item);Hold findById(String id);}''',
      'Gate.java':'''class Gate extends OncePerRequestFilter {
        void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain){before();chain.doFilter(req,res);after();}
        void before(){}void after(){}}'''}
    work=args.work/label
    project,db,ids=build(work,sources,rows={'holds':[]})
    skeleton=project.skeleton
    for unit in ('client','warehouse'):skeleton['nodes']['module:'+unit]={'kind':'module','name':unit,'deployment_units':[unit]}
    for node in skeleton['nodes'].values():
        if node.get('file'):node['module']='client' if node['file']=='Caller.java' else 'warehouse'
    (work/'skeleton.json').write_text(json.dumps(skeleton))
    methods=['Caller.start','Gate.doFilterInternal','Gate.before','Gate.after']+(['Api.reserve','Api.read'] if success else ['Caller.rejected'])
    expected={('', 'executes',ids[name]) for name in methods}
    expected|={(ids['Gate.doFilterInternal'],'calls',ids['Gate.'+name]) for name in ('before','after')}
    if success:
        expected|={(ids['Caller.start'],'remote',ids['Api.'+name]) for name in ('reserve','read')}
        expected|={(ids['Api.'+name],'data','res:table:service.holds') for name in ('reserve','read')}
    else:expected.add((ids['Caller.start'],'calls',ids['Caller.rejected']))
    reference={'edges':sorted(expected),'result':'found:2' if success else 'rejected','rows':1 if success else 0}
    reference_path=work/'reference.json'
    reference_path.write_text(json.dumps(reference,indent=2)+'\n')
    reference_sha=hashlib.sha256(reference_path.read_bytes()).hexdigest()
    project=Project(work/'skeleton.json',work)
    paths=run_paths(project,ScenarioState(db),ids['Caller.start'],{},limit=8)
    found=set.union(*(set(p['engine'].edges) for p in paths))
    comparisons={}
    for relation in ('executes','calls','remote','data'):
        wanted={e for e in expected if e[1]==relation};actual={e for e in found if e[1]==relation}
        comparisons[relation]={'tp':len(wanted&actual),'fp':len(actual-wanted),'fn':len(wanted-actual),
            'iou':len(wanted&actual)/len(wanted|actual) if wanted|actual else None,'exact':actual==wanted}
    states=[p['engine'].state.database.rows(project.nodes['res:table:service.holds']) for p in paths]
    correct=found==expected and all(p['result']==reference['result'] for p in paths) and all(rows is not None and len(rows)==reference['rows'] for rows in states)
    results.append({'case':label,'passed':correct,'relations':comparisons,'reference_sha256':reference_sha,
        'sources_sha256':{name:hashlib.sha256(s.encode()).hexdigest() for name,s in sources.items()},
        'reference':reference,'predicted_edges':sorted(found),'results':[p['result'] for p in paths],
        'row_counts':[len(rows) if rows is not None else None for rows in states],
        'warnings':sorted(set.union(*(p['engine'].warnings for p in paths)))})
    assert hashlib.sha256(reference_path.read_bytes()).hexdigest()==reference_sha
report={'passed':all(r['passed'] for r in results),'exact_graphs':sum(r['passed'] for r in results),'cases':results,
        'reference_fixed_before_prediction':True,'application_started':False,
        'limits':['Synthetic two-service warehouse; not a representative corpus','Filter registration is assumed by the inherited core',
                  'Security, custom codecs and general ORM lifecycle are outside this panel']}
args.output.write_text(json.dumps(report,indent=2,default=serial)+'\n')
print(json.dumps({'passed':report['passed'],'exact_graphs':report['exact_graphs'],'total':len(results)}))
