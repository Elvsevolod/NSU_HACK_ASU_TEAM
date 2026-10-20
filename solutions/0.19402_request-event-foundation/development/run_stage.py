"""Freeze candidate code before each measurement. Never start target services."""
import argparse
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import time

variant = Path(__file__).resolve().parents[1]
root = variant.parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('stage')
parser.add_argument('--timeout', type=int, default=600)
parser.add_argument('--trace-stacks',action='store_true')
args = parser.parse_args()
snapshot = variant / 'development/stages' / args.stage
output = variant / 'benchmark/stages' / args.stage
assert not snapshot.exists() and not output.exists()
snapshot.mkdir(parents=True); output.mkdir(parents=True)
shutil.copytree(variant/'code', snapshot/'code', ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','*.pyc'))
digests = {str(p.relative_to(snapshot/'code')):hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
           for p in sorted((snapshot/'code').rglob('*')) if p.is_file()}
(snapshot/'code-sha256.json').write_text(json.dumps(digests,indent=2)+'\n')
command = [sys.executable, '-B', str(snapshot/'code/offline_run.py'),
    '--source', str(root/'tt-challenge/targets/trainticket'), '--skeleton', str(root/'tt-challenge/skeleton/trainticket.json.gz'),
    '--context', str(root/'tt-challenge/context'), '--scenarios', str(root/'tt-challenge/scenarios'),
    '--output', str(output/'submission.json'), '--report', str(output/'analysis-report.json')]
if args.trace_stacks:command[2:2]=[str(variant/'development/profile_entry.py')]
started = time.perf_counter()
with (output/'stdout.txt').open('w') as stdout, (output/'stderr.txt').open('w') as stderr:
    try:
        result = subprocess.run(command,cwd=root,stdout=stdout,stderr=stderr,timeout=args.timeout)
        status = {'returncode':result.returncode,'timed_out':False}
    except subprocess.TimeoutExpired:
        status = {'returncode':None,'timed_out':True}
status.update(stage=args.stage,elapsed_seconds=time.perf_counter()-started,command=command,code_manifest=str(snapshot/'code-sha256.json'))
(output/'run.json').write_text(json.dumps(status,indent=2)+'\n')
print(json.dumps(status))
raise SystemExit(0 if status['returncode']==0 else 1)
