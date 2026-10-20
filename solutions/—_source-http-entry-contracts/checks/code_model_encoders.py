"""Pinned local embedding paths, with the checkpoint's actual pooling contract."""
import hashlib
import importlib
import json
import sys
from pathlib import Path

import torch
from torch import nn
from transformers import BertTokenizerFast,RobertaConfig,RobertaModel,RobertaTokenizer,T5Config,T5EncoderModel

V=Path(__file__).resolve().parents[1]
PREFIXES={'unixcoder':'','codet5p':'','coderank':'Represent this query for searching relevant code: ',
    'qwen':"Instruct: Retrieve the source HTTP contract that implements the user's requested action.\nQuery: "}


class ProjectedT5(T5EncoderModel):
    def __init__(self,config,dimension):
        super().__init__(config)
        self.proj=nn.Linear(config.d_model,dimension)

    def forward(self,input_ids,attention_mask):
        encoded=self.encoder(input_ids=input_ids,attention_mask=attention_mask,return_dict=True).last_hidden_state
        return torch.nn.functional.normalize(self.proj(encoded[:,0,:]),dim=-1)


class Encoder:
    def __init__(self,name,storage,qwen,device):
        self.name,self.device,self.calls=name,device,0
        torch.set_num_threads(4);torch.manual_seed(0)
        self.source_files={}
        if name=='qwen':
            from sentence_transformers import SentenceTransformer
            self.model=SentenceTransformer(str(qwen),device=device,local_files_only=True,trust_remote_code=False,
                model_kwargs={'torch_dtype':'float32'})
            self.model.max_seq_length=512
            self.tokenizer=self.model.tokenizer
            self.revision='97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3'
        else:
            metadata=next(row for row in json.loads((V/'development/model-metadata/pins.json').read_text()) if row['name']==name)
            self.revision=metadata['revision'];root=storage/name
            for file,expected in metadata['downloaded_files'].items():
                assert hashlib.sha256((root/file).read_bytes()).hexdigest()==expected,file
            weight=next(row for row in metadata['siblings'] if row['name']==('model.safetensors' if name=='coderank' else 'pytorch_model.bin'))
            with (root/weight['name']).open('rb') as stream:
                assert hashlib.file_digest(stream,'sha256').hexdigest()==weight['lfs']['sha256']
            config=json.loads((root/'config.json').read_text())
            if name=='unixcoder':
                config=RobertaConfig(**config);config.is_decoder=True;config._attn_implementation='eager'
                self.model=RobertaModel(config)
                self.tokenizer=RobertaTokenizer.from_pretrained(root,local_files_only=True)
                assert self.tokenizer.convert_tokens_to_ids('<encoder-only>')!=self.tokenizer.unk_token_id
            elif name=='codet5p':
                self.model=ProjectedT5(T5Config(**config),config['embed_dim'])
                self.tokenizer=RobertaTokenizer.from_pretrained(root,local_files_only=True)
            elif name=='coderank':
                source=V/'development/model-code/coderank'
                for file in ('configuration_hf_nomic_bert.py','modeling_hf_nomic_bert.py'):
                    expected=metadata['downloaded_files'][file]
                    assert hashlib.sha256((source/file).read_bytes()).hexdigest()==expected
                    self.source_files[file]=expected
                assert (source/'__init__.py').read_bytes()==b''
                sys.path.insert(0,str(source.parent))
                configuration=importlib.import_module('coderank.configuration_hf_nomic_bert')
                modeling=importlib.import_module('coderank.modeling_hf_nomic_bert')
                self.model=modeling.NomicBertModel(configuration.NomicBertConfig(**config),add_pooling_layer=False)
                self.tokenizer=BertTokenizerFast.from_pretrained(root,local_files_only=True)
            else:raise ValueError(name)
            if name=='coderank':
                from safetensors.torch import load_file
                weights=load_file(root/weight['name'],device='cpu')
            else:weights=torch.load(root/weight['name'],map_location='cpu',weights_only=True)
            assert isinstance(weights,dict) and all(isinstance(k,str) and isinstance(v,torch.Tensor) for k,v in weights.items())
            if name=='unixcoder' and 'embeddings.position_ids' in weights:
                # Older Transformers persisted this deterministic buffer. Keep strict loading.
                positions=self.model.embeddings.position_ids
                assert torch.equal(weights['embeddings.position_ids'],positions)
                self.model.embeddings.register_buffer('position_ids',positions,persistent=True)
            self.loading_info=str(self.model.load_state_dict(weights,strict=True))
            del weights
            self.model.to(device=device,dtype=torch.float32)
        self.model.eval()

    def encode(self,texts,role):
        applied=[(PREFIXES[self.name] if role=='query' else '')+text for text in texts]
        lengths=[];unknown_tokens=[]
        for text in applied:
            ids=self.tokenizer.encode(text,add_special_tokens=False)
            lengths.append(len(ids)+(4 if self.name=='unixcoder' else 2))
            unknown_tokens.append(ids.count(self.tokenizer.unk_token_id))
        with torch.inference_mode():
            if self.name=='qwen':
                vectors=self.model.encode(applied,batch_size=len(applied),prompt='',normalize_embeddings=True,
                    show_progress_bar=False,convert_to_tensor=True)
            else:
                if self.name=='unixcoder':
                    rows=[]
                    for text in applied:
                        tokens=self.tokenizer.tokenize(text)[:508]
                        rows.append(self.tokenizer.convert_tokens_to_ids([self.tokenizer.cls_token,'<encoder-only>',self.tokenizer.sep_token,*tokens,self.tokenizer.sep_token]))
                    maximum=max(map(len,rows))
                    ids=torch.tensor([row+[self.tokenizer.pad_token_id]*(maximum-len(row)) for row in rows],device=self.device)
                    mask=ids.ne(self.tokenizer.pad_token_id)
                    hidden=self.model(ids,attention_mask=mask.unsqueeze(1)*mask.unsqueeze(2),use_cache=False).last_hidden_state
                    vectors=(hidden*mask.unsqueeze(-1)).sum(1)/mask.sum(-1).unsqueeze(-1)
                else:
                    batch=self.tokenizer(applied,padding=True,truncation=True,max_length=512,return_tensors='pt').to(self.device)
                    output=self.model(input_ids=batch['input_ids'],attention_mask=batch['attention_mask'])
                    vectors=output if self.name=='codet5p' else output.last_hidden_state[:,0,:]
                vectors=torch.nn.functional.normalize(vectors,p=2,dim=-1)
            if self.device=='mps':torch.mps.synchronize()
            assert torch.isfinite(vectors).all()
            assert torch.allclose(torch.linalg.vector_norm(vectors,dim=-1),torch.ones(len(texts),device=self.device),atol=1e-4)
            result=vectors.float().cpu().tolist()
        self.calls+=1
        return result,[{'untruncated_tokens':length,'truncated':length>512,'unknown_tokens':unknown}
            for length,unknown in zip(lengths,unknown_tokens)]
