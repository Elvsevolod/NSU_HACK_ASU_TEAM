"""Explicit real-source HTTP replay. No oracle is loaded by this runner."""
from pathlib import Path
import argparse
import json
import sys
import time
import resource
from copy import deepcopy
from datetime import datetime
from decimal import Decimal

VARIANT=Path(__file__).resolve().parents[1]
BACKEND=Path(sys.argv[sys.argv.index('--code')+1]) if '--code' in sys.argv else VARIANT/'code'
sys.path.insert(0,str(BACKEND))
from analyzer.project import Project
from analyzer.engine import Engine
from analyzer.state import Database,ScenarioState,U
from analyzer.request import Request,MISSING
from analyzer.__main__ import serial
from analyzer.paths import run_paths,join_states
from analyzer.bean_lifecycle import BeanLifecycle


def json_default(value):
    if isinstance(value,Decimal):return {'$decimal':str(value)}
    if isinstance(value,datetime):return {'$instant':value.isoformat()+'Z'}
    return serial(value)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--path-limit',type=int)
    parser.add_argument('--code',type=Path)
    args=parser.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
    started=time.perf_counter();project=Project(args.input/'skeleton.json',args.input)
    db=Database(args.input/'initial.sql')
    state=ScenarioState(db,{'clock':datetime(2026,10,18),'provided_auth_contexts':{},
        'client_oauth_contexts':{'account-service':{'token':'service-proof','authorities':[],'oauth2_request':{'clientId':'account-service','scope':['server']},'principal':{'name':'account-service'},'authenticated':True}}})
    initial={'authenticated':False,'principal':None,'authorities':[],'oauth2_request':None}
    server={'authenticated':True,'principal':{'name':'account-service'},'authorities':[],'oauth2_request':{'clientId':'account-service','scope':['server']}}
    user={'authenticated':True,'principal':{'name':'aurora'},'authorities':[],'oauth2_request':{'clientId':'browser','scope':['ui']}}
    create={'username':'aurora','password':'alpha-safe-pass'}
    update={'name':'body-mismatch','incomes':None,'expenses':[],'saving':{'amount':20,'currency':'EUR','interest':0,'deposit':False,'capitalization':False},'note':'changed before remote rejection'}
    requests=[('POST','/accounts/',create,initial),('GET',None,MISSING,server),('PUT','/accounts/current',update,user),
        ('GET',None,MISSING,server),('POST','/accounts/',create,initial),
        ('POST','/accounts/',{'username':'occupied','password':'other-safe-pass'},initial),
        ('GET',None,MISSING,server),('POST','/accounts/',MISSING,initial)]
    preparation=time.perf_counter()-started;analysis_started=time.perf_counter()
    rows=[];response_id=U
    for index,(method,path,body,session) in enumerate(requests):
        callbacks=[]
        original=BeanLifecycle.callback
        def observed(self,mid,obj,values,role,*rest,**kwargs):
            receiver=deepcopy(obj)
            result=original(self,mid,obj,values,role,*rest,**kwargs)
            callbacks.append({'method':mid,'role':role,'receiver_type':obj.declared_type,'receiver':receiver,
                'result':deepcopy(result),'arguments':deepcopy(values),
                'declared_return':project.methods[mid].get('return_raw'),'completed_normally':True})
            return result
        BeanLifecycle.callback=observed
        if path is None:path='/accounts/'+response_id if isinstance(response_id,str) else U
        headers={'Accept':'application/json'}
        if body is not MISSING or method in ('POST','PUT','PATCH'):headers['Content-Type']='application/json'
        if session is server:headers['Authorization']='Bearer supplied-server-token'
        if session is user:headers['Authorization']='Bearer supplied-user-token'
        request=Request.http('account-service',method,path,headers,body,session=session)
        candidates=sorted(project.ix.handlers_for(method,[part for part in path.split('/') if part] if isinstance(path,str) else [],'account-service'))
        engine=Engine(project,state)
        path_consistency=None
        if len(candidates)==1 and args.path_limit is not None:
            paths=run_paths(project,state,candidates[0],request,limit=args.path_limit)
            def signature(path):
                e=path['engine']
                observed={'result':path['result'],'outcome':e.outcome,'edges':sorted(e.edges),'requests':e.request_events,
                    'responses':e.http_responses,'tables':{schema+'.'+table:values for (schema,table),values in e.state.database.tables.raw_items()},
                    'unknown_tables':sorted(e.state.database.unknown_tables)}
                return json.dumps(observed,sort_keys=True,default=json_default)
            signatures=[signature(path) for path in paths]
            path_consistency={'path_limit':args.path_limit,'alternatives':len(paths),'all_observables_identical':bool(paths) and len(set(signatures))==1,
                'outcomes':[path['engine'].outcome for path in paths]}
            engine=paths[0]['engine'];result=paths[0]['result'];engine.state=join_states([path['state'] for path in paths])
        else:result=engine.run(candidates[0],request) if len(candidates)==1 else U
        if index==0 and isinstance(result,dict):response_id=result.get('name',U)
        state=engine.state
        BeanLifecycle.callback=original
        row={'n':index+1,'request':request.record(),'candidates':candidates,'result':result,'outcome':engine.outcome,
             'events':engine.events,'requests':engine.request_events,'responses':engine.http_responses,
             'semantic_callbacks':engine.semantic_callbacks,'reflection_edges':sorted(engine.reflection_edges),
             'callbacks':callbacks,
             'warnings':sorted(engine.warnings),'data_operations':engine.data_operations,'persistence':engine.persistence_events,
             'edges':sorted(engine.edges),'tables':{schema+'.'+table:deepcopy(values) for (schema,table),values in state.database.tables.raw_items()},
             'unknown_tables':sorted(state.database.unknown_tables),'path_consistency':path_consistency}
        rows.append(row)
        (args.output/'trace.json').write_text(json.dumps({'targets_started':False,'oracle_loaded':False,'steps':rows},default=json_default,indent=2)+'\n')
        print(json.dumps({'step':index+1,'outcome':row['outcome'],'candidates':len(candidates),'events':len(engine.events),'warnings':row['warnings'][:3]},default=json_default),flush=True)
    (args.output/'trace.json').write_text(json.dumps({'targets_started':False,'oracle_loaded':False,'steps':rows,
        'preparation_seconds':preparation,'analysis_seconds':time.perf_counter()-analysis_started,
        'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'project_constructions':1,
        'external_llm_api_calls':0,'model_calls':0},default=json_default,indent=2)+'\n')


if __name__=='__main__':main()
