"""Post-hoc acceptance of the independently reviewed real-source cases."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from check_real_journey import equal,arguments,typed_value


def main():
    parser=argparse.ArgumentParser()
    for key in ('input','oracle','trace','output'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists()
    oracle=json.loads(args.oracle.read_text());trace=json.loads(args.trace.read_text());graph=json.loads((args.input/'skeleton.json').read_text())
    symbols={}
    for symbol,declaration in oracle['method_symbols'].items():
        matches=[mid for mid,meta in graph['nodes'].items() if meta['kind']=='method' and meta['module']==declaration['module'] and
            graph['nodes'][meta['owner']]['fqn']==declaration['owner_fqn'] and meta['name']==symbol.rsplit('.',1)[-1] and
            meta['line']<=declaration['declaration_line']<=meta['end']]
        assert len(matches)==1,(symbol,matches)
        symbols[matches[0]]=symbol
    method=lambda value:symbols.get(value,value)
    def receiver(expected,path):
        match=re.fullmatch(r'initial_state\.(.+?)\[([^=]+)=([^\]]+)\](.*)',path)
        if not match:return None
        table,key,value,tail=match.groups();record=next(row for row in expected['initial_state'][table] if row[key]==value)
        for field,index in re.findall(r'\.([\w]+)|\[(\d+)\]',tail):record=record[field] if field else record[int(index)]
        return record
    results=[]
    for wanted,found in zip(oracle['cases'],trace['cases']):
        checks={'case':wanted['id']==found['id'],'state':equal(wanted['expected_state'],found['tables']) and not found['unknown_tables']}
        checks['state_types']=True
        for table,contract in wanted['state_native_types'].items():
            for row in found['tables'][table]:
                checks['state_types'] &= all(typed_value(typ,row.get(key)) for key,typ in contract['fields'].items())
                for path,nested in contract.items():
                    if not isinstance(nested,dict) or 'fields' not in nested:continue
                    values=row.get(path.removesuffix('.element'))
                    values=values if path.endswith('.element') and isinstance(values,list) else [] if values is None else [values]
                    checks['state_types'] &= all(typed_value(nested['entity_fqn'],item) and
                        all(typed_value(typ,item.get(key)) for key,typ in nested['fields'].items()) for item in values)
        actual={relation:set() for relation in ('executes','calls','remote','data')}
        for source,relation,target in found['edges']:
            actual[relation].add(method(target) if relation=='executes' else
                (method(source),graph['nodes'][target]['schema']+'.'+graph['nodes'][target]['name']) if relation=='data' else (method(source),method(target)))
        for relation,items in wanted['edges'].items():checks['edges_'+relation]=actual[relation]=={tuple(item) if isinstance(item,list) else item for item in items}
        if wanted['request'] is None:
            selection=found['selection'] or {}
            checks['ambiguity']=found['request'] is None and found['proposals']==0 and selection.get('grounding_status')=='unresolved_semantic_ambiguity' and \
                {method(mid) for mid in selection.get('semantic_candidates',[])}==set(wanted['expected_decision']['candidate_set'])
            checks['no_execution']=not any(found[key] for key in ('requests','responses','events','callbacks','data_operations'))
            checks['arguments']=None;checks['status']=None;checks['response']=None
        else:
            wire=wanted['request'];request=found['request'];reply=found['responses'][-1]
            checks['wire']=request['method']==wire['method'] and request['url']==wire['path'] and request['query']==wire['query'] and equal(wire['headers'],request['headers']) and equal(wire['body'],request['body'])
            checks['identity']=equal(wanted['identity']['context'],request['session'])
            checks['handler']=len(found['candidates'])==1 and method(found['candidates'][0])==wanted.get('route_candidate',wanted['handler']) and reply['entered']==wanted['handler_entered']
            checks['status']=reply['status']==wanted['status']
            if wanted['handler_entered']:
                checks['arguments']=arguments(wanted['bound_arguments'],found['requests'][0].get('bound_arguments',[]))
                checks['response']=equal(wanted['response_body'],found['result'])
            else:
                checks['arguments']=None;checks['response']=None
                checks['rejected_candidate']=arguments(wanted['binding_candidate_arguments'],found['requests'][0].get('binding_candidate_arguments',[]))
                checks['no_handler_arguments']='bound_arguments' not in found['requests'][0]
            expected_callbacks=[event for event in wanted['events'] if event['kind']=='framework_callback']
            expected_callbacks.extend(callback for event in wanted['events'] if event['kind']=='serialization_phase' for callback in event['callbacks'])
            observed_callbacks=list(found['callbacks']);matched=[]
            for callback in expected_callbacks:
                choices=[i for i,item in enumerate(observed_callbacks) if method(item['method'])==callback['method'] and
                    (item.get('declared_return')=='void' and item.get('completed_normally') is True if callback.get('result')=={'$void':True}
                     else equal(callback['result'],item['result']) if 'result' in callback else item['role']=='setter') and
                    ('arguments' not in callback or equal(callback['arguments'],item.get('arguments'))) and
                    (equal(receiver(wanted,callback['receiver_path']),item['receiver']) if callback.get('receiver_path','').startswith('initial_state.') else True)]
                if choices:matched.append(observed_callbacks.pop(choices[0]))
            checks['callbacks']=len(matched)==len(expected_callbacks) and not observed_callbacks
            checks['no_unexpected_remote']=len(found['requests'])==1
            checks['no_persistent_writes']=not any(item.get('operation') in ('save','insert','update','delete') for item in found['data_operations'])
        results.append({'id':wanted['id'],'checks':checks,'passed':all(value is not False for value in checks.values()),
            'unmeasured':[key for key,value in checks.items() if value is None]})
    passed=len(results)==len(oracle['cases'])==len(trace['cases']) and all(row['passed'] for row in results)
    args.output.write_text(json.dumps({'passed':passed,'oracle_sha256':hashlib.sha256(args.oracle.read_bytes()).hexdigest(),
        'trace_sha256':hashlib.sha256(args.trace.read_bytes()).hexdigest(),'oracle_available_to_inference':False,
        'unmeasured_fields_count_as_passed':False,'cases':results},indent=2)+'\n')
    print(json.dumps({'passed':passed,'failures':{row['id']:[key for key,value in row['checks'].items() if value is False] for row in results if not row['passed']}}))
    raise SystemExit(0 if passed else 1)


if __name__=='__main__':main()
