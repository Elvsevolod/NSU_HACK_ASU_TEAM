"""Experimental ranking adapter; unchanged production binding/HTTP/execution."""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--profile',choices=('baseline','lexical','dense-same','dense-expanded'),required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--snapshot',type=Path)
    p.add_argument('--storage',type=Path);p.add_argument('--qwen',type=Path)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_IMPLICIT_TOKEN='1',HF_HUB_DISABLE_TELEMETRY='1')
    sys.path[:0]=[str(V/'code'),str(a.storage/'dependencies')] if a.storage else [str(V/'code')]
    from analyzer import portable
    from analyzer.contracts import ContractIndex
    from analyzer.actors import actor_role,canonical_role,declared_roles
    from analyzer.hashing import fingerprint
    from analyzer.retrieval_sources import documents
    from analyzer.project import text
    from analyzer.state import U
    encoder=None;snapshot=None;model_load_seconds=0
    if a.profile.startswith('dense'):
        from code_model_encoders import Encoder
        snapshot=json.loads(a.snapshot.read_text());started=time.perf_counter()
        encoder=Encoder(snapshot['model'],a.storage,a.qwen,'mps');model_load_seconds=time.perf_counter()-started
        assert encoder.revision==snapshot['revision']
        assert snapshot['adapter_sha256']==hashlib.sha256((V/'checks/code_model_encoders.py').read_bytes()).hexdigest()
    audit={'network_attempts':0,'target_process_attempts':0,'forbidden_reads':0}
    def guard(event,items):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
            audit['network_attempts' if event.startswith('socket.') else 'target_process_attempts']+=1
            raise PermissionError(event)
        if event=='open' and isinstance(items[0],(str,bytes)):
            path=Path(os.fsdecode(items[0]));mode=items[1]
            if (not isinstance(mode,str) or not any(c in mode for c in 'wax')) and (
                path.suffix=='.json' and ('label' in path.name or path.name.startswith('oracle') or path.name in ('queries.json','expected.json','predictions.json','model-comparison.json')) or 'gold' in path.parts):
                audit['forbidden_reads']+=1;raise PermissionError(str(path))
    sys.addaudithook(guard)
    query_cache={};decisions=[]
    class ShadowIndex(ContractIndex):
        def __init__(self,project,frontend):
            super().__init__(project,frontend)
            self.model_calls=0;self.last_decision={}
            self.documents=snapshot['projects'][name]
            assert snapshot['input_fingerprints'][name]==fingerprint(project),'source/config input changed'
            assert {c['entry'] for c in self.contracts.values()}==set(self.documents),'changed candidate universe'
            for row in documents(project,self.contracts).values():
                facts=row['facts']
                prefix=f"{facts['owner']}.{facts['method']}\nHTTP {facts['http_method']} /{'/'.join(facts['route'])}\nRequest fields: "+json.dumps(facts['request_fields'],ensure_ascii=False,sort_keys=True)+'\n'
                assert hashlib.sha256((prefix+text(project.ast.get(row['entry']))).encode()).hexdigest()==self.documents[row['entry']]['text_sha256'],'source contract text changed'
            for mid,doc in self.documents.items():
                assert doc['source_sha256']==hashlib.sha256(project.sources[project.methods[mid]['file']]).hexdigest(),'source digest mismatch'
        def rank(self,action,active_page=None,scenario_text=''):
            original=super().rank(action,active_page,scenario_text)
            if action not in query_cache:query_cache[action]=encoder.encode([action],'query')[0][0]
            self.model_calls=encoder.calls;query=query_cache[action];actor=actor_role(action)
            allowed={key for _,key,_ in original} if a.profile=='dense-same' else set(self.contracts)
            ranked=[]
            for key in allowed:
                c=self.contracts[key];roles=declared_roles(self.project,c['entry'])
                if actor is not U and roles and canonical_role(actor) not in {canonical_role(r) for r in roles}:continue
                score=sum(x*y for x,y in zip(query,self.documents[c['entry']]['vector']))
                ranked.append((score,key,c))
            ranked.sort(key=lambda r:(-r[0],r[1]));distinct=[]
            for score,key,c in ranked:
                if c['entry'] not in [row[2]['entry'] for row in distinct]:distinct.append((score,key,c))
            accepted=bool(distinct) and distinct[0][0]>=snapshot['minimum_score'] and (
                len(distinct)<2 or distinct[0][0]-distinct[1][0]>=snapshot['minimum_margin'])
            self.last_decision={'mode':a.profile,'accepted':accepted,'model':snapshot['model'],'revision':encoder.revision,
                'candidates':[{'entry':c['entry'],'score':score,'file':self.documents[c['entry']]['file'],
                    'line':self.documents[c['entry']]['line'],'source_sha256':self.documents[c['entry']]['source_sha256']} for score,key,c in distinct[:6]],
                'candidate_pool':sorted({self.contracts[key]['entry'] for key in allowed})}
            decisions.append({'project':name,'action':action,**self.last_decision})
            return ranked if accepted else []
    if encoder:portable.ContractIndex=ShadowIndex
    runs=[]
    for name in ('organization','library'):
        package=V/'development/transfer'/name;manifest=json.loads((package/'package.json').read_text())
        for mode in ('explicit','nl'):
            target=a.output/name/mode;target.mkdir(parents=True)
            sys.argv=['offline_run.py']
            for flag,key in [('source','source'),('skeleton','skeleton'),('context','context'),('scenarios',mode+'_scenarios')]:
                sys.argv+=['--'+flag,str(package/manifest[key])]
            sys.argv+=['--output',str(target/'submission.json'),'--report',str(target/'report.json'),'--path-limit','4']
            if a.profile=='lexical':sys.argv+=['--retrieval','lexical']
            started=time.perf_counter();before=encoder.calls if encoder else 0
            portable.main()
            runs.append({'project':name,'mode':mode,'seconds':time.perf_counter()-started,'model_forward_batches':encoder.calls-before if encoder else 0,
                'arguments':sys.argv[1:]})
    (a.output/'experiment.json').write_text(json.dumps({'profile':a.profile,'runs':runs,'audit':audit,
        'model_load_seconds':model_load_seconds,'decisions':decisions,'snapshot_sha256':hashlib.sha256(a.snapshot.read_bytes()).hexdigest() if a.snapshot else None,
        'model_forward_batches':encoder.calls if encoder else 0,'labels_or_oracle_in_inference':False,
        'default_integration':False,'semantics':'Same current production analyze, ContractGrounder, path runner and budgets',
        'explicit_bypass_preserved':all(r['model_forward_batches']==0 for r in runs if r['mode']=='explicit')},ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
