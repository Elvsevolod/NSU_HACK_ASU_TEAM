"""Check the exported graph against its explanations without a reference answer."""
import argparse
from collections import Counter
import json
from pathlib import Path


def edges(items):
    result = {(e['source'], e['relation'], e['target']) for e in items}
    assert len(result) == len(items), 'Duplicate exported edges'
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    answer = json.loads(args.submission.read_text())
    report = json.loads(args.report.read_text())
    assert set(answer['scenarios']) == set(report['scenarios'])
    summary = {}
    for sid, block in answer['scenarios'].items():
        detail = report['scenarios'][sid]
        exported = edges(block['edges'])
        confirmed, possible = edges(detail['confirmed']), edges(detail['possible'])
        policy=detail.get('graph_policy','observed-union')
        assert not confirmed & possible
        assert exported == (confirmed if policy=='confirmed' else confirmed | possible)
        evidence = {tuple(item['edge'][k] for k in ('source', 'relation', 'target')): item['grounds']
                    for item in detail['evidence']}
        assert set(evidence) == confirmed | possible, 'Every observed edge needs its grounds'
        steps = {s['n']: s for s in detail['steps']}
        alternative_edges = {}
        event_edges=set()
        conditional_events=0
        for step in detail['steps']:
            for alternative in step['alternatives']:
                requests={request['id'] for request in alternative.get('requests',[])}
                for event in alternative.get('events',[]):
                    event_edge=next(iter(edges([event['edge']])))
                    event_edges.add(event_edge)
                    assert event_edge in edges(alternative['edges'])
                    assert event.get('callsite') and event.get('cause')
                    assert isinstance(event.get('values'),dict),'Every event needs argument facts or request provenance'
                    assert event['request'] is None or event['request'] in requests
                    assert event['values'].get('target_request') is None or event['values']['target_request'] in requests
                    context=alternative['event_contexts'][event['context']]
                    assert set(context['assumptions']) <= alternative['assumptions'].keys()
                    conditional_events+=bool(context['assumptions'] or any(guard.get('assumed') for guard in context['guards']))
                    if event_edge[1]=='data':assert event['cause'] in ('sql','datastore')
                # Static closure is diagnostic; it cannot be the sole witness.
                assert edges(alternative['edges']) <= {next(iter(edges([event['edge']]))) for event in alternative.get('events',[])}
        assert confirmed | possible == event_edges
        for edge, grounds in evidence.items():
            assert grounds
            for ground in grounds:
                alternative = steps[ground['step']]['alternatives'][ground['alternative']]
                key = (ground['step'], ground['alternative'])
                if key not in alternative_edges:
                    alternative_edges[key] = edges(alternative['edges'])
                assert edge in alternative_edges[key]
                assert ground['source_sites'] and ground['source_locations'] and ground['applied_rules']
                assert ground['entry'] == alternative['entry']
        summary[sid] = {
            'status': detail['analysis_status'], 'graph_policy':policy,'conditional_events':conditional_events,'confirmed': len(confirmed), 'possible': len(possible),
            'relations': dict(Counter(e['relation'] for e in block['edges'])),
            'steps': len(detail['steps']),
            'steps_without_request': [s['n'] for s in detail['steps'] if not s['alternatives']],
            'steps_with_limits': [s['n'] for s in detail['steps'] if any(a['unresolved'] for a in s['alternatives'])],
            'unresolved_count': len(detail['unresolved'])}
    args.output.write_text(json.dumps({'passed': True, 'checks': [
        'same scenario sets', 'unique edges', 'confirmed/possible partition',
        'grounds for every edge', 'valid step and alternative references',
        'source locations and applied rules'], 'scenarios': summary}, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
