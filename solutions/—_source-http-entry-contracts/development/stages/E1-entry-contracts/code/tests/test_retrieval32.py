"""Retrieval protocol and failure controls; fake vectors are not model evaluation."""
import hashlib,json,socket
import pytest
from analyzer.contracts import ContractIndex,ContractGrounder
from analyzer.frontend import Frontend
from analyzer.state import ScenarioState
from analyzer.retrieval_sources import unicode_tokens,documents,CHUNK_TOKENS
from analyzer.offline_retrieval import OfflineDenseIndex,PINS
from builders import build,LIBRARY


def setup(tmp_path):
    p,db,ids=build(tmp_path/'source',LIBRARY);f=Frontend(p)
    return p,db,ids,f


def test_unicode_acronym_camel_snake_tokens():
    assert unicode_tokens('HTTPСервер_имяJSON42 DéjàVu')==['http','сервер','имя','json42','déjà','vu']


def test_chunks_are_exact_bounded_source_spans(tmp_path):
    p,_,_,f=setup(tmp_path)
    for document in documents(p,ContractIndex(p,f).contracts).values():
        for chunk in document['chunks']:
            raw=p.sources[chunk['file']][chunk['start_byte']:chunk['end_byte']]
            assert raw.decode()==chunk['text']
            assert hashlib.sha256(raw).hexdigest()==chunk['sha256']
            assert len(unicode_tokens(chunk['text']))<=CHUNK_TOKENS


def cache(tmp_path,p,f,**changes):
    index=OfflineDenseIndex(p,f);root=tmp_path/'snapshot';root.mkdir()
    values={key:[1.,0.] for key in index.contracts}
    for name,data in {'vectors.json':json.dumps(values),'config.json':'{}','modules.json':'[]',
                      'tokenizer.json':'{}','model.safetensors':'unit-test-placeholder-not-weights'}.items():
        (root/name).write_text(data)
    manifest={'model_id':'Qwen/Qwen3-Embedding-0.6B','revision':PINS['Qwen/Qwen3-Embedding-0.6B'],
        'corpus_digest':index.corpus_digest,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()},
        'minimum_score':.5,'minimum_margin':0.,'candidate_policy':'expanded',**changes}
    (root/'manifest.json').write_text(json.dumps(manifest));return root


def test_no_model_network_denied_keeps_baseline(tmp_path,monkeypatch):
    p,_,_,f=setup(tmp_path)
    def denied(*args,**kwargs):pytest.fail('retrieval attempted network')
    monkeypatch.setattr(socket.socket,'connect',denied)
    baseline=ContractIndex(p,f).rank('Read book');index=OfflineDenseIndex(p,f)
    assert [(s,k) for s,k,_ in index.rank('Read book')]==[(s,k) for s,k,_ in baseline]
    assert index.last_decision['mode']=='baseline_fallback' and index.model_calls==0


def test_explicit_bypasses_encoder_and_snapshot_load(tmp_path):
    p,db,ids,f=setup(tmp_path)
    def forbidden(*args):pytest.fail('explicit HTTP loaded a model')
    index=OfflineDenseIndex(p,f,tmp_path/'absent',forbidden)
    proposals,_=ContractGrounder(p,f,index,None,{'facts':{}}).step('GET /books/B1',ScenarioState(db))
    assert proposals and index.encoder is None and index.model_calls==0


@pytest.mark.parametrize('case',['revision','source','corrupt','foreign-id','dimension'])
def test_invalid_cache_preserves_exact_fallback(tmp_path,case):
    p,_,_,f=setup(tmp_path);root=cache(tmp_path,p,f)
    m=json.loads((root/'manifest.json').read_text())
    if case=='revision':m['revision']='0'*40
    elif case=='source':m['corpus_digest']='0'*64
    elif case=='corrupt':(root/'config.json').write_text('corrupt')
    elif case=='foreign-id':
        (root/'vectors.json').write_text(json.dumps({'foreign-contract':[1.,0.]}))
        m['files']['vectors.json']=hashlib.sha256((root/'vectors.json').read_bytes()).hexdigest()
    (root/'manifest.json').write_text(json.dumps(m))
    index=OfflineDenseIndex(p,f,root,lambda *args:lambda query:[1.,0.,0.])
    baseline=ContractIndex(p,f).rank('Read book')
    assert [(s,k) for s,k,_ in index.rank('Read book')]==[(s,k) for s,k,_ in baseline]
    assert index.last_decision['mode']=='baseline_fallback'


def test_fake_encoder_returns_existing_ids_and_evidence_only(tmp_path):
    p,_,_,f=setup(tmp_path);root=cache(tmp_path,p,f)
    index=OfflineDenseIndex(p,f,root,lambda *args:lambda query:[1.,0.]);ranked=index.rank('Read book')
    assert ranked and all(key in index.contracts and contract is index.contracts[key] for _,key,contract in ranked)
    assert index.model_calls==1 and index.last_decision['mode']=='offline_dense'
    assert all(row['source_sha256'] and row['file'] for row in index.last_decision['candidates'])
