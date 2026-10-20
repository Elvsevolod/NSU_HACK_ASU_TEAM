"""Run the exact packaged analyzer from an independent extracted directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import zipfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    for name in ('archive', 'source', 'skeleton', 'context', 'scenarios', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='analyzer30-replay-') as directory:
        root = Path(directory)
        with zipfile.ZipFile(args.archive) as z:
            assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
            manifest = json.loads(z.read('benchmark/package-manifest.json'))
            assert all(hashlib.sha256(z.read(n)).hexdigest() == value for n, value in manifest.items())
            z.extractall(root)
        command = [sys.executable, '-B', str(root / 'code/offline_run.py')]
        for name in ('source', 'skeleton', 'context', 'scenarios'):
            command += ['--' + name, str(getattr(args, name).resolve())]
        command += ['--output', str((args.output / 'submission.json').resolve()),
                    '--report', str((args.output / 'analysis-report.json').resolve())]
        env = {**os.environ, 'PYTHONPATH': str(root / 'code')}
        with (args.output / 'stdout.txt').open('w') as out, (args.output / 'stderr.txt').open('w') as err:
            run = subprocess.run(command, cwd=root, env=env, stdout=out, stderr=err, timeout=600)
        with (args.output / 'tests.txt').open('w') as out:
            tests = subprocess.run([sys.executable, '-B', '-m', 'pytest', str(root / 'code/tests'),
                                    '-q', '-p', 'no:cacheprovider'], cwd=root, env=env,
                                   stdout=out, stderr=subprocess.STDOUT, timeout=120)
        matches = run.returncode == 0 and sha(args.output / 'submission.json') == sha(root / 'submission.json')
        audit = json.loads((args.output / 'analysis-report-offline-audit.json').read_text())
    result = {'passed': matches and tests.returncode == 0 and not any(audit[k] for k in
                ('blocked_network', 'blocked_processes', 'blocked_reference_reads')),
              'archive_sha256': sha(args.archive), 'submission_sha256': sha(args.output / 'submission.json'),
              'all_package_hashes_match': True, 'all_eight_answers_match': matches,
              'analyzer_returncode': run.returncode, 'tests_returncode': tests.returncode,
              'offline_audit': audit, 'elapsed_seconds_including_tests': time.perf_counter() - started,
              'target_applications_started': False}
    (args.output / 'replay.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    assert result['passed']


if __name__ == '__main__':
    main()
