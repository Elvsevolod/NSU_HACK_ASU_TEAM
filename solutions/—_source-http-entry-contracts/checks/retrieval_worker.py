"""Prediction worker: receives actions only, never relevance labels."""
import argparse,hashlib,json,platform,resource,sys,time
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--code',type=Path,required=True);p.add_argument('--profile',choices=('A','B','C'),required=True)
    p.add_argument('--actions',type=Path,required=True);p.add_argument('--projects',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--snapshots',type=Path);p.add_argument('--candidate-policy',choices=('same_candidates','expanded'),default='expanded')
    args=p.parse_args();sys.path.insert(0,str(args.code.resolve()))
    from analyzer.project import Project
    from analyzer.frontend import Frontend
    from analyzer.contracts import ContractIndex,ContractGrounder
    from analyzer.state import Database,ScenarioState
    from analyzer.__main__ import serial
    shared={};model_loads=[];environment=platform.platform()
    if args.profile=='C':
        import torch
        from sentence_transformers import SentenceTransformer
        from analyzer.offline_retrieval import OfflineDenseIndex,LocalEncoder
        def factory(root,manifest):
            signature=json.dumps({k:v for k,v in manifest.items() if k not in ('corpus_digest','files','candidate_policy')},sort_keys=True)
            signature+=json.dumps({k:v for k,v in manifest['files'].items() if k!='vectors.json'},sort_keys=True)
            if signature not in shared:
                start=time.perf_counter();shared[signature]=LocalEncoder(root,manifest)
                model_loads.append({'seconds':time.perf_counter()-start,'device':manifest['device'],'revision':manifest['revision']})
            return shared[signature]
        class Index(OfflineDenseIndex):
            def __init__(self,project,frontend):
                super().__init__(project,frontend,args.snapshots/name,factory)
            def load(self):
                super().load();self.manifest={**self.manifest,'candidate_policy':args.candidate_policy}
    elif args.profile=='B':
        from analyzer.lexical_retrieval import LexicalContractIndex
        Index=LexicalContractIndex
    else:Index=ContractIndex
    audit={'network_attempts':0,'forbidden_reads':0,'target_process_attempts':0}
    def guard(event,items):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
            audit['network_attempts' if event.startswith('socket.') else 'target_process_attempts']+=1
            raise PermissionError(event)
        if event=='open' and isinstance(items[0],(str,bytes)):
            path=Path(items[0]);mode=items[1]
            if (not isinstance(mode,str) or not any(c in mode for c in 'wax')) and (
                path.name=='queries.json' or path.name.startswith('oracle') or 'gold' in path.parts):
                audit['forbidden_reads']+=1;raise PermissionError(str(path))
    actions=json.loads(args.actions.read_text());projects=json.loads(args.projects.read_text())
    sys.addaudithook(guard);predictions=[];cost=[]
    for name,location in projects.items():
        root=Path(location);started=time.perf_counter()
        project=Project(root/'skeleton.json',root) if name!='trainticket' else Project(root/'skeleton/trainticket.json.gz',root/'targets/trainticket')
        frontend=Frontend(project);prepared=time.perf_counter();index=Index(project,frontend);indexed=time.perf_counter()
        dump=root/'initial.sql' if name!='trainticket' else root/'context/db-after-warmup.sql.gz'
        database=Database(dump);context={'facts':{},'unresolved':[]}
        grounder=ContractGrounder(project,frontend,index,None,context)
        for query in (q for q in actions if q['project']==name):
            action=query['action'];state=ScenarioState(database,context);start=time.perf_counter()
            if query['language']=='explicit':
                original=index.rank
                def forbidden_rank(*a,**kw):raise AssertionError('explicit request entered retrieval')
                index.rank=forbidden_rank
                try:proposals,detail=grounder.step(action,state)
                finally:index.rank=original
                ranked=[];decision={'bypass':True}
            else:
                ranked=index.rank(action);decision=dict(getattr(index,'last_decision',{}))
                proposals,detail=grounder.step(action,state)
            rows=[{'contract_id':key,'entry':c['entry'],'score':score} for score,key,c in ranked]
            if not rows and decision.get('raw_top'):rows=decision['raw_top']
            if not rows and decision.get('candidates'):
                rows=[{**row,'entry':index.contracts[row['contract_id']]['entry']} for row in decision['candidates']]
            for row in rows:
                meta=project.methods[row['entry']]
                row['evidence']={'file':meta['file'],'line':meta.get('line'),
                    'source_sha256':hashlib.sha256(project.sources[meta['file']]).hexdigest()}
            unique=[]
            for row in rows:
                if row['entry'] not in [r['entry'] for r in unique]:unique.append(row)
            predictions.append({'id':query['id'],'ranking':unique[:6],'accepted_entries':sorted({p['entry'] for p in proposals}),
                'decision':decision,'grounding':detail,'requests':[p['request'].record() for p in proposals if p.get('request')],
                'bindings':[p['bindings'] for p in proposals],'query_seconds':time.perf_counter()-start})
        cost.append({'project':name,'source_preparation_seconds':prepared-started,'index_seconds':indexed-prepared,
            'contracts':len(index.contracts),'canonical_handlers':len({c['entry'] for c in index.contracts.values()})})
    warm=[]
    if shared:
        encoder=next(iter(shared.values()));sample=next(q['action'] for q in actions if q['language']!='explicit')
        for _ in range(3):
            before=time.perf_counter()
            encoder.model.encode([encoder.prefix+sample],batch_size=1,prompt='',normalize_embeddings=True,show_progress_bar=False)
            if encoder.model.device.type=='mps':torch.mps.synchronize()
            warm.append(time.perf_counter()-before)
    args.output.write_text(json.dumps({'profile':args.profile,'predictions':predictions,'cost':cost,'audit':audit,
        'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'model_calls':sum(e.model_calls for e in shared.values()),'additional_warm_forward_samples':warm,
        'model_loads':model_loads,'environment':environment,'candidate_policy':args.candidate_policy,
        'mps_allocated_bytes':torch.mps.current_allocated_memory() if shared and torch.backends.mps.is_available() else None,
        'mps_driver_allocated_bytes':torch.mps.driver_allocated_memory() if shared and torch.backends.mps.is_available() else None,
        'labels_available_to_worker':False},default=serial,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
