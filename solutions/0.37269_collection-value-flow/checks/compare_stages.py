"""Comparison-only witnesses; never imported by the answer builder."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

VARIANT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def read(stage):
    path = VARIANT / 'benchmark/stages' / stage / 'analysis-report.json.gz'
    return json.loads(gzip.decompress(path.read_bytes()))


def edges(step):
    return {(e['source'], e['relation'], e['target']) for a in step['alternatives'] for e in a['edges']}


def witness(step):
    return [{k: a.get(k) for k in ('entry', 'ui_site', 'request', 'requests', 'parameters',
             'bindings', 'result', 'state_after', 'outcome', 'data_operations')} for a in step['alternatives']]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('before'); parser.add_argument('after')
    args = parser.parse_args()
    before, after = read(args.before), read(args.after)
    rows = []
    for sid in before['scenarios']:
        for a, b in zip(before['scenarios'][sid]['steps'], after['scenarios'][sid]['steps']):
            ea, eb = edges(a), edges(b)
            av, bv = witness(a), witness(b)
            entries = lambda s: sorted({(v['entry'], v.get('ui_site')) for v in s['alternatives']})
            rows.append({'scenario': sid, 'step': a['n'], 'action': a['action'],
                'before_entries': entries(a), 'after_entries': entries(b),
                'entry_or_site_changed': entries(a) != entries(b),
                'before_witness_sha256': digest(av), 'after_witness_sha256': digest(bv),
                'relations': {k: {'before': sum(e[1] == k for e in ea), 'after': sum(e[1] == k for e in eb),
                    'added': sorted(e for e in eb-ea if e[1] == k),
                    'removed': sorted(e for e in ea-eb if e[1] == k)} for k in ('executes','calls','remote','data')}})
    output = VARIANT / 'benchmark/comparisons'
    output.mkdir(exist_ok=True)
    report = {'before': args.before, 'after': args.after, 'steps_compared': len(rows),
        'entry_or_site_changes': sum(row['entry_or_site_changed'] for row in rows), 'steps': rows,
        'witnesses': 'Full wire, bound arguments, results, state and events remain in each stage analysis-report.json.gz.'}
    (output / (args.before + '--' + args.after + '.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('steps','witnesses')}))


if __name__ == '__main__': main()
