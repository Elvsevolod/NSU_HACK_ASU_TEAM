"""Current TT source/UI controls; no supplied token, ID, guard override or gold."""
import argparse,gzip,hashlib,json,sys
from datetime import datetime
from pathlib import Path
V=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(V/'code'))
from analyzer.project import Project
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex,ContractGrounder,read_static_context
from analyzer.state import Database,ScenarioState,U
from analyzer.paths import run_paths
from analyzer.request import Request
from analyzer.__main__ import serial


def scrub(value,key=''):
    if any(part in key.lower() for part in ('token','password','secret')):
        return {'observed':value is not U,'sha256':hashlib.sha256(str(value).encode()).hexdigest() if value is not U else None}
    if isinstance(value,dict):return {k:scrub(v,k) for k,v in value.items()}
    if isinstance(value,list):return [scrub(v) for v in value]
    return value


def main():
    p=argparse.ArgumentParser();p.add_argument('--challenge',type=Path,required=True);p.add_argument('--stage-report',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
    project=Project(a.challenge/'skeleton/trainticket.json.gz',a.challenge/'targets/trainticket');frontend=Frontend(project)
    index=ContractIndex(project,frontend);context=read_static_context(project.skeleton.get('context',{}))
    database=Database(a.challenge/'context/db-after-warmup.sql.gz');database.schemas=project.schemas
    action=json.loads((a.challenge/'scenarios/S0.json').read_text())['steps'][0]['action']
    entries=project.ix.handlers_for('POST','/api/v1/users/login','ts-auth-service');assert len(entries)==1
    entry=next(iter(entries));sites={key:c for key,c in index.contracts.items() if c['entry']==entry and c['site']}
    controls=[]
    class SourceSiteOnly:
        def __init__(self,row):self.row=row
        def rank(self,*args):return [self.row]
    for key,c in sorted(sites.items()):
        state=ScenarioState(database,context)
        proposed,detail=ContractGrounder(project,frontend,SourceSiteOnly((1,key,c)),None,context).step(action,state)
        controls.append({'file':c['site']['file'],'line':c['site'].get('line'),'site':c['site']['id'],
            'source_conditions':c['site'].get('conditions',[]),'proposals':len(proposed),'selection':detail,
            'guard_override':False,'storage_assignments':[{k:e.get(k) for k in ('space','key','expr','conditions')}
                for e in c['site'].get('effects',[]) if e.get('space')=='storage']})
    credentials={key:context['facts'][key]['value'] for key in ('username','password')}
    request=Request.http('ts-auth-service','POST','/api/v1/users/login',
        {'content-type':'application/json'},credentials,provenance={'source':'provided context; explicit HTTP control'})
    def observed(rows):return [{'result':r['result'],'outcome':r['engine'].outcome,'warnings':sorted(r['engine'].warnings),
        'unknown_tables':sorted(r['state'].database.unknown_tables),'edges':sorted(r['engine'].edges),
        'data_operations':r['engine'].data_operations} for r in rows]
    def run_chain(supplied):
        first=run_paths(project,ScenarioState(database,supplied),entry,request,limit=4)
        chain=[{'step':'explicit login','alternatives':observed(first)}]
        successful=[r for r in first if r['engine'].outcome=='returned' and isinstance(r['result'],dict)
            and r['result'].get('status')==1 and isinstance(r['result'].get('data'),dict)]
        for producer in successful:
            account_id=producer['result']['data'].get('userId',U)
            if not isinstance(account_id,str):continue
            path='/api/v1/contactservice/contacts/account/'+account_id
            found=project.ix.handlers_for('GET',path,'ts-contacts-service');assert len(found)==1
            contact=Request.http('ts-contacts-service','GET',path,{},provenance={'source':'actual login result.data.userId'})
            second=run_paths(project,producer['state'],next(iter(found)),contact,limit=4)
            chain.append({'step':'contacts','producer':'actual login result.data.userId','alternatives':observed(second)})
        return chain
    chain=run_chain(context)
    runtime_control=run_chain({**context,'clock':datetime(2026,10,1),'java_default_charset':'UTF-8'})
    with gzip.open(a.stage_report,'rt') as stream:report=json.load(stream)
    steps=report['scenarios']['S0']['steps'][:2]
    automatic=[{'n':s['n'],'action':s['action'],'selection':s['selection'],
        'alternatives':[{'entry':r['entry'],'ui_site':r.get('ui_site'),'outcome':r['outcome'],'bindings':r.get('bindings'),
            'storage':r.get('state_after',{}).get('browser',{}).get('storage'),
            'warnings':r.get('warnings')} for r in s['alternatives']]} for s in steps]
    a.output.write_text(json.dumps(scrub({'source_site_controls':controls,'explicit_chain':chain,'current_automatic_s0':automatic,
        'runtime_control_chain':runtime_control,'runtime_control_assumptions':{'clock':'2026-10-01T00:00:00','java_default_charset':'UTF-8',
            'scope':'Synthetic runtime-input control, not evidence these values exist in the supplied S0 context'},
        'intermediate_values_injected':False,'full_frontend_success_claimed':False,'target_apps_started':False,
        'conclusion_rule':'A successful explicit chain cannot certify a guarded browser path. Site-only controls retain the production binder and every guard.'}),default=serial,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'site_controls':len(controls),'explicit_chain_steps':len(chain),'guards_overridden':False}))


if __name__=='__main__':main()
