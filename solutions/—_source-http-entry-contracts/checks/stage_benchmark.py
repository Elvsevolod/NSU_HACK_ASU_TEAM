"""Measure one immutable code stage, its outcomes and event differences."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

VARIANT = Path(__file__).resolve().parents[1]
ROOT = VARIANT.parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage')
    parser.add_argument('--existing-snapshot', action='store_true')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--challenge',type=Path,default=ROOT/'tt-challenge')
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    challenge=args.challenge.resolve()
    assert (challenge/'skeleton/trainticket.json.gz').is_file(),'Supply --challenge with the complete original input package'
    snapshot = VARIANT / 'development/stages' / args.stage
    output = args.output.resolve() if args.output else VARIANT / 'benchmark/stages' / args.stage
    assert not output.exists()
    output.mkdir(parents=True)
    if not args.existing_snapshot:
        assert not snapshot.exists()
        snapshot.mkdir(parents=True)
        shutil.copytree(VARIANT / 'code', snapshot / 'code',
                        ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', '*.pyc'))
        save(snapshot / 'code-sha256.json', {f.relative_to(snapshot / 'code').as_posix(): sha(f)
                                           for f in sorted((snapshot / 'code').rglob('*')) if f.is_file()})
    manifest = json.loads((snapshot / 'code-sha256.json').read_text())
    assert all(sha(snapshot / 'code' / name) == digest for name, digest in manifest.items())
    command = [sys.executable, '-B', str(snapshot / 'code/offline_run.py'),
               '--source', str(challenge / 'targets/trainticket'),
               '--skeleton', str(challenge / 'skeleton/trainticket.json.gz'),
               '--context', str(challenge / 'context'),
               '--scenarios', str(challenge / 'scenarios'),
               '--output', str(output / 'submission.json'), '--report', str(output / 'analysis-report.json')]
    started = time.perf_counter()
    with (output / 'stdout.txt').open('w') as out, (output / 'stderr.txt').open('w') as err:
        try:
            result = subprocess.run(command, cwd=VARIANT, stdout=out, stderr=err, timeout=args.timeout)
            status = {'returncode': result.returncode, 'timed_out': False}
        except subprocess.TimeoutExpired:
            status = {'returncode': None, 'timed_out': True}
    status.update(stage=args.stage, elapsed_seconds=time.perf_counter() - started, command=command,
                  code_sha256=manifest, targets_started=False, external_llm_api_calls=0)
    save(output / 'run.json', status)
    if status['returncode'] != 0:
        print(json.dumps({k: v for k, v in status.items() if k != 'code_sha256'}))
        raise SystemExit(1)
    for name, arguments in [('evaluation', [str(challenge / 'gold/S0.json')]),
                            ('format-check', ['--check', str(challenge / 'skeleton/trainticket.json.gz')])]:
        check = subprocess.run([sys.executable, '-B', str(challenge / 'platform/evaluate_golden.py'),
                                *arguments, str(output / 'submission.json'), '--json'], capture_output=True, text=True)
        (output / (name + '.json')).write_text(check.stdout)
        assert check.returncode in (0, 3)
    report = json.loads((output / 'analysis-report.json').read_text())
    summary = {key: report.get(key) for key in ('elapsed_seconds', 'preparation_seconds', 'analysis_seconds',
                                               'peak_rss_bytes', 'source_fingerprint', 'input_sha256')}
    summary['submission_sha256'] = sha(output / 'submission.json')
    summary['scenarios'] = {}
    totals = Counter()
    for sid, scenario in report['scenarios'].items():
        alternatives = [a for step in scenario['steps'] for a in step.get('alternatives', [step])]
        outcomes = Counter(a.get('outcome') for a in alternatives)
        effects = Counter(e.get('operation') for a in alternatives for e in a.get('call_effects', []))
        last = Counter((a.get('call_effects') or [{}])[-1].get('operation') for a in alternatives
                       if a.get('outcome') != 'returned')
        summary['scenarios'][sid] = {'outcomes': dict(outcomes), 'opaque_operations': dict(effects),
                                     'last_opaque_before_stop': dict(last)}
        totals.update(outcomes)
    summary['outcomes'] = dict(totals)
    save(output / 'summary.json', summary)
    del report
    raw = output / 'analysis-report.json'
    original_sha = sha(raw)
    compressed = output / 'analysis-report.json.gz'
    with raw.open('rb') as src, gzip.GzipFile(filename=str(compressed), mode='wb', mtime=0) as dst:
        shutil.copyfileobj(src, dst)
    digest = hashlib.sha256()
    with gzip.open(compressed, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    assert digest.hexdigest() == original_sha
    save(output / 'report-integrity.json', {'uncompressed_bytes': raw.stat().st_size,
                                           'uncompressed_sha256': original_sha, 'gzip_sha256': sha(compressed)})
    raw.unlink()
    print(json.dumps({'stage': args.stage, 'submission_sha256': summary['submission_sha256'],
                      'elapsed_seconds': summary['elapsed_seconds'], 'peak_rss_bytes': summary['peak_rss_bytes'],
                      'outcomes': summary['outcomes']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
