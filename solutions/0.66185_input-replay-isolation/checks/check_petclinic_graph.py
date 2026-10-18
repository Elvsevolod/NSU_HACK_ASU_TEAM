"""Complete source reference for a bounded authorized Petclinic body journey.

This is a component graph test, not an HTTP/security/validation execution trace.
The source adapter supplies skeleton facts; runtime core has no Petclinic rules.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys
import time

VARIANT=Path(__file__).resolve().parents[1]
bootstrap=argparse.ArgumentParser(add_help=False)
bootstrap.add_argument('--code',type=Path,default=VARIANT/'code')
selected,_=bootstrap.parse_known_args()
sys.path[:0]=[str(selected.code),str(selected.code/'tests')]
from builders import build
from analyzer.project import Project
from analyzer.state import ScenarioState
from analyzer.engine import Engine
from analyzer.__main__ import serial


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=serial)+'\n')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--code',type=Path,default=VARIANT/'code')
    parser.add_argument('--work-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.work_dir.exists():raise ValueError('Use a fresh work directory')
    started=time.perf_counter()
    sources={p.relative_to(args.repository).as_posix():p.read_text()
             for p in sorted((args.repository/'src/main/java').rglob('*.java')) if p.name!='package-info.java'}
    fixture=args.work_dir/'inputs'
    project,db,ids=build(fixture,sources,module='clinic',rows={'types':[{'id':7,'name':'canine'}]})
    skeleton=project.skeleton
    for node in skeleton['nodes'].values():
        if node['kind']=='type':
            package=re.search(r'^package\s+([\w.]+)\s*;',sources[node['file']],re.M)
            if package:node['fqn']=package[1]+'.'+node['fqn']
    skeleton['nodes']['config:profiles']={'kind':'config_entry','module':'clinic',
        'key':'spring.profiles.active','value':'hsqldb,spring-data-jpa',
        'file':'src/main/resources/application.properties'}
    # Generic test-skeleton adapter: custom repository interface -> entity table
    # from an active Spring Data interface's Repository<Entity, Key> declaration.
    mappings={}
    for source in sources.values():
        match=re.search(r'interface\s+\w+\s+extends\s+(\w+)\s*,\s*Repository\s*<\s*(\w+)',source)
        if match:
            entity=next((n for n in skeleton['nodes'].values() if n['kind']=='type' and n['fqn'].endswith('.'+match[2])),None)
            resources=[rid for rid,n in skeleton['nodes'].items() if n['kind']=='data_resource' and entity
                       and any(origin.get('file')==entity['file'] for origin in n.get('origin',[]))]
            if len(resources)==1:mappings[match[1]]=resources[0]
    for cid,node in skeleton['nodes'].items():
        if node['kind']=='call_site' and node.get('receiver_type') in mappings:
            edge={'source':cid,'type':'data_access','target':mappings[node['receiver_type']]}
            if edge not in skeleton['edges']:skeleton['edges'].append(edge)
    save(fixture/'skeleton.json',skeleton)
    # Reference is fixed BEFORE the prediction core is created/run. It is
    # manually enumerated from the controller/service/accessor source bodies.
    get=ids['PetTypeRestController.getPetType'];update=ids['PetTypeRestController.updatePetType']
    find=ids['ClinicServiceImpl.findPetTypeById'];persist=ids['ClinicServiceImpl.savePetType']
    getter=ids['NamedEntity.getName'];setter=ids['NamedEntity.setName'];table='res:table:clinic.types'
    read={('', 'executes',get),('', 'executes',find),(get,'calls',find),(find,'data',table)}
    write={('', 'executes',method) for method in (update,find,persist,getter,setter)}
    write|={(update,'calls',method) for method in (find,persist,getter,setter)}
    write|={(find,'data',table),(persist,'data',table)}
    expected=[read,write,read]
    reference={'scope':'authorized controller/service method bodies with supplied successful BindingResult',
        'preconditions':{'profiles':['hsqldb','spring-data-jpa'],'authority':'ROLE_VET_ADMIN',
                         'validation_errors':[],'initial_types':[{'id':7,'name':'canine'}]},
        'request_edges':[sorted(edges) for edges in expected],
        'union':sorted(set.union(*expected)),
        'source_evidence':{mid:{'file':skeleton['nodes'][mid]['file'],'line':skeleton['nodes'][mid]['line']}
                           for mid in (get,update,find,persist,getter,setter)},
        'limits':['Component test; security, filters, Jackson and bean validation not exercised end to end',
                  'Skeleton supplied by source-only validation adapter, not organizer metadata',
                  'No interservice request in this journey; remote IoU is empty/empty, not tested']}
    save(args.work_dir/'reference.json',reference)
    reference_hash=hashlib.sha256((args.work_dir/'reference.json').read_bytes()).hexdigest()
    project=Project(fixture/'skeleton.json',fixture)
    state=ScenarioState(db)
    requests=[('GET','/api/pettypes/7',get,{'petTypeId':7}),
              ('PUT','/api/pettypes/7',update,{'petTypeId':7,
                  'petType':{'id':7,'name':'hound'},
                  'bindingResult':{'__type__':'BindingResult','__binding_errors__':[]}}),
              ('GET','/api/pettypes/7',get,{'petTypeId':7})]
    observed=[]
    for number,(verb,url,entry,params) in enumerate(requests):
        assert project.ix.handlers_for(verb,url)=={entry}
        engine=Engine(project,state)
        result=engine.run(entry,params)
        observed.append({'request':number+1,'method':verb,'url':url,'edges':sorted(engine.edges),
                         'result':result,'outcome':engine.outcome,'warnings':sorted(engine.warnings),
                         'approximate':engine.approximate,'state_types':deepcopy(state.database.rows(project.nodes[table]))})
    save(args.work_dir/'prediction.json',observed)
    actual=[set(map(tuple,row['edges'])) for row in observed]
    comparisons=[]
    for number,(wanted,found) in enumerate(zip(expected,actual)):
        comparisons.append({'request':number+1,'relations':{
            rel:{'expected':len(a:={edge for edge in wanted if edge[1]==rel}),
                 'actual':len(b:={edge for edge in found if edge[1]==rel}),
                 'iou':len(a&b)/len(a|b) if a|b else 1.0,
                 'missing':sorted(a-b),'extra':sorted(b-a),'nonempty':bool(a|b)}
            for rel in ('executes','calls','remote','data')}})
    report={'repository':'https://github.com/spring-petclinic/spring-petclinic-rest',
            'commit':'2cd2f9c7a3eee55d7c6d09fa100e02341ae27070','tag':'v2.1.5',
            'source_files':len(sources),'source_sha256':{name:hashlib.sha256(source.encode()).hexdigest() for name,source in sources.items()},
            'reference_sha256':reference_hash,'reference_fixed_before_prediction':True,
            'application_started':False,'full_bounded_graph_compared':True,'full_http_graph_compared':False,
            'comparisons':comparisons,'state_update_preserved':observed[-1]['result'].get('name')=='hound',
            'elapsed_seconds':time.perf_counter()-started,'limits':reference['limits']}
    report['passed']=all(row['relations'][rel]['iou']==1 for row in comparisons for rel in ('executes','calls','data')) and report['state_update_preserved']
    assert hashlib.sha256((args.work_dir/'reference.json').read_bytes()).hexdigest()==reference_hash
    save(args.output,report)
    print(json.dumps({key:value for key,value in report.items() if key not in ('source_sha256',)},ensure_ascii=False))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
