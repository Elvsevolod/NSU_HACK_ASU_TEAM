"""Post-inference causal ledger, immutable-parent audit and measured model tables."""
import argparse,difflib,hashlib,json,shutil,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from check_source_state import evaluate
from transfer_semantics import inspect_semantics
from evaluate_code_models import metrics
V=Path(__file__).resolve().parents[1];ROOT=V.parents[1]


def read(path):return json.loads(path.read_text())
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    parent=V.parent/'0.22997_state-semantics-and-retrieval'
    parent_hashes=read(V/'development/parent32-sha256.json')
    parent_errors=[name for name,digest in parent_hashes.items() if not (parent/name).is_file() or sha(parent/name)!=digest]
    protected=read(parent/'development/protected-files.json')
    registry='solutions/README.md'
    input_errors=[name for name,digest in protected.items() if name!=registry and (not (ROOT/name).is_file() or sha(ROOT/name)!=digest)]
    save(a.output/'integrity.json',{'parent32_files':len(parent_hashes),'parent32_mismatches':parent_errors,
        'protected_input_files':len(protected)-int(registry in protected),'protected_input_mismatches':input_errors,
        'authorized_mutable_registry':{'path':registry,'reason':'Solution-version skill requires score/version registry updates; not a read-only target/sample/run input',
            'baseline_sha256':protected.get(registry),'current_sha256':sha(ROOT/registry)},'passed':not parent_errors and not input_errors})
    assert not parent_errors and not input_errors
    stage=V/'benchmark/stages/E2-source-contracts';code_hashes=read(stage/'run.json')['code_sha256']
    assert all(sha(V/'code'/name)==digest for name,digest in code_hashes.items())
    diff=[]
    files=set(code_hashes)|{p.relative_to(parent/'code').as_posix() for p in (parent/'code').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    changed=[]
    for name in sorted(files):
        before=parent/'code'/name;after=V/'code'/name
        left=before.read_text().splitlines(keepends=True) if before.is_file() else [];right=after.read_text().splitlines(keepends=True) if after.is_file() else []
        if left!=right:
            changed.append(name);diff.extend(difflib.unified_diff(left,right,fromfile='a/code/'+name,tofile='b/code/'+name))
    (a.output/'parent32-to33.patch').write_text(''.join(diff))
    save(a.output/'changed-code.json',{'files':changed,'stage':'E2-source-contracts','code_sha256':code_hashes})
    cutoff=datetime.fromisoformat('2026-10-19T04:48:22.179257+00:00');commands=[]
    for file in (parent/'benchmark/implementation').rglob('run.json'):
        record=read(file)
        if record.get('started_at') and datetime.fromisoformat(record['started_at'])>=cutoff:
            commands.append({'path':file.relative_to(parent).as_posix(),**record})
    commands.sort(key=lambda row:row['started_at'])
    save(a.output/'parent32-after-report-replacement.json',{'cutoff_utc':cutoff.isoformat(),
        'pre_cutoff_work':'Draft static cells already existed before replacement; not counted as new post-replacement implementation.',
        'commands':commands,'assessed_zip_sha256':sha(parent/'solution.zip'),'site':read(parent/'benchmark/site-score.json')})
    models=read(V/'benchmark/model-comparison-checked.json')['results'];old=read(V/'benchmark/model-comparison.json')['results']
    assert models==old,'checker strengthening changed computed metrics'
    model_rows=[]
    for name,result in models.items():
        row={'model':name,'metrics':result['metrics'],'calibration':result['calibration'],'cost':result['cost'],'identity':result['identity'],'audit':result['audit']}
        row['per_split_language']={split:{lang:metrics([r for r in result['rows'] if r['split']==split and r['language']==lang]) for lang in ('en','ru')}
            for split in ('development','test')}
        row['truncation']={role:{'items':len(items:=[t for t in result['tokens'] if t['role']==role]),
            'truncated':sum(t['truncated'] for t in items),'unknown_tokens':sum(t['unknown_tokens'] for t in items)} for role in ('document','query')}
        model_rows.append(row)
    save(a.output/'model-summary.json',{'hardware':{'cpu':'Apple M4 Pro','ram_bytes':25769803776,'model_device':'MPS','threads':4,'dtype':'float32'},
        'models':model_rows,'cpu_model_runtime_benchmark':'not_run','selection':'Development-only CodeRank winner retained; no test-driven reselection',
        'default_adoption':'experiment_rejected after actual paired downstream comparison','holdout_scope':'Licensing source retrieval only, not complete execution/state/graph transfer'})
    matrix=V/'benchmark/final-model-matrix';ledger=[];summary=[]
    source_corpus=read(V/'development/model-pilot/frozen-v2/corpus.json')
    for profile in ('baseline','lexical','dense-same','dense-expanded'):
        for project in ('organization','library'):
            folder=matrix/profile/project;sem=inspect_semantics(project,folder,V/'development/transfer')
            state={mode:evaluate(project,read(folder/mode/'report.json')) for mode in ('explicit','nl')}
            for mode in ('explicit','nl'):
                checks=[c for c in sem['checks'] if c['mode']==mode];states=state[mode]['checks']
                summary.append({'profile':profile,'project':project,'mode':mode,'steps':len(checks),'partial_passed':sum(c['passed'] for c in checks),
                    'state_passed':sum(c['passed'] for c in states),**{k:sum(c['checks'][k] for c in checks) for k in ('handler','wire','completion','required_edges','exploration_complete')}})
                report=read(folder/mode/'report.json')['scenarios']
                obligations=read(V/'development/transfer'/project/'source-obligations.json')
                expected={(c['id'],i+1):s for c in obligations['cases'] for i,s in enumerate(c['steps'])}
                state_by={(r['scenario'],r['step']):r for r in states}
                for check in checks:
                    step=report[check['scenario']]['steps'][check['step']-1];selection=step['selection'];alts=step['alternatives']
                    entry=expected[(check['scenario'],check['step'])]['expected_entry'];decision=selection.get('retrieval_decision',{})
                    ranked=selection.get('ranking') or decision.get('candidates',[]) or decision.get('raw_top',[])
                    rank=next((i+1 for i,r in enumerate(ranked) if r.get('entry')==entry),None)
                    pool=decision.get('candidate_pool');first='passed_partial_obligations'
                    if not check['checks']['handler']:
                        if pool is not None and entry not in pool:first='candidate_extraction'
                        elif rank is not None and rank!=1:first='ranking'
                        elif decision.get('accepted') is False:first='abstention'
                        elif ranked and rank is None:first='ranking_or_unrecorded_candidate_filter'
                        else:first='binding_or_no_supported_source_request'
                    elif not check['checks']['wire']:first='request_binding_or_wire'
                    elif any(a['outcome']=='HTTP binding failure' for a in alts):first='http_binding'
                    elif any('scenario request' in item and 'JSON bean plan' in item for a in alts for item in a.get('unresolved',[])):
                        first='http_json_binding'
                    elif not check['checks']['completion'] or not check['checks']['exploration_complete']:first='execution_or_completion_boundary'
                    elif not check['checks']['required_edges']:first='required_edge_coverage'
                    elif not state_by[(check['scenario'],check['step'])]['passed']:first='persistent_state_projection'
                    elif not check['passed']:first='result_projection_or_refusal_effect'
                    ledger.append({'profile':profile,'project':project,'mode':mode,'scenario':check['scenario'],'step':check['step'],
                        'expected_entry':entry,'source_handler_available':entry in source_corpus[project]['documents'],
                        'recorded_candidate_available':entry in pool if pool is not None else None,'recorded_top6_rank':rank,
                        'first_failed_layer':first,'unresolved':selection.get('unresolved',[]),'checks':check['checks'],
                        'outcomes':check['outcomes'],'diagnostics':[a.get('unresolved',[]) for a in alts],
                        'first_recorded_knowledge_losses':check['first_losses'],
                        'evidence':'benchmark/final-model-matrix/'+profile+'/'+project+'/'+mode+'/report.json',
                        'qualification':'Layer classification from recorded facts; ambiguous layers remain combined rather than invented.'})
    save(a.output/'downstream-summary.json',{'rows':summary,'partial_oracle':True,'full_semantic_transfer_verified':False})
    save(a.output/'causal-ledger.json',{'rows':ledger,'counts':dict(Counter(r['first_failed_layer'] for r in ledger)),
        'denominators':'21 execution steps per profile/mode. Distinct from 24 development and 12 test answer retrieval queries.',
        'not_claimed':'No full edge precision/IoU or single unique cause from an incomplete trace.'})
    before=read(parent/'submission.json')['scenarios'];after=read(stage/'submission.json')['scenarios'];deltas={}
    for sid in before:
        left={(e['source'],e['relation'],e['target']) for e in before[sid]['edges']};right={(e['source'],e['relation'],e['target']) for e in after[sid]['edges']}
        deltas[sid]={relation:{'before':sum(e[1]==relation for e in left),'after':sum(e[1]==relation for e in right),
            'added':[list(e) for e in sorted(right-left) if e[1]==relation],'removed':[list(e) for e in sorted(left-right) if e[1]==relation]}
            for relation in ('executes','calls','remote','data')}
    save(a.output/'tt-prediction-delta.json',{'scenarios':deltas,'hidden_correctness':'unknown; deltas are predictions, not hidden gold corrections'})
    print(json.dumps({'parent_immutable':True,'protected_unchanged':True,'changed_code_files':len(changed),'ledger_rows':len(ledger),
        'post_replacement_parent_commands':len(commands),'layer_counts':dict(Counter(r['first_failed_layer'] for r in ledger))}))


if __name__=='__main__':main()
