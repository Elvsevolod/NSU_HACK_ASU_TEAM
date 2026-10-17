"""Fixed public-source HTTP oracle. Never imports or starts the target app."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import argparse
import sys
import time
import os
import subprocess

VARIANT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(VARIANT/'code'))
import jwt
from pwdlib import PasswordHash
from check_corpus import declarations, metrics
from polygraph.analysis import analyze
from polygraph.grounding import Grounder
from polygraph.project import Project
from polygraph.state import Store


CLOCK='2026-01-02T10:00:00Z'
USER='10000000-0000-4000-8000-000000000001'
OTHER='20000000-0000-4000-8000-000000000001'
ITEM='30000000-0000-4000-8000-000000000001'
SECRET='public-fixture-only-'+ 'a'*48
PASSWORD='fixture-password-39'


def request(method,path,**values):return {'action':'Explicit public source HTTP contract','request':{'method':method,'path':path,**values}}


def scenarios(case):
    login=request('POST','/api/v1/login/access-token',form={'username':'reader@example.com','password':case.get('password',PASSWORD)})
    authorization={'Authorization':{'$concat':['Bearer ',{'$ref':'steps.1.body.access_token'}]}}
    endpoint='/api/v1/items/{id}'
    if case['id']=='login-create-update-read-delete-missing':
        address={'path_params':{'id':{'$ref':'steps.3.body.id'}},'headers':authorization}
        steps=[login,request('POST','/api/v1/login/test-token',headers=authorization),
               request('POST','/api/v1/items/',headers=authorization,body={'title':'Before','description':'keep'}),
               request('PUT',endpoint,**address,body={'title':'Changed'}),request('GET',endpoint,**address),
               request('DELETE',endpoint,**address),request('GET',endpoint,**address)]
    elif case['id'] in {'wrong-password','inactive-account'}:steps=[login]
    elif case['id']=='missing-bearer':steps=[request('GET','/api/v1/items/'+ITEM)]
    elif case['id'] in {'invalid-signature-token','expired-token'}:
        clock=datetime.fromisoformat(CLOCK.replace('Z','+00:00'))
        token=jwt.encode({'exp':clock-timedelta(seconds=1) if case['id']=='expired-token' else clock+timedelta(minutes=15),'sub':USER},SECRET if case['id']=='expired-token' else 'wrong-fixture-only-'+'b'*48,algorithm='HS256')
        steps=[request('GET','/api/v1/items/'+ITEM,headers={'Authorization':'Bearer '+token})]
    elif case['id']=='foreign-owner':steps=[login,request('GET','/api/v1/items/'+ITEM,headers=authorization)]
    else:steps=[login,request('POST','/api/v1/items/',headers=authorization,body={'title':''})]
    return {'project':'public-python','id':case['id'],'steps':steps}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    reference_path=Path(__file__).with_name('http_reference.json');reference=json.loads(reference_path.read_text())
    skeleton,_,hashes,parse_errors=declarations(args.source,'python',['user','item'])
    names={Path(node['file']).with_suffix('').as_posix().replace('/','.')+'.'+node['name']:mid for mid,node in skeleton['nodes'].items() if node['kind']=='method'}
    (args.output/'skeleton.json').write_text(json.dumps(skeleton,indent=2)+'\n')
    # Stable input data, prepared only by trusted library code. No app imports.
    hash_file=args.output/'password-hash.txt'
    if not hash_file.exists():hash_file.write_text(PasswordHash.recommended().hash(PASSWORD)+'\n')
    password_hash=hash_file.read_text().strip()
    assert PasswordHash.recommended().verify(PASSWORD,password_hash)
    config={'API_V1_STR':'/api/v1','SECRET_KEY':SECRET,'ACCESS_TOKEN_EXPIRE_MINUTES':15,'DATABASE_URL':'postgresql+psycopg://fixture:fixture@database/portable','PROJECT_NAME':'Public source probe','FRONTEND_HOST':'http://localhost:5173','SENTRY_DSN':None,'FASTAPI_ENV':None,'FIRST_SUPERUSER':'reader@example.com','FIRST_SUPERUSER_PASSWORD':PASSWORD}
    context={'clock':CLOCK,'globals':{'app.core.config.settings':config},'sql_dialect':'postgres','framework_versions':{'backend':{'fastapi':'0.143.3','pydantic':'2.14.1','PyJWT':'2.15.1','pwdlib':'0.3.1'}}}
    started=time.perf_counter();project=Project(args.source,skeleton,source_globals=context['globals']);grounder=Grounder(project);preparation=time.perf_counter()-started
    fixture_source=args.output/'fixture/src'
    analysis_hashes={file:hashlib.sha256(raw).hexdigest() for file,raw in project.sources.items()}
    for file,raw in project.sources.items():
        path=fixture_source/file;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    license_file=args.output/'fixture/LICENSE';license_file.write_bytes((args.source.parent/'LICENSE').read_bytes())
    report={'reference_sha256':hashlib.sha256(reference_path.read_bytes()).hexdigest(),'scope':reference['scope'],'application_executed':False,'source_sha256':hashes,'parse_errors':parse_errors,'preparation_seconds':preparation,'cases':[],
            'code_sha256':{p.relative_to(VARIANT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((VARIANT/'code').rglob('*.py'))}}
    report['analysis_source_sha256']=analysis_hashes
    report['fixture_license_sha256']=hashlib.sha256(license_file.read_bytes()).hexdigest()
    environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(VARIANT/'code')}
    for case in reference['cases']:
        user={'id':USER,'email':'reader@example.com','is_active':case.get('active',True),'is_superuser':False,'full_name':'Reader','hashed_password':password_hash,'created_at':None,'items':[]}
        item={'id':ITEM,'title':'Existing','description':'keep','owner_id':OTHER,'created_at':None,'owner':None}
        rows={'resource:user':(user,), 'resource:item':(item,) if case['id']=='foreign-owner' else ()}
        inputs=scenarios(case);(args.output/(case['id']+'-input.json')).write_text(json.dumps({'scenario':inputs,'context':context,'tables':rows},indent=2)+'\n')
        started=time.perf_counter();block,detail=analyze(project,Store(deepcopy(rows)),context,inputs,grounder,path_limit=32);duration=time.perf_counter()-started
        expected_methods=list(case['methods']);expected_calls=list(case['calls']);expected_data=list(case['data'])
        for group in case['groups']:
            expected_methods.extend(reference['groups'].get(group+'_methods',[]));expected_calls.extend(reference['groups'].get(group+'_calls',[]));expected_data.extend(reference['groups'].get(group+'_data',[]))
        expected={('scenario:'+case['id'],'executes',names[name]) for name in expected_methods}
        expected|={(names[a],'calls',names[b]) for a,b in expected_calls};expected|={(names[a],'data','resource:'+table) for a,table in expected_data}
        actual={tuple(e[k] for k in ['source','relation','target']) for e in block['edges']};comparison=metrics(expected,actual)
        paths=detail['paths'];checks={'edges':actual==expected,'one_path':len(paths)==1,'statuses':all([step['response']['status'] for step in p['steps']]==case['statuses'] for p in paths)}
        if case.get('detail'):checks['detail']=all(p['steps'][-1]['response']['body']=={'detail':case['detail']} for p in paths if p['steps'])
        if case['id']=='login-create-update-read-delete-missing' and paths:
            steps=paths[0]['steps'];checks['complete_chain']=len(steps)==7
            if len(steps)==7:
                checks['response_projection']='hashed_password' not in steps[1]['response']['body'] and 'owner' not in steps[2]['response']['body']
                checks['state_and_result']=paths[0]['state']['resource:item']==[] and steps[4]['response']['body']['title']=='Changed' and steps[4]['response']['body']['description']=='keep'
                checks['token_transferred']=steps[2]['request']['headers']['Authorization']=='Bearer '+steps[0]['response']['body']['access_token']
        scenario_file=args.output/(case['id']+'-scenario.json');scenario_file.write_text(json.dumps(inputs,indent=2)+'\n')
        context_file=args.output/(case['id']+'-context.json');context_file.write_text(json.dumps({**context,'tables':rows},indent=2)+'\n')
        command=[sys.executable,'-B',str(VARIANT/'code/offline_run.py'),'--source',str(args.source),'--skeleton',str(args.output/'skeleton.json'),
                 '--scenarios',str(scenario_file),'--context',str(context_file),'--sql-dialect','postgres','--path-limit','32']
        replay={}
        for mode,seed in [('cold','7'),('repeat','31')]:
            output=args.output/(case['id']+'-'+mode+'.json');diagnostics=args.output/(case['id']+'-'+mode+'-report.json')
            actual_command=command+['--output',str(output),'--report',str(diagnostics)]
            before=time.perf_counter();process=subprocess.run(actual_command,capture_output=True,text=True,env={**environment,'PYTHONHASHSEED':seed});wall=time.perf_counter()-before
            (args.output/(case['id']+'-'+mode+'.stdout.txt')).write_text(process.stdout)
            (args.output/(case['id']+'-'+mode+'.stderr.txt')).write_text(process.stderr)
            checks[mode+'_offline_exit']=process.returncode==0
            if process.returncode:continue
            result=json.loads(output.read_text());trace=json.loads(diagnostics.read_text())
            checks[mode+'_graph']=result['scenarios'][case['id']]==block
            checks[mode+'_state_and_steps']=[{key:p[key] for key in ['steps','state','edges','coverage']} for p in trace['scenarios'][case['id']]['paths']]==[{key:p[key] for key in ['steps','state','edges','coverage']} for p in paths]
            replay[mode]={'command':actual_command,'wall_seconds':wall,'measurements':{k:trace[k] for k in ['preparation_seconds','analysis_seconds','elapsed_seconds','peak_rss_bytes','native_security','model_calls','submission_sha256']}}
        row={'id':case['id'],'passed':all(checks.values()),'checks':checks,'relations':comparison,'analysis_seconds':duration,'offline_replay':replay,'detail':detail}
        report['cases'].append(row)
    report['source_unchanged']=all(hashlib.sha256((args.source/file).read_bytes()).hexdigest()==digest for file,digest in analysis_hashes.items())
    report['passed']=report['source_unchanged'] and all(case['passed'] for case in report['cases']);(args.output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'cases':[{k:case[k] for k in ['id','passed','checks']} for case in report['cases']]}))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
