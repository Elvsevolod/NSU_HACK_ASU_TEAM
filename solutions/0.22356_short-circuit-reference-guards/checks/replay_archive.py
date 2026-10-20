"""Run exact packaged Python analyzer; failures/timeouts always leave replay.json."""
import argparse,hashlib,json,os,sys,tempfile,time,zipfile
from pathlib import Path
from archive_support import verified_manifest,execute


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser()
    for name in ('archive','source','skeleton','context','scenarios','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--timeout',type=float,default=600);parser.add_argument('--tests-timeout',type=float,default=120)
    args=parser.parse_args();args.output=args.output.resolve();assert not args.output.exists();args.output.mkdir(parents=True)
    started=time.perf_counter();result={'passed':False,'target_applications_started':False,'runs':{},'temporary_directory_removed':False}
    directory=None
    try:
        result['archive_sha256']=sha(args.archive)
        with tempfile.TemporaryDirectory(prefix='analyzer31-replay-') as directory:
            root=Path(directory)
            with zipfile.ZipFile(args.archive) as z:
                manifest=verified_manifest(z,'benchmark/package-manifest.json');z.extractall(root)
            result.update(all_package_hashes_match=True,package_files=len(manifest)+1)
            command=[sys.executable,'-B',str(root/'code/offline_run.py')]
            for name in ('source','skeleton','context','scenarios'):command+=['--'+name,str(getattr(args,name).resolve())]
            command+=['--output',str(args.output/'submission.json'),'--report',str(args.output/'analysis-report.json')]
            environment={**os.environ,'PYTHONPATH':str(root/'code'),'PYTHONDONTWRITEBYTECODE':'1'}
            result['runs']['analyzer']=execute(command,root,environment,args.output,'analyzer',args.timeout)
            if result['runs']['analyzer']['returncode']==0:
                result['submission_sha256']=sha(args.output/'submission.json')
                result['all_eight_answers_match']=result['submission_sha256']==sha(root/'submission.json')
                result['offline_audit']=json.loads((args.output/'analysis-report-offline-audit.json').read_text())
                result['runs']['tests']=execute([sys.executable,'-B','-m','pytest','code/tests','-q','-p','no:cacheprovider'],root,environment,args.output,'tests',args.tests_timeout)
                result['passed']=result['all_eight_answers_match'] and result['runs']['tests']['returncode']==0 and not any(result['offline_audit'][k] for k in ('blocked_network','blocked_processes','blocked_reference_reads'))
            else:result['tests_not_run']='Packaged analyzer failed or timed out; partial outputs retained.'
    except Exception as error:
        result['failure']={'type':type(error).__name__,'message':str(error)}
    finally:
        result.update(temporary_directory_removed=directory is None or not Path(directory).exists(),elapsed_seconds_including_tests=time.perf_counter()-started)
        (args.output/'replay.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result));raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
