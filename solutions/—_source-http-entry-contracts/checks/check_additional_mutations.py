"""Challenge the real-profile checker with incorrect values and execution."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser()
    for key in ('input','oracle','trace','output'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
    original=json.loads(args.trace.read_text());cases={}
    case=deepcopy(original);case['cases'][1]['result']['incomes'].reverse();cases['collection_positions']=case
    case=deepcopy(original);case['cases'][1]['tables']['account-service.accounts'][0]['incomes'][0]['currency']['__type__']='other.Currency';cases['unknown_field_type']=case
    case=deepcopy(original);case['cases'][1]['callbacks'].pop();cases['missing_callback']=case
    case=deepcopy(original);case['cases'][2]['proposals']=1;cases['invented_ambiguous_request']=case
    case=deepcopy(original);case['cases'][0]['request']['body']={};cases['explicit_null_becomes_missing']=case
    case=deepcopy(original);case['cases'][1]['callbacks'][-1]['receiver']['title']='another-object';cases['callback_receiver']=case
    rows=[]
    for name,trace in cases.items():
        path=args.output/(name+'.json');path.write_text(json.dumps(trace,indent=2)+'\n')
        run=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('check_additional_journey.py')),
            '--input',str(args.input),'--oracle',str(args.oracle),'--trace',str(path),'--output',str(args.output/(name+'-checks.json'))],capture_output=True,text=True)
        assert run.returncode==1,(name,run.stdout,run.stderr)
        rows.append({'mutation':name,'rejected':True})
    (args.output/'summary.json').write_text(json.dumps({'passed':True,'negative_controls':rows},indent=2)+'\n')
    print(json.dumps({'passed':True,'mutations_rejected':len(rows)}))


if __name__=='__main__':main()
