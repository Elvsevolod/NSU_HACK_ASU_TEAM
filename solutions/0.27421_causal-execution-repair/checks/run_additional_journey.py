"""Source-profile inputs only; the frozen oracle is never loaded here."""
import argparse
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import sys

VARIANT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(VARIANT/'code'))
from analyzer.project import Project
from analyzer.engine import Engine
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex,ContractGrounder
from analyzer.state import Database,ScenarioState,U
from analyzer.request import Request,MISSING
from analyzer.java_collections import JavaRecord
from analyzer.bean_lifecycle import BeanLifecycle
from run_real_journey import json_default


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
    p=Project(args.input/'skeleton.json',args.input);frontend=Frontend(p);index=ContractIndex(p,frontend)
    server={'authenticated':True,'principal':{'name':'account-service'},'authorities':[],'oauth2_request':{'clientId':'account-service','scope':['server']}}
    user={'authenticated':True,'principal':{'name':'aurora'},'authorities':[],'oauth2_request':{'clientId':'browser','scope':['ui']}}
    def enum(typ,name):
        owner=p.resolve_type('com.piggymetrics.account.domain.'+typ,'account-service')
        return deepcopy(next(value for key,value in p.enum_objects.items() if value.enum_owner==owner and value.enum_name==name))
    def record(typ,fields):
        fqn='com.piggymetrics.account.domain.'+typ
        return JavaRecord(fqn,{'__type__':fqn,'__http_entity__':False,**fields})
    rows=[]
    for case_id in ('invalid-saving-null','partly-known-real-list','ambiguous-account-read'):
        db=Database(args.input/'initial.sql');incomes=None
        if case_id=='partly-known-real-list':
            types={'title':'java.lang.String','amount':'java.math.BigDecimal','currency':'com.piggymetrics.account.domain.Currency',
                   'period':'com.piggymetrics.account.domain.TimePeriod','icon':'java.lang.String'}
            unknown=record('Item',{key:{'__symbol__':'seed.aurora.incomes[0].'+key,'__type__':typ,'__constraints__':[]} for key,typ in types.items()})
            known=record('Item',{'title':'Rent','amount':Decimal(7),'currency':enum('Currency','USD'),'period':enum('TimePeriod','MONTH'),'icon':'home'})
            incomes=[unknown,known]
        saving=record('Saving',{'amount':Decimal(20),'currency':enum('Currency','USD'),'interest':Decimal(0),'deposit':False,'capitalization':False})
        db.tables[('account-service','accounts')]=[{'name':'aurora','lastSeen':datetime(2026,10,18),'incomes':incomes,'expenses':[],
            'saving':saving,'note':'partially-known-seed'}]
        state=ScenarioState(db,{'clock':datetime(2026,10,18)})
        engine=Engine(p,state);callbacks=[]
        original=BeanLifecycle.callback
        def observed(self,mid,obj,values,role,*rest,**kwargs):
            receiver=deepcopy(obj)
            result=original(self,mid,obj,values,role,*rest,**kwargs)
            callbacks.append({'method':mid,'role':role,'receiver_type':obj.declared_type,'receiver':receiver,'result':deepcopy(result),
                'arguments':deepcopy(values),'declared_return':p.methods[mid].get('return_raw'),'completed_normally':True})
            return result
        request=None;proposals=[];selection=None;result=U;candidates=[]
        try:
            BeanLifecycle.callback=observed
            if case_id=='ambiguous-account-read':
                state.browser['session']=deepcopy(server)
                grounder=ContractGrounder(p,frontend,index,None,{'facts':{},'choice_rules':[]})
                proposals,selection=grounder.step('Read account',state)
            else:
                headers={'Accept':'application/json','Authorization':'Bearer supplied-user-token' if case_id=='invalid-saving-null' else 'Bearer supplied-server-token'}
                body={'saving':None} if case_id=='invalid-saving-null' else MISSING
                if body is not MISSING:headers['Content-Type']='application/json'
                request=Request.http('account-service','PUT' if body is not MISSING else 'GET',
                    '/accounts/current' if body is not MISSING else '/accounts/aurora',headers,body,session=user if body is not MISSING else server)
                candidates=sorted(p.ix.handlers_for(request.method,request.url.split('/')[1:],'account-service'))
                assert len(candidates)==1
                result=engine.run(candidates[0],request);state=engine.state
        finally:BeanLifecycle.callback=original
        rows.append({'id':case_id,'request':request.record() if request else None,'candidates':candidates,'proposals':len(proposals),
            'selection':selection,'result':result,'outcome':engine.outcome if request else 'no unique request selected','requests':engine.request_events,'responses':engine.http_responses,
            'events':engine.events,'callbacks':callbacks,'edges':sorted(engine.edges),'data_operations':engine.data_operations,
            'warnings':sorted(engine.warnings),'tables':{schema+'.'+table:deepcopy(values) for (schema,table),values in state.database.tables.raw_items()},
            'unknown_tables':sorted(state.database.unknown_tables)})
    (args.output/'trace.json').write_text(json.dumps({'oracle_loaded':False,'targets_started':False,
        'observer':'Records source JSON callback receiver/result without changing return, state or dispatch','cases':rows},default=json_default,indent=2)+'\n')
    print(json.dumps([{'id':row['id'],'outcome':row['outcome'],'callbacks':len(row['callbacks']),'proposals':row['proposals']} for row in rows]))


if __name__=='__main__':main()
