"""Evaluate saved analyzer traces against separately frozen transport facts."""
import argparse
import hashlib
import json
from pathlib import Path
from semantic_holdout_checker33 import evaluate_case

V=Path(__file__).resolve().parents[1]


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runs',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--oracle',type=Path,default=V/'development/transport-oracle-frozen-v2')
    args=parser.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    frozen=args.oracle;manifest=read(frozen/'freeze.json')
    assert all(sha(frozen/name)==digest for name,digest in manifest['files'].items())
    result={}
    for project in ('employment','healthcare'):
        folder=args.runs/project
        if not folder.is_dir():continue
        package=V/'development/semantic-holdout-packages-v1'/project
        assert sha(package/'oracle.json')==manifest['inputs'][project]['oracle_sha256']
        expected=read(package/'oracle.json');witness=read(frozen/(project+'.json'));checks={}
        for run in read(folder/'runs.json'):
            path=folder/run['environment']/run['mode']/'report.json';report=read(path)
            for sid,case in expected['cases'].items():
                if case['environment']==run['environment'] and case['mode']==run['mode']:
                    checks[sid]=evaluate_case(case,report['scenarios'][sid],expected['initial_tables'],witness.get(sid))
        result[project]={'checks':checks,'report_files':{str(p.relative_to(args.runs)):sha(p) for p in folder.rglob('report.json')}}
    artifact={'source_runs':str(args.runs),'full_semantic_transfer_verified':False,'oracle_changed':False,
        'source_oracle_extension_prepared_after_observation':True,'transport_freeze_sha256':sha(frozen/'freeze.json'),'projects':result}
    (output/'checks.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n')
    counts={project:{mode:{'passed':sum(step['passed'] for sid,case in data['checks'].items() if expected_mode(sid)==mode for step in case['steps']),
                           'steps':sum(len(case['steps']) for sid,case in data['checks'].items() if expected_mode(sid)==mode)}
                     for mode in ('explicit-script','nl-en','nl-ru')} for project,data in result.items()}
    (output/'counts.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(counts))


def expected_mode(sid):
    return 'explicit-script' if sid.endswith('explicit-script') else 'nl-en' if sid.endswith(('-nl-en','-en')) else 'nl-ru'


if __name__=='__main__':main()
