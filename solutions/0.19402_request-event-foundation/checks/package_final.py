"""Package frozen code without target sources, weights or intermediate reports."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    final = ROOT / 'benchmark/final'
    metadata = json.loads((final / 'metadata.json').read_text())
    assert digest(ROOT / 'submission.json') == metadata['submission_sha256']
    assert json.loads((final / 'witness-check.json').read_text())['passed']
    assert not json.loads((final / 'format-check.json').read_text())['errors']
    for name, sha in json.loads((final / 'code-sha256.json').read_text()).items():
        assert digest(ROOT / 'code' / name) == sha, name
    assert json.loads((ROOT / 'benchmark/protected-integrity.json').read_text())['passed']
    reports = ['final', 'final-public-candidate', 'final-public-controls',
               'final-synthetic-candidate', 'heldout-first', 'heldout-repair-replay',
               'optional-extractor-v2', 'optional-local-reranker-metal', 'optional-summary-smt']
    names = ['README.md', 'IMPLEMENTATION_REVIEW.md', 'requirements.txt', 'submission.json',
             'benchmark/repeated-analysis-final.json', 'benchmark/export-policy-comparison.json',
             'benchmark/protected-integrity.json', 'development/requirements.json',
             'development/tests-final-resource-filter.txt']
    files = {ROOT / name for name in names}
    for directory in ['code', 'checks', 'fixtures', *['benchmark/' + name for name in reports]]:
        files.update(p for p in (ROOT / directory).rglob('*') if p.is_file()
                     and not {'__pycache__', '.pytest_cache'} & set(p.parts)
                     and p.suffix not in ('.pyc', '.class', '.jar', '.gguf'))
    manifest = {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(files)}
    manifest_path = ROOT / 'benchmark/package-manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    archive = ROOT / 'solution.zip'
    assert not archive.exists(), 'Preserve an existing archive; never replace an evaluated ZIP'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in [*sorted(files), manifest_path]:
            z.write(p, p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(hashlib.sha256(z.read(name)).hexdigest() == sha for name, sha in manifest.items())
        assert z.read('submission.json') == (ROOT / 'submission.json').read_bytes()
    result = {'sha256': digest(archive), 'bytes': archive.stat().st_size,
              'files': len(files) + 1, 'submission_sha256': metadata['submission_sha256'],
              'root_submission_matches': True, 'all_member_hashes_match': True, 'testzip': 'passed'}
    (ROOT / 'benchmark/archive-check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
