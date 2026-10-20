"""Label-only evaluation; development selection is saved before test is opened."""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

V=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(V/'code'))
from baseline_closure import BM25
from analyzer.retrieval_sources import unicode_tokens


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_predictions(predictions,actions,corpus):
    assert len(predictions)==len(actions) and {p['id'] for p in predictions}=={a['id'] for a in actions},'incomplete/duplicate predictions'
    by_id={a['id']:a for a in actions}
    for prediction in predictions:
        project=corpus[by_id[prediction['id']]['project']]
        assert prediction['candidate_pool']==project['candidate_pool'],'foreign/changed candidate pool'
        ranked=prediction['ranking'];ids=[r['entry'] for r in ranked];scores=[r['score'] for r in ranked]
        assert len(ids)==len(set(ids)) and set(ids)==set(project['candidate_pool']),'incomplete/foreign ranking IDs'
        assert all(type(s) in (int,float) and math.isfinite(s) for s in scores),'nonfinite ranking score'
        assert scores==sorted(scores,reverse=True),'ranking is not sorted'


def lexical(frozen,output):
    corpus=json.loads((frozen/'corpus.json').read_text());actions=json.loads((frozen/'actions.json').read_text())
    started=time.perf_counter()
    indices={name:BM25({mid:unicode_tokens(doc['text']) for mid,doc in project['documents'].items()})
             for name,project in corpus.items()}
    index_seconds=time.perf_counter()-started;predictions=[];times=[]
    for q in actions:
        before=time.perf_counter();project=corpus[q['project']]
        scores={mid:score/(1+score) for score,mid in indices[q['project']].rank(unicode_tokens(q['action']))}
        ranking=sorted(({'entry':mid,'score':scores.get(mid,0)} for mid in project['candidate_pool']),key=lambda r:(-r['score'],r['entry']))
        seconds=time.perf_counter()-before;times.append(seconds)
        predictions.append({'id':q['id'],'ranking':ranking,'candidate_pool':project['candidate_pool'],'ranking_seconds':seconds})
    save(output,{'model':'common-bm25','predictions':predictions,'candidate_context':'method_contract',
        'labels_available_to_model':False,'cost':{'index_seconds':index_seconds,'query_seconds':sum(times),'model_forward_batches':0},
        'tokenizer':'NFKC Unicode + identifier split; same documents/pool as embeddings','score':'BM25 s/(1+s); not probability'})


def rows(labels,predictions,threshold):
    by_id={p['id']:p for p in predictions};score_min,margin_min=threshold;result=[]
    for q in labels:
        prediction=by_id[q['id']];ranked=prediction['ranking'];ids=[p['entry'] for p in ranked]
        assert len(ids)==len(set(ids)) and set(ids)==set(prediction['candidate_pool'])
        valid=set(q['acceptable_entries']);refuse=q['requires_refusal'];answer=not refuse
        score=ranked[0]['score'] if ranked else -1;second=ranked[1]['score'] if len(ranked)>1 else 0
        accepted=bool(ranked) and score>=score_min and score-second>=margin_min
        rank=next((i+1 for i,mid in enumerate(ids) if mid in valid),None)
        result.append({**q,'top1':ids[0] if ids else None,'rank':rank,'score':score,'margin':score-second,
            'accepted':accepted,'correct_top1':answer and bool(ids) and ids[0] in valid,
            'false_accept':refuse and accepted,'false_reject':answer and not accepted,
            'wrong_accept':answer and accepted and (not ids or ids[0] not in valid),
            'accepted_correct':answer and accepted and bool(ids) and ids[0] in valid,
            'candidate_available':bool(valid&set(ids)),'ranking':ranked})
    return result


def metrics(records):
    answer=[r for r in records if not r['requires_refusal']];refusal=[r for r in records if r['requires_refusal']]
    accepted=[r for r in records if r['accepted']];result={'queries':len(records),'answer_queries':len(answer),'refusal_queries':len(refusal)}
    for k in (1,3,6):
        count=sum(r['rank'] is not None and r['rank']<=k for r in answer)
        result['recall_at_'+str(k)]={'count':count,'denominator':len(answer),'rate':count/len(answer) if answer else None}
    result.update(mrr=sum(1/r['rank'] if r['rank'] else 0 for r in answer)/len(answer) if answer else None,
        accepted=len(accepted),accepted_correct=sum(r['accepted_correct'] for r in records),
        false_accepts=sum(r['false_accept'] for r in records),false_rejects=sum(r['false_reject'] for r in records),
        wrong_accepts=sum(r['wrong_accept'] for r in records),
        coverage=len(accepted)/len(records) if records else None,
        accepted_error=(sum(r['wrong_accept'] or r['false_accept'] for r in accepted)/len(accepted)) if accepted else None,
        candidate_available=sum(r['candidate_available'] for r in answer))
    result['refusal_by_kind']={kind:{'count':sum(r['kind']==kind for r in refusal),
        'false_accepts':sum(r['kind']==kind and r['false_accept'] for r in refusal)} for kind in sorted({r['kind'] for r in refusal})}
    return result


