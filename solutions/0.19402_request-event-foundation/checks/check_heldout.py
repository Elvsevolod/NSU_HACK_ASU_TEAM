"""Evaluate sealed scenarios once; their expected requests never reach inference."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

VARIANT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(VARIANT/'code'),str(VARIANT/'checks')]
from analyzer.project import Project
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex,ContractGrounder,read_static_context
from analyzer.state import Database
from analyzer.__main__ import analyze,serial
from compare_public_corpus import edge_set


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fixtures',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    assert not args.output.exists();args.output.mkdir(parents=True)
    sealed=args.fixtures/'heldout.json';sealed_digest=hashlib.sha256(sealed.read_bytes()).hexdigest()
    cases=json.loads(sealed.read_text())['cases']
    references=[]
    for number,case in enumerate(cases):
        fixture=args.fixtures/case['fixture'];graph=json.loads((fixture/'skeleton.json').read_text())
        ids={node['owner'].split(':')[-1]+'.'+node['name']:mid for mid,node in graph['nodes'].items() if node['kind']=='method'}
        sid='heldout-'+str(number+1)
        if number==0:
            methods=['OwnerResource.updateOwner','ResourceNotFoundException.<init>']
            gold={(ids['OwnerResource.updateOwner'],'calls',ids['ResourceNotFoundException.<init>']),
                  (ids['OwnerResource.updateOwner'],'data','res:table:customers.owners')}
        else:
            methods=['AccountController.getAccountByName','AccountServiceImpl.findByName']
            gold={(ids[methods[0]],'calls',ids[methods[1]]),(ids[methods[1]],'data','res:collection:account.accounts')}
        gold.update(('scenario:'+sid,'executes',ids[name]) for name in methods)
        references.append({'id':sid,**case,'entry':ids[case['endpoint']],'edges':sorted(gold)})
    reference=args.output/'reference.json';reference.write_text(json.dumps({'fixed_before_prediction':True,'sealed_cases_sha256':sealed_digest,'cases':references},indent=2)+'\n')
    digest=hashlib.sha256(reference.read_bytes()).hexdigest()
    results=[]
    for expected in references:
        fixture=args.fixtures/expected['fixture'];project=Project(fixture/'skeleton.json',fixture)
        frontend=Frontend(project);index=ContractIndex(project,frontend)
        scenario={'id':expected['id'],'project':project.skeleton['project'],'steps':[{'n':1,'action':expected['action']}]}
        block,detail=analyze(project,frontend,index,None,Database(fixture/'initial.sql'),read_static_context({}),scenario,grounder_type=ContractGrounder)
        alternatives=detail['steps'][0]['alternatives']
        row={'id':expected['id'],'endpoint':bool(alternatives) and all(a['entry']==expected['entry'] for a in alternatives),
            'status':bool(alternatives) and all(a['responses'] and a['responses'][-1]['status']==expected['status'] for a in alternatives),
            'graph_exact':edge_set(block['edges'])==set(map(tuple,expected['edges']))}
        row['passed']=all(row[key] for key in ('endpoint','status','graph_exact'))
        results.append(row)
        (args.output/(expected['id']+'.json')).write_text(json.dumps({'prediction':block,'report':detail},default=serial,indent=2)+'\n')
    assert hashlib.sha256(reference.read_bytes()).hexdigest()==digest
    (args.output/'results.json').write_text(json.dumps({'reference_sha256':digest,'sealed_cases_sha256':sealed_digest,'results':results,
        'passed':all(row['passed'] for row in results),'targets_started':False,'limits':[
        'New sealed scenarios on already inspected projects, not unseen-project validation',
        'Two gold data cases; gold remote empty in both cases, so interservice generalization remains unmeasured']},indent=2)+'\n')
    print(json.dumps(results))


if __name__=='__main__':main()
