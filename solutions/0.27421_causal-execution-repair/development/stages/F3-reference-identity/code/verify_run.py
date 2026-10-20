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
    parser.add_argument('--source',type=Path)
    parser.add_argument('--skeleton',type=Path)
    args = parser.parse_args()
    assert bool(args.source)==bool(args.skeleton),'Strict source checks require both source and skeleton'
    project=None
    if args.source:
        from analyzer.project import Project
        project=Project(args.skeleton,args.source)
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
                request_details={request['id']:request for request in alternative.get('requests',[])}
                observed_edges=edges(alternative['edges'])
                if project:
                    for request in request_details.values():
                        assert request['entry'] in project.methods
                        wire=request['request']
                        assert isinstance(wire,dict),'HTTP execution must preserve its immutable request'
                        assert 'headers' not in wire['headers'],'Aggregate HttpHeaders is not a header name'
                        if 'bound_arguments' in request:
                            assert len(request['bound_arguments'])==len(project.parameters(request['entry']))
                            assert ('scenario:'+sid,'executes',request['entry']) in observed_edges,'Entered request needs an execution prefix'
                            for expected,bound in zip(project.parameters(request['entry']),request['bound_arguments']):
                                assert bound['name']==expected[0] and 'value' in bound and bound['declared_type']
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
                    if project:
                        source,relation,target=event_edge
                        assert target in project.nodes
                        assert project.nodes[target]['kind']==('data_resource' if relation=='data' else 'method')
                        if relation=='executes':assert event['method']==target
                        else:assert source in project.methods
                        if relation=='remote':
                            target_request=event['values'].get('target_request')
                            assert target_request in request_details,'Remote edge needs its concrete target request'
                            request=request_details[target_request]
                            assert request['entry']==target and 'bound_arguments' in request
                            assert ('scenario:'+sid,'executes',target) in observed_edges
                            assert project.ix.unit_of(source)!=project.ix.unit_of(target)
                            assert all(response.get('entered') is True for response in alternative.get('responses',[]) if response['request']==target_request)
                        if relation=='calls' and event['callsite'] in project.nodes:
                            site=project.nodes[event['callsite']]
                            assert site['kind']=='call_site' and site['method']==source
                            assert site['callee']==project.methods[target]['name']
                        if relation=='data':
                            assert any(op['method']==source and op['resource']==target and op['source_site']==event['callsite']
                                       for op in alternative.get('data_operations',[])),'Data edge needs its observed operation'
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
    args.output.write_text(json.dumps({'passed': True,'validation_scope':'source/request-compatible witnesses' if project else 'structural witnesses only',
        'correctness_oracle_used':False,'semantic_accuracy_proven':False,'checks': [
        'same scenario sets', 'unique edges', 'confirmed/possible partition',
        'grounds for every edge', 'valid step and alternative references',
        'source locations and applied rules'], 'scenarios': summary}, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