def calibrate(labels,predictions,protocol):
    trials=[]
    for score in protocol['refusal_calibration']['minimum_score_grid']:
        for margin in protocol['refusal_calibration']['minimum_margin_grid']:
            m=metrics(rows(labels,predictions,(score,margin)))
            errors=m['wrong_accepts']+m['false_accepts']
            trials.append(((m['accepted_correct']-2*errors,-errors,m['accepted_correct'],margin,score),(score,margin),m))
    _,threshold,m=max(trials,key=lambda row:row[0])
    return {'minimum_score':threshold[0],'minimum_margin':threshold[1],'development':m}


def main():
    p=argparse.ArgumentParser();p.add_argument('--frozen',type=Path,required=True)
    p.add_argument('--mode',choices=('lexical','select-dev','evaluate'),required=True)
    p.add_argument('--predictions',type=Path,nargs='*',default=[]);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--selection',type=Path);p.add_argument('--context',type=Path)
    a=p.parse_args();assert not a.output.exists(),a.output
    if a.mode=='lexical':lexical(a.frozen,a.output);return
    protocol=json.loads((a.frozen/'protocol.json').read_text())
    actions=json.loads((a.frozen/'actions.json').read_text());corpus=json.loads((a.frozen/'corpus.json').read_text())
    manifest=json.loads((a.frozen/'sha256.json').read_text())
    for file in ('protocol.json','actions.json','corpus.json','labels-dev.json'):assert digest(a.frozen/file)==manifest[file]
    labels_dev=json.loads((a.frozen/'labels-dev.json').read_text())
    predictions={};paths={}
    for path in a.predictions:
        value=json.loads(path.read_text());validate_predictions(value['predictions'],actions,corpus)
        predictions[value['model']]=value;paths[value['model']]=path
    if a.mode=='select-dev':
        choices={name:calibrate(labels_dev,value['predictions'],protocol) for name,value in predictions.items()}
        embeddings=[name for name in choices if name!='common-bm25']
        winner=max(embeddings,key=lambda name:(choices[name]['development']['mrr'],
            choices[name]['development']['recall_at_1']['count'],-choices[name]['development']['false_accepts']))
        save(a.output,{'selection_scope':'Development labels only; test labels not opened',
            'protocol_sha256':digest(a.frozen/'protocol.json'),'dev_labels_sha256':digest(a.frozen/'labels-dev.json'),
            'prediction_sha256':{name:digest(path) for name,path in paths.items()},'calibration':choices,
            'embedding_winner':winner,'test_used_for_selection':False});print(winner);return
    selection=json.loads(a.selection.read_text());assert selection['protocol_sha256']==digest(a.frozen/'protocol.json')
    assert selection['prediction_sha256']=={name:digest(path) for name,path in paths.items()}
    calibrations=selection['calibration']
    if a.context:
        context=json.loads(a.context.read_text());assert context['model']==selection['embedding_winner']
        validate_predictions(context['predictions'],actions,corpus)
        # Context's threshold is also calibrated on development before opening test.
        calibrations[context['model']+'-context']=calibrate(labels_dev,context['predictions'],protocol)
        predictions[context['model']+'-context']=context
    assert digest(a.frozen/'labels-test.json')==manifest['labels-test.json']
    labels_test=json.loads((a.frozen/'labels-test.json').read_text())
    assert not ({r['id'] for r in labels_dev}&{r['id'] for r in labels_test})
    results={}
    for name,value in predictions.items():
        c=calibrations[name];threshold=(c['minimum_score'],c['minimum_margin'])
        detail=rows(labels_dev+labels_test,value['predictions'],threshold);grouped={}
        for field in ('split','project','language','family'):
            grouped[field]={key:metrics([r for r in detail if r[field]==key]) for key in sorted({r[field] for r in detail})}
        results[name]={'calibration':c,'metrics':grouped,'rows':detail,'cost':value.get('cost'),
            'tokens':value.get('tokens',[]),'identity':value.get('identity'),'audit':value.get('audit')}
    save(a.output,{'selection_sha256':digest(a.selection),'results':results,
        'interpretation':'Retrieval-only source holdout. No full graph precision/IoU or semantic transfer claim.',
        'protocol_sha256':digest(a.frozen/'protocol.json')})
    print(json.dumps({name:{split:row['metrics']['split'][split] for split in ('development','test')} for name,row in results.items()},ensure_ascii=False))


if __name__=='__main__':main()
