"""Separate source-oracle checker for the paired E27 development extension."""
import argparse
import hashlib
import json
from pathlib import Path
from semantic_holdout_checker33 import evaluate_case

V=Path(__file__).resolve().parents[1]
PROFILES={'baseline':'semantic-holdout-e27-baseline-v1','lexical':'semantic-holdout-e27-lexical-v1',
    'coderank-same':'semantic-model-e27-same','coderank-expanded':'semantic-model-e27-expanded'}


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);result={}
    measured=read(V/'development/stages/E27-readiness-witnesses/code-sha256.json')
    measured={k:v for k,v in measured.items() if not k.startswith('tests/')}
    for label,folder in PROFILES.items():
        rows=[];explicit={};captures=[]
        for project in ('employment','healthcare'):
            package=V/'development/semantic-holdout-packages-v1'/project
            oracle=read(package/'oracle.json');wire=read(V/'development/transport-oracle-frozen-v2'/(project+'.json'))
            base=V/'benchmark'/folder/project
            for run in read(base/'runs.json'):
                assert run['returncode']==0
                report=read(base/run['environment']/run['mode']/'report.json')
                if run['mode']=='explicit-script':explicit[project+'/'+run['environment']]=sha(base/run['environment']/run['mode']/'submission.json')
                for sid,case in oracle['cases'].items():
                    if (case['mode'],case['environment'])!=(run['mode'],run['environment']):continue
                    actual=report['scenarios'][sid]
                    semantic=evaluate_case(case,actual,oracle['initial_tables'])
                    strict=evaluate_case(case,actual,oracle['initial_tables'],wire.get(sid))
                    for wanted,observed,plain,strong in zip(case['steps'],actual['steps'],semantic['steps'],strict['steps']):
                        rows.append({'project':project,'environment':run['environment'],'mode':run['mode'],'scenario':sid,
                            'step':observed['n'],'action':observed['action'],'refusal_kind':wanted.get('refusal'),
                            'false_accept':bool(wanted.get('refusal') and observed['alternatives']),
                            'semantic_passed':plain['passed'],'strict_passed':strong['passed'],
                            'checks':strong['checks'],'relations':strong['relations'],
                            'selected_entries':sorted({a['entry'] for a in observed['alternatives']})})
        names=([f'semantic-holdout-e27-{label}-{project}-command' for project in ('employment','healthcare')]
            if label in ('baseline','lexical') else ['semantic-model-e27-'+('same' if label.endswith('same') else 'expanded')+'-command'])
        for name in names:
            capture=read(V/'benchmark'/name/'run.json')
            assert {k:v for k,v in capture['code_sha256'].items() if not k.startswith('tests/')}==measured
            captures.append({'path':str(Path('benchmark')/name/'run.json'),'returncode':capture['returncode'],'seconds':capture['seconds']})
        groups={}
        for project in ('employment','healthcare'):
            groups[project]={}
            for mode in ('explicit-script','nl-en','nl-ru'):
                selected=[row for row in rows if row['project']==project and row['mode']==mode]
                names=sorted({key for row in selected for key in row['checks']})
                component={key:{'passed':sum(row['checks'][key] for row in selected if key in row['checks']),
                    'denominator':sum(key in row['checks'] for row in selected)} for key in names}
                refusal={kind:{'false_accepts':sum(row['false_accept'] for row in selected if row['refusal_kind']==kind),
                    'denominator':sum(row['refusal_kind']==kind for row in selected)} for kind in ('ambiguous','no-handler')}
                relations={}
                for kind in ('executes','calls','remote','data'):
                    counts={key:sum(row['relations'][kind][key] for row in selected) for key in ('tp','fp','fn')}
                    denominator=sum(counts.values());relations[kind]={**counts,'iou':counts['tp']/denominator if denominator else 1.0}
                groups[project][mode]={'steps':len(selected),'semantic_passed':sum(row['semantic_passed'] for row in selected),
                    'strict_passed':sum(row['strict_passed'] for row in selected),'components':component,'refusals':refusal,'relations':relations}
        experiment=read(V/'benchmark'/folder/'experiment.json') if label.startswith('coderank') else None
        if experiment:
            assert experiment['explicit_bypass_preserved'] and not any(experiment['audit'].values())
        result[label]={'groups':groups,'rows':rows,'explicit_answer_hashes':explicit,'captures':captures,'experiment':experiment}
    baseline=result['baseline']['explicit_answer_hashes']
    assert all(value['explicit_answer_hashes']==baseline for value in result.values()),'Model changed an explicit answer'
    paired=[]
    for label in ('lexical','coderank-same','coderank-expanded'):
        for a,b in zip(result['baseline']['rows'],result[label]['rows']):
            assert (a['project'],a['scenario'],a['step'])==(b['project'],b['scenario'],b['step'])
            if a['checks']!=b['checks'] or a['selected_entries']!=b['selected_entries']:
                paired.append({'profile':label,'project':a['project'],'scenario':a['scenario'],'step':a['step'],
                    'baseline_entries':a['selected_entries'],'profile_entries':b['selected_entries'],
                    'changed_checks':{key:[a['checks'].get(key),b['checks'].get(key)] for key in set(a['checks'])|set(b['checks']) if a['checks'].get(key)!=b['checks'].get(key)}})
    output={'stage':'E27-readiness-witnesses','profiles':result,'paired_differences':paired,
        'explicit_answers_unchanged':True,'model_reselected':False,'thresholds_recalibrated':False,
        'default_adoption':'experiment_rejected; full downstream benefit still unproved',
        'new_untouched_transfer_claim':False,'full_semantic_transfer_verified':False,
        'limits':'Applications were already observed. Strict NL wire and exact history-path obligations remain separate from graph/value/state success; no unknown headers or origins were invented.'}
    (args.output/'review.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({profile:{p:{mode:[x['semantic_passed'],x['strict_passed'],x['steps']] for mode,x in modes.items()} for p,modes in value['groups'].items()} for profile,value in result.items()}))


if __name__=='__main__':main()
