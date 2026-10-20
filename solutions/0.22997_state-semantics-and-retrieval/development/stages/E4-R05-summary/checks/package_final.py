"""Freeze one code-gated judge ZIP. It is never rebuilt after assessment."""
import hashlib,json,zipfile
from pathlib import Path
from archive_support import verified_manifest
V=Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    assert json.loads((V/'benchmark/final/witness-check.json').read_text())['passed']
    meta=json.loads((V/'benchmark/final/metadata.json').read_text());assert sha(V/'submission.json')==meta['submission_sha256']
    code=json.loads((V/'benchmark/final/code-sha256.json').read_text());assert all(sha(V/'code'/n)==d for n,d in code.items())
    files={V/n for n in ('README.md','IMPLEMENTATION_REVIEW.md','requirements.txt','submission.json')}
    files.update(p for p in (V/'code').rglob('*') if p.is_file() and not {'__pycache__','.pytest_cache','.git'}&set(p.parts) and p.suffix!='.pyc' and p.name!='.DS_Store')
    files.update(V/'benchmark/final'/n for n in ('metadata.json','code-sha256.json','evaluation.json','format-check.json','witness-check.json','analysis-report-offline-audit.json','analysis-report-timings.json'))
    manifest={p.relative_to(V).as_posix():sha(p) for p in sorted(files)}
    path=V/'benchmark/package-manifest.json';assert not path.exists();path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    archive=V/'solution.zip';assert not archive.exists()
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for file in [*sorted(files),path]:z.write(file,file.relative_to(V).as_posix())
    with zipfile.ZipFile(archive) as z:
        verified_manifest(z,'benchmark/package-manifest.json');assert z.read('submission.json')==(V/'submission.json').read_bytes()
    result={'passed':True,'sha256':sha(archive),'bytes':archive.stat().st_size,'files':len(files)+1,'submission_sha256':meta['submission_sha256'],
        'documents_boundary':'Pre-site copy in judged ZIP; later workspace documentation has a separate post-site status. ZIP/code/submission immutable.',
        'all_member_hashes_match':True,'target_sources_included':False,'previous_variants_included':False,'judge_credentials_included':False}
    (V/'benchmark/archive-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
