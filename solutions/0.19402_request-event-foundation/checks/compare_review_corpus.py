"""Run frozen controls and candidate against the same predeclared NL oracle."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

variant=Path(__file__).resolve().parents[1]
root=variant.parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--fixture',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
fixture=args.fixture.resolve();args.output.mkdir(parents=True,exist_ok=True)
oracle_path=fixture/'oracle.json'
oracle_digest=hashlib.sha256(oracle_path.read_bytes()).hexdigest()
oracle=json.loads(oracle_path.read_text())
edge_key=lambda edge:tuple(edge[key] for key in ('source','relation','target'))
gold={edge_key(edge) for edge in oracle['edges']}


def cleaned(value):
    if isinstance(value,dict):
        return {key:cleaned(child) for key,child in value.items() if not key.startswith('__')}
    if isinstance(value,list):return [cleaned(child) for child in value]
    return value


results=[]
for number,directory in [(5,'0.909870_field-constructor-projection'),(12,'0.748530_dom-state-flow'),
                         (23,'0.66185_lvalue-evaluation'),(26,'0.61822_json-bean-lifecycle'),
                         (27,variant.name)]:
    code=root/'solutions'/directory/'code'
    output=args.output/str(number);output.mkdir()
    launcher=code/'offline_run.py'
    command=[sys.executable,'-B',str(launcher)] if launcher.exists() else [sys.executable,'-B','-m','analyzer']
    command.extend(['--source',str(fixture),'--skeleton',str(fixture/'skeleton.json'),
        '--context',str(fixture/'initial.sql'),'--scenarios',str(fixture/'scenario.json'),
        '--output',str((output/'submission.json').resolve()),'--report',str((output/'analysis-report.json').resolve())])
    import os
    env=os.environ.copy();env['PYTHONPATH']=str(code)
    started=time.perf_counter()
    with (output/'stdout.txt').open('w') as stdout,(output/'stderr.txt').open('w') as stderr:
        try:
            process=subprocess.run(command,cwd=root,env=env,stdout=stdout,stderr=stderr,timeout=120)
            status={'returncode':process.returncode,'timed_out':False}
        except subprocess.TimeoutExpired:
            status={'returncode':None,'timed_out':True}
    row={'variant':number,**status,'wall_seconds':time.perf_counter()-started,'command':command,
         'oracle_sha256':oracle_digest,'relations':{},'steps':[]}
    if status['returncode']==0:
        answer=json.loads((output/'submission.json').read_text())
        report=json.loads((output/'analysis-report.json').read_text())
        actual={edge_key(edge) for edge in answer['scenarios']['review-journey']['edges']}
        for relation in ('executes','calls','remote','data'):
            wanted={edge for edge in gold if edge[1]==relation};found={edge for edge in actual if edge[1]==relation}
            tp,fp,fn=len(wanted&found),len(found-wanted),len(wanted-found)
            row['relations'][relation]={'tp':tp,'fp':fp,'fn':fn,'precision':tp/(tp+fp) if tp+fp else None,
                'recall':tp/(tp+fn) if tp+fn else None,'iou':tp/(tp+fp+fn) if tp+fp+fn else None,
                'nonempty_gold':bool(wanted)}
        row['graph_exact']=actual==gold
        for expected,observed in zip(oracle['steps'],report['scenarios']['review-journey']['steps']):
            alternatives=observed.get('alternatives',[observed])
            endpoints=bool(alternatives) and all(item['entry']==expected['endpoint'] for item in alternatives)
            result_ok=bool(alternatives) and all(expected['optional_result'] or
                item['result']=={'unknown':True} if expected['result_must_be_unresolved'] else
                expected['optional_result'] or cleaned(item['result'])==expected['result'] for item in alternatives)
            state_ok=bool(alternatives) and all(item.get('state_after',{}).get('database_rows',{}).get('review.bookings')==expected['rows'] for item in alternatives)
            no_stale=not expected['result_must_be_unresolved'] or all(item['parameters'].get('bookingId') not in ('A','B') for item in alternatives)
            row['steps'].append({'n':expected['n'],'endpoint':endpoints,'result':result_ok,'state':state_ok,'no_stale_identifier':no_stale})
        row['passed']=row['graph_exact'] and len(row['steps'])==len(oracle['steps']) and all(
            all(step[key] for key in ('endpoint','result','state','no_stale_identifier')) for step in row['steps'])
        row['preparation_seconds']=report.get('preparation_seconds')
        row['analysis_seconds']=report.get('analysis_seconds')
        row['peak_rss_bytes']=report.get('peak_rss_bytes')
    else:
        row['passed']=False
        row['failure_log']=str(output/'stderr.txt')
    results.append(row)
    print(json.dumps({'variant':number,'passed':row['passed'],'graph_exact':row.get('graph_exact'),'seconds':row['wall_seconds']}),flush=True)
assert hashlib.sha256(oracle_path.read_bytes()).hexdigest()==oracle_digest
(args.output/'comparison.json').write_text(json.dumps({'oracle_sha256':oracle_digest,
    'same_inputs_for_every_variant':True,'application_started':False,'kind':'synthetic full NL/HTTP/state control',
    'nonempty_gold_remote_cases':1,'nonempty_gold_data_cases':1,'results':results},indent=2)+'\n')
