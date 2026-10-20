"""Deterministic judged ZIP. No oracle, model or prior output is an input to code."""
import hashlib,json,zipfile
from pathlib import Path
V=Path(__file__).resolve().parents[1]
stage=V/'development/stages/E7-release'
manifest=json.loads((stage/'code-sha256.json').read_text())
actual={p.relative_to(V/'code').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((V/'code').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
assert manifest==actual,'working code must equal measured release code'
assert (V/'submission.json').read_bytes()==(V/'benchmark/stages/E7-release/submission.json').read_bytes()
readme='''Solution 32. Python source-only Java/Spring scenario analyzer.
Install requirements.txt in an isolated Python 3.11 environment.
Run: python -B code/offline_run.py --source SOURCE --skeleton SKELETON --context CONTEXT --scenarios SCENARIOS --output answer.json --report report.json
All six paths are supplied by the caller. path-limit defaults to 4. Target JVM/services are never launched. No external LLM API or model weights are required.
The default uses accepted bounded static/List/Stream/Set/ordering semantics and baseline retrieval. Lexical/dense retrieval remain optional rejected development experiments. This is not complete Java/JVM/SQL support; unsupported cases are diagnosed and may stop a path.
Local S0 is separate from hidden/site quality. See the analytical package for experiments, independent fixtures and limitations. The ready skeleton is required; no graph is built from scratch.
'''
files={**{'code/'+name:(V/'code'/name).read_bytes() for name in actual},'submission.json':(V/'submission.json').read_bytes(),
  'requirements.txt':(V/'requirements.txt').read_bytes(),'README.md':readme.encode()}
metadata={'solution':32,'parent':31,'release_stage':'E7-release','files':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}}
files['MANIFEST.json']=(json.dumps(metadata,indent=2)+'\n').encode()
archive=V/'solution.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in sorted(files.items()):
        item=zipfile.ZipInfo(name,(2026,10,19,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;item.external_attr=0o100644<<16;z.writestr(item,data)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()))
    assert all(z.read(name)==data for name,data in files.items())
result={'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bytes':archive.stat().st_size,'members':len(files),'submission_sha256':hashlib.sha256(files['submission.json']).hexdigest(),'code_files':len(actual),'code_matches_E7':True}
(V/'benchmark/packaging').mkdir(exist_ok=True)
(V/'benchmark/packaging/judge-build.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
