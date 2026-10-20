import hashlib,json,os,subprocess,tempfile,zipfile
from pathlib import Path

root=Path.cwd()
variant=root/'solutions/—_source-request-state'
bench=variant/'benchmark'
archive=variant/'solution.zip'
work=Path(tempfile.mkdtemp(prefix='nsu-variant10-archive-',dir='/private/tmp'))
extracted=work/'unpacked';extracted.mkdir()
expected=json.loads((bench/'code-sha256.json').read_text())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert z.read('submission.json')==(variant/'submission.json').read_bytes()
    assert not any(Path(name).is_absolute() or '..' in Path(name).parts for name in z.namelist())
    assert all(hashlib.sha256(z.read(path)).hexdigest()==digest for path,digest in expected.items())
    assert not any('experiments/' in name or '-export.json' in name for name in z.namelist())
    z.extractall(extracted)
scenario=json.loads((root/'tt-challenge/scenarios/S0.json').read_text())
scenario['id']='archive-independent-replay'
scenario_path=work/'scenario.json';scenario_path.write_text(json.dumps(scenario)+'\n')
output=work/'replayed.json';report=work/'replayed-report.json'
python='/private/tmp/nsu-alternatives-venv/bin/python'
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'991','PYTHONPATH':str(extracted/'code')}
command=[python,'-B',str(extracted/'code/offline_run.py'),'--source',str(root/'tt-challenge/targets/trainticket'),
 '--skeleton',str(root/'tt-challenge/skeleton/trainticket.json.gz'),'--context',str(root/'tt-challenge/context/db-after-warmup.sql.gz'),
 '--scenarios',str(scenario_path),'--output',str(output),'--report',str(report)]
with (work/'stdout.txt').open('w') as out,(work/'stderr.txt').open('w') as err:
    completed=subprocess.run(command,env=env,stdout=out,stderr=err,timeout=120)
assert completed.returncode==0,(completed.returncode,work)
original=json.loads((variant/'submission.json').read_text())['scenarios']['S0']['edges']
actual=json.loads(output.read_text())['scenarios'][scenario['id']]['edges']
canon=lambda edges:{('scenario' if e['relation']=='executes' else e['source'],e['relation'],e['target']) for e in edges}
assert canon(original)==canon(actual)
result=json.loads((bench/'archive-check.json').read_text())
result.update({'measured_code_hashes_match_archive':True,'extracted_S0_replay_matches':True,
 'scenario_id_changed':True,'replay_hash_seed':991,'reference_not_read_by_builder':json.loads(report.with_name(report.stem+'-offline-audit.json').read_text())['blocked_reference_reads']==0,
 'work_directory':str(work)})
(bench/'archive-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
