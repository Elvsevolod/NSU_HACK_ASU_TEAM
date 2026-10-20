import hashlib,json,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2]
variant=root/'solutions/—_value-type-flow'
info=json.loads((variant/'benchmark/archive-info.json').read_text())
extracted=Path(info['extracted_to'])
work=Path(__file__).parent/'archive-replay'
work.mkdir(exist_ok=False)
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'991','PYTHONPATH':str(extracted/'code')}
python='/private/tmp/nsu-alternatives-venv/bin/python'
command=[python,'-B',str(extracted/'code/offline_run.py'),'--source',str(root/'tt-challenge/targets/trainticket'),
 '--skeleton',str(root/'tt-challenge/skeleton/trainticket.json.gz'),'--context',str(root/'tt-challenge/context'),
 '--scenarios',str(root/'tt-challenge/scenarios'),'--output',str(work/'submission.json'),'--report',str(work/'report.json')]
with (work/'stdout.txt').open('w') as out,(work/'stderr.txt').open('w') as err:
 result=subprocess.run(command,cwd=extracted,env=env,stdout=out,stderr=err,timeout=600)
assert result.returncode==0,result.returncode
assert json.loads((work/'submission.json').read_text())==json.loads((variant/'submission.json').read_text())
audit=json.loads((work/'report-offline-audit.json').read_text())
assert all(audit[key]==0 for key in ('blocked_network','blocked_processes','blocked_reference_reads'))
with (work/'tests.stdout.txt').open('w') as out,(work/'tests.stderr.txt').open('w') as err:
 result=subprocess.run([python,'-B','-m','pytest','-q','-p','no:cacheprovider','tests'],cwd=extracted/'code',env=env,stdout=out,stderr=err,timeout=120)
assert result.returncode==0,result.returncode
assert '888 passed' in (work/'tests.stdout.txt').read_text()
assert hashlib.sha256((variant/'solution.zip').read_bytes()).hexdigest()==info['archive_sha256']
report={'passed':True,'all_eight_scenarios_exact_match':True,'extracted_code_only':True,'hash_seed':991,
 'archive_sha256':info['archive_sha256'],'submission_sha256':info['submission_sha256'],'offline_audit':audit,'extracted_tests_passed':888}
(variant/'benchmark/archive-replay.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
