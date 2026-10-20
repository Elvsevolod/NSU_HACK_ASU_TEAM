"""Correct explicit HTTP inputs isolate execution from NL grounding. No gold."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

VARIANT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(VARIANT/'code'))
from analyzer.project import Project
from analyzer.paths import run_paths
from analyzer.state import Database,ScenarioState
from analyzer.request import Request
from analyzer.contracts import read_static_context
from analyzer.__main__ import serial


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--challenge',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists()
    project=Project(args.challenge/'skeleton/trainticket.json.gz',args.challenge/'targets/trainticket')
    database=Database(args.challenge/'context/db-after-warmup.sql.gz');database.schemas=project.schemas
    context=read_static_context(project.skeleton.get('context',{}))
    order=next(row for row in database.tables[('ts_order','orders')] if row['status']==0)
    payment={'orderId':order['id'],'tripId':order['trainNumber'],'userId':order['accountId'],'price':order['price']}
    cases=[('search','ts-travel-service','POST','/api/v1/travelservice/trips/left',
        {'startPlace':'Shang Hai','endPlace':'Su Zhou','departureTime':'2026-10-01'}),
        ('known-unpaid-order','ts-inside-payment-service','POST','/api/v1/inside_pay_service/inside_payment',payment),
        ('missing-order','ts-inside-payment-service','POST','/api/v1/inside_pay_service/inside_payment',
            {**payment,'orderId':'independent-missing-order'})]
    output=[]
    for name,module,verb,path,body in cases:
        request=Request.http(module,verb,path,{'Content-Type':'application/json'},body)
        entries=project.ix.handlers_for(verb,path,module);assert len(entries)==1,(name,entries)
        state=ScenarioState(database,context);state.now=context['clock']
        rows=[]
        for result in run_paths(project,state,next(iter(entries)),request,limit=4):
            engine=result['engine']
            rows.append({'outcome':engine.outcome,'result':result['result'],'warnings':sorted(engine.warnings),
                'requests':engine.request_events,'responses':engine.http_responses,
                'edges':sorted(engine.edges),'data_operations':engine.data_operations,
                'state_after':deepcopy(engine.state.snapshot(full=True)),
                'call_effects':engine.effect_events})
        output.append({'name':name,'wire':request.record(),'entry':next(iter(entries)),'alternatives':rows})
        args.output.write_text(json.dumps({'oracle_loaded':False,'target_apps_started':False,'cases':output},
            default=serial,ensure_ascii=True,indent=2)+'\n')
        print(name,[row['outcome'] for row in rows],flush=True)


if __name__=='__main__':main()
