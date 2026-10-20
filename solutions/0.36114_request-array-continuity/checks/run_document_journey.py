"""Export explicit and NL witnesses for the synthetic document regression."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

VARIANT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(VARIANT/'code'),str(VARIANT/'code/tests')]
from test_document_array_journey import fixture,expected
from analyzer.engine import Engine
from analyzer.state import ScenarioState
from analyzer.request import Request
from analyzer.frontend import Frontend
from analyzer.contracts import ContractGrounder,ContractIndex
from analyzer.__main__ import analyze,serial


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
    project,db,ids=fixture(args.output/'inputs')
    wanted=[expected(ids),expected(ids,True),expected(ids)]
    oracle={'source':'manually enumerated in test_document_array_journey.expected before prediction',
        'kind':'synthetic regression, not a public application',
        'edges':[sorted(edges) for edges in wanted],
        'values':[[{'id':'D7','revision':7,'approved':False}],{'id':'D7','revision':8,'approved':True},
                  [{'id':'D7','revision':8,'approved':True}]]}
    (args.output/'oracle.json').write_text(json.dumps(oracle,indent=2)+'\n')
    state=ScenarioState(db);rows=[];body=None
    for index,(entry,method,path) in enumerate([
        ('portal.PortalGateway.listDocuments','GET','/library'),
        ('portal.PortalGateway.approveDocument','POST','/library/approve'),
        ('portal.PortalGateway.listDocuments','GET','/library')]):
        engine=Engine(project,state)
        request=Request.http('portal',method,path,body=body) if body else Request.http('portal',method,path)
        result=engine.run(ids[entry],request);state=engine.state
        rows.append({'n':index+1,'wire':request.record(),'requests':engine.request_events,'result':result,
            'responses':engine.http_responses,'edges':sorted(engine.edges),'data_operations':engine.data_operations,
            'state_after':deepcopy(state.snapshot(full=True))})
        if index==0:body={'id':result[0]['id'],'revision':result[0]['revision'],'approved':True}
    frontend=Frontend(project)
    _,trace=analyze(project,frontend,ContractIndex(project,frontend),None,db,
        {'facts':{},'unresolved':[],'choice_rules':[]},
        {'id':'documents','steps':[{'n':i+1,'action':text} for i,text in enumerate(
            ['List documents','Approve the first document','List documents'])]},path_limit=4,grounder_type=ContractGrounder)
    (args.output/'explicit.json').write_text(json.dumps(rows,default=serial,indent=2)+'\n')
    (args.output/'nl.json').write_text(json.dumps(trace,default=serial,indent=2)+'\n')
    checks=[]
    for i,(row,step) in enumerate(zip(rows,trace['steps'])):
        actual={tuple(edge) for edge in row['edges']}
        nl=step['alternatives'];graphs=[{('' if e['relation']=='executes' else e['source'],e['relation'],e['target']) for e in a['edges']} for a in nl]
        checks.append({'n':i+1,'explicit_graph':actual==wanted[i],
            'explicit_result':row['result']==oracle['values'][i],
            'nl_graph':len(graphs)==1 and graphs[0]==wanted[i],
            'nl_result':len(nl)==1 and nl[0]['result']==oracle['values'][i]})
    result={'passed':all(all(value for key,value in row.items() if key!='n') for row in checks),'steps':checks,
        'targets_started':False,'oracle_available_to_core':False,'synthetic':True}
    (args.output/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],result


if __name__=='__main__':main()
