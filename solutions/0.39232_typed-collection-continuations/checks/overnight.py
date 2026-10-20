"""Durable, evidence-owned journal for the explicitly authorized G01–G18 run."""
import argparse
import fcntl
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

VARIANT = Path(__file__).resolve().parents[1]
STATE = VARIANT / 'development/overnight-state.json'


def save(path, value):
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def manifest():
    return {p.relative_to(VARIANT / 'code').as_posix():
            hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((VARIANT / 'code').rglob('*'))
            if p.is_file() and not {'__pycache__', '.pytest_cache'} & set(p.parts)}


def _record(goal_id, status=None, **details):
    state = json.loads(STATE.read_text())
    goal = next(g for g in state['goals'] if g['goal_id'] == goal_id)
    if status is not None:
        assert status in {'pending', 'in_progress', 'verified', 'experiment_rejected',
                          'blocked_with_reproducer', 'not_run'}
        goal['status'] = status
    for key, value in details.items():
        if key in {'evidence_paths', 'tests_run', 'findings', 'what_changed', 'commands'}:
            goal[key] += [item for item in value if item not in goal[key]]
        else:
            goal[key] = value
    state['updated_at'] = datetime.now(timezone.utc).isoformat()
    state['current_goal'] = goal_id
    state['next_action'] = goal.get('next_action', goal.get('next_goal'))
    save(STATE, state)
    with (VARIANT / 'development/overnight-log.md').open('a') as stream:
        stream.write('\n' + state['updated_at'] + ' ' + goal_id + ' ' + goal['status'] + '\n\n')
        stream.write(json.dumps(details, ensure_ascii=False, indent=2) + '\n')


def record(goal_id,status=None,**details):
    with STATE.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:_record(goal_id,status,**details)
        finally:fcntl.flock(lock,fcntl.LOCK_UN)


def checkpoint(goal_id, label, status='in_progress', **details):
    target = VARIANT / 'development/checkpoints' / label
    target.mkdir()
    current = manifest()
    save(target / 'code-sha256.json', current)
    baseline = VARIANT / 'development/stages/G01-parent30/code'
    names = set(current) | {p.relative_to(baseline).as_posix()
                            for p in baseline.rglob('*') if p.is_file()}
    patch = []
    for name in sorted(names):
        before, after = baseline / name, VARIANT / 'code' / name
        a = before.read_text().splitlines(True) if before.is_file() else []
        b = after.read_text().splitlines(True) if after.is_file() else []
        patch.extend(difflib.unified_diff(a, b, fromfile='parent30/' + name, tofile='candidate/' + name))
    (target / 'code.patch').write_text(''.join(patch))
    evidence = details.pop('evidence_paths', [])
    record(goal_id, status, code_hashes=current,
           evidence_paths=[str(target.relative_to(VARIANT)), *evidence], **details)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('goal')
    parser.add_argument('label')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    assert command, 'An explicitly reviewed command is required'
    if command[0] == '@python':
        command[0] = sys.executable
    output = VARIANT / 'benchmark/overnight' / args.goal / args.label
    output.mkdir(parents=True)
    record(args.goal, 'in_progress', commands=[command],
           next_action='Inspect command result in ' + str(output.relative_to(VARIANT)))
    environment = {**os.environ, 'PYTHONPATH': str(VARIANT / 'code'), 'PYTHONDONTWRITEBYTECODE': '1'}
    result = {'command': command, 'cwd': str(VARIANT), 'code_hashes': manifest(),
              'environment_overrides': {k: environment[k] for k in ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE')},
              'input_manifest': 'development/input-sha256.json',
              'started_at': datetime.now(timezone.utc).isoformat()}
    start = time.perf_counter()
    with (output / 'stdout.txt').open('w') as out, (output / 'stderr.txt').open('w') as err:
        try:
            run = subprocess.run(command, cwd=VARIANT, env=environment, stdout=out, stderr=err, timeout=args.timeout)
            result.update(returncode=run.returncode, timed_out=False)
        except subprocess.TimeoutExpired:
            result.update(returncode=None, timed_out=True)
    result['elapsed_seconds'] = time.perf_counter() - start
    save(output / 'run.json', result)
    record(args.goal, evidence_paths=[str(output.relative_to(VARIANT))],
           actual_exit_status=result['returncode'],
           tests_run=[{'label': args.label, 'returncode': result['returncode'],
                       'timed_out': result['timed_out']}])
    print(json.dumps({k: v for k, v in result.items() if k != 'code_hashes'}))
    raise SystemExit(0 if result['returncode'] == 0 else 1)


if __name__ == '__main__':
    main()
