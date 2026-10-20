"""Build one immutable submission ZIP after mandatory acceptance checks."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    final=ROOT/'benchmark/final';metadata=json.loads((final/'metadata.json').read_text())
    assert digest(ROOT/'submission.json')==metadata['submission_sha256']
    assert json.loads((final/'witness-check.json').read_text())['passed']
    assert not json.loads((final/'format-check.json').read_text())['errors']
    for name,value in json.loads((final/'code-sha256.json').read_text()).items():assert digest(ROOT/'code'/name)==value,name
    for name in ('real-budget-1','real-budget-4','real-budget-8'):
        assert json.loads((ROOT/'benchmark'/name/'checks.json').read_text())['passed']
    assert json.loads((ROOT/'benchmark/real-additional-r4/checks-with-types.json').read_text())['passed']
    assert json.loads((ROOT/'benchmark/journey-negative-controls-final/summary.json').read_text())['passed']
    assert json.loads((ROOT/'benchmark/additional-negative-controls/summary.json').read_text())['passed']
    assert json.loads((ROOT/'benchmark/protected-integrity.json').read_text())['passed']
    assert all(row['matches_expected'] for row in json.loads((ROOT/'benchmark/repeated-analysis-final.json').read_text())['runs'])
    names=['README.md','IMPLEMENTATION_REVIEW.md','requirements.txt','submission.json',
        'benchmark/final/metadata.json','benchmark/final/code-sha256.json','benchmark/final/evaluation.json',
        'benchmark/final/format-check.json','benchmark/final/witness-check.json',
        'benchmark/final/analysis-report-offline-audit.json','benchmark/protected-integrity.json']
    files={ROOT/name for name in names}
    for directory in ('code','checks'):
        files.update(path for path in (ROOT/directory).rglob('*') if path.is_file() and
            not {'__pycache__','.pytest_cache'}&set(path.parts) and path.suffix not in ('.pyc','.class','.jar') and path.name!='.DS_Store')
    manifest={path.relative_to(ROOT).as_posix():digest(path) for path in sorted(files)}
    manifest_path=ROOT/'benchmark/package-manifest.json';manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    archive=ROOT/'solution.zip';assert not archive.exists(),'An evaluated archive must never be replaced'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as output:
        for path in [*sorted(files),manifest_path]:output.write(path,path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as output:
        assert output.testzip() is None
        assert all(hashlib.sha256(output.read(name)).hexdigest()==value for name,value in manifest.items())
        assert output.read('submission.json')==(ROOT/'submission.json').read_bytes()
    result={'sha256':digest(archive),'bytes':archive.stat().st_size,'files':len(files)+1,
        'submission_sha256':metadata['submission_sha256'],'root_submission_matches':True,
        'all_member_hashes_match':True,'testzip':'passed','previous_variants_or_target_sources_included':False}
    (ROOT/'benchmark/archive-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
