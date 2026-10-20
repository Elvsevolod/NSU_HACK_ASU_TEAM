"""Post-hoc measured evidence; never imported by inference."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

V=Path(__file__).resolve().parents[1]


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def edges(path):
    answer=json.loads(path.read_text())
    return {(sid,e['source'],e['relation'],e['target']) for sid,row in answer['scenarios'].items() for e in row['edges']}


def main():
    rows=[];base=edges(V/'benchmark/stages/base/submission.json')
    for folder in sorted((V/'benchmark/stages').iterdir()):
        if not (folder/'evaluation.json').exists():continue
        summary=json.loads((folder/'summary.json').read_text());evaluation=json.loads((folder/'evaluation.json').read_text())
        found=edges(folder/'submission.json')
        rows.append({'stage':folder.name,'submission_sha256':summary['submission_sha256'],
            'code_manifest_sha256':hashlib.sha256((V/'development/stages'/folder.name/'code-sha256.json').read_bytes()).hexdigest(),
            'local_S0_score':evaluation['scenarios']['S0']['score'],'S0_relations':evaluation['scenarios']['S0']['sets'],
            'all_scenario_edges':len(found),'added_to_base':len(found-base),'removed_from_base':len(base-found),
            'relations':dict(Counter(edge[2] for edge in found)),
            **{key:summary[key] for key in ('elapsed_seconds','preparation_seconds','analysis_seconds','peak_rss_bytes','outcomes')}})
    save(V/'benchmark/stage-comparison.json',{'stages':rows,'site_scores_inferred':False,
        'causal_scope':'A/B/C/D are independent base factors; later snapshots are sequential integration, not isolated causal shares',
        'limits':['More edges is not proof of accuracy','S0 has empty reference remote set','Some development timings overlap short checks; repeated prepared timings are reported separately']})
    report=json.load(gzip.open(V/'benchmark/final/analysis-report.json.gz'))
    classes=Counter();stops=Counter();examples={};all_unknown_steps=0;alternatives=0
    for sid,scenario in report['scenarios'].items():
        for step in scenario['steps']:
            paths=step['alternatives'];alternatives+=len(paths)
            all_unknown_steps+=bool(paths) and all(path['result']=={'unknown':True} for path in paths)
            for index,path in enumerate(paths):
                stops[path['outcome']]+=1
                for effect in path.get('call_effects',[]):
                    category=effect.get('uncertainty_class','known_operation_unknown_value' if effect['model_version'].startswith('resolved-native') else 'legacy_unclassified')
                    classes[category]+=1
                    key=(category,effect['operation'],effect.get('declared_receiver',''))
                    if key not in examples:examples[key]={'category':category,'operation':effect['operation'],'declared_receiver':effect.get('declared_receiver'),
                        'scenario':sid,'step':step['n'],'alternative':index,'callsite':effect['callsite'],
                        'heap_roots':effect['heap_roots'],'resource_writes':effect['resource_writes'],'completions':effect['completions']}
    budgets=[]
    for limit in (1,4,8):
        folder=V/('benchmark/real-budget-'+str(limit));trace=json.loads((folder/'trace.json').read_text());check=json.loads((folder/'checks.json').read_text())
        budgets.append({'path_limit':limit,'passed_full_source_oracle':check['passed'],
            'steps':len(trace['steps']),'alternatives':[step['path_consistency']['alternatives'] for step in trace['steps']],
            **{key:trace[key] for key in ('preparation_seconds','analysis_seconds','peak_rss_bytes')}})
    save(V/'benchmark/uncertainty-and-budget.json',{'alternatives':alternatives,'all_unknown_steps':all_unknown_steps,
        'outcomes':dict(stops),'effect_categories':dict(classes),'operation_examples':list(examples.values()),'controlled_request_budget_runs':budgets,
        'policy':'Preserve typed readonly native summaries and join compatible continuations; retain separate throwing completions and visible stops for unsupported calls',
        'decision':'No global budget increase: the real full chain passes at 1/4/8; unsupported TT library/receiver cases remain partial and are not replaced by static closure',
        'accuracy_limits':['True opaque effects cannot promise exact heap or future edges','Application exception is not automatically a legitimate business refusal',
            'TT requests come from NL hypotheses; only the separate source-profile HTTP chain is an independently controlled Request experiment'],
        'model_calls':0,'external_llm_api_calls':0,'deepseek_calls':0})
    manifest={path.relative_to(V/'code').as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((V/'code').rglob('*')) if path.is_file() and not {'__pycache__','.pytest_cache'}&set(path.parts) and path.suffix!='.pyc'}
    previous=json.loads((V/'development/stages/final-candidate/code-sha256.json').read_text())
    changed=[name for name,digest in manifest.items() if previous.get(name)!=digest]
    assert changed==['verify_run.py'],changed
    save(V/'benchmark/final/code-sha256.json',manifest)
    metadata=json.loads((V/'benchmark/final/metadata.json').read_text())
    metadata['code_sha256']=manifest;metadata['post_run_manifest_delta']={'files':changed,'reason':'Verifier recognizes explicitly conditional JSON setters; inference code and all eight graph bytes unchanged'}
    save(V/'benchmark/final/metadata.json',metadata)
    print(json.dumps({'stages':len(rows),'outcomes':dict(stops),'effect_categories':dict(classes),'all_unknown_steps':all_unknown_steps,'non_runtime_delta':changed}))


if __name__=='__main__':main()
