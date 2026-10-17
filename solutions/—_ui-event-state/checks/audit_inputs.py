"""Report-only input coverage audit; never imported by graph construction."""
import argparse
import json
from pathlib import Path


def symbols(value):
    if isinstance(value,dict):
        symbol=value.get('__symbol__','')
        if symbol.startswith('symbolic-input-'):yield symbol
        for child in value.values():yield from symbols(child)
    elif isinstance(value,list):
        for child in value:yield from symbols(child)


def audit(path):
    report=json.loads(path.read_text())
    steps=[]
    free=[]
    first_count=0
    for sid,scenario in report['scenarios'].items():
        for step in scenario['steps']:
            fields={}
            alternatives=step['alternatives']
            for number,alternative in enumerate(alternatives):
                for problem in alternative['unresolved']:
                    if problem.startswith('Unknown input: '):
                        field=problem.split(': ',1)[1]
                        fields.setdefault(field,[]).append(number)
                for field,value in alternative['parameters'].items():
                    names=sorted(set(symbols(value)))
                    if names:free.append({'scenario':sid,'step':step['n'],'alternative':number,'field':field,'symbols':names,
                                          'binding':alternative['bindings'].get(field)})
            if alternatives and any(p.startswith('Unknown input: ') for p in alternatives[0]['unresolved']):first_count+=1
            if fields:steps.append({'scenario':sid,'step':step['n'],'action':step['action'],'fields':fields,
                                    'entries':sorted({a['entry'] for a in alternatives}),
                                    'bindings':{field:[a['bindings'].get(field) for a in alternatives] for field in fields}})
    return {'unknown_steps_any_alternative':len(steps),'unknown_steps_first_alternative':first_count,
            'unknown_step_fields':sum(len(step['fields']) for step in steps),'steps':steps,
            'symbolic_user_input_occurrences':free,
            'definition':'Unknown input diagnostics across every alternative; generated identities and free user symbols are separate. A bound symbol does not determine concrete bytes.',
            'scenario_statuses':{sid:s['analysis_status'] for sid,s in report['scenarios'].items()}}


parser=argparse.ArgumentParser()
parser.add_argument('--report',type=Path,required=True)
parser.add_argument('--parent-report',type=Path)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
result={'current':audit(args.report)}
if args.parent_report:result['parent']=audit(args.parent_report)
args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({label:{key:value for key,value in data.items() if key not in ('steps','symbolic_user_input_occurrences')}
                  for label,data in result.items()},ensure_ascii=False))
