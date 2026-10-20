"""Conditional public Spring handler targets, including unresolved broad cases.

A failing target is evidence of missing work, never a portability claim. The
manual reference is not imported by the analyzer or used to build predictions.
"""
import argparse
from copy import deepcopy
import hashlib,json,sys,time,os,subprocess
from pathlib import Path
import yaml

VARIANT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(VARIANT/'code'))
from check_corpus import declarations,metrics
from polygraph.analysis import analyze
from polygraph.grounding import Grounder
from polygraph.project import Project
from polygraph.state import Store


def flatten(mapping,prefix=''):
    result={}
    for key,value in mapping.items():
        name=prefix+'.'+key if prefix else key
        if isinstance(value,dict):result.update(flatten(value,name))
        else:result[name]=value
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--license',type=Path)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    ref_file=Path(__file__).with_name('spring_http_reference.json');reference=json.loads(ref_file.read_text())
    skeleton,_,hashes,errors=declarations(args.source,'java',['accounts','datapoints','users','recipients'])
    names={skeleton['nodes'][node['owner']]['fqn']+'.'+node['name']:mid for mid,node in skeleton['nodes'].items() if node['kind']=='method'}
    config={};config_hashes={}
    for module in ['account-service','statistics-service','auth-service','notification-service']:
        files=['config/src/main/resources/shared/'+module+'.yml','config/src/main/resources/shared/application.yml',module+'/src/main/resources/bootstrap.yml']
        sources=[]
        for file in files:
            raw=(args.source/file).read_bytes();config_hashes[file]=hashlib.sha256(raw).hexdigest()
            sources.append({'name':file,'source':flatten(yaml.safe_load(raw))})
        config[module]={'name':module,'profiles':['default'],'propertySources':sources}
    context={'clock':'2026-01-02T10:00:00Z','timezone':'UTC','principal':{'name':'reader'},'configuration':config,
             'assumptions':{'framework_entry':True,'authorization_passed':True},
             'external_http':[{'method':'GET','url':config['statistics-service']['propertySources'][0]['source']['rates.url']+'/latest?base=USD','response':{'status':200,'body':{'date':'2026-01-02','base':'USD','rates':{'EUR':'0.8','RUB':'60'}}}}]}
    (args.output/'skeleton.json').write_text(json.dumps(skeleton,indent=2)+'\n')
    # Production declarations/configuration are immutable public test inputs.
    # Do not copy Docker images, service launchers, frontend, test applications,
    # or the repository as a whole into the solution artifact.
    fixture_source=args.output/'fixture/src';fixture_hashes={**hashes,**config_hashes}
    for path in args.source.rglob('pom.xml'):
        file=path.relative_to(args.source).as_posix();fixture_hashes[file]=hashlib.sha256(path.read_bytes()).hexdigest()
    for file,digest in fixture_hashes.items():
        raw=(args.source/file).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
        path=fixture_source/file;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    license_file=args.output/'fixture/LICENSE';license_file.write_bytes((args.license or args.source/'LICENCE').read_bytes())
    before=time.perf_counter();project=Project(fixture_source,skeleton,source_configuration=config);grounder=Grounder(project);prep=time.perf_counter()-before
    report={'scope':reference['scope'],'reference_sha256':hashlib.sha256(ref_file.read_bytes()).hexdigest(),'source_sha256':hashes,'configuration_source_sha256':config_hashes,
            'parse_errors':errors,'preparation_seconds':prep,'application_executed':False,'full_Spring_HTTP_support_proven':False,
            'code_sha256':{p.relative_to(VARIANT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((VARIANT/'code').rglob('*.py'))},'cases':[]}
    report['fixture_sha256']=fixture_hashes;report['fixture_license_sha256']=hashlib.sha256(license_file.read_bytes()).hexdigest()
    environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(VARIANT/'code')}
    saving={'amount':'100','currency':'USD','interest':'0','deposit':False,'capitalization':False}
    original={'name':'reader','lastSeen':None,'incomes':[],'expenses':[],'saving':saving,'note':'Before'}
    update={'incomes':[{'title':'Salary','amount':'20','currency':'USD','period':'DAY','icon':'salary.png'}],
            'expenses':[{'title':'Rent','amount':'8','currency':'EUR','period':'DAY','icon':'rent.png'}],'saving':saving,'note':'Changed'}
    for case in reference['cases']:
        rows={'resource:accounts':() if case['kind']=='save-missing' else (deepcopy(original),),'resource:datapoints':(),'resource:users':(),'resource:recipients':()}
        read={'module':'account-service','path':'/accounts/current'}
        if case['kind']=='read':requests=[read]
        elif case['kind']=='missing-record':requests=[{'module':'account-service','path':'/accounts/absent'}]
        elif case['kind']=='wrong-prefix':requests=[{'module':'account-service','path':'/current'}]
        elif case['kind']=='wrong-method':requests=[{'module':'account-service','path':'/accounts/current','method':'POST'}]
        elif case['kind'] in {'invalid-body','save-missing'}:requests=[{'module':'account-service','path':'/accounts/current','method':'PUT','body':{**update,'saving':None} if case['kind']=='invalid-body' else update}]
        else:requests=[read,{'module':'account-service','path':'/accounts/current','method':'PUT','body':update},read,{'module':'statistics-service','path':'/statistics/current'}]
        scenario={'project':skeleton['project'],'id':case['id'],'steps':[{'action':'Explicit conditional public-source HTTP request','request':request} for request in requests]}
        (args.output/(case['id']+'-input.json')).write_text(json.dumps({'scenario':scenario,'context':{**context,'tables':rows}},indent=2)+'\n')
        expected={('scenario:'+case['id'],'executes',names[name]) for name in case['methods']}
        expected|={(names[a],'calls',names[b]) for a,b in case['calls']};expected|={(names[a],'data','resource:'+table) for a,table in case['data']}
        expected|={(names[a],'remote',names[b]) for a,b in case.get('remote',[])}
        start=time.perf_counter();block,detail=analyze(project,Store(deepcopy(rows)),context,scenario,grounder,path_limit=16);duration=time.perf_counter()-start
        actual={tuple(edge[k] for k in ['source','relation','target']) for edge in block['edges']}
        paths=detail['paths'];checks={'edges':expected==actual,'one_path':len(paths)==1,'statuses':bool(paths) and all([step['response']['status'] for step in path['steps']]==case['statuses'] for path in paths)}
        if case.get('expected_null'):checks['body']=bool(paths) and all(path['steps'] and path['steps'][-1]['response']['body'] is None for path in paths)
        if 'expected_note' in case:
            checks['note']=bool(paths) and all(isinstance(path['state'].get('resource:accounts'),list) and path['state']['resource:accounts'] and path['state']['resource:accounts'][0].get('note')==case['expected_note'] for path in paths)
        if case['kind']=='update-chain':
            checks['data_point']=bool(paths) and all(isinstance(path['state'].get('resource:datapoints'),list) and len(path['state']['resource:datapoints'])==1 for path in paths)
            checks['statistics']=bool(paths) and all(isinstance(path['state'].get('resource:datapoints'),list) and len(path['state']['resource:datapoints'])==1 and all(str(path['state']['resource:datapoints'][0].get('statistics',{}).get(name))==value for name,value in case['expected_statistics'].items()) for path in paths)
        scenario_file=args.output/(case['id']+'-scenario.json');scenario_file.write_text(json.dumps(scenario,indent=2)+'\n')
        context_file=args.output/(case['id']+'-context.json');context_file.write_text(json.dumps({**context,'tables':rows},indent=2)+'\n')
        command=[sys.executable,'-B',str(VARIANT/'code/offline_run.py'),'--source',str(fixture_source),'--skeleton',str(args.output/'skeleton.json'),
                 '--scenarios',str(scenario_file),'--context',str(context_file),'--path-limit','16']
        replays={}
        for mode,seed in [('cold','7'),('repeat','31')]:
            output=args.output/(case['id']+'-'+mode+'.json');diagnostics=args.output/(case['id']+'-'+mode+'-report.json')
            cmd=command+['--output',str(output),'--report',str(diagnostics)]
            before=time.perf_counter();process=subprocess.run(cmd,capture_output=True,text=True,env={**environment,'PYTHONHASHSEED':seed});wall=time.perf_counter()-before
            (args.output/(case['id']+'-'+mode+'.stdout.txt')).write_text(process.stdout)
            (args.output/(case['id']+'-'+mode+'.stderr.txt')).write_text(process.stderr)
            checks[mode+'_offline_exit']=process.returncode==0
            if process.returncode:continue
            answer=json.loads(output.read_text());trace=json.loads(diagnostics.read_text())
            checks[mode+'_graph']=answer['scenarios'][case['id']]==block
            checks[mode+'_state_and_steps']=[{key:p[key] for key in ['steps','state','edges','coverage']} for p in trace['scenarios'][case['id']]['paths']]==[{key:p[key] for key in ['steps','state','edges','coverage']} for p in paths]
            replays[mode]={'command':cmd,'wall_seconds':wall,'measurements':{key:trace[key] for key in ['preparation_seconds','analysis_seconds','elapsed_seconds','peak_rss_bytes','model_calls','submission_sha256']}}
        report['cases'].append({'id':case['id'],'passed':bool(all(checks.values())),'checks':checks,'relations':metrics(expected,actual),'analysis_seconds':duration,'offline_replay':replays,'detail':detail})
    report['source_unchanged']=all(hashlib.sha256((args.source/file).read_bytes()).hexdigest()==digest for file,digest in fixture_hashes.items())
    report['passed']=all(case['passed'] for case in report['cases']);report['deployment_configuration']=project.configuration.summary()
    (args.output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'scope':report['scope'],'cases':[{k:case[k] for k in ['id','passed','checks']} for case in report['cases']]}))


if __name__=='__main__':main()
