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
from evidence import capture,chain,heap
from check_document_journey import check


def oracle_steps(ids,wanted,db):
    old={'id':'D7','revision':7,'approved':False};new={'id':'D7','revision':8,'approved':True}
    body={**old,'approved':True};actions=['List documents','Approve the first document','List documents']
    endpoints=[ids['portal.PortalGateway.listDocuments'],ids['portal.PortalGateway.approveDocument'],ids['portal.PortalGateway.listDocuments']]
    table_before={'docs.documents':[{'id':'D7','revision':7,'approved':0}]}
    initial=ScenarioState(db).snapshot(full=True);steps=[]
    for i in range(3):
        write=i==1
        entries=[endpoints[i],ids['docs.DocumentController.approveDocument' if write else 'docs.DocumentController.listDocuments']]
        argument={'name':'input','declared_type':'Approval','value':body}
        arguments=[[argument],[{'name':'id','declared_type':'java.lang.String','value':'D7'},argument],
                   [{'name':'id','declared_type':'java.lang.String','value':'D7'}]] if write else [[],[]]
        if write:entries.append(ids['audit.AuditController.accept'])
        wires={};states={}
        for mode in ('explicit','nl'):
            headers={'content-type':['application/json']} if write else {}
            if mode=='nl':headers={'__rest_unknown__':True,**headers}
            wires[mode]={'method':'POST' if write else 'GET','url':'/library/approve' if write else '/library',
                'body':body if write else {'missing':True},'headers':headers,'query':{}}
            state=deepcopy(initial);state['clock']={'unknown':True}
            state['tables']=table_before if i==0 else {'docs.documents':[new]}
            if mode=='nl':
                state['browser'].update(pages={},dom_text={},script_unknown=False,active_page='portal/page.html',source_options=[])
                state['browser']['form']={'documents':[new if i==2 else old]}
                state['history']=[{'step':j+1,'entry':endpoints[j],'action':actions[j]} for j in range(i+1)]
                state['analysis_assumptions']=['step 1: unresolved source/request/state assumptions']
            states[mode]=state
        steps.append({'n':i+1,'wire':wires,'arguments':arguments,'entries':entries,'state':states,
            'remote_wire':[{'method':'POST','url':'http://docs/documents/D7/approve','body':body,'query':{},'headers':{'content-type':['application/json']}},
                           {'method':'POST','url':'http://audit/events','body':'D7','query':{},'headers':{}}] if write else
                          [{'method':'GET','url':'http://docs/documents','body':None,'query':{},'headers':{}}],
            'result':new if write else [new if i==2 else old],'statuses':[[3,503],[2,200],[1,200]] if write else [[2,200],[1,200]],
            'diagnostics':{'explicit':[] if write else ['codec_payload_projection'],
                           'nl':(['codec_payload_projection'] if i!=1 else [])+(['prior_analysis_assumption'] if i else [])},
            'edges':sorted(wanted[i])})
    return steps


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
    oracle.update(version=3,steps=oracle_steps(ids,wanted,db),
        limits=['Codec failure completeness is explicitly unproven and its diagnostic must remain present',
                'Synthetic regression, not new real-source holdout; native DTO metadata is checked separately from payload'])
    (args.output/'oracle.json').write_text(json.dumps(oracle,indent=2)+'\n')
    state=ScenarioState(db);rows=[];body=None
    for index,(entry,method,path) in enumerate([
        ('portal.PortalGateway.listDocuments','GET','/library'),
        ('portal.PortalGateway.approveDocument','POST','/library/approve'),
        ('portal.PortalGateway.listDocuments','GET','/library')]):
        engine=Engine(project,state)
        request=Request.http('portal',method,path,body=body) if method=='POST' else Request.http('portal',method,path)
        result=engine.run(ids[entry],request);state=engine.state
        rows.append({'n':index+1,**capture(engine,request,result)})
        if index==0:body={'id':result[0]['id'],'revision':result[0]['revision'],'approved':True}
    frontend=Frontend(project)
    from analyzer.paths import run_paths
    heaps=[]
    def observed_paths(*args,**kwargs):
        paths=run_paths(*args,**kwargs);heaps.extend(heap(p['state']) for p in paths);return paths
    _,trace=analyze(project,frontend,ContractIndex(project,frontend),None,db,
        {'facts':{},'unresolved':[],'choice_rules':[]},
        {'id':'documents','steps':[{'n':i+1,'action':text} for i,text in enumerate(
            ['List documents','Approve the first document','List documents'])]},path_limit=4,grounder_type=ContractGrounder,path_runner=observed_paths)
    nlrows=[a for step in trace['steps'] for a in step['alternatives']]
    assert len(nlrows)==len(heaps)==3
    for row,value in zip(nlrows,heaps):row['heap_after']=value
    (args.output/'explicit.json').write_text(json.dumps(rows,default=serial,indent=2)+'\n')
    (args.output/'nl.json').write_text(json.dumps(trace,default=serial,indent=2)+'\n')
    json_copy=lambda value:json.loads(json.dumps(value,default=serial))
    checks={mode:check(json_copy(value),json_copy(oracle),mode) for mode,value in [('explicit',rows),('nl',nlrows)]}
    result={'passed':all(value['passed'] for value in checks.values()),'modes':checks,
        'targets_started':False,'oracle_available_to_core':False,'synthetic':True}
    (args.output/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    (args.output/'witness.json').write_text(json.dumps([chain(rows,'documents/explicit'),chain(nlrows,'documents/NL')],default=serial,indent=2)+'\n')
    assert result['passed'],result


if __name__=='__main__':main()
