"""Run the pinned development worker and retain JSONL evidence outside solution code."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import signal

p = argparse.ArgumentParser()
p.add_argument('prompt', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--permissions', type=Path)
p.add_argument('--session')
p.add_argument('--timeout', type=int, default=180)
args = p.parse_args()
root = Path(__file__).resolve().parents[2]
env = os.environ.copy()
env['OPENCODE_PERMISSION'] = args.permissions.read_text() if args.permissions else json.dumps({
    'edit': 'deny', 'bash': 'deny', 'task': 'deny', 'external_directory': 'deny'})
command = [str(Path.home() / '.local/bin/opencode-deepseek'), 'run', '--dir', str(root),
           '--format', 'json', '--agent', 'build', '--variant', 'max']
if args.session:
    command += ['--session', args.session]
command.append(args.prompt.read_text())
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open('w') as out, args.output.with_suffix('.stderr.txt').open('w') as err:
    process = subprocess.Popen(command, env=env, stdout=out, stderr=err, start_new_session=True)
    try:
        code = process.wait(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        code = process.wait(timeout=10)
        err.write('\nStopped after the bounded timeout without completion.\n')
print(json.dumps({'returncode': code, 'log': str(args.output)}))
raise SystemExit(code)
