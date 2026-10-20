"""Independent partial transfer obligations preserved from the source review."""
import json
from pathlib import Path
from urllib.parse import urlsplit
BASE=Path(__file__).resolve().parents[1]/"development"

def read(path):return json.loads(path.read_text())

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def subset(wanted,actual):
    if isinstance(wanted,dict):return isinstance(actual,dict) and all(k in actual and subset(v,actual[k]) for k,v in wanted.items())
    if isinstance(wanted,list):return isinstance(actual,list) and len(wanted)==len(actual) and all(subset(a,b) for a,b in zip(wanted,actual))
    return type(wanted) is type(actual) and wanted==actual

def wire(wanted,actual):
    if not isinstance(actual,dict):return False
    expected_path=[part for part in urlsplit(wanted['url']).path.strip('/').split('/') if part]
    if actual.get('method')!=wanted['method'] or actual.get('path')!=expected_path:
        return False
    headers={key.lower():value for key,value in actual.get('headers',{}).items()}
    for key,value in wanted['headers'].items():
        if headers.get(key.lower()) not in (value,[value]):return False
    return 'body' not in wanted or subset(wanted['body'],actual.get('body'))

def inspect_semantics(project,result,packages_root=None):
    expected=read((packages_root or BASE/'packages')/project/'source-obligations.json')
    checks=[]
    for mode in ('explicit','nl'):
        report=read(result/mode/'report.json')['scenarios']
        for case in expected['cases']:
            scenario=report[case['id']]
            for number,wanted in enumerate(case['steps'],1):
                step=scenario['steps'][number-1];alts=step['alternatives']
                actual={(e['source'],e['relation'],e['target']) for a in alts for e in a['edges']}
                required={(e['source'].replace('$scenario','scenario:'+case['id']),e['relation'],e['target']) for e in wanted['required_edges']}
                returned=wanted['expected_completion']=='returned'
                exact_results=wanted['expected_result_projection']
                evidence={
                    'handler':bool(alts) and all(a['entry']==wanted['expected_entry'] for a in alts),
                    'wire':bool(alts) and all(wire(wanted['http_request'],a.get('request')) for a in alts),
                    'required_edges':required<=actual,
                    'completion':bool(alts) and all((a['outcome']=='returned') if returned else any(isinstance(r.get('status'),int) and r['status']>=400 for r in a.get('responses',[])) for a in alts),
                    'result_projection':exact_results is None or bool(alts) and all(subset(exact_results,a['result']) for a in alts),
                    'exploration_complete':bool(alts) and all(a.get('exploration',{}).get('complete') is True for a in alts),
                }
                if wanted.get('result_required_nonnull'):
                    from check_source_state import unknown
                    evidence['result_nonnull']=bool(alts) and all(isinstance(a['result'],dict) and all(
                        key in a['result'] and a['result'][key] is not None and not unknown(a['result'][key])
                        for key in wanted['result_required_nonnull']) for a in alts)
                if not returned:
                    evidence['no_write_after_refusal']=all(not any(o.get('datastore_event') and o['operation'].startswith(('save','delete','update')) for o in a.get('data_operations',[])) for a in alts)
                checks.append({'mode':mode,'scenario':case['id'],'step':number,'passed':all(evidence.values()),'checks':evidence,
                    'required_edge_coverage':len(required&actual)/len(required) if required else None,
                    'missing_required_edges':[list(e) for e in sorted(required-actual)],
                    'partial_oracle':True,'full_precision_or_iou':None,
                    'first_losses':[a.get('knowledge_losses',[])[:1] for a in alts],
                    'outcomes':[a['outcome'] for a in alts]})
    return {'project':project,'passed':all(c['passed'] for c in checks),'checks':checks,
        'scope':'Partial source edge, actual wire, result/completion and complete-exploration checks. Full state/timestamp/history/filter oracle is not claimed.',
        'real_project_evaluation_performed':True,'full_real_transfer_verified':False}
