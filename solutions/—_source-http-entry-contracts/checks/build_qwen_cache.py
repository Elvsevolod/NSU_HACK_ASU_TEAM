"""Build pinned local source indexes offline. No relevance labels are read."""
import argparse,hashlib,json,os,platform,resource,sys,time
from importlib.metadata import version
from pathlib import Path
V=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(V/'code'))
from analyzer.offline_retrieval import LocalEncoder,PINS,digest,vector
from analyzer.retrieval_sources import documents
from analyzer.contracts import ContractIndex
from analyzer.project import Project
from analyzer.frontend import Frontend


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--frozen',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--device',choices=('cpu','mps'),required=True);args=p.parse_args()
    assert not args.output.exists() and not args.evidence.exists();args.output.mkdir(parents=True);args.evidence.mkdir(parents=True)
    # Import approved runtime before the application-input audit; no application
    # data, network requests or model loading have happened at this point.
    import torch
    from sentence_transformers import SentenceTransformer
    torch.set_num_threads(4)
    audit={'network_attempts':0,'process_attempts':0,'label_or_gold_reads':0}
    def guard(event,items):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
            audit['network_attempts' if event.startswith('socket.') else 'process_attempts']+=1;raise PermissionError(event)
        if event=='open' and isinstance(items[0],(str,bytes)):
            file=Path(items[0]);mode=items[1]
            if (not isinstance(mode,str) or not any(c in mode for c in 'wax')) and (file.name=='queries.json' or file.name.startswith('oracle') or 'gold' in file.parts):
                audit['label_or_gold_reads']+=1;raise PermissionError(str(file))
    sys.addaudithook(guard);started=time.perf_counter()
    model=args.model.resolve()
    hashes={}
    for file in sorted(model.rglob('*')):
        if not file.is_file() or '.cache' in file.parts:continue
        if file.suffix=='.py':raise ValueError('custom model code is outside this pilot')
        with file.open('rb') as stream:hashes[file.relative_to(model).as_posix()]=hashlib.file_digest(stream,'sha256').hexdigest()
    runtime={name:version(name) for name in ('torch','transformers','sentence-transformers','tokenizers')}
    manifest={'schema':'offline-source-retrieval/1','model_id':'Qwen/Qwen3-Embedding-0.6B',
      'revision':PINS['Qwen/Qwen3-Embedding-0.6B'],'files':hashes,'runtime_versions':runtime,
      'device':args.device,'dtype':'float32','threads':4,'max_sequence_length':512,
      'query_prefix':"Instruct: Retrieve the source HTTP contract that implements the user's requested action.\nQuery: ",
      'document_prefix':'','pooling':'revision modules: last-token then Normalize; normalized mean of all fact/chunk unit embeddings per contract',
      'document_batch_size':4,'query_batch_size':1,'candidate_policy':'expanded','minimum_score':.35,'minimum_margin':.03,
      'license':'apache-2.0','custom_code':False,'test_labels_used':False,'split':'development only'}
    # Freeze profile before any forward pass or query-label access.
    (args.evidence/'protocol.json').write_text(json.dumps(manifest,indent=2)+'\n')
    load_start=time.perf_counter();encoder=LocalEncoder(model,manifest)
    load_seconds=time.perf_counter()-load_start
    corpus=json.loads((args.frozen/'corpus.json').read_text())
    projects={'piggymetrics':V/'validation_inputs/piggymetrics','cart':V/'validation_inputs/shopping-cart',
      'petclinic':V/'validation_inputs/legacy-real/petclinic-customers','unicode':args.frozen/'unicode-source',
      'trainticket':V.parents[1]/'tt-challenge'}
    rows=[]
    for name,root in projects.items():
        start=time.perf_counter()
        project=Project(root/'skeleton.json',root) if name!='trainticket' else Project(root/'skeleton/trainticket.json.gz',root/'targets/trainticket')
        index=ContractIndex(project,Frontend(project));docs=documents(project,index.contracts);prepared=time.perf_counter()
        assert digest(docs)==digest(corpus[name]['documents']),name+' corpus drift'
        units=[];owners=[]
        for key,doc in docs.items():
            for content in [doc['fact_text'],*(chunk['text'] for chunk in doc['chunks'])]:units.append(content);owners.append(key)
        lengths=[len(encoder.model.tokenizer.encode(unit,add_special_tokens=True,truncation=False)) for unit in units]
        before=time.perf_counter()
        embeddings=encoder.model.encode(units,batch_size=4,prompt='',normalize_embeddings=True,show_progress_bar=False,convert_to_numpy=True)
        if args.device=='mps':torch.mps.synchronize()
        encoded=time.perf_counter();grouped={}
        for key,embedding in zip(owners,embeddings):grouped.setdefault(key,[]).append(embedding.tolist())
        vectors={key:vector([sum(parts)/len(group) for parts in zip(*group)]) for key,group in grouped.items()}
        destination=args.output/name;destination.mkdir()
        for file in hashes:
            target=destination/file;target.parent.mkdir(parents=True,exist_ok=True);os.link(model/file,target)
        (destination/'vectors.json').write_text(json.dumps(vectors,separators=(',',':'))+'\n')
        local={**manifest,'files':{**hashes,'vectors.json':hashlib.sha256((destination/'vectors.json').read_bytes()).hexdigest()},'corpus_digest':digest(docs)}
        (destination/'manifest.json').write_text(json.dumps(local,indent=2)+'\n')
        row={'project':name,'contracts':len(docs),'units':len(units),'source_preparation_seconds':prepared-start,
          'document_encoding_seconds':encoded-before,'units_over_512_tokens':sum(n>512 for n in lengths),'max_untruncated_tokens':max(lengths),
          'index_bytes':(destination/'vectors.json').stat().st_size,'corpus_digest':digest(docs)}
        rows.append(row);print(json.dumps(row),flush=True)
    result={'model_load_seconds':load_seconds,'elapsed_seconds':time.perf_counter()-started,'projects':rows,'audit':audit,
      'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'device':args.device,'python':platform.python_version(),
      'platform':platform.platform(),'runtime':runtime,'mps_allocated_bytes':torch.mps.current_allocated_memory() if args.device=='mps' else None,
      'mps_driver_allocated_bytes':torch.mps.driver_allocated_memory() if args.device=='mps' else None,
      'model_weight_bytes':(model/'model.safetensors').stat().st_size,'labels_available_to_inference':False,'targets_started':False,
      'fresh_process':'model unloaded at process start; OS disk/page cache uncontrolled'}
    (args.evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
