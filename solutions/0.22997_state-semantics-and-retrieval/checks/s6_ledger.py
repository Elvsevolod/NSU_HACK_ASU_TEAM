"""Historical comparison only: no input from this file reaches inference."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import shutil

VARIANT = Path(__file__).resolve().parents[1]
PARENT = VARIANT.parents[1] / 'solutions/0.37269_collection-value-flow'


def edges(step):
    return {(e['source'], e['relation'], e['target'])
            for alternative in step['alternatives'] for e in alternative['edges']}


def main():
    output = VARIANT / 'benchmark/overnight/G02/historical-evidence'
    output.mkdir(parents=True)
    reports = {}
    for name in ('base', 'C1-scalar-hashset'):
        source = PARENT / 'benchmark/stages' / name
        target = VARIANT / 'development/historical30' / name
        target.mkdir(parents=True)
        for file in ('submission.json', 'analysis-report.json.gz'):
            shutil.copy2(source / file, target / file)
        reports[name] = json.loads(gzip.decompress((target / 'analysis-report.json.gz').read_bytes()))
    reports['parent30'] = json.loads(gzip.decompress(
        (VARIANT / 'benchmark/stages/G01-parent30/analysis-report.json.gz').read_bytes()))
    comparisons = []
    for before, after in [('base', 'C1-scalar-hashset'), ('base', 'parent30')]:
        rows = []
        for sid, scenario in reports[before]['scenarios'].items():
            following = reports[after]['scenarios'][sid]
            assert len(scenario['steps']) == len(following['steps'])
            for a, b in zip(scenario['steps'], following['steps']):
                ea, eb = edges(a), edges(b)
                rows.append({'scenario': sid, 'step': a['n'], 'action': a['action'],
                             'added': sorted(eb - ea), 'removed': sorted(ea - eb),
                             'before': dict(Counter(e[1] for e in ea)),
                             'after': dict(Counter(e[1] for e in eb))})
        comparison = {'before': before, 'after': after, 'steps_compared': len(rows), 'steps': rows}
        (output / (before + '--' + after + '.json')).write_text(json.dumps(comparison, indent=2) + '\n')
        comparisons.append(comparison)
    s6_before = reports['base']['scenarios']['S6']['steps']
    s6_after = reports['parent30']['scenarios']['S6']['steps']
    previous = set().union(*(edges(s) for s in s6_before))
    following = set().union(*(edges(s) for s in s6_after))
    removed = previous - following
    assert len(removed) == 6 and not following - previous
    assert len(edges(s6_before[0]) - edges(s6_after[0])) == 12
    retained = edges(s6_before[0]) - edges(s6_after[0])
    assert retained <= edges(s6_after[6])
    origins = [{'stage': name, 'step': step['n'], 'alternative': index,
                'outcome': a['outcome'], 'affected_edges': sorted(removed & {
                    (e['source'], e['relation'], e['target']) for e in a['edges']}),
                'request': a['request'], 'parameters': a['parameters'],
                'state_unknown_tables': a['state_after']['unknown_tables'],
                'path_conditions': a['path_conditions']}
               for name, report in reports.items() for step in report['scenarios']['S6']['steps']
               for index, a in enumerate(step['alternatives'])
               if removed & {(e['source'], e['relation'], e['target']) for e in a['edges']}]
    first_unknown = {}
    for step in s6_after:
        for index, a in enumerate(step['alternatives']):
            for table in a['state_after']['unknown_tables']:
                first_unknown.setdefault(table, {'step': step['n'], 'alternative': index,
                    'outcome': a['outcome'], 'data_operations': a['data_operations'],
                    'request': a['request'], 'conditions': a['path_conditions']})
    ledger = {'schema': 'S6-causal-ledger/1', 'union_removed': sorted(removed),
              'union_added': sorted(following - previous),
              'step1_removed_but_retained_step7': sorted(retained),
              'historical_origins': origins, 'first_unknown_observations': first_unknown,
              'confirmed': ['Six union edges first disappear base→C1 at step8.',
                            'Twelve actor-login step1 removals remain in step7 union.',
                            'Every historical path containing removed converter edges is incomplete.'],
              'unresolved': ['Separate order-choice/completion reserve effects from consumer type loss.',
                             'Hidden gold is unavailable; individual edge correctness is not established.']}
    assert all(row['outcome'] == 'analysis completion budget exhausted' for row in origins)
    (output / 'causal-ledger.json').write_text(json.dumps(ledger, indent=2) + '\n')
    print(json.dumps({'comparisons': [c['steps_compared'] for c in comparisons],
                      'S6_union_removed': len(removed), 'step1_retained_step7': len(retained),
                      'first_unknown': {k: v['step'] for k, v in first_unknown.items()}}))


if __name__ == '__main__':
    main()
