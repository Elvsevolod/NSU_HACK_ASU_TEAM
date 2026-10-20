"""Immutable submission, with all acceptance evidence checked beforehand."""
import hashlib
import json
from pathlib import Path
import zipfile

VARIANT=Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    root=VARIANT;final=root/'benchmark/final'
    assert json.loads((final/'witness-check.json').read_text())['passed']
    assert not json.loads((final/'format-check.json').read_text())['errors']
    assert sha(root/'submission.json')==json.loads((final/'metadata.json').read_text())['submission_sha256']
    for name,digest in json.loads((final/'code-sha256.json').read_text()).items():assert sha(root/'code'/name)==digest,name
    for profile in ('1','4','8','additional'):
        for name in ('checks.json','semantic-checks.json'):
            assert json.loads((root/'benchmark/piggymetrics-final'/profile/name).read_text())['passed']
    for profile in ('negative-main','negative-additional'):
        assert json.loads((root/'benchmark/piggymetrics-final'/profile/'summary.json').read_text())['passed']
    for file in ('benchmark/protected-integrity.json','benchmark/document-journey/checks.json'):
        assert json.loads((root/file).read_text())['passed']
    assert all(row['matches_expected'] for row in json.loads((root/'benchmark/repeated-analysis-final.json').read_text())['runs'])
    names=['README.md','IMPLEMENTATION_REVIEW.md','requirements.txt','submission.json']
    names += ['benchmark/final/'+name for name in ('metadata.json','code-sha256.json','evaluation.json',
        'format-check.json','witness-check.json','analysis-report-offline-audit.json')]
    names+=['benchmark/protected-integrity.json','benchmark/repeated-analysis-final.json']
    files={root/name for name in names}
    for folder in ('code','checks'):
        files.update(p for p in (root/folder).rglob('*') if p.is_file() and
            not {'__pycache__','.pytest_cache'}&set(p.parts) and p.suffix not in ('.pyc','.class','.jar') and p.name!='.DS_Store')
    manifest={p.relative_to(root).as_posix():sha(p) for p in sorted(files)}
    path=root/'benchmark/package-manifest.json';path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    archive=root/'solution.zip';assert not archive.exists()
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in [*sorted(files),path]:z.write(p,p.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(hashlib.sha256(z.read(name)).hexdigest()==digest for name,digest in manifest.items())
        assert z.read('submission.json')==(root/'submission.json').read_bytes()
    result={'passed':True,'sha256':sha(archive),'bytes':archive.stat().st_size,'files':len(files)+1,
        'submission_sha256':sha(root/'submission.json'),'testzip':'passed','all_member_hashes_match':True,
        'target_sources_included':False,'previous_variants_included':False}
    (root/'benchmark/archive-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
