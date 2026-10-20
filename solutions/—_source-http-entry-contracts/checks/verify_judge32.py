"""Extract and replay the exact immutable judge ZIP, then check its output."""
import gzip,hashlib,json,os,shutil,subprocess,sys,tempfile,time,zipfile
from pathlib import Path
V=Path(__file__).resolve().parents[1];ROOT=V.parents[1]
output=V/'benchmark/packaging/judge-replay';assert not output.exists();output.mkdir(parents=True)
archive=V/'solution.zip';before=hashlib.sha256(archive.read_bytes()).hexdigest();runs=[]
def run(label,command,cwd,env=None):
    started=time.perf_counter()
    with (output/(label+'.stdout.txt')).open('w') as out,(output/(label+'.stderr.txt')).open('w') as err:
        completed=subprocess.run(command,cwd=cwd,env=env,stdout=out,stderr=err,timeout=600)
    row={'label':label,'command':command,'cwd':str(cwd),'returncode':completed.returncode,'seconds':time.perf_counter()-started};runs.append(row)
    (output/'runs.json').write_text(json.dumps(runs,indent=2)+'\n');return completed.returncode
with tempfile.TemporaryDirectory(prefix='judge32-') as temporary:
    root=Path(temporary)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
        z.extractall(root)
    manifest=json.loads((root/'MANIFEST.json').read_text())
    assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==h for name,h in manifest['files'].items())
    env={**os.environ,'PYTHONPATH':str(root/'code'),'PYTHONDONTWRITEBYTECODE':'1'}
    assert run('code-tests',[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',str(root/'code/tests')],root,env)==0
    challenge=ROOT/'tt-challenge';command=[sys.executable,'-B',str(root/'code/offline_run.py'),
      '--source',str(challenge/'targets/trainticket'),'--skeleton',str(challenge/'skeleton/trainticket.json.gz'),
      '--context',str(challenge/'context'),'--scenarios',str(challenge/'scenarios'),
      '--output',str(output/'submission.json'),'--report',str(output/'report.json')]
    assert run('inference',command,root,env)==0
    assert (output/'submission.json').read_bytes()==(V/'submission.json').read_bytes()
    for label,flags in [('format',['--check',str(challenge/'skeleton/trainticket.json.gz')]),('S0',[str(challenge/'gold/S0.json')])]:
        assert run(label,[sys.executable,'-B',str(challenge/'platform/evaluate_golden.py'),*flags,str(output/'submission.json'),'--json'],root,env) in (0,3)
        result=json.loads((output/(label+'.stdout.txt')).read_text());assert not result['errors'] and not result['warnings']
    raw=output/'report.json'
    with raw.open('rb') as src,gzip.open(output/'report.json.gz','wb') as dst:shutil.copyfileobj(src,dst)
    raw.unlink()
assert hashlib.sha256(archive.read_bytes()).hexdigest()==before
result={'passed':True,'judge_zip_sha256':before,'submission_sha256':hashlib.sha256((output/'submission.json').read_bytes()).hexdigest(),
    'code_and_all_file_hashes_verified':True,'exact_inference_replay':True,'targets_started':False}
(output/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
