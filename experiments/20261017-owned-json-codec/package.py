"""Package only the self-contained variant; preserve all earlier measurements."""
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

root=Path(__file__).resolve().parents[2]
variant=root/'solutions/0.66185_owned-json-codec'
archive=variant/'solution.zip'
assert not archive.exists(),'Do not replace a delivered archive'
summary=json.loads((variant/'benchmark/summary.json').read_text())
assert hashlib.sha256((variant/'submission.json').read_bytes()).hexdigest()==summary['submission_sha256']
assert json.loads((variant/'benchmark/verification.json').read_text())['passed']
assert json.loads((variant/'benchmark/reproducibility.json').read_text())['passed']
assert '1067 passed' in (variant/'benchmark/tests.stdout.txt').read_text()
source=json.loads((variant/'package-code-sha256.json').read_text())
assert all(hashlib.sha256((variant/name).read_bytes()).hexdigest()==digest for name,digest in source.items())
excluded={'solution.zip','benchmark/archive-info.json','benchmark/archive-replay.json','benchmark/code-sha256.json'}
compact_reports={'summary.json','evaluation.json','format_check.json','verification.json','coverage-summary.json',
 'input-coverage.json','comparison.json','mechanism-comparison.json','mechanism-baseline18.json','mechanism-candidate19.json',
 'petclinic.json','petclinic-body-graph.json','generalization.json','reproducibility.json','protected-files.json',
 'deepseek-development.json','code-review.json','tests.stdout.txt'}
def included(path):
    rel=path.relative_to(variant)
    if {'__pycache__','.pytest_cache','.venv'}&set(rel.parts) or path.suffix=='.pyc':return False
    if rel.parts[0] in ('code','checks'):return True
    if rel.parts[0]=='benchmark':return len(rel.parts)==2 and rel.name in compact_reports
    return rel.as_posix() in {'README.md','DIAGNOSTICS.md','requirements.txt','submission.json','package-code-sha256.json'}
files=[path for path in sorted(variant.rglob('*')) if path.is_file() and included(path)]
manifest={path.relative_to(variant).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
(variant/'package-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
files.append(variant/'package-manifest.json')
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as output:
    for path in files:
        name=path.relative_to(variant).as_posix()
        assert not name.startswith('/') and '..' not in Path(name).parts
        info=zipfile.ZipInfo(name,date_time=(2026,10,17,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=0o644<<16
        output.writestr(info,path.read_bytes())
with zipfile.ZipFile(archive) as package:
    assert package.testzip() is None
    assert 'submission.json' in package.namelist()
    assert not any(name.startswith(('tt-challenge/','experiments/')) for name in package.namelist())
    extracted=Path(tempfile.mkdtemp(prefix='nsu-solution19-archive-',dir='/private/tmp'))
    package.extractall(extracted)
    assert all(hashlib.sha256((extracted/name).read_bytes()).hexdigest()==digest for name,digest in manifest.items())
info={'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_bytes':archive.stat().st_size,
      'submission_sha256':summary['submission_sha256'],'files':len(files),'extracted_to':str(extracted),'compact_archive':True,
      'excluded_full_reports_and_secondary_submissions':True,
      'manifest_verified':True,'runtime_source_manifest_verified':True,
      'excluded_transient_test_cache':True,'raw_working_tree_code_manifest_in_repository_only':True}
(variant/'benchmark/archive-info.json').write_text(json.dumps(info,indent=2)+'\n')
print(json.dumps(info))
