"""Check independent v3 callback values and v2-compatible semantic relations."""
import argparse
import hashlib
import json
from pathlib import Path
from check_real_journey import equal


def main():
    parser=argparse.ArgumentParser()
    for name in ('input','oracle','trace','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists()
    oracle=json.loads(args.oracle.read_text());trace=json.loads(args.trace.read_text())
    graph=json.loads((args.input/'skeleton.json').read_text())['nodes'];symbols={}
    for symbol,declaration in oracle['method_symbols'].items():
        matches=[mid for mid,meta in graph.items() if meta['kind']=='method' and meta['module']==declaration['module']
          and graph[meta['owner']]['fqn']==declaration['owner_fqn'] and meta['name']==symbol.rsplit('.',1)[-1]
          and meta['line']<=declaration['declaration_line']<=meta['end']]
        assert len(matches)==1
        symbols[matches[0]]=symbol
    method=lambda mid:symbols.get(mid,mid)
    def relations(edges):
        result={kind:set() for kind in ('executes','calls','remote','data')}
        for source,kind,target in edges:
            result[kind].add(method(target) if kind=='executes' else
                (method(source),graph[target]['schema']+'.'+graph[target]['name']) if kind=='data' else
                (method(source),method(target)))
        return result
    rows=[]
    expected_rows=oracle.get('steps',oracle.get('cases'))
    actual_rows=trace.get('steps',trace.get('cases'))
    assert len(expected_rows)==len(actual_rows),'All oracle rows must be present'
    for expected,actual in zip(expected_rows,actual_rows):
        semantic=[*actual['edges'],*(edge for edge in actual['reflection_edges']
          if graph[edge[2]]['kind']=='method' and graph[edge[2]].get('name')!='<init>' and
             (not edge[0] or graph.get(edge[0],{}).get('name')!='<init>'))]
        found=relations(semantic)
        checks={kind:found[kind]=={tuple(edge) if isinstance(edge,list) else edge for edge in expected['semantic_edges'][kind]}
            for kind in found}
        callbacks=list(actual.get('callbacks',[]));missing=[]
        for callback in expected['semantic_callbacks']:
            if not callback['role'].startswith('json_'):continue
            role='getter' if callback['role']=='json_serialization_getter' else 'setter'
            matches=[i for i,event in enumerate(callbacks) if method(event['method'])==callback['method'] and event['role']==role
                and event.get('completed_normally') is True
                and (event['declared_return']=='void' if callback.get('result')=={'$void':True} else equal(callback.get('result'),event.get('result')))
                and ('arguments' not in callback or equal(callback['arguments'],event['arguments']))]
            if matches:callbacks.pop(matches[0])
            else:missing.append(callback['callback_id'])
        checks['callback_values']=not missing and not callbacks
        rows.append({'id':expected.get('id',expected.get('n')),'checks':checks,'missing_callbacks':missing,
                     'extra_callbacks':[method(event['method']) for event in callbacks]})
    result={'passed':all(all(row['checks'].values()) for row in rows),'rows':rows,
        'oracle_sha256':hashlib.sha256(args.oracle.read_bytes()).hexdigest(),
        'contract':'v3 projected graph checked separately; semantic edges retain the exact v2 constructor exclusion'}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'failed':[row for row in rows if not all(row['checks'].values())]}))
    assert result['passed']


if __name__=='__main__':main()
