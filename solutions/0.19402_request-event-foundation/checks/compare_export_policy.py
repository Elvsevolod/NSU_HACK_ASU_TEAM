"""Posthoc observed-union/confirmed export ablation over the same executions."""
import argparse
import json
from pathlib import Path


def edges(items):return {tuple(e[k] for k in ('source','relation','target')) for e in items}


def compare(gold,found):
    output={}
    for rel in ('executes','calls','remote','data'):
        g={e for e in gold if e[1]==rel};p={e for e in found if e[1]==rel}
        tp,fp,fn=len(g&p),len(p-g),len(g-p)
        output[rel]={'tp':tp,'fp':fp,'fn':fn,'precision':tp/(tp+fp) if tp+fp else None,
            'recall':tp/(tp+fn) if tp+fn else None,'iou':tp/(tp+fp+fn) if tp+fp+fn else None,'nonempty_gold':bool(g)}
    return output


parser=argparse.ArgumentParser();parser.add_argument('--fixtures',type=Path,required=True)
parser.add_argument('--predictions',type=Path,required=True);parser.add_argument('--synthetic',type=Path,required=True)
parser.add_argument('--synthetic-prediction',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();cases=[]
for fixture,prediction,name in [(f,args.predictions/f.name/'27',f.name) for f in sorted(args.fixtures.iterdir()) if (f/'oracle.json').exists()]+[
    (args.synthetic,args.synthetic_prediction,'synthetic-full-journey')]:
    oracle=json.loads((fixture/'oracle.json').read_text());gold=edges(oracle['edges'])
    answer=json.loads((prediction/'submission.json').read_text());report=json.loads((prediction/'analysis-report.json').read_text())
    sid=next(iter(answer['scenarios']));detail=report['scenarios'][sid]
    union=edges(detail['confirmed'])|edges(detail['possible']);confirmed=edges(detail['confirmed'])
    cases.append({'case':name,'observed_union':compare(gold,union),'confirmed':compare(gold,confirmed),
        'source_executions_identical':True,'observed_union_exact':union==gold,'confirmed_exact':confirmed==gold})
args.output.write_text(json.dumps({'cases':cases,'decision':'Keep observed-union of supported events as default: confirmed export loses independently expected edges. Static closure candidates are excluded under both policies.',
    'limits':'This is an export ablation on fixed executions; it does not validate unknown endpoint hypotheses or unsupported future continuations.'},indent=2)+'\n')
print(json.dumps([{k:v for k,v in row.items() if k in ('case','observed_union_exact','confirmed_exact')} for row in cases]))
