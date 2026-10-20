"""Checker-side C/B comparison from label-blind worker outputs."""
import argparse,json
from collections import defaultdict
from pathlib import Path
from benchmark_retrieval import metrics


def main():
    p=argparse.ArgumentParser();p.add_argument('--frozen',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--prediction',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();assert not args.output.exists()
    labels=json.loads((args.frozen/'queries.json').read_text());pred=json.loads(args.prediction.read_text());byid={r['id']:r for r in pred['predictions']}
    rows=[]
    for q in labels:
        row={**q,**byid[q['id']]};row['rank']=next((i for i,r in enumerate(row['ranking'],1) if r['entry'] in q['acceptable_entries']),None);rows.append(row)
    base=json.loads(args.baseline.read_text())['profiles']['B'];a=base['metrics'];b=metrics([r for r in rows if r['language']!='explicit'])
    decision='accept_on_development' if b['MRR']>a['MRR'] and b['false_accept']<=a['false_accept'] and b['false_reject']<=a['false_reject'] and b['accepted_wrong_handler']<=a['accepted_wrong_handler'] else 'experiment_rejected'
    groups={}
    for field in ('project','language','family','kind'):
        collected=defaultdict(list)
        for row in rows:collected[row[field]].append(row)
        groups[field]={key:metrics(items) for key,items in collected.items()}
    result={'C':b,'B':a,'decision':decision,'groups':groups,'paired_rows':rows,
        'model_cost':{k:pred[k] for k in ('cost','peak_rss_bytes','model_calls','model_loads','additional_warm_forward_samples','mps_allocated_bytes','mps_driver_allocated_bytes','environment','candidate_policy','audit')},
        'real_holdout':'not_run','test_queries':0,'scope':'development retrieval and grounding, downstream evaluated separately',
        'paired_errors':[{'id':c['id'],'B_rank':old['rank'],'C_rank':c['rank'],'B_accepted':old['accepted_entries'],'C_accepted':c['accepted_entries']}
            for old,c in zip(base['paired_rows'],rows) if old['rank']!=c['rank'] or old['accepted_entries']!=c['accepted_entries']]}
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'decision':decision,'B':a,'C':b}))


if __name__=='__main__':main()
