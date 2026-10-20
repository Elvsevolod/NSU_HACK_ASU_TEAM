"""Record an explicitly reviewed Python check in a new immutable evidence directory."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

VARIANT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def code_manifest():
    return {p.relative_to(VARIANT / 'code').as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((VARIANT / 'code').rglob('*'))
            if p.is_file() and not {'__pycache__', '.pytest_cache'} & set(p.parts)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('goal')
    p.add_argument('label')
    p.add_argument('command', nargs=argparse.REMAINDER)
    args = p.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    assert command, 'An explicitly reviewed command is required'
    if command[0] == '@python':
        command[0] = sys.executable
    output = VARIANT / 'benchmark/implementation' / args.goal / args.label
    output.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, 'PYTHONPATH': str(VARIANT / 'code'), 'PYTHONDONTWRITEBYTECODE': '1'}
    result = {'goal': args.goal, 'label': args.label, 'command': command,
              'cwd': str(VARIANT), 'started_at': datetime.now(timezone.utc).isoformat(),
              'python': sys.version, 'platform': platform.platform(), 'code_sha256': code_manifest(),
              'input_manifest': 'development/input-sha256.json', 'targets_started': False,
              'external_llm_api_calls': 0,
              'environment_overrides': {k: env[k] for k in ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE')}}
    write(output / 'run-start.json', result)
    start = time.perf_counter()
    with (output / 'stdout.txt').open('w') as out, (output / 'stderr.txt').open('w') as err:
        try:
            run = subprocess.run(command, cwd=VARIANT, env=env, stdout=out, stderr=err, timeout=args.timeout)
            result.update(returncode=run.returncode, timed_out=False)
        except subprocess.TimeoutExpired:
            result.update(returncode=None, timed_out=True)
    result['elapsed_seconds'] = time.perf_counter() - start
    write(output / 'run.json', result)
    path = VARIANT / 'development/implementation-state.json'
    state = json.loads(path.read_text())
    state['updated_at'] = datetime.now(timezone.utc).isoformat()
    record = next((g for g in state['goals'] if g['id'] == args.goal), None)
    if record is not None:
        record['evidence'].append(str(output.relative_to(VARIANT)))
        record['last_exit_status'] = result['returncode']
    state.setdefault('commands', []).append({'path': str(output.relative_to(VARIANT)),
                                           'returncode': result['returncode']})
    write(path, state)
    with (VARIANT / 'development/implementation-log.md').open('a') as log:
        log.write('\n' + state['updated_at'] + ' ' + args.goal + '/' + args.label + '\n\n')
        log.write('Exit: ' + str(result['returncode']) + '; evidence: ' + str(output.relative_to(VARIANT)) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('code_sha256',)}, ensure_ascii=False))
    raise SystemExit(0 if result['returncode'] == 0 else 1)


if __name__ == '__main__':
    main()
