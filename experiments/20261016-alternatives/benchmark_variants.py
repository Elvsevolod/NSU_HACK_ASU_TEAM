"""Run builders under their offline guard, then evaluate in separate processes."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path('/private/tmp/nsu-alternatives-venv/bin/python')
NAMES = ('—_evidence-contract-grounding', '—_predicate-state-analysis')
ENV = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0'}


def run(command, out, err, codes=(0,), env=None):
    with out.open('w') as stdout, err.open('w') as stderr:
        result = subprocess.run([str(x) for x in command], cwd=ROOT, env=env or ENV,
                                stdout=stdout, stderr=stderr, check=False)
    if result.returncode not in codes:
        raise RuntimeError(str(command) + ': ' + str(result.returncode) + '; see ' + str(err))


def builder(variant, output, report, extra=(), scenarios=None, seed='0'):
    return run([PYTHON, '-B', variant / 'code/offline_run.py',
        '--source', ROOT / 'tt-challenge/targets/trainticket',
        '--skeleton', ROOT / 'tt-challenge/skeleton/trainticket.json.gz',
        '--context', ROOT / 'tt-challenge/context',
        '--scenarios', scenarios or ROOT / 'tt-challenge/scenarios',
        '--output', output, '--report', report, *extra],
        report.with_suffix('.stdout.txt'), report.with_suffix('.stderr.txt'),
        env={**ENV, 'PYTHONHASHSEED': seed})


def code_hashes(variant):
    return {p.relative_to(variant).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((variant / 'code').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


summaries = []
for name in NAMES:
    variant = ROOT / 'solutions' / name
    bench = variant / 'benchmark'
    if sys.argv[1:] and name not in sys.argv[1:]:
        summaries.append(json.loads((bench / 'summary.json').read_text()))
        continue
    before = code_hashes(variant)
    builder(variant, variant / 'submission.json', bench / 'analysis-report.json')
    run([PYTHON, '-B', '-m', 'pytest', variant / 'code/tests', '-q', '-p', 'no:cacheprovider',
         '--junitxml', bench / 'pytest.xml'], bench / 'tests.txt', bench / 'tests.stderr.txt',
        env={**ENV, 'PYTHONPATH': str(variant / 'code')})
    for label, reference in [('evaluation', [ROOT / 'tt-challenge/gold/S0.json']),
                             ('format_check', ['--check', ROOT / 'tt-challenge/skeleton/trainticket.json.gz'])]:
        run([PYTHON, '-B', ROOT / 'tt-challenge/platform/evaluate_golden.py', *reference,
             variant / 'submission.json', '--json'], bench / (label + '.json'), bench / (label + '.stderr.txt'), (0, 3))
        result = json.loads((bench / (label + '.json')).read_text())
        assert not result['errors']
        assert all(not block.get('rejected') and not block.get('duplicates') for block in result['scenarios'].values())
    run([PYTHON, '-B', variant / 'code/verify_run.py', '--submission', variant / 'submission.json',
         '--report', bench / 'analysis-report.json', '--output', bench / 'verification.json'],
        bench / 'verification.stdout.txt', bench / 'verification.stderr.txt')
    run([PYTHON, '-B', variant / 'code/check_generalization.py', '--directory', bench],
        bench / 'generalization.stdout.txt', bench / 'generalization.stderr.txt')
    checks = variant / 'checks'
    checks.mkdir(exist_ok=True)
    scenario = json.loads((ROOT / 'tt-challenge/scenarios/S0.json').read_text())
    scenario['id'] = 'replay-arbitrary-name'
    (checks / 'replay.json').write_text(json.dumps(scenario, indent=2) + '\n')
    builder(variant, bench / 'reproduction-submission.json', bench / 'reproduction-report.json',
            scenarios=checks / 'replay.json', seed='991')
    answer = json.loads((variant / 'submission.json').read_text())
    replay = json.loads((bench / 'reproduction-submission.json').read_text())
    def normalize(block):
        return {('scenario' if e['relation'] == 'executes' else e['source'], e['relation'], e['target']) for e in block['edges']}
    assert normalize(answer['scenarios']['S0']) == normalize(replay['scenarios']['replay-arbitrary-name'])
    assert before == code_hashes(variant), 'Source changed during benchmark'
    (bench / 'code-sha256.json').write_text(json.dumps(before, indent=2) + '\n')
    (bench / 'reproducibility.json').write_text(json.dumps({'passed': True,
        'scope': 'all S0 edges with changed identifier and PYTHONHASHSEED', 'seeds': [0, 991]}, indent=2) + '\n')
    report = json.loads((bench / 'analysis-report.json').read_text())
    evaluation = json.loads((bench / 'evaluation.json').read_text())
    summary = {'variant': name, 'score_S0': evaluation['score'],
        'iou': {key: value['iou'] for key, value in evaluation['scenarios']['S0']['sets'].items()},
        'elapsed_seconds': report['elapsed_seconds'], 'preparation_seconds': report['preparation_seconds'],
        'analysis_seconds': report['analysis_seconds'], 'peak_rss_bytes': report['peak_rss_bytes'],
        'submission_sha256': report['submission_sha256'], 'model_calls': len(report['model_calls']),
        'requested_scenarios': report['requested_scenarios'], 'run_complete': report['run_complete'],
        'scenarios': {sid: {'status': block['analysis_status'], 'steps': len(block['steps']),
            'steps_without_request': sum(not s['alternatives'] for s in block['steps']),
            'steps_with_unknown_input': sum(any(any(w.startswith('Unknown input: ') for w in a['unresolved']) for a in s['alternatives']) for s in block['steps']),
            'confirmed': len(block['confirmed']), 'possible': len(block['possible'])} for sid, block in report['scenarios'].items()},
        'environment': report['environment']}
    (bench / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    summaries.append(summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('scenarios', 'environment')}, ensure_ascii=False), flush=True)

variant = ROOT / 'solutions' / NAMES[1]
builder(variant, variant / 'benchmark/ablation-submission.json', variant / 'benchmark/ablation-report.json',
        extra=['--no-constraints'])
parent_bytes = (ROOT / 'solutions' / NAMES[0] / 'submission.json').read_bytes()
ablation = (variant / 'benchmark/ablation-submission.json').read_bytes()
assert ablation == parent_bytes, 'Disabled constraints must reproduce variant 7 byte for byte'
comparison = {'disabled_constraints_reproduce_parent_bytes': True, 'variants': summaries}
left, right = [json.loads((ROOT / 'solutions' / name / 'submission.json').read_text()) for name in NAMES]
comparison['edge_changes'] = {}
for sid in left['scenarios']:
    def triples(block):
        return {(e['source'], e['relation'], e['target']) for e in block['edges']}
    a, b = triples(left['scenarios'][sid]), triples(right['scenarios'][sid])
    comparison['edge_changes'][sid] = {'added': len(b - a), 'removed': len(a - b)}
(ROOT / 'experiments/20261016-alternatives/comparison.json').write_text(json.dumps(comparison, indent=2) + '\n')
(variant / 'benchmark/ablation-check.json').write_text(json.dumps(comparison, indent=2) + '\n')
print(json.dumps({'ablation_passed': True, 'edge_changes': comparison['edge_changes']}), flush=True)
