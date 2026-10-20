"""Untuned real-source transfer probe. The runner never reads the oracle."""
import argparse,json,sys,time
from functools import partial
from copy import deepcopy
from datetime import datetime
from pathlib import Path
V=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(V/'code'))
from evidence import trace_document
from analyzer.project import Project
from analyzer.state import Database,ScenarioState,U
from analyzer.request import Request
from analyzer.paths import run_paths,join_states
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex,ContractGrounder
from analyzer.__main__ import analyze,serial
from analyzer.history_agreement import agree_completed


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--retrieval',choices=('baseline','lexical','offline-dense'),default='baseline')
    parser.add_argument('--model-snapshot',type=Path);args=parser.parse_args()
    assert not args.output.exists();args.output.mkdir(parents=True)
    root=V/'validation_inputs/shopping-cart';started=time.perf_counter()
    project=Project(root/'skeleton.json',root);db=Database(root/'initial.sql')
    context={**json.loads((root/'deployment-context-v2.json').read_text()),'clock':datetime(2026,10,18),'facts':{},'unresolved':[],'choice_rules':[]}
    state=ScenarioState(db,context);rows=[];payment_id=order_id=U
    runner=partial(run_paths,entry_boundary='application_after_authentication')
    lineage={}
    plan=[('payment-service','GET','/api/payments?orderId=11'),
          ('payment-service','PATCH',None),('payment-service','GET',None),('order-service','GET',None),
          ('payment-service','PATCH',None),('payment-service','GET','/api/payments/999'),
          (None,None,None),('payment-service','GET','/api/payments?orderId=11')]
    for index,(module,method,url) in enumerate(plan,1):
        before=deepcopy(state.snapshot(full=True))
        if index==7:
            rows.append({'n':index,'alternatives':[], 'outcome':'explicit HTTP has no meaning for an ambiguous NL action; see NL trace','not_executed':True,
                         'state_before':before,'state_after':deepcopy(before)});continue
        if url is None:
            value=order_id if index==4 else payment_id
            url=(('/api/orders/' if index==4 else '/api/payments/')+str(value)+('/refund' if index in (2,5) else '')) if type(value) is int else U
        request=Request.http(module,method,url,headers={})
        candidates=sorted(project.ix.handlers_for(method,list(request.path) if request.path is not None else [],module))
        if len(candidates)!=1:
            rows.append({'n':index,'request':request.record(),'candidates':candidates,'outcome':'unknown_request',
                         'first_loss':'producer did not supply a unique concrete identifier','state_after':deepcopy(state.snapshot(full=True))});continue
        alternatives=[];states=[]
        for path in runner(project,state,candidates[0],request,limit=4):
            engine=path['engine'];states.append(path['state'])
            alternatives.append({'result':path['result'],'outcome':engine.outcome,'requests':engine.request_events,
                'entry':candidates[0],'exploration':deepcopy(path.get('exploration',{})),
                'responses':engine.http_responses,'edges':sorted(engine.edges),'effects':engine.effect_events,
                'warnings':sorted(engine.warnings),'conditions':engine.conditions,'data_operations':engine.data_operations,
                'state_after':deepcopy(engine.state.snapshot(full=True))})
        state=join_states(states) if len(states)>1 else states[0]
        if index==1:
            def selected(a):
                found=[r for r in a['result'] if isinstance(r,dict) and r.get('status')=='APPROVED'] if isinstance(a['result'],list) and a['outcome']=='returned' else []
                if len(found)!=1 or any(type(found[0].get(key)) is not int for key in ('id','orderId')):return None
                return (found[0]['id'],found[0]['orderId'])
            agreement=agree_completed(alternatives,selected)
            if agreement:
                payment_id,order_id=agreement['value']
                lineage={'producer_step':1,'selection':'unique APPROVED record in every completed producer alternative',
                         'payment_id':payment_id,'order_id':order_id,'source':'actual root result','agreement':agreement}
        rows.append({'n':index,'request':request.record(),'alternatives':alternatives,'state_before':before,
                     'state_after':deepcopy(state.snapshot(full=True)), 'producer':deepcopy(lineage) if index in (2,3,4,5) else None})
    (args.output/'explicit.json').write_text(json.dumps(trace_document({'steps':rows,'oracle_loaded':False,'targets_started':False,
        'entry_boundary':'application_after_authentication','security_evaluated':False,
        'seconds_including_index':time.perf_counter()-started}),default=serial,indent=2)+'\n')
    frontend=Frontend(project)
    Index=ContractIndex
    if args.retrieval=='lexical':
        from analyzer.lexical_retrieval import LexicalContractIndex
        Index=LexicalContractIndex
    elif args.retrieval=='offline-dense':
        from analyzer.offline_retrieval import OfflineDenseIndex
        Index=partial(OfflineDenseIndex,snapshot=args.model_snapshot)
    submission,trace=analyze(project,frontend,Index(project,frontend),None,db,context,
        json.loads((root/'scenarios.json').read_text()),path_limit=4,grounder_type=ContractGrounder,path_runner=runner)
    trace.update(entry_boundary='application_after_authentication',security_evaluated=False)
    (args.output/'nl.json').write_text(json.dumps(trace_document(trace),default=serial,indent=2)+'\n')
    (args.output/'submission.json').write_text(json.dumps(submission,indent=2)+'\n')


if __name__=='__main__':main()
