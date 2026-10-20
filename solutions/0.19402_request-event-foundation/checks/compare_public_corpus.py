"""Equal frozen real-source inputs; the oracle is read only by this evaluator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

VARIANT=Path(__file__).resolve().parents[1]
ROOT=VARIANT.parents[1]
CONTROLS=[(5,'0.909870_field-constructor-projection'),(12,'0.748530_dom-state-flow'),
    (23,'0.66185_lvalue-evaluation'),(26,'0.61822_json-bean-lifecycle'),(27,VARIANT.name)]


def edge_set(edges):return {tuple(e[k] for k in ('source','relation','target')) for e in edges}


def subset(expected,actual):
    if isinstance(expected,dict):return isinstance(actual,dict) and all(key in actual and subset(value,actual[key]) for key,value in expected.items())
    if isinstance(expected,list):return isinstance(actual,list) and len(actual)==len(expected) and all(subset(a,b) for a,b in zip(expected,actual))
    return type(expected) is type(actual) and expected==actual


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--fixtures',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--candidate-only',action='store_true')
    args=parser.parse_args();assert not args.output.exists()
    args.output.mkdir(parents=True)
    results=[]
    for fixture in sorted(args.fixtures.iterdir()):
        if not fixture.is_dir() or not (fixture/'oracle.json').exists():continue
        oracle_path=fixture/'oracle.json';digest=hashlib.sha256(oracle_path.read_bytes()).hexdigest()
        oracle=json.loads(oracle_path.read_text());gold=edge_set(oracle['edges'])
        scenario=json.loads((fixture/'scenarios.json').read_text())['id']
        for number,directory in (CONTROLS[-1:] if args.candidate_only else CONTROLS):
            code=ROOT/'solutions'/directory/'code';output=args.output/fixture.name/str(number);output.mkdir(parents=True)
            launcher=code/'offline_run.py'
            command=[sys.executable,'-B',str(launcher)] if launcher.exists() else [sys.executable,'-B','-m','analyzer']
            command += ['--source',str(fixture.resolve()),'--skeleton',str((fixture/'skeleton.json').resolve()),
                '--context',str((fixture/'initial.sql').resolve()),'--scenarios',str((fixture/'scenarios.json').resolve()),
                '--output',str((output/'submission.json').resolve()),'--report',str((output/'analysis-report.json').resolve())]
            started=time.perf_counter();row={'fixture':fixture.name,'variant':number,'oracle_sha256':digest,'command':command}
            with (output/'stdout.txt').open('w') as out,(output/'stderr.txt').open('w') as err:
                try:process=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(code)},stdout=out,stderr=err,timeout=120)
                except subprocess.TimeoutExpired:process=None
            row.update(wall_seconds=time.perf_counter()-started,returncode=process.returncode if process else None,passed=False)
            if process is not None and process.returncode==0:
                report=json.loads((output/'analysis-report.json').read_text())
                actual=edge_set(json.loads((output/'submission.json').read_text())['scenarios'][scenario]['edges'])
                row['relations']={}
                for relation in ('executes','calls','remote','data'):
                    a={e for e in actual if e[1]==relation};g={e for e in gold if e[1]==relation}
                    tp,fp,fn=len(a&g),len(a-g),len(g-a)
                    row['relations'][relation]={'tp':tp,'fp':fp,'fn':fn,'precision':tp/(tp+fp) if tp+fp else None,
                        'recall':tp/(tp+fn) if tp+fn else None,'iou':tp/(tp+fp+fn) if tp+fp+fn else None,'nonempty_gold':bool(g)}
                row['graph_exact']=gold==actual;row['steps']=[]
                for expected,observed in zip(oracle['steps'],report['scenarios'][scenario]['steps']):
                    alternatives=observed.get('alternatives',[observed])
                    checks={'endpoint':bool(alternatives) and all(a['entry']==expected['endpoint'] for a in alternatives),
                        'arguments':bool(alternatives) and all(subset(expected['arguments'],a['parameters']) for a in alternatives),
                        'status':bool(alternatives) and all(a.get('responses') and a['responses'][-1]['status']==expected['status'] for a in alternatives),
                        'result':bool(alternatives) and all(expected['ignore_result'] or
                            (subset(expected['result'],a['result']) if expected.get('result_subset') else expected['result']==a['result']) for a in alternatives),
                        'state':bool(alternatives) and all(subset(expected['rows'],a.get('state_after',{}).get('database_rows',{})) and
                            not a.get('state_after',{}).get('unknown_tables',[]) for a in alternatives)}
                    row['steps'].append({'n':expected['n'],**checks})
                row['passed']=row['graph_exact'] and len(row['steps'])==len(oracle['steps']) and all(all(v for k,v in step.items() if k!='n') for step in row['steps'])
                row.update({key:report.get(key) for key in ('preparation_seconds','analysis_seconds','peak_rss_bytes')})
            assert hashlib.sha256(oracle_path.read_bytes()).hexdigest()==digest
            results.append(row);print(json.dumps({key:row.get(key) for key in ('fixture','variant','passed','graph_exact','wall_seconds')}),flush=True)
    (args.output/'comparison.json').write_text(json.dumps({'same_inputs_for_all_variants':True,'targets_started':False,
        'oracle_not_available_to_inference':True,'results':results,'nonempty_gold_remote_cases':0,'nonempty_gold_data_cases':2,
        'limits':['Pinned HTTP profiles, not universal framework coverage','Older controls do not report HTTP statuses; absence is unmeasured, not success',
                  'Real profiles do not test remote; nonempty remote is measured separately on the full synthetic journey']},indent=2)+'\n')


if __name__=='__main__':main()
