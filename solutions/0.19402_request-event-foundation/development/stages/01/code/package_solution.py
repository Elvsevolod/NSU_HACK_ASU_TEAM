"""Package the verified snapshot, excluding diagnostics, caches and test fixtures."""
import hashlib
import json
from pathlib import Path
import zipfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root=Path(__file__).resolve().parents[1]
    benchmark=root/'benchmark'
    summary=json.loads((benchmark/'summary.json').read_text())
    assert summary['submission_sha256']==digest(root/'submission.json')
    assert json.loads((benchmark/'verification.json').read_text())['passed']
    assert not json.loads((benchmark/'format_check.json').read_text())['errors']
    assert json.loads((benchmark/'public-projects.json').read_text())['passed']
    assert json.loads((benchmark/'request-graphs.json').read_text())['passed']
    assert json.loads((benchmark/'input-replay-graphs.json').read_text())['passed']
    assert json.loads((benchmark/'lvalue-graphs.json').read_text())['passed']
    code=json.loads((benchmark/'code-sha256.json').read_text())
    assert all(digest(root/name)==value for name,value in code.items())
    archive=root/'solution.zip'
    assert not archive.exists(),'Preserve an already packaged snapshot'
    reports={'summary.json','evaluation.json','format_check.json','verification.json',
             'comparison.json','coverage-summary.json','public-projects.json','petclinic-body-graph.json',
             'generalization.json','mechanisms.json','request-graphs.json',
             'tests.json','protected-files.json','development-review.json','code-sha256.json',
             'input-replay-graphs.json','input-replay-parent20.json','reproducibility.json','deepseek-development.json',
             'lvalue-graphs.json','lvalue-parent22.json'}
    def included(path):
        rel=path.relative_to(root)
        if {'__pycache__','.pytest_cache','.venv'}&set(rel.parts) or path.suffix=='.pyc':return False
        if rel.parts[0] in ('code','checks'):return True
        if rel.parts[0]=='benchmark':return len(rel.parts)==2 and rel.name in reports
        return rel.as_posix() in ('README.md','DIAGNOSTICS.md','requirements.txt','submission.json')
    files=[p for p in sorted(root.rglob('*')) if p.is_file() and included(p)]
    manifest={p.relative_to(root).as_posix():digest(p) for p in files}
    manifest_path=benchmark/'package-manifest.json'
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as output:
        for path in [*files,manifest_path]:output.write(path,path.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as output:
        assert output.testzip() is None
        assert all(hashlib.sha256(output.read(name)).hexdigest()==value for name,value in manifest.items())
        assert output.read('submission.json')==(root/'submission.json').read_bytes()
    check={'sha256':digest(archive),'bytes':archive.stat().st_size,'files':len(files)+1,
           'root_submission_matches':True,'all_member_hashes_match':True,'testzip':'passed'}
    (benchmark/'archive-check.json').write_text(json.dumps(check,indent=2)+'\n')
    print(json.dumps(check))


if __name__=='__main__':main()
