"""Strict post-hoc checker. Only this process may read the frozen oracle."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import argparse
import hashlib
import json


def normal(value):
    if isinstance(value,list):return [normal(child) for child in value]
    if not isinstance(value,dict):return value
    if '$decimal' in value:return Decimal(value['$decimal'])
    if '__enum__' in value:return value.get('name',value['__enum__'].rsplit('.',1)[-1])
    return {key:normal(child) for key,child in value.items() if not key.startswith('__')}


def equal(expected,actual):
    if isinstance(expected,dict) and expected.get('$unknown') is True:
        return isinstance(actual,dict) and (actual.get('__symbol__')==expected['symbol_id'] if 'symbol_id' in expected else actual=={'unknown':True} or '__symbol__' in actual)
    if isinstance(expected,dict) and '$encoded_from' in expected:
        return isinstance(actual,dict) and actual.get('__encoded_from__')==expected['$encoded_from'] and \
            actual.get('__type__')=='String' and 'non_null' in actual.get('__constraints__',[]) and \
            actual.get('__encoding_contract__','').endswith('BCryptPasswordEncoder')
    if isinstance(expected,dict) and '$instant' in expected:
        return isinstance(actual,dict) and actual.get('$instant')==expected['$instant']
    if isinstance(expected,dict) and '$missing' in expected:return actual=={'missing':True}
    if isinstance(expected,dict):
        if not isinstance(actual,dict):return False
        if '__enum__' in actual:return normal(actual)==expected
        keys={key for key in actual if not key.startswith('__')}
        return keys==set(expected) and all(equal(value,actual[key]) for key,value in expected.items())
    if isinstance(expected,list):return isinstance(actual,list) and len(expected)==len(actual) and all(equal(a,b) for a,b in zip(expected,actual))
    if isinstance(actual,dict) and '$decimal' in actual:
        return type(expected) in (int,float) and Decimal(str(expected))==Decimal(actual['$decimal'])
    if isinstance(actual,dict) and '__enum__' in actual:return expected==normal(actual)
    return type(expected) is type(actual) and expected==actual


def typed_value(typ,value):
    """Check runtime kinds, including nested DTO/enum module identity."""
    if value is None:return typ not in ('boolean','byte','short','int','long','float','double','char')
    if isinstance(value,dict) and '__symbol__' in value:return value.get('__type__')==typ
    base=typ.split('<',1)[0]
    if base in ('String','java.lang.String'):return isinstance(value,str) or isinstance(value,dict) and value.get('__type__') in ('String','java.lang.String')
    if base in ('boolean','Boolean','java.lang.Boolean'):return type(value) is bool
    if base in ('int','Integer','java.lang.Integer','long','Long','java.lang.Long'):return type(value) is int
    if base=='java.math.BigDecimal':return isinstance(value,dict) and '$decimal' in value
    if base=='java.util.Date':return isinstance(value,dict) and '$instant' in value
    if base in ('java.util.List','java.util.Collection','java.util.Set'):
        item=typ.split('<',1)[1][:-1] if '<' in typ else None
        return isinstance(value,list) and (item is None or all(typed_value(item,child) for child in value))
    return isinstance(value,dict) and (value.get('__type__')==typ or value.get('__enum__','').rsplit('.',1)[0]==typ)


def arguments(expected,actual):
    if len(expected)!=len(actual):return False
    for a,b in zip(expected,actual):
        if a['name']!=b['name'] or a['declared_type']!=b['declared_type'] or not equal(a['value'],b['value']):return False
        value=b['value']
        if not typed_value(a['declared_type'],value):return False
        if any(not typed_value(typ,value.get(field)) for field,typ in a.get('field_types',{}).items()):return False
        for field,types in a.get('nested_field_types',{}).items():
            nested=value.get(field)
            if nested is not None and any(not typed_value(typ,nested.get(key)) for key,typ in types.items()):return False
    return True


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--oracle',type=Path,required=True);parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--trace',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists()
    digest=hashlib.sha256(args.oracle.read_bytes()).hexdigest();oracle=json.loads(args.oracle.read_text())
    trace=json.loads(args.trace.read_text());graph=json.loads((args.input/'skeleton.json').read_text())
    symbols={}
    for symbol,declaration in oracle['method_symbols'].items():
        matches=[mid for mid,meta in graph['nodes'].items() if meta['kind']=='method' and meta['module']==declaration['module'] and
            graph['nodes'][meta['owner']]['fqn']==declaration['owner_fqn'] and meta['name']==symbol.rsplit('.',1)[-1] and
            meta['line']<=declaration['declaration_line']<=meta['end']]
        assert len(matches)==1,(symbol,matches)
        symbols[matches[0]]=symbol
    def method(value):return symbols.get(value,value)
    def edges(row):
        result={relation:set() for relation in ('executes','calls','remote','data')}
        for source,relation,target in row['edges']:
            if relation=='executes':result[relation].add(method(target))
            elif relation=='data':
                resource=graph['nodes'][target]
                result[relation].add((method(source),resource['schema']+'.'+resource['name']))
            else:result[relation].add((method(source),method(target)))
        return result
    results=[]
    for expected,observed in zip(oracle['steps'],trace['steps']):
        requests=observed['requests'];responses=observed['responses'];first_request=requests[0] if requests else {}
        response=next((item for item in reversed(responses) if item['request']==1),{})
        request=observed['request'];wire=expected['wire']
        checks={'wire':request['method']==wire['method'] and request['url']==wire['path'] and request['query']==wire['query'] and
            equal(wire['headers'],request['headers']) and equal(wire['body'],request['body']),
            'identity':equal(oracle['preconditions']['authentication_boundary']['contexts'][expected['identity_context']],request['session']),
            'handler':len(observed['candidates'])==1 and method(observed['candidates'][0])==expected['route_candidate'] and response.get('entered')==expected['handler_entered'],
            'status':response.get('status')==expected['status'],
            'request_observed':bool(requests),
            'bound_arguments':arguments(expected['bound_arguments'],first_request.get('bound_arguments',[])) if expected['handler_entered'] else None,
            'rejected_before_handler':None if expected['handler_entered'] else bool(requests) and 'bound_arguments' not in first_request,
            'state':set(observed['tables'])==set(expected['state']) and not observed['unknown_tables']}
        if checks['state']:
            for table,records in expected['state'].items():
                actual=observed['tables'][table]
                key='username' if table.endswith('.users') else 'name' if table.endswith('.accounts') else 'id'
                checks['state'] &= len(records)==len(actual) and all(any(equal(record,row) for row in actual) for record in records)
        expected_operations=[event for event in expected['events'] if event['kind']=='persistence']
        actual_operations=observed.get('data_operations',[])
        checks['data_operation_sequence']=len(expected_operations)==len(actual_operations)
        for wanted,found in zip(expected_operations,actual_operations):
            resource=graph['nodes'][found['resource']]
            matching=method(found['method'])==wanted['source_method'] and resource['schema']+'.'+resource['name']==wanted['collection'] and \
                found['operation']==wanted['operation'] and found.get('datastore_event') is True and found.get('uncertain_write') is False
            values=found.get('arguments',[])
            matching &= bool(values) and (equal(wanted['record'],values[0]) if 'record' in wanted else equal(wanted['key'],values[0]))
            if wanted.get('completed'):matching &= found.get('transactional') is False
            checks['data_operation_sequence'] &= matching
        body=expected['response_body']
        if observed.get('path_consistency'):
            checks['path_consistency']=observed['path_consistency']['all_observables_identical']
        unmeasured=bool(isinstance(body,dict) and ('$unmeasured' in body or '$error_body_not_a_source_contract' in body))
        if body=={'$empty':True}:checks['response_body']=response.get('body_presence')=='empty' and observed['result'] is None
        elif unmeasured:checks['response_body']=None
        else:checks['response_body']=equal(body,observed['result'])
        actual_edges=edges(observed);differences={}
        for relation in actual_edges:
            wanted={tuple(item) if isinstance(item,list) else item for item in expected['edges'][relation]}
            found=actual_edges[relation]
            checks['edges_'+relation]=wanted==found
            differences[relation]={'missing':sorted(wanted-found),'extra':sorted(found-wanted)}
        remote=expected.get('remote_requests',[]);actual_remote=requests[1:]
        checks['remote_requests']=len(remote)==len(actual_remote)
        remote_results=[]
        for wanted,found in zip(remote,actual_remote):
            item=found['request'];reply=next((item for item in responses if item['request']==found['id']),{})
            matching={'handler':method(found['entry'])==wanted.get('route_candidate',wanted['handler']),
                'wire':item['method']==wanted['method'] and item['url'].split('://',1)[-1].split('/',1)[-1]==wanted['path'].lstrip('/') and
                    item['query']==wanted['query'] and equal(wanted['headers'],item['headers']) and equal(wanted['body'],item['body']),
                'identity':equal(oracle['preconditions']['authentication_boundary']['contexts'][wanted['identity_context']],
                    {key:item['session'].get(key) for key in ('authenticated','principal','authorities','oauth2_request')}),
                'status':reply.get('status')==wanted['status'] and reply.get('entered')==wanted['entered'],
                'arguments':arguments(wanted['bound_arguments'],found.get('bound_arguments',[])) if wanted['entered'] else None,
                'rejected_before_handler':None if wanted['entered'] else 'bound_arguments' not in found}
            if 'binding_candidate_arguments' in wanted:matching['rejected_candidate']=arguments(wanted['binding_candidate_arguments'],found.get('binding_candidate_arguments',[]))
            if wanted.get('response_body')=={'$empty':True}:matching['response_body']=reply.get('body_presence')=='empty'
            if wanted.get('fallback'):
                fallback=found.get('fallback',{})
                matching['fallback']=method(fallback.get('entry'))==wanted['fallback']['method'] and arguments(wanted['fallback']['arguments'],fallback.get('bound_arguments',[]))
            remote_results.append(matching);checks['remote_requests'] &= all(value is not False for value in matching.values())
        results.append({'n':expected['n'],'checks':checks,'passed':all(value is not False for value in checks.values()),'edges':differences,
            'remote':remote_results,'unmeasured_fields':[body] if unmeasured else []})
    passed=len(results)==len(oracle['steps'])==len(trace['steps']) and all(row['passed'] for row in results)
    output={'oracle_sha256':digest,'trace_sha256':hashlib.sha256(args.trace.read_bytes()).hexdigest(),'passed':passed,
        'steps':results,'ignored_payloads_count_as_checked':False,'oracle_available_to_inference':False,
        'limits':['Post-auth business slice only; OAuth issuance/verification excluded','Additional required cases have separate frozen inputs and checks']}
    args.output.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'passed':passed,'failed':{row['n']:[key for key,value in row['checks'].items() if value is False] for row in results if not row['passed']}}))
    raise SystemExit(0 if passed else 1)


if __name__=='__main__':main()
