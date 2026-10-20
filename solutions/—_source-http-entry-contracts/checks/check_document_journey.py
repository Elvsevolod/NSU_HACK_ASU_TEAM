"""Strict document checks, including wire, actual DTOs, all stored fields and diagnostics."""
from evidence import equal,payload,bound_equal


def classify(messages):
    result=[]
    for message in messages:
        if message.startswith('JSON payload projection is not proven complete for codec failures:'):result.append('codec_payload_projection')
        elif message.startswith('State depends on earlier analysis assumptions:'):result.append('prior_analysis_assumption')
        else:result.append(message)
    return sorted(result)


def check(rows,oracle,mode):
    results=[]
    if len(rows)!=3:return {'passed':False,'reason':'step count'}
    for index,(row,wanted) in enumerate(zip(rows,oracle['steps'])):
        request=row.get('wire',row.get('request',{}));wire=wanted['wire'][mode]
        actual_graph={tuple(e) if isinstance(e,(list,tuple)) else ('' if e['relation']=='executes' else e['source'],e['relation'],e['target']) for e in row['edges']}
        requests=row['requests'];arguments=[payload(r.get('bound_arguments',[])) for r in requests]
        dto_types=all(argument['value'].get('__type__')==argument['declared_type'] for r in requests
                      for argument in r.get('bound_arguments',[]) if isinstance(argument.get('value'),dict) and argument['declared_type']=='Approval')
        remote=[{k:r['request'].get(k) for k in ('method','url','body','query','headers')} for r in requests[1:]]
        state=payload(row['state_after'])
        checks={'wire':all(equal(wire[k],request.get(k)) for k in wire),
            'actual_arguments':dto_types and len(wanted['arguments'])==len(arguments) and all(bound_equal(actual,expected) for actual,expected in zip(arguments,wanted['arguments'])),
            'remote_wire':equal(wanted['remote_wire'],remote),
            'request_entries':equal(wanted['entries'],[r['entry'] for r in requests]),
            'result':equal(wanted['result'],payload(row['result'])),
            'state':equal(wanted['state'][mode],state),
            'status':equal(wanted['statuses'],[[r['request'],r['status']] for r in row['responses']]),
            'diagnostics':equal(wanted['diagnostics'][mode],classify(row.get('diagnostics',row.get('unresolved',[])))),
            'effects':not row.get('call_effects',[]),
            'graph':actual_graph=={tuple(e) for e in wanted['edges']}}
        results.append({'n':index+1,**checks})
    return {'passed':all(all(v for k,v in r.items() if k!='n') for r in results),'steps':results}
