"""Independent exact graph/state checker. Never imported by inference."""
from copy import deepcopy
from datetime import datetime
import json

RELATIONS=('executes','calls','remote','data')
INTERNAL={'__type__','__http_entity__','__resource__','__orm_provider__','__orm_state__'}


def unknown(value):
    if isinstance(value,dict):
        return value.get('unknown') is True or value.get('knowledge')=='unknown' or any(unknown(v) for v in value.values())
    return isinstance(value,list) and any(unknown(v) for v in value)


def payload(value):
    if isinstance(value,dict) and value.get('__http_entity__') is True:return value.get('body')
    return value


def public(value):
    if isinstance(value,dict):return {k:public(v) for k,v in value.items() if k not in INTERNAL}
    if isinstance(value,list):return [public(v) for v in value]
    return value


def typed_key(value):
    return json.dumps([type(value).__name__,value],sort_keys=True,ensure_ascii=True,separators=(',',':'))


def match(wanted,actual,identities):
    if unknown(actual):return False
    if isinstance(wanted,dict) and '$identity' in wanted:
        expected=identities.get(wanted['$identity'])
        return expected is not None and typed_key(actual)==typed_key(expected)
    if isinstance(wanted,dict) and '$native' in wanted:
        if wanted['$native']=='LocalDateTime':
            if not isinstance(actual,str):return False
            try:datetime.fromisoformat(actual);return 'T' in actual
            except ValueError:return False
        if wanted['$native']=='DefaultSpringErrorBody':return isinstance(actual,dict) and actual.get('status')==wanted['status']
        if wanted['$native']=='FeignExceptionMessage':
            if not isinstance(actual,dict) or actual.get('__type__')!='String' or 'non_null' not in actual.get('__constraints__',[]):return False
            fact=actual.get('__feign_error_message__',{})
            return (fact.get('model_version')=='feign-default-error-message/1' and fact.get('exact_text') is False
                and fact.get('status')==wanted['response']['status'] and isinstance(fact.get('client_method'),str)
                and fact['client_method'].startswith('method:') and fact.get('request_id',0)>1
                and fact.get('request',{}).get('method')=='GET' and match(wanted['response'],fact.get('response_body'),identities))
        return False
    if isinstance(wanted,dict) and '$text' in wanted:
        from semantic_wire_checker33 import text_match
        return text_match(wanted['$text'],actual,identities)
    if isinstance(wanted,dict):
        return isinstance(actual,dict) and set(wanted)==set(public(actual)) and all(match(v,actual[k],identities) for k,v in wanted.items())
    if isinstance(wanted,list):return isinstance(actual,list) and len(wanted)==len(actual) and all(match(a,b,identities) for a,b in zip(wanted,actual))
    return type(wanted) is type(actual) and wanted==actual


def table_rows(wanted,actual,identities):
    if not isinstance(actual,list) or len(wanted)!=len(actual):return False
    remaining=list(actual)
    for row in wanted:
        found=next((i for i,item in enumerate(remaining) if match(row,item,identities)),None)
        if found is None:return False
        remaining.pop(found)
    return True


def state_matches(wanted,actual,identities):
    return not actual.get('unknown_tables') and set(wanted)==set(actual.get('tables',{})) and all(
        table_rows(rows,actual['tables'][table],identities) for table,rows in wanted.items())


def graph_metrics(wanted,actual):
    result={}
    for relation in RELATIONS:
        gold={(e['source'],e['target']) for e in wanted if e['relation']==relation}
        observed={(e['source'],e['target']) for e in actual if e['relation']==relation}
        tp,fp,fn=len(gold&observed),len(observed-gold),len(gold-observed)
        result[relation]={'tp':tp,'fp':fp,'fn':fn,'iou':tp/(tp+fp+fn) if tp+fp+fn else 1.0,
            'missing':[list(e) for e in sorted(gold-observed)],'extra':[list(e) for e in sorted(observed-gold)]}
    return result


def outgoing_requests(alternative):
    # Request 1 is the external client input, not an outbound application call.
    return [r for r in alternative.get('requests',[]) if r.get('id',0)>1 and r.get('request') is not None]


