"""Package one measured stage without replacing any frozen archive."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from archive_support import verified_manifest

V=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tag',default='e4')
    parser.add_argument('--stage',default='E4-feign-contracts')
    parser.add_argument('--full-gate',default='feign-boundary-full-02')
    parser.add_argument('--checker-gate',default='feign-boundary-checker')
    parser.add_argument('--integration',default='feign-boundary-integration-02')
    args=parser.parse_args()
    assert re.fullmatch(r'e[0-9]+',args.tag)
    assert all(Path(value).name==value for value in (args.stage,args.full_gate,args.checker_gate,args.integration))
    stage=V/'benchmark/stages'/args.stage
    run=json.loads((stage/'run.json').read_text());assert run['returncode']==0 and not run['timed_out']
    code={p.relative_to(V/'code').as_posix():sha(p) for p in sorted((V/'code').rglob('*')) if p.is_file()}
    assert code==run['code_sha256']
    gate=V/'benchmark'/args.full_gate;test_run=json.loads((gate/'run.json').read_text())
    assert test_run['returncode']==0 and test_run['code_sha256']==code
    tests=int(re.search(r'(\d+) passed', (gate/'stdout.txt').read_text())[1])
    check_gate=V/'benchmark'/args.checker_gate
    assert json.loads((check_gate/'run.json').read_text())['returncode']==0
    check_count=int(re.search(r'(\d+) passed',(check_gate/'stdout.txt').read_text())[1])
    integration=json.loads((V/'benchmark'/args.integration/'results.json').read_text());assert integration['passed']
    source=json.loads((V/'benchmark'/(args.integration+'-command')/'run.json').read_text())
    assert all(digest==source['code_sha256'][name] for name,digest in code.items() if not name.startswith('tests/'))
    assert sha(stage/'submission.json')==sha(V/'submission.json'),'Preserved answer must equal the measured stage answer'
    evaluation=json.loads((stage/'evaluation.json').read_text());fmt=json.loads((stage/'format-check.json').read_text())
    assert not fmt['errors'] and not fmt['warnings']
    metadata={'variant':33,'parent':32,'source_stage':args.stage,'status':'local candidate, not submitted',
        'code_sha256':code,'submission_sha256':sha(V/'submission.json'),'s0':evaluation['score'],
        'code_tests':tests,'checker_tests':check_count,'integration_runs':len(integration['runs']),
        'all_queues_verified':False,'default_retrieval':'baseline','model_weights_required':False,'source_applications_started':False,
        'preserved_E2_archive':'solution.zip','answer_unchanged_from_E2':True}
    meta=V/'benchmark'/(args.tag+'-candidate-metadata.json');assert not meta.exists();meta.write_text(json.dumps(metadata,indent=2)+'\n')
    files={'code/'+name:V/'code'/name for name in code}
    files.update({'README.md':V/'JUDGE_README.md','requirements.txt':V/'requirements.txt','submission.json':V/'submission.json',
        'benchmark/candidate-metadata.json':meta,'benchmark/evaluation.json':stage/'evaluation.json','benchmark/format-check.json':stage/'format-check.json'})
    manifest={name:sha(file) for name,file in sorted(files.items())}
    file=V/'benchmark'/(args.tag+'-package-manifest.json');assert not file.exists();file.write_text(json.dumps(manifest,indent=2)+'\n')
    archive=V/('solution-'+args.tag+'.zip');assert not archive.exists()
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,file in sorted(files.items()):assert not file.is_symlink();z.write(file,name)
        z.writestr('benchmark/package-manifest.json',json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(archive) as z:verified_manifest(z,'benchmark/package-manifest.json');assert z.testzip() is None
    receipt={'passed':True,'archive_sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(files)+1,
        'code_matches_measured_stage':True,'submission_sha256':sha(V/'submission.json'),'uploaded':False,'runtime_replay':'pending'}
    (V/'benchmark'/(args.tag+'-candidate-package-check.json')).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


if __name__=='__main__':main()
