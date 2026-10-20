"""Offline prediction worker: source corpus and actions only, never labels."""
import argparse
import hashlib
import json
import math
import os
import platform
import resource
import sys
import time
from importlib.metadata import version
from pathlib import Path

V=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',choices=('unixcoder','codet5p','coderank','qwen'),required=True)
    parser.add_argument('--storage',type=Path,required=True)
    parser.add_argument('--qwen',type=Path,required=True)
    parser.add_argument('--frozen',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--context',action='store_true')
    parser.add_argument('--device',choices=('mps','cpu'),required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    for key in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_HUB_DISABLE_IMPLICIT_TOKEN','HF_HUB_DISABLE_TELEMETRY'):
        os.environ[key]='1'
    sys.path.insert(0,str(args.storage/'dependencies'))
    import torch
    from code_model_encoders import Encoder
    environment=platform.platform()
    runtime={name:version(name) for name in ('torch','transformers','tokenizers','sentence-transformers','safetensors','einops')}
    audit={'network_attempts':0,'process_attempts':0,'label_or_oracle_reads':0}
    def guard(event,items):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
            audit['network_attempts' if event.startswith('socket.') else 'process_attempts']+=1
            raise PermissionError(event)
        if event=='open' and isinstance(items[0],(str,bytes)):
            path=Path(os.fsdecode(items[0]));mode=items[1]
            if (not isinstance(mode,str) or not any(c in mode for c in 'wax')) and (
                (path.suffix=='.json' and ('label' in path.name or path.name in ('queries.json','expected.json') or path.name.startswith('oracle')))
                or 'gold' in path.parts):
                audit['label_or_oracle_reads']+=1;raise PermissionError(str(path))
    sys.addaudithook(guard)
    manifest=json.loads((args.frozen/'sha256.json').read_text())
    for name in ('protocol.json','corpus.json','actions.json'):
        assert hashlib.sha256((args.frozen/name).read_bytes()).hexdigest()==manifest[name],name
    corpus=json.loads((args.frozen/'corpus.json').read_text())
    actions=json.loads((args.frozen/'actions.json').read_text())
    assert all(set(q)=={'id','project','action','language','split'} for q in actions)
    started=time.perf_counter();encoder=Encoder(args.model,args.storage,args.qwen,args.device)
    load_seconds=time.perf_counter()-started
    smoke_start=time.perf_counter()
    smoke,smoke_tokens=encoder.encode(['Read one item by identifier.','String find(String id) { return store.findById(id); }'],'document')
    smoke_seconds=time.perf_counter()-smoke_start
    smoke_result={'passed':len(smoke)==2 and len(smoke[0])>0,'dimension':len(smoke[0]),'tokens':smoke_tokens,'seconds':smoke_seconds}
    (args.output/'smoke.json').write_text(json.dumps(smoke_result,indent=2)+'\n')
    identity={'model':args.model,'revision':encoder.revision,'device':args.device,'dtype':'float32','max_tokens':512,
        'adapter_sha256':hashlib.sha256((V/'checks/code_model_encoders.py').read_bytes()).hexdigest(),'runtime':runtime}
    cache_hits=0;cache_misses=0;token_info=[];encoded_times=[]
    def encode_cached(items,role,batch_size):
        nonlocal cache_hits,cache_misses
        result={};missing=[]
        for key,text in items:
            digest=hashlib.sha256(json.dumps([identity,role,text],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            path=args.cache/args.model/(digest+'.json')
            if path.is_file():
                cached=json.loads(path.read_text());assert cached['identity']==identity and cached['text_sha256']==hashlib.sha256(text.encode()).hexdigest()
                result[key]=cached['vector'];cache_hits+=1
                token_info.append({'id':key,'role':role,**cached['tokens'],'cache_hit':True})
            else:missing.append((key,text,path));cache_misses+=1
        for offset in range(0,len(missing),batch_size):
            group=missing[offset:offset+batch_size];before=time.perf_counter()
            vectors,tokens=encoder.encode([text for _,text,_ in group],role)
            encoded_times.append({'role':role,'items':len(group),'seconds':time.perf_counter()-before})
            for (key,text,path),vector,stats in zip(group,vectors,tokens):
                assert all(math.isfinite(v) for v in vector)
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(json.dumps({'identity':identity,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),
                    'vector':vector,'tokens':stats},separators=(',',':'))+'\n')
                result[key]=vector;token_info.append({'id':key,'role':role,**stats,'cache_hit':False})
        return result
    column='context_text' if args.context else 'text'
    documents=[(entry,doc[column]) for project in corpus.values() for entry,doc in project['documents'].items()]
    assert len({key for key,_ in documents})==len(documents)
    indexed=time.perf_counter();vectors=encode_cached(documents,'document',4);index_seconds=time.perf_counter()-indexed
    query_start=time.perf_counter();queries=encode_cached([(q['id'],q['action']) for q in actions],'query',1);query_seconds=time.perf_counter()-query_start
    predictions=[]
    for query in actions:
        started_rank=time.perf_counter();project=corpus[query['project']];pool=project['candidate_pool']
        ranked=sorted(({'entry':entry,'score':sum(a*b for a,b in zip(queries[query['id']],vectors[entry])),
            'evidence':{key:project['documents'][entry][key] for key in ('file','line','source_sha256')}} for entry in pool),
            key=lambda row:(-row['score'],row['entry']))
        predictions.append({'id':query['id'],'ranking':ranked,'candidate_pool':pool,'ranking_seconds':time.perf_counter()-started_rank})
    warm=[]
    for _ in range(3):
        before=time.perf_counter();encoder.encode([actions[0]['action']],'query');warm.append(time.perf_counter()-before)
    (args.output/'vectors.json').write_text(json.dumps({'identity':identity,'documents':vectors,'queries':queries},separators=(',',':'))+'\n')
    result={'model':args.model,'identity':identity,'predictions':predictions,'audit':audit,'labels_available_to_model':False,
        'candidate_context':'source_context' if args.context else 'method_contract','smoke':smoke_result,
        'cost':{'model_load_seconds':load_seconds,'smoke_seconds':smoke_seconds,'index_seconds':index_seconds,
            'query_encoding_seconds':query_seconds,'model_forward_batches':encoder.calls,'batch_timings':encoded_times,
            'warm_forward_seconds':warm,'cache_hits':cache_hits,'cache_misses':cache_misses,
            'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'index_json_bytes':(args.output/'vectors.json').stat().st_size,
            'mps_allocated_bytes':torch.mps.current_allocated_memory() if args.device=='mps' else None,
            'mps_driver_bytes':torch.mps.driver_allocated_memory() if args.device=='mps' else None,
            'fresh_process':'Model absent at process start; OS disk/page cache uncontrolled'},
        'tokens':token_info,'environment':environment,'audited_model_code':encoder.source_files,
        'strict_tensor_loading':getattr(encoder,'loading_info','approved stock SentenceTransformer Qwen local-only loader'),
        'external_apis':False,'target_applications_started':False}
    (args.output/'predictions.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'model':args.model,'dimension':smoke_result['dimension'],'queries':len(predictions),
        'index_seconds':index_seconds,'query_seconds':query_seconds,'audit':audit},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
