"""Source-derived legacy state controls; no expected value comes from a prediction."""
import argparse,hashlib,json
from pathlib import Path
from evidence import equal,payload,chain
V=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--reports',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();assert not args.output.exists();rows=[];witnesses=[]
    for name in ('petclinic-customers','piggymetrics-account'):
        root=args.reports/name/'30';report=json.loads((root/'analysis-report.json').read_text());scenario=next(iter(report['scenarios'].values()))
        steps=[s['alternatives'][0] for s in scenario['steps']]
        assert all(len(s['alternatives'])==1 for s in scenario['steps'])
        oracle_path=V/'development/oracles/legacy-v2'/(name+'.oracle-v2.json');oracle=json.loads(oracle_path.read_text())
        graph=lambda edges:{tuple(e[k] for k in ('source','relation','target')) for e in edges}
        actual=graph(next(iter(json.loads((root/'submission.json').read_text())['scenarios'].values()))['edges'])
        expected=graph(oracle['edges']);checks=[]
        for i,(row,wanted) in enumerate(zip(steps,oracle['steps'])):
            first=row['requests'][0];response=next(r for r in row['responses'] if r['request']==1)
            values=payload(row['state_after']['tables']);wire=row['request']
            step={'n':i+1,'entry':row['entry']==wanted['endpoint'],'status':type(response['status']) is int and response['status']==wanted['status'],
                  'known_tables':not row['state_after']['unknown_tables']}
            if name=='petclinic-customers':
                old={'id':1,'firstName':'Joe','lastName':'Smith','address':'Main','city':'York','telephone':'12345'}
                updated={**old,'address':'Oak','city':'Leeds','telephone':'11223'}
                created={'firstName':'Eva','lastName':'Jones','address':'Elm','city':'York','telephone':'67890'}
                records=values['customers.owners'];original=[r for r in records if r.get('id')==1]
                step['existing_id_fields']=len(original)==1 and equal({k:original[0].get(k) for k in old},updated if i>=3 else old)
                step['counts']=len(records)==(1 if i==0 else 2) and values['customers.pets']==[] and values['customers.types']==[]
                if i>=1:
                    others=[r for r in records if isinstance(r.get('id'),dict) and '__symbol__' in r['id']]
                    identity=others[0]['id'] if len(others)==1 else {}
                    step['generated_id']=len(others)==1 and identity.get('__type__')=='Integer' and 'non_null' in identity.get('__constraints__',[]) and 1 in identity.get('__distinct_from__',[]) and equal(identity,steps[1]['result']['id'])
                    step['created_fields']=bool(others) and equal({k:others[0].get(k) for k in created},created)
                body=created if i==1 else {k:v for k,v in updated.items() if k!='id'} if i==3 else {'missing':True}
                method='POST' if i==1 else 'PUT' if i==3 else 'GET'
                url='/owners/1' if i in (3,4) else '/owners/invalid' if i==5 else '/owners'
                step['wire']=wire['method']==method and wire['url']==url and equal(wire['body'],body)
                bound=first.get('bound_arguments',[])
                if i==5:step['binding_rejection']=not response['entered'] and not bound
                elif i in (3,4):step['actual_id']=type(bound[0]['value']) is int and bound[0]['value']==1
                if i in (1,3):step['actual_dto']=equal(payload(bound[-1]['value']),body)
                if i==4:step['reread_fields']=equal(payload(row['result']),{**updated,'pets':[]})
            else:
                state={'account.accounts':[{'name':'demo','lastSeen':None,'incomes':None,'expenses':None,'saving':None,'note':'seed'}]}
                step['all_stored_fields']=equal(values,state)
                body={'username':'demo','password':'valid-password'} if i==1 else {'missing':True}
                step['wire']=wire['method']==('POST' if i==1 else 'GET') and wire['url']==('/' if i==1 else '/demo') and equal(wire['body'],body)
                step['arguments']=equal(payload(first['bound_arguments'][0]['value']),body if i==1 else 'demo')
                step['no_remote_or_write']=not any(e['relation']=='remote' for e in row['edges']) and not any(o['operation']=='save' for o in row['data_operations'])
            checks.append(step)
        rows.append({'fixture':name,'passed':actual==expected and all(all(v for k,v in r.items() if k!='n') for r in checks),
            'oracle_sha256':hashlib.sha256(oracle_path.read_bytes()).hexdigest(),'graph_exact':actual==expected,'steps':checks,
            'graph_precision_recall':{kind:{'tp':len({e for e in actual&expected if e[1]==kind}),'fp':len({e for e in actual-expected if e[1]==kind}),
              'fn':len({e for e in expected-actual if e[1]==kind})} for kind in ('executes','calls','remote','data')}})
        witnesses.append(chain(steps,name))
    args.output.write_text(json.dumps({'passed':all(r['passed'] for r in rows),'profiles':rows,'limits':['Legacy regression, not new holdout','Generated identifiers remain symbolic; no integer is guessed']},indent=2)+'\n')
    args.output.with_name('legacy-witnesses.json').write_text(json.dumps(witnesses,indent=2)+'\n')
    assert all(r['passed'] for r in rows),rows


if __name__=='__main__':main()
