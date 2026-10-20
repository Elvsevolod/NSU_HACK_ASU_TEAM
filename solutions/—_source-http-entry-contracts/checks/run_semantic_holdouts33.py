"""Run frozen inputs in child processes; read oracle only in this checker."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from semantic_holdout_checker33 import evaluate_case

V=Path(__file__).resolve().parents[1]


def read(path):return json.loads(path.read_text())


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',choices=('healthcare','employment'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--retrieval',choices=('baseline','lexical'),default='baseline')
    args=parser.parse_args()
    package=V/'development/semantic-holdout-packages-v1'/args.project
    manifest=read(package/'package.json')
    assert all(sha(package/name)==digest for name,digest in manifest['files'].items())
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    runs=[]
    for environment in ('normal','remote-error'):
        if not (package/environment).is_dir():continue
        for mode in ('explicit-script','nl-en','nl-ru'):
            target=output/environment/mode;target.mkdir(parents=True)
            driver=V/'checks/run_scripted_http33.py' if mode=='explicit-script' else V/'code/offline_run.py'
            skeleton=package/('remote-error-skeleton.json' if environment=='remote-error' else 'skeleton.json')
            command=[sys.executable,'-B',str(driver),'--source',str(package/'source'),'--skeleton',str(skeleton),
                     '--context',str(package/'initial.sql'),'--scenarios',str(package/environment/mode),
                     '--output',str(target/'submission.json'),'--report',str(target/'report.json'),
                     '--path-limit','4','--retrieval',args.retrieval]
            before=time.perf_counter()
            with (target/'stdout.txt').open('w') as out,(target/'stderr.txt').open('w') as err:
                result=subprocess.run(command,cwd=V,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(V/'code')},
                                      stdout=out,stderr=err,timeout=600)
            row={'environment':environment,'mode':mode,'command':command,'returncode':result.returncode,
                 'seconds':time.perf_counter()-before};runs.append(row)
            (output/'runs.json').write_text(json.dumps(runs,ensure_ascii=False,indent=2)+'\n')
    assert all(r['returncode']==0 for r in runs),'Inference process failed; inspect separate stderr'
    oracle=read(package/'oracle.json');checks={}
    for run in runs:
        report=read(output/run['environment']/run['mode']/'report.json')
        for sid,case in oracle['cases'].items():
            if case['environment']==run['environment'] and case['mode']==run['mode']:
                checks[sid]=evaluate_case(case,report['scenarios'][sid],oracle['initial_tables'])
    result={'project':args.project,'retrieval':args.retrieval,'runtime_succeeded':True,
        'passed':all(c['passed'] for c in checks.values()),'full_semantic_transfer_verified':False,
        'new_application_evaluation_performed':True,'targets_started':False,'path_limit':4,
        'oracle_sha256':sha(package/'oracle.json'),'package_sha256':sha(package/'package.json'),
        'checks':checks,'runs':runs,
        'limits':'Full source E/C/R/D and persistent-row expectations; error-value, wire-origin and native-kind checks are not yet a full framework oracle. These now observed applications are development for later tuning.'}
    (output/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'project':args.project,'runtime_succeeded':True,'scenarios':len(checks),
                      'steps':sum(len(c['steps']) for c in checks.values()),
                      'steps_passed':sum(s['passed'] for c in checks.values() for s in c['steps']),
                      'full_semantic_transfer_verified':False}))
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
