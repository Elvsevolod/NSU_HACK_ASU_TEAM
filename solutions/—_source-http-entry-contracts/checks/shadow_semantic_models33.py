"""Development-only paired model run; oracle/checker execute in another process."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

V=Path(__file__).resolve().parents[1]


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--storage',type=Path,required=True);parser.add_argument('--qwen',type=Path,required=True)
    parser.add_argument('--policy',choices=('same_candidates','expanded'),required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    prereg=read(V/'development/semantic-model-preregistration-e20.json')
    assert all(sha(V/name)==digest for name,digest in prereg['files'].items())
    for key in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_HUB_DISABLE_IMPLICIT_TOKEN','HF_HUB_DISABLE_TELEMETRY'):os.environ[key]='1'
    sys.path[:0]=[str(V/'code'),str(args.storage/'dependencies')]
    from analyzer import portable
    from analyzer.contracts import ContractIndex,ContractGrounder
    from analyzer.actors import actor_role,canonical_role,declared_roles
    from analyzer.retrieval_sources import documents
    from analyzer.project import text
    from analyzer.state import U
    from scripted_http_inputs33 import script_grounder
    audit={'network_attempts':0,'target_process_attempts':0,'forbidden_reads':0}
    def guard(event,items):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
            audit['network_attempts' if event.startswith('socket.') else 'target_process_attempts']+=1
            raise PermissionError(event)
        if event=='open' and isinstance(items[0],(str,bytes)):
            path=Path(os.fsdecode(items[0]));mode=items[1]
            if (not isinstance(mode,str) or not any(c in mode for c in 'wax')) and (
                path.suffix=='.json' and ('label' in path.name or path.name.startswith('oracle') or path.name in ('expected.json','queries.json','predictions.json')) or 'gold' in path.parts):
                audit['forbidden_reads']+=1;raise PermissionError(str(path))
    sys.addaudithook(guard)
    corpus=read(V/'development/real-retrieval-frozen-v1/corpus.json')
    cached=read(V/'benchmark/real-retrieval-coderank-02/vectors.json')
    assert cached['identity']['revision']==prereg['revision']
    calibration=read(V/'benchmark/real-retrieval-fixed-selection.json')['calibration']['coderank']
    from code_model_encoders import Encoder
    started=time.perf_counter();encoder=Encoder('coderank',args.storage,args.qwen,'mps');load=time.perf_counter()-started
    assert encoder.revision==prereg['revision']
    query_cache={};query_seconds=0.0;decisions=[];index_checks=[]
    class ShadowIndex(ContractIndex):
        def __init__(self,project,frontend):
            super().__init__(project,frontend);began=time.perf_counter()
            self.docs=corpus[name]['documents'];self.model_calls=0;self.last_decision={}
            assert {c['entry'] for c in self.contracts.values()}==set(self.docs),'candidate universe changed'
            for row in documents(project,self.contracts).values():
                doc=self.docs[row['entry']];facts=row['facts']
                prefix=f"{facts['owner']}.{facts['method']}\nHTTP {facts['http_method']} /{'/'.join(facts['route'])}\nRequest fields: "+json.dumps(facts['request_fields'],ensure_ascii=False,sort_keys=True)+'\n'
                assert prefix+text(project.ast[row['entry']])==doc['text'],'source text changed'
                assert row['source_sha256']==doc['source_sha256'],'source digest changed'
                assert row['entry'] in cached['documents']
            index_checks.append({'project':name,'environment':environment,'mode':mode,'seconds':time.perf_counter()-began,
                'document_vectors_reused':len(self.docs),'new_document_forward_batches':0})
        def rank(self,action,active_page=None,scenario_text=''):
            nonlocal query_seconds
            original=super().rank(action,active_page,scenario_text)
            if action not in query_cache:
                began=time.perf_counter();query_cache[action]=encoder.encode([action],'query')[0][0]
                query_seconds+=time.perf_counter()-began
            self.model_calls=encoder.calls;query=query_cache[action];actor=actor_role(action)
            allowed={key for _,key,_ in original} if args.policy=='same_candidates' else set(self.contracts)
            ranked=[]
            for key in allowed:
                c=self.contracts[key];roles=declared_roles(self.project,c['entry'])
                if actor is not U and roles and canonical_role(actor) not in {canonical_role(role) for role in roles}:continue
                score=sum(x*y for x,y in zip(query,cached['documents'][c['entry']]))
                ranked.append((score,key,c))
            ranked.sort(key=lambda row:(-row[0],row[1]));distinct=[]
            for row in ranked:
                if row[2]['entry'] not in {other[2]['entry'] for other in distinct}:distinct.append(row)
            accepted=bool(distinct) and distinct[0][0]>=calibration['minimum_score'] and (
                len(distinct)==1 or distinct[0][0]-distinct[1][0]>=calibration['minimum_margin'])
            self.last_decision={'mode':'experimental_coderank_'+args.policy,'accepted':accepted,
                'revision':encoder.revision,'minimum_score':calibration['minimum_score'],'minimum_margin':calibration['minimum_margin'],
                'candidate_pool':sorted({self.contracts[key]['entry'] for key in allowed}),
                'candidates':[{'entry':c['entry'],'score':score,'file':self.docs[c['entry']]['file'],
                    'line':self.docs[c['entry']]['line'],'source_sha256':self.docs[c['entry']]['source_sha256']} for score,_,c in distinct[:6]]}
            decisions.append({'project':name,'environment':environment,'mode':mode,'action':action,**self.last_decision})
            return ranked if accepted else []
    portable.ContractIndex=ShadowIndex;runs=[]
    for name in ('employment','healthcare'):
        package=V/'development/semantic-holdout-packages-v1'/name;manifest=read(package/'package.json')
        # The manifest contains hashes, never expected values. Do not open oracle.
        assert all(sha(package/file)==digest for file,digest in manifest['files'].items() if Path(file).name!='oracle.json')
        project_output=args.output/name;project_output.mkdir()
        for environment in ('normal','remote-error'):
            if not (package/environment).is_dir():continue
            for mode in ('explicit-script','nl-en','nl-ru'):
                target=project_output/environment/mode;target.mkdir(parents=True)
                scenarios=package/environment/mode;recipes={}
                if mode=='explicit-script':
                    for file in sorted(scenarios.glob('*.json')):
                        for key,value in read(file).get('request_scripts',{}).items():assert key not in recipes;recipes[key]=value
                portable.ContractGrounder=script_grounder(recipes) if mode=='explicit-script' else ContractGrounder
                skeleton=package/('remote-error-skeleton.json' if environment=='remote-error' else 'skeleton.json')
                sys.argv=['offline_run.py','--source',str(package/'source'),'--skeleton',str(skeleton),
                    '--context',str(package/'initial.sql'),'--scenarios',str(scenarios),
                    '--output',str(target/'submission.json'),'--report',str(target/'report.json'),'--path-limit','4']
                began=time.perf_counter();before=encoder.calls;portable.main()
                runs.append({'environment':environment,'mode':mode,'command':sys.argv[:],
                    'returncode':0,'seconds':time.perf_counter()-began,'model_forward_batches':encoder.calls-before})
                save(project_output/'runs.json',[row for row in runs if Path(row['command'][row['command'].index('--source')+1])==package/'source'])
    import torch
    save(args.output/'experiment.json',{'policy':args.policy,'model':'coderank','revision':encoder.revision,'audit':audit,
        'preregistration_sha256':sha(V/'development/semantic-model-preregistration-e20.json'),
        'source_stage':'E20-response-only-history','model_load_seconds':load,'query_encoding_seconds':query_seconds,
        'unique_queries':len(query_cache),'model_forward_batches':encoder.calls,'index_checks':index_checks,
        'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'mps_allocated_bytes':torch.mps.current_allocated_memory(),'mps_driver_allocated_bytes':torch.mps.driver_allocated_memory(),
        'explicit_bypass_preserved':all(r['model_forward_batches']==0 for r in runs if r['mode']=='explicit-script'),
        'labels_or_oracle_in_inference':False,'default_integration':False,'full_semantic_transfer_verified':False,
        'new_untouched_transfer_claim':False,'runs':runs,'decisions':decisions})
    print(json.dumps({'policy':args.policy,'queries':len(query_cache),'accepted':sum(row['accepted'] for row in decisions),'audit':audit}))


if __name__=='__main__':main()
