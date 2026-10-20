"""Negative controls: realistic corruptions must fail the strict checker."""
from copy import deepcopy
from pathlib import Path
import argparse
import json
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--oracle',type=Path,required=True);parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
    original=json.loads(args.trace.read_text());cases={}
    case=deepcopy(original);case['steps'][2]['tables']['account-service.accounts'][0]['note']='wrong same-sized state';cases['state_fields']=case
    case=deepcopy(original);case['steps'][2]['requests'][0]['bound_arguments'][1]['value']['name']='wrong bound DTO';cases['bound_arguments']=case
    case=deepcopy(original);case['steps'][1]['request']['headers'].pop('authorization');cases['wire_headers']=case
    case=deepcopy(original);case['steps'][2]['requests'][1]['binding_candidate_arguments'][1]['value']['incomes']=[];cases['rejected_candidate']=case
    case=deepcopy(original);first=case['steps'][0];last=case['steps'][1]
    # Same scenario-union graph, but execution attributed to the wrong step.
    edge=next(edge for edge in first['edges'] if edge[1]=='remote');first['edges'].remove(edge);last['edges'].append(edge);cases['per_step_edges']=case
    case=deepcopy(original);case['steps'][5]['tables']['auth-service.users'][1]['password']['__encoded_from__']='other password';cases['password_origin']=case
    case=deepcopy(original);case['steps'][2]['requests'][0]['bound_arguments'][1]['value']['saving']['__type__']='other.domain.Saving';cases['nested_dto_type']=case
    case=deepcopy(original);case['steps'][0]['requests'][1]['request']['session']['principal']['name']='another-service';cases['remote_identity']=case
    case=deepcopy(original);case['steps'][2]['requests'][1]['fallback']['bound_arguments'][0]['value']='wrong-account';cases['fallback_argument']=case
    case=deepcopy(original);case['steps'][2]['data_operations'][1]['arguments'][0]['note']='wrong saved value despite correct final state';cases['saved_operation_value']=case
    results=[]
    for name,trace in cases.items():
        path=args.output/(name+'.json');path.write_text(json.dumps(trace,indent=2)+'\n')
        result=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('check_real_journey.py')),
            '--input',str(args.input),'--oracle',str(args.oracle),'--trace',str(path),'--output',str(args.output/(name+'-check.json'))],capture_output=True,text=True)
        checks=json.loads((args.output/(name+'-check.json')).read_text())
        assert result.returncode==1 and not checks['passed'],name
        results.append({'mutation':name,'rejected':True})
    (args.output/'summary.json').write_text(json.dumps({'passed':True,'negative_controls':results},indent=2)+'\n')
    print(json.dumps({'passed':True,'mutations_rejected':len(results)}))


if __name__=='__main__':main()
