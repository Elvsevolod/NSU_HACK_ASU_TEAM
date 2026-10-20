"""Preregistered new-app ranking extension: fixed old model and thresholds."""
import argparse
import hashlib
import json
from pathlib import Path
from evaluate_code_models import lexical,validate_predictions,rows,metrics

V=Path(__file__).resolve().parents[1]
F=V/'development/real-retrieval-frozen-v1'


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    assert not path.exists();path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=('prepare','evaluate'),required=True)
    parser.add_argument('--dense',type=Path)
    parser.add_argument('--output',type=Path,default=V/'benchmark/real-retrieval-evaluation.json');args=parser.parse_args()
    prereg=read(V/'development/real-retrieval-preregistration.json')
    assert all(sha(V/name)==digest for name,digest in prereg['files'].items())
    selection=V/'benchmark/real-retrieval-fixed-selection.json'
    lexical_path=V/'benchmark/real-retrieval-common-bm25.json'
    if args.mode=='prepare':
        old=read(V/'benchmark/model-selection-dev.json');assert old['embedding_winner']=='coderank'
        save(selection,{'model':'coderank','model_reselected':False,'thresholds_recalibrated':False,
            'old_selection_sha256':sha(V/'benchmark/model-selection-dev.json'),
            'calibration':{key:old['calibration'][key] for key in ('common-bm25','coderank')},
            'new_test_opened':False,'new_semantic_apps_previously_observed':True,
            'scope':'Untuned new retrieval queries; application debugging is development and no full semantic transfer claim is made'})
        lexical(F,lexical_path);print('Fixed previous selection; common lexical predictions saved without test labels');return
    fixed=read(selection);assert fixed['old_selection_sha256']==sha(V/'benchmark/model-selection-dev.json')
    assert args.dense is not None
    corpus=read(F/'corpus.json');actions=read(F/'actions.json');manifest=read(F/'sha256.json')
    assert all(sha(F/name)==digest for name,digest in manifest.items())
    labels=read(F/'labels-dev.json')+read(F/'labels-test.json');results={}
    for name,path in (('common-bm25',lexical_path),('coderank',args.dense)):
        value=read(path);validate_predictions(value['predictions'],actions,corpus)
        calibration=fixed['calibration'][name]
        detail=rows(labels,value['predictions'],(calibration['minimum_score'],calibration['minimum_margin']))
        groups={field:{key:metrics([row for row in detail if row[field]==key]) for key in sorted({row[field] for row in detail})}
                for field in ('split','project','language','family','kind')}
        results[name]={'calibration':calibration,'metrics':groups,'rows':detail,'cost':value['cost'],
            'audit':value.get('audit'),'prediction_sha256':sha(path)}
    paired=[{'id':a['id'],'lexical_rank':a['rank'],'dense_rank':b['rank'],'lexical_accepted':a['accepted'],'dense_accepted':b['accepted']}
        for a,b in zip(results['common-bm25']['rows'],results['coderank']['rows']) if a['split']=='test' and (a['rank']!=b['rank'] or a['accepted']!=b['accepted'])]
    output={'results':results,'paired_test_differences':paired,'fixed_selection_sha256':sha(selection),
        'full_semantic_transfer_verified':False,'model_reselected':False,'thresholds_recalibrated':False,
        'interpretation':'Ranking extension only; no automatic model adoption. New query families become development after this measurement.'}
    save(args.output,output)
    print(json.dumps({name:value['metrics']['split']['test'] for name,value in results.items()}))


if __name__=='__main__':main()
