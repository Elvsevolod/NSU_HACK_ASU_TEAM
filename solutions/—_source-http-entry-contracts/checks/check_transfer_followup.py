"""Compare paired transfer runs using independent, explicitly partial oracles."""
import argparse
import json
from pathlib import Path

from check_source_state import evaluate
from transfer_semantics import inspect_semantics, read, save

V=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--before',type=Path,required=True)
    parser.add_argument('--after',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--packages',type=Path,default=V/'development/transfer')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    summary=[]
    for project in ('organization','library'):
        row={'project':project,'partial_oracle':True,'full_precision_or_iou':None}
        for stage,root in (('before',args.before),('after',args.after)):
            folder=root/(project+'-results')
            if not folder.is_dir():folder=root/project
            semantic=inspect_semantics(project,folder,args.packages)
            states={mode:evaluate(project,read(folder/mode/'report.json')) for mode in ('explicit','nl')}
            save(args.output/(project+'-'+stage+'-semantics.json'),semantic)
            save(args.output/(project+'-'+stage+'-states.json'),states)
            row[stage]={
                'steps':{mode:{'denominator':len(checks:=[c for c in semantic['checks'] if c['mode']==mode]),
                    'passed':sum(c['passed'] for c in checks),
                    **{kind:sum(c['checks'][kind] for c in checks) for kind in ('handler','wire','completion','required_edges','exploration_complete')}}
                    for mode in ('explicit','nl')},
                'states':{mode:{'denominator':len(state['checks']),'passed':sum(c['passed'] for c in state['checks'])} for mode,state in states.items()},
            }
        summary.append(row)
    result={'projects':summary,'all_full_transfer_verified':False,
        'classification':'development/regression after previous predictions; unchanged partial source oracle',
        'semantics_of_counts':'Each count is a required-fact/completion check, not full edge accuracy.',
        'model_thresholds_changed':False,'targets_started':False}
    save(args.output/'comparison.json',result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