def write_policy(wanted,alternative):
    actual=[o for o in alternative.get('data_operations',[]) if o.get('datastore_event') is True
            and o.get('sql_emitted') is True and o['operation'].startswith(('save','insert','delete','update'))]
    expected=[{'method':o['method'],'resource':o['table'],'operation':o['operation']}
              for o in wanted.get('operations',[]) if o.get('writes')]
    if wanted.get('producer') and not expected:
        # The frozen creation cases use one repository.save and one data edge.
        # An ambiguous producer effect is not evidence of a write.
        sites={(e['source'],e['target']) for e in wanted['edges'] if e['relation']=='data'}
        if len(sites)!=1:return False
        method,resource=next(iter(sites))
        expected=[{'method':method,'resource':resource,'operation':'save'}]
    return len(actual)==len(expected) and all(not found.get('uncertain_write') and
        all(found.get(key)==value for key,value in spec.items()) for spec,found in zip(expected,actual))


def bind_producer(expected,alternatives,identities,initial):
    producer=expected.get('producer')
    if not producer:return True
    if not alternatives or any(a['outcome']!='returned' or a.get('exploration',{}).get('complete') is not True for a in alternatives):return False
    found=[]
    for alternative in alternatives:
        actual=payload(alternative['result'])
        for part in producer['response_path']:
            if not isinstance(actual,dict) or part not in actual:return False
            actual=actual[part]
        if unknown(actual) or actual is None:return False
        tables=[table for table,rows in expected['tables'].items() if any(isinstance(row.get('id'),dict) and row['id'].get('$identity')==producer['identity'] for row in rows)]
        excluded=[row['id'] for table in tables for row in initial[table]]
        if type(actual) is int:
            if actual in excluded or not -(2**63)<=actual<2**63:return False
        elif isinstance(actual,dict) and actual.get('__symbol__') and actual.get('__type__') in ('Long','long','java.lang.Long'):
            if 'non_null' not in actual.get('__constraints__',[]) or not set(excluded)<=set(actual.get('__distinct_from__',[])):return False
        else:return False
        found.append(actual)
    if any(typed_key(item)!=typed_key(found[0]) for item in found[1:]):return False
    identities[producer['identity']]=deepcopy(found[0])
    return True


def evaluate_case(case,actual,initial,witness=None):
    identities={};checks=[]
    for number,wanted in enumerate(case['steps'],1):
        step=actual['steps'][number-1];alternatives=step['alternatives']
        observed=[e for a in alternatives for e in a['edges']]
        metrics=graph_metrics(wanted['edges'],observed)
        conditions={'graph_exact':all(row['fp']==row['fn']==0 for row in metrics.values())}
        if wanted.get('refusal'):
            conditions.update(refused=not alternatives,state_exact=state_matches(wanted['tables'],step['state_after'],identities))
        else:
            conditions['producer']=bind_producer(wanted,alternatives,identities,initial)
            conditions.update(handler=bool(alternatives) and all(a['entry']==wanted['entry'] for a in alternatives),
                complete=bool(alternatives) and all(a.get('exploration',{}).get('complete') is True for a in alternatives),
                status=bool(alternatives) and all(any(r['request']==1 and r['status']==wanted['status'] for r in a.get('responses',[])) for a in alternatives),
                result=bool(alternatives) and all(match(wanted['result'],payload(a['result']),identities) for a in alternatives),
                state_exact=bool(alternatives) and all(state_matches(wanted['tables'],a['state_after'],identities) for a in alternatives))
            conditions['write_policy']=bool(alternatives) and all(write_policy(wanted,a) for a in alternatives)
            # A matching edge does not prove that a remote message was sent.
            conditions['remote_count']=bool(alternatives) and all(len(outgoing_requests(a))==len(wanted.get('remote_requests',[])) for a in alternatives)
            conditions['graph_each_alternative']=bool(alternatives) and all(all(row['fp']==row['fn']==0
                for row in graph_metrics(wanted['edges'],a['edges']).values()) for a in alternatives)
            if witness is not None:
                from semantic_wire_checker33 import evaluate_wire
                values=[evaluate_wire(witness[number-1],a,actual['steps'][:number-1],identities,match) for a in alternatives]
                for key in ('outer_wire','remote_wire_and_response','native_binding','ordered_sql','history_origin','error_message_origin'):
                    conditions[key]=bool(values) and all(row[key] for row in values)
        checks.append({'step':number,'passed':all(conditions.values()),'checks':conditions,'relations':metrics,
            'outcomes':[a['outcome'] for a in alternatives],
            'first_losses':[a.get('knowledge_losses',[])[:1] for a in alternatives],
            'full_graph_oracle':True,'full_persistent_rows_oracle':True,
            'value_limits':wanted.get('value_limits',[])})
    return {'passed':all(row['passed'] for row in checks),'steps':checks,'identities':identities,
        'full_semantic_transfer_verified':False,
        'limitation':'Exact graph/state checks are independent; typed wire/order/origin and partial framework error-value witnesses require additional checks before a full semantic claim.'}
