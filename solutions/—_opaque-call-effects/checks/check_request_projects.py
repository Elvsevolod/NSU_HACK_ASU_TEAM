"""Pinned public source contracts; no server or application is launched.

These are route/argument probes, not complete execution graph measurements.
The fixture adapter supplies a skeleton derived from unmodified Java sources.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

VARIANT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(VARIANT/'code'),str(VARIANT/'code/tests')]
from builders import build
from analyzer.project import Project
from analyzer.engine import Engine
from analyzer.state import ScenarioState
from analyzer.__main__ import serial
from analyzer.symbolic_text import concat_text


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--petclinic',type=Path,required=True)
    parser.add_argument('--piggymetrics',type=Path,required=True)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    assert not args.work.exists()
    args.work.mkdir(parents=True)
    atom={'__symbol__':'external-id','__type__':'String','__uuid_text__':True,'__length__':36}
    panels=[('petclinic',args.petclinic,'src/main/java',[
        ('PetTypeRestController.getPetType','/api/pettypes/7',[7]),
        ('PetTypeRestController.getPetType','/api/pettypes/2147483648','reject'),
        ('PetTypeRestController.getPetType','/api/pettypes/not-a-number','reject'),
        ('OwnerRestController.getOwner','/api/owners/-2147483648',[-2147483648]),
        ('OwnerRestController.getOwnersList','/api/owners/all/lastname/A%20B',['A B']),
        ('OwnerRestController.getOwnersList','/api/owners/all/lastname/A+B',['A+B']),
        ('OwnerRestController.getOwnersList',concat_text(concat_text('/api/owners/all/lastname/',atom),'?unused=1&unused=2'),[atom]),
    ]),('piggymetrics-account',args.piggymetrics,'account-service/src/main/java',[
        ('AccountController.getAccountByName','/alice%20smith',['alice smith']),
        ('AccountController.getAccountByName','/alice%2520smith',['alice%20smith']),
        ('AccountController.getAccountByName',concat_text(concat_text('/',atom),'?view=a&view=b#ignored'),[atom]),
    ]),('piggymetrics-statistics',args.piggymetrics,'statistics-service/src/main/java',[
        ('StatisticsController.getStatisticsByAccountName','/user+suffix?ignored=x',['user+suffix']),
        ('StatisticsController.getStatisticsByAccountName',concat_text(concat_text('/',atom),'?ignored=x'),[atom]),
    ])]
    reports=[]
    for name,repository,source_directory,probes in panels:
        sources={p.relative_to(repository).as_posix():p.read_text() for p in sorted((repository/source_directory).rglob('*.java')) if p.name!='package-info.java'}
        work=args.work/name
        project,db,ids=build(work,sources,module=name)
        for node in project.skeleton['nodes'].values():
            if node['kind']=='type':
                package=re.search(r'^package\s+([\w.]+)\s*;',sources[node['file']],re.M)
                if package:node['fqn']=package[1]+'.'+node['fqn']
        (work/'skeleton.json').write_text(json.dumps(project.skeleton))
        project=Project(work/'skeleton.json',work)
        # Source contract expectations are fixed before any argument binding.
        reference=[{'handler':ids[handler],'wire_url':url,'expected':expected} for handler,url,expected in probes]
        (work/'reference.json').write_text(json.dumps(reference,indent=2,default=serial)+'\n')
        results=[]
        for probe in reference:
            entry,url,expected=probe['handler'],probe['wire_url'],probe['expected']
            engine=Engine(project,ScenarioState(db))
            address=engine.request_address(url)
            selected=project.ix.handlers_for('GET',address['segments'])
            if expected=='reject':
                response,entered=engine.http_invoke(entry,lambda:engine.request_arguments(entry,url,{},None,'source probe'),'source probe')
                found={'status':response['status'],'entered':entered,'edges':sorted(engine.edges),
                       'status_measured':False,'status_limit':'Public source has a custom exception resolver; its status mapping is outside this probe'}
                correct=not entered and not any(t==entry for _,_,t in engine.edges) and any('HTTP binding rejected' in w for w in engine.warnings)
            else:
                found=engine.request_arguments(entry,url,{},None,'source probe')
                correct=found==expected
            results.append({**probe,'selected':sorted(selected),'observed':found,'passed':correct and selected=={entry},'warnings':sorted(engine.warnings)})
        reports.append({'project':name,'source_files':len(sources),
            'source_sha256':{p:hashlib.sha256(s.encode()).hexdigest() for p,s in sources.items()},
            'indexed_methods':len(project.methods),'source_parse_errors':project.source_errors,'probes':results})
    report={'passed':all(p['passed'] for r in reports for p in r['probes']),'panels':reports,
        'repositories':{'petclinic':{'url':'https://github.com/spring-petclinic/spring-petclinic-rest','commit':'2cd2f9c7a3eee55d7c6d09fa100e02341ae27070'},
                        'piggymetrics':{'url':'https://github.com/sqshq/piggymetrics','commit':'6bb2cf9ddbca980b664d3edbb6ff775d75369278'}},
        'application_started':False,'reference_fixed_before_binding':True,
        'scope':'Supplied wire URLs, source routing and named arguments; invalid numbers stop before handler execution',
        'limits':['Security authorization is a precondition; not a complete security/HTTP trace',
                  'Public projects here exercise path contracts; query multiplicity is tested in the independent graph panel',
                  'Source skeleton supplied by validation adapter; not an automatic skeleton product']}
    args.output.write_text(json.dumps(report,indent=2,default=serial)+'\n')
    print(json.dumps({'passed':report['passed'],'probes':sum(len(r['probes']) for r in reports),'source_files':{r['project']:r['source_files'] for r in reports}}))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
