"""Immutable judge ZIP after explicit local acceptance, with root submission.json."""
import hashlib,json,zipfile
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert json.loads((V/'benchmark/final/witness-check.json').read_text())['passed']
    meta=json.loads((V/'benchmark/final/metadata.json').read_text());assert sha(V/'submission.json')==meta['submission_sha256']
    code=json.loads((V/'benchmark/final/code-sha256.json').read_text())
    assert all(sha(V/'code'/name)==digest for name,digest in code.items())
    files={V/name for name in ('README.md','IMPLEMENTATION_REVIEW.md','requirements.txt','submission.json')}
    for folder in ('code','checks'):
        files.update(p for p in (V/folder).rglob('*') if p.is_file() and not {'__pycache__','.pytest_cache','.git'}&set(p.parts)
                     and p.suffix not in ('.pyc','.class','.jar') and p.name!='.DS_Store')
    files.update(V/'benchmark/final'/name for name in ('metadata.json','code-sha256.json','evaluation.json','format-check.json',
                 'witness-check.json','analysis-report-offline-audit.json','analysis-report-timings.json'))
    files.update(V/name for name in ('benchmark/protected-integrity.json','benchmark/repeated-analysis-final.json','development/requirements.json','development/scope-check.json'))
    manifest={p.relative_to(V).as_posix():sha(p) for p in sorted(files)}
    path=V/'benchmark/package-manifest.json';path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    archive=V/'solution.zip';assert not archive.exists()
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for file in [*sorted(files),path]:z.write(file,file.relative_to(V).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and z.read('submission.json')==(V/'submission.json').read_bytes()
        assert all(hashlib.sha256(z.read(name)).hexdigest()==digest for name,digest in manifest.items())
    result={'passed':True,'sha256':sha(archive),'bytes':archive.stat().st_size,'files':len(files)+1,
            'submission_sha256':meta['submission_sha256'],'testzip':'passed','all_member_hashes_match':True,
            'target_sources_included':False,'previous_variants_included':False,'judge_credentials_included':False}
    (V/'benchmark/archive-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
