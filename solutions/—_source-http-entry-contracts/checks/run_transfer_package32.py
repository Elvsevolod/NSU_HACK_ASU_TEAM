"""Generic ready-package harness; inference and oracle evaluation are separate."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path


def strict_subset(wanted,actual):
    if isinstance(wanted,dict):return isinstance(actual,dict) and all(k in actual and strict_subset(v,actual[k]) for k,v in wanted.items())
    if isinstance(wanted,list):return isinstance(actual,list) and len(wanted)==len(actual) and all(strict_subset(a,b) for a,b in zip(wanted,actual))
    return type(wanted) is type(actual) and wanted==actual


def edges(rows):return {(e['source'],e['relation'],e['target']) for e in rows}


def main():
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--code',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--retrieval',choices=('baseline','lexical','offline-dense'),default='baseline')
    p.add_argument('--model-snapshot',type=Path);p.add_argument('--python',type=Path);p.add_argument('--validate-only',action='store_true');args=p.parse_args()
    manifest=json.loads(args.package.read_text());root=args.package.resolve().parent
    required=('project','source','skeleton','context','explicit_scenarios','nl_scenarios','oracle','files','origin','oracle_review')
    assert all(k in manifest for k in required),'incomplete ready package'
    assert manifest['oracle_review']['inference_predictions_used'] is False,'oracle must be independent of predictions'
    assert manifest['origin']['revision'] and manifest['oracle_review']['source_evidence']
    for file,digest in manifest['files'].items():
        with (root/file).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==digest,file
    assert all((root/manifest[k]).exists() for k in ('source','skeleton','context','explicit_scenarios','nl_scenarios','oracle'))
    if args.validate_only:print(json.dumps({'validated':True,'inference_run':False}));return
    assert not args.output.exists();args.output.mkdir(parents=True);runs=[]
    for mode in ('explicit','nl'):
        target=args.output/mode;target.mkdir()
        command=[str(args.python or sys.executable),'-B',str(args.code.resolve()/'offline_run.py')]
        for flag,key in [('source','source'),('skeleton','skeleton'),('context','context'),('scenarios',mode+'_scenarios')]:command+=['--'+flag,str((root/manifest[key]).resolve())]
        command+=['--output',str((target/'submission.json').resolve()),'--report',str((target/'report.json').resolve()),'--path-limit','4']
        if args.retrieval!='baseline':command+=['--retrieval',args.retrieval]
        if args.model_snapshot:command+=['--model-snapshot',str(args.model_snapshot.resolve())]
        started=time.perf_counter()
        with (target/'stdout.txt').open('w') as out,(target/'stderr.txt').open('w') as err:
            result=subprocess.run(command,stdout=out,stderr=err,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=600)
        row={'mode':mode,'command':command,'returncode':result.returncode,'seconds':time.perf_counter()-started};runs.append(row)
        (args.output/'runs.json').write_text(json.dumps(runs,indent=2)+'\n');assert result.returncode==0
    # Only the checker process below reads the independent expected answer.
    oracle=json.loads((root/manifest['oracle']).read_text());checks=[]
    for run in runs:
        mode=run['mode'];actual=json.loads((args.output/mode/'submission.json').read_text())['scenarios']
        report=json.loads((args.output/mode/'report.json').read_text())['scenarios']
        for sid,wanted in oracle[mode].items():
            observed=edges(actual[sid]['edges']);gold=edges(wanted['edges']);complete=wanted.get('complete') is True
            conditions=[strict_subset(c,report[sid]['steps'][int(n)-1]) for n,c in wanted.get('step_constraints',{}).items()]
            checks.append({'mode':mode,'scenario':sid,'complete_oracle':complete,'required_coverage':len(gold&observed)/len(gold) if gold else None,
                'iou':len(gold&observed)/len(gold|observed) if complete and gold|observed else None,
                'passed':(observed==gold if complete else gold<=observed) and all(conditions),'step_constraints':conditions})
    (args.output/'checks.json').write_text(json.dumps({'checks':checks,'passed':all(x['passed'] for x in checks),'targets_started':False},indent=2)+'\n')
    raise SystemExit(0 if all(x['passed'] for x in checks) else 1)


if __name__=='__main__':main()
