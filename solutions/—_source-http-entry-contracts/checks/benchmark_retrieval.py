"""Evaluate frozen labels outside inference, preserving paired retrieval errors."""
import argparse,hashlib,json,os,subprocess,sys,time
from collections import defaultdict
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def metrics(rows):
    answers=[r for r in rows if r['kind']=='answer'];refusals=[r for r in rows if r['requires_refusal']]
    result={'queries':len(rows),'answer_denominator':len(answers),'refusal_denominator':len(refusals),
        'coverage':sum(bool(r['accepted_entries']) for r in rows)/len(rows) if rows else None}
    for k in (1,3,6):result['recall@'+str(k)]=sum(r['rank'] is not None and r['rank']<=k for r in answers)/len(answers) if answers else None
    result['top1']=result['recall@1'];result['MRR']=sum(1/r['rank'] if r['rank'] else 0 for r in answers)/len(answers) if answers else None
    result['false_accept']=sum(bool(r['accepted_entries']) for r in refusals)
    result['false_reject']=sum(not r['accepted_entries'] for r in answers)
    result['accepted_wrong_handler']=sum(bool(r['accepted_entries']) and not set(r['accepted_entries'])<=set(r['acceptable_entries']) for r in answers)
    result['ndcg']=None;result['ndcg_reason']='binary acceptable-set labels, no graded relevance'
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--frozen',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--semantic-code',type=Path);args=p.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
    frozen=args.frozen.resolve();manifest=json.loads((frozen/'sha256.json').read_text())
    assert all(hashlib.sha256((frozen/file).read_bytes()).hexdigest()==digest for file,digest in manifest.items())
    labels=json.loads((frozen/'queries.json').read_text())
    actions=[{k:q[k] for k in ('id','project','action','language')} for q in labels]
    (args.output/'actions.json').write_text(json.dumps(actions,ensure_ascii=False,indent=2)+'\n')
    projects={'piggymetrics':str(V/'validation_inputs/piggymetrics'),'cart':str(V/'validation_inputs/shopping-cart'),
      'petclinic':str(V/'validation_inputs/legacy-real/petclinic-customers'),'unicode':str(frozen/'unicode-source'),
      'trainticket':str(V.parents[1]/'tt-challenge')}
    (args.output/'projects.json').write_text(json.dumps(projects,ensure_ascii=False,indent=2)+'\n')
    output={};runs=[]
    for profile in ('A','B'):
        code=args.semantic_code if args.semantic_code else V/'development/stages'/('B00-parent31' if profile=='A' else 'B-R07-lexical')/'code'
        command=[sys.executable,'-B',str(V/'checks/retrieval_worker.py'),'--code',str(code),'--profile',profile,
          '--actions',str((args.output/'actions.json').resolve()),'--projects',str((args.output/'projects.json').resolve()),'--output',str((args.output/(profile+'.json')).resolve())]
        start=time.perf_counter()
        with (args.output/(profile+'.stdout.txt')).open('w') as out,(args.output/(profile+'.stderr.txt')).open('w') as err:
            completed=subprocess.run(command,cwd=V,stdout=out,stderr=err,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=180)
        runs.append({'profile':profile,'code':str(code),'command':command,'returncode':completed.returncode,'wall_seconds':time.perf_counter()-start})
        (args.output/'runs.json').write_text(json.dumps(runs,indent=2)+'\n');assert completed.returncode==0
        prediction=json.loads((args.output/(profile+'.json')).read_text());byid={r['id']:r for r in prediction['predictions']}
        rows=[]
        for label in labels:
            row={**label,**byid[label['id']]};entries=[r['entry'] for r in row['ranking']]
            row['rank']=next((i for i,entry in enumerate(entries,1) if entry in label['acceptable_entries']),None)
            rows.append(row)
        groups={}
        for dimension in ('project','language','family','kind'):
            grouped=defaultdict(list)
            for row in rows:grouped[row[dimension]].append(row)
            groups[dimension]={k:metrics(v) for k,v in grouped.items()}
        output[profile]={'metrics':metrics([r for r in rows if r['language']!='explicit']),
            'groups':groups,'paired_rows':rows,'cost':prediction['cost'],'peak_rss_bytes':prediction['peak_rss_bytes'],'audit':prediction['audit']}
    a,b=output['A']['metrics'],output['B']['metrics']
    decision='accept_on_development' if b['MRR']>a['MRR'] and b['false_accept']<=a['false_accept'] and b['accepted_wrong_handler']<=a['accepted_wrong_handler'] and b['false_reject']<=a['false_reject'] else 'experiment_rejected'
    result={'profiles':output,'decision':decision,'decision_scope':'development retrieval only; downstream and real holdout are separate',
      'real_transfer':'not_run','test_queries':0,'input_sha256':hashlib.sha256((frozen/'sha256.json').read_bytes()).hexdigest(),
      'paired_errors':[{'id':a['id'],'A_rank':a['rank'],'B_rank':b['rank'],'A_accepted':a['accepted_entries'],'B_accepted':b['accepted_entries']}
        for a,b in zip(output['A']['paired_rows'],output['B']['paired_rows']) if a['rank']!=b['rank'] or a['accepted_entries']!=b['accepted_entries']]}
    (args.output/'evaluation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'decision':decision,'A':a,'B':b,'real_transfer':'not_run'},ensure_ascii=False))


if __name__=='__main__':main()
