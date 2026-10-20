"""Optional, lazy offline vector ranking over existing source contracts only."""
from importlib.metadata import version
import hashlib,json,math,os
from pathlib import Path
from .contracts import ContractIndex
from .retrieval_sources import documents
from .actors import actor_role,canonical_role,declared_roles
from .state import U

PINS={'nomic-ai/CodeRankEmbed':'3c4b60807d71f79b43f3c4363786d9493691f8b1',
      'Qwen/Qwen3-Embedding-0.6B':'97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3'}


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def vector(value):
    if not isinstance(value,list) or not value or any(type(x) not in (int,float) or not math.isfinite(x) for x in value):raise ValueError('invalid vector')
    norm=math.sqrt(sum(x*x for x in value))
    if not norm:raise ValueError('zero vector')
    return [x/norm for x in value]


class LocalEncoder:
    def __init__(self,root,manifest):
        # No remote modules are executed. CodeRank requires a separate custom
        # code audit and is deliberately not supported by this stock loader.
        if manifest['model_id']!='Qwen/Qwen3-Embedding-0.6B':raise ValueError('custom runtime is not audited')
        pins=manifest.get('runtime_versions',{})
        required={'torch','transformers','sentence-transformers','tokenizers'}
        if set(pins)!=required or any(version(name)!=pin for name,pin in pins.items()):raise ValueError('runtime revision mismatch')
        device=manifest.get('device')
        if device not in ('cpu','mps') or manifest.get('dtype')!='float32':raise ValueError('unvalidated device/dtype')
        config=json.loads((root/'config.json').read_text());modules=json.loads((root/'modules.json').read_text())
        if config.get('auto_map') or any(not m['type'].startswith('sentence_transformers.') for m in modules):raise ValueError('unreviewed custom module')
        os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
        import torch
        from sentence_transformers import SentenceTransformer
        if device=='mps' and not torch.backends.mps.is_available():raise ValueError('MPS unavailable in this process')
        torch.set_num_threads(manifest['threads'])
        self.model=SentenceTransformer(str(root),device=device,local_files_only=True,trust_remote_code=False,
            model_kwargs={'torch_dtype':'float32'})
        self.model.max_seq_length=manifest['max_sequence_length']
        self.prefix=manifest['query_prefix'];self.cache={};self.model_calls=0

    def __call__(self,query):
        if query not in self.cache:
            self.model_calls+=1
            self.cache[query]=self.model.encode([self.prefix+query],batch_size=1,prompt='',normalize_embeddings=True,
                show_progress_bar=False,convert_to_numpy=True)[0].tolist()
        return self.cache[query]


class OfflineDenseIndex(ContractIndex):
    def __init__(self,project,frontend,snapshot=None,encoder_factory=LocalEncoder):
        super().__init__(project,frontend)
        self.snapshot=Path(snapshot) if snapshot else None;self.encoder_factory=encoder_factory
        self.corpus=documents(project,self.contracts);self.corpus_digest=digest(self.corpus)
        self.encoder=None;self.vectors=None;self.failure=None;self.last_decision={};self.model_calls=0

    def load(self):
        if self.snapshot is None:raise ValueError('model snapshot absent')
        root=self.snapshot.resolve();manifest=json.loads((root/'manifest.json').read_text())
        if manifest.get('revision')!=PINS.get(manifest.get('model_id')):raise ValueError('model revision mismatch')
        if manifest.get('corpus_digest')!=self.corpus_digest:raise ValueError('source digest changed')
        files=manifest.get('files',{})
        if not files or not {'vectors.json','config.json','modules.json','model.safetensors','tokenizer.json'}<=files.keys():raise ValueError('snapshot files missing')
        for name,expected in files.items():
            path=(root/name).resolve()
            if not path.is_relative_to(root) or not path.is_file():raise ValueError('snapshot file outside root or absent')
            with path.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
            if actual!=expected:raise ValueError('snapshot cache corrupt')
        raw=json.loads((root/'vectors.json').read_text())
        if set(raw)!=set(self.contracts):raise ValueError('vector IDs differ from source contracts')
        self.vectors={key:vector(value) for key,value in raw.items()}
        if len({len(v) for v in self.vectors.values()})!=1:raise ValueError('vector dimension mismatch')
        if not (0<=manifest['minimum_score']<=1 and 0<=manifest['minimum_margin']<=1):raise ValueError('calibration absent')
        if manifest.get('candidate_policy') not in ('same_candidates','expanded'):raise ValueError('candidate policy absent')
        self.manifest=manifest;self.encoder=self.encoder_factory(root,manifest)

    def rank(self,action,active_page=None,scenario_text=''):
        fallback=super().rank(action,active_page,scenario_text)
        try:
            if self.failure:raise ValueError(self.failure)
            if self.encoder is None:self.load()
            self.model_calls+=1;query=vector(self.encoder(action))
            self.model_calls=getattr(self.encoder,'model_calls',self.model_calls)
            if len(query)!=len(next(iter(self.vectors.values()))):raise ValueError('query dimension mismatch')
            actor=actor_role(action);ranked=[]
            allowed={key for _,key,_ in fallback} if self.manifest.get('candidate_policy')=='same_candidates' else set(self.contracts)
            for key in allowed:
                c=self.contracts[key];roles=declared_roles(self.project,c['entry'])
                if actor is not U and roles and canonical_role(actor) not in {canonical_role(r) for r in roles}:continue
                score=sum(a*b for a,b in zip(query,self.vectors[key]));ranked.append((score,key,c))
            ranked.sort(key=lambda r:(-r[0],r[1]));distinct=[]
            for row in ranked:
                if row[2]['entry'] not in [x[2]['entry'] for x in distinct]:distinct.append(row)
            accepted=bool(distinct) and distinct[0][0]>=self.manifest['minimum_score'] and (
                len(distinct)==1 or distinct[0][0]-distinct[1][0]>=self.manifest['minimum_margin'])
            self.last_decision={'mode':'offline_dense','accepted':accepted,'model_id':self.manifest['model_id'],
                'revision':self.manifest['revision'],'corpus_digest':self.corpus_digest,
                'candidates':[{'contract_id':key,'score':score,'file':self.corpus[key]['file'],
                    'line':self.corpus[key]['line'],'source_sha256':self.corpus[key]['source_sha256']} for score,key,_ in ranked[:6]]}
            return ranked if accepted else []
        except (OSError,ValueError,KeyError,ImportError) as error:
            self.failure=str(error);self.last_decision={'mode':'baseline_fallback','reason':self.failure,'model_calls':self.model_calls}
            return fallback
