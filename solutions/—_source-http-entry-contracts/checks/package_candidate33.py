"""Freeze the measured model-free candidate; no site upload."""
import hashlib,json,shutil,zipfile
from pathlib import Path
from archive_support import verified_manifest
V=Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    stage=V/'benchmark/stages/E2-source-contracts';record=json.loads((stage/'run.json').read_text())
    assert record['returncode']==0 and not record['timed_out']
    assert all(sha(V/'code'/name)==value for name,value in record['code_sha256'].items())
    assert json.loads((V/'benchmark/followup-integration/results.json').read_text())['passed']
    assert json.loads((V/'benchmark/full-code-tests-06/run.json').read_text())['returncode']==0
    assert json.loads((V/'benchmark/all-checker-tests-02/run.json').read_text())['returncode']==0
    target=V/'submission.json';assert not target.exists();shutil.copyfile(stage/'submission.json',target)
    evaluation=json.loads((stage/'evaluation.json').read_text());format_check=json.loads((stage/'format-check.json').read_text())
    assert not format_check['errors'] and not format_check['warnings']
    metadata={'variant':33,'parent':32,'status':'local experimental candidate, not submitted','all_queues_verified':False,
        'submission_sha256':sha(target),'code_sha256':record['code_sha256'],'s0':evaluation['score'],
        'source_stage':'E2-source-contracts','code_tests':2065,'checker_tests':76,'integration_runs':17,
        'default_retrieval':'baseline','model_weights_required':False,'source_applications_started':False}
    meta=V/'benchmark/candidate-metadata.json';meta.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    files={name:V/'code'/name.removeprefix('code/') for name in ('code/'+p for p in record['code_sha256'])}
    files.update({'README.md':V/'JUDGE_README.md','requirements.txt':V/'requirements.txt','submission.json':target,
        'benchmark/candidate-metadata.json':meta,'benchmark/evaluation.json':stage/'evaluation.json','benchmark/format-check.json':stage/'format-check.json'})
    manifest={name:sha(path) for name,path in sorted(files.items())}
    manifest_file=V/'benchmark/package-manifest.json';assert not manifest_file.exists();manifest_file.write_text(json.dumps(manifest,indent=2)+'\n')
    archive=V/'solution.zip';assert not archive.exists()
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,path in sorted(files.items()):assert not path.is_symlink();z.write(path,name)
        z.write(manifest_file,'benchmark/package-manifest.json')
    with zipfile.ZipFile(archive) as z:
        verified_manifest(z,'benchmark/package-manifest.json');assert z.testzip() is None
    receipt={'passed':True,'archive_sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(files)+1,
        'submission_sha256':sha(target),'code_matches_measured_stage':True,'uploaded':False,'runtime_replay':'pending'}
    (V/'benchmark/candidate-package-check.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


if __name__=='__main__':main()
