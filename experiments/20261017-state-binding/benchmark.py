"""Reproducible builder run with scoring isolated from inference."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path('/private/tmp/nsu-alternatives-venv/bin/python')
VARIANT = ROOT / 'solutions/—_request-state-linking'
ENV = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0',
       'PYTHONPATH': str(VARIANT / 'code')}
p = argparse.ArgumentParser()
p.add_argument('--label')
p.add_argument('--final', action='store_true')
p.add_argument('--all', action='store_true')
args = p.parse_args()
assert args.final or args.label
bench = VARIANT / 'benchmark' if args.final else Path(__file__).parent / 'iterations' / args.label
bench.mkdir(parents=True, exist_ok=True)
assert not (bench / 'summary.json').exists(), 'Keep previous measured runs immutable'
output = VARIANT / 'submission.json' if args.final else bench / 'prediction.json'
report_path = bench / 'analysis-report.json'


def run(command, label, codes=(0,), env=ENV):
    with (bench / (label + '.stdout.txt')).open('w') as out, (bench / (label + '.stderr.txt')).open('w') as err:
        proc = subprocess.run([str(x) for x in command], cwd=ROOT, env=env, stdout=out, stderr=err)
    assert proc.returncode in codes, (label, proc.returncode)


def hashes():
    return {p.relative_to(VARIANT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((VARIANT / 'code').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def build(output, report, scenarios, seed='0'):
    run([PYTHON, '-B', VARIANT / 'code/offline_run.py',
         '--source', ROOT / 'tt-challenge/targets/trainticket',
         '--skeleton', ROOT / 'tt-challenge/skeleton/trainticket.json.gz',
         '--context', ROOT / 'tt-challenge/context', '--scenarios', scenarios,
         '--output', output, '--report', report], report.stem, env={**ENV, 'PYTHONHASHSEED': seed})


before = hashes()
build(output, report_path, ROOT / 'tt-challenge/scenarios' if args.all or args.final else ROOT / 'tt-challenge/scenarios/S0.json')
assert hashes() == before, 'Code changed during measurement; rerun with a fresh label'
for label, reference in [('evaluation', [ROOT / 'tt-challenge/gold/S0.json']),
                         ('format_check', ['--check', ROOT / 'tt-challenge/skeleton/trainticket.json.gz'])]:
    run([PYTHON, '-B', ROOT / 'tt-challenge/platform/evaluate_golden.py', *reference, output, '--json'], label, (0, 3))
    value = json.loads((bench / (label + '.stdout.txt')).read_text())
    assert not value['errors'] and all(not v.get('rejected') and not v.get('duplicates') for v in value['scenarios'].values())
    (bench / (label + '.json')).write_text(json.dumps(value, indent=2) + '\n')
run([PYTHON, '-B', VARIANT / 'code/verify_run.py', '--submission', output, '--report', report_path,
     '--output', bench / 'verification.json'], 'verify')
if args.final:
    run([PYTHON, '-B', '-m', 'pytest', VARIANT / 'code/tests', '-q', '-p', 'no:cacheprovider',
         '--junitxml', bench / 'pytest.xml'], 'tests')
    run([PYTHON, '-B', VARIANT / 'code/check_generalization.py', '--directory', bench], 'generalization')
    replay = json.loads((ROOT / 'tt-challenge/scenarios/S0.json').read_text())
    replay['id'] = 'independent-replay-label'
    checks = VARIANT / 'checks'
    checks.mkdir(exist_ok=True)
    (checks / 'replay.json').write_text(json.dumps(replay, indent=2) + '\n')
    build(bench / 'reproduction-submission.json', bench / 'reproduction-report.json', checks / 'replay.json', '991')
    def triples(block):
        return {('scenario' if e['relation'] == 'executes' else e['source'], e['relation'], e['target']) for e in block['edges']}
    original = json.loads(output.read_text())['scenarios']['S0']
    repeated = json.loads((bench / 'reproduction-submission.json').read_text())['scenarios'][replay['id']]
    assert triples(original) == triples(repeated)
    (bench / 'reproducibility.json').write_text(json.dumps({'passed': True, 'changed_scenario_id': True,
        'hash_seeds': [0, 991]}, indent=2) + '\n')
assert hashes() == before
(bench / 'code-sha256.json').write_text(json.dumps(before, indent=2) + '\n')
report = json.loads(report_path.read_text())
evaluation = json.loads((bench / 'evaluation.json').read_text())
summary = {'variant': 9, 'score_S0': evaluation['score'],
    'beats_variant_5_S0': evaluation['score'] > 0.9260149572649572,
    'iou': {k: v['iou'] for k, v in evaluation['scenarios']['S0']['sets'].items()},
    'elapsed_seconds': report['elapsed_seconds'], 'preparation_seconds': report['preparation_seconds'],
    'analysis_seconds': report['analysis_seconds'], 'peak_rss_bytes': report['peak_rss_bytes'],
    'submission_sha256': report['submission_sha256'], 'runtime_model_calls': len(report['model_calls']),
    'run_complete': report['run_complete'], 'scenarios': report['requested_scenarios'],
    'environment': report['environment']}
(bench / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, ensure_ascii=False), flush=True)
