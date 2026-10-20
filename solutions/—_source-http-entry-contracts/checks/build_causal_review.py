"""Checker-side loss ledger and E/C/R/D deltas; no inference is performed."""
import argparse,gzip,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def read(stage):
    with gzip.open(V/'benchmark/stages'/stage/'analysis-report.json.gz','rt') as stream:return json.load(stream)


def edge_set(step):return {(e['source'],e['relation'],e['target']) for a in step.get('alternatives',[]) for e in a['edges']}


def identity(alt):
    # Guards and source/request provenance identify a path. Array position does
    # not: encounter choices may introduce different alternatives at each stage.
    value={k:alt.get(k) for k in ('entry','request','path_conditions','bindings')}
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def ledger(report,stage):
    groups={};phases=Counter();firsts=[]
    for sid,scenario in report['scenarios'].items():
        for step in scenario['steps']:
            for alt in step.get('alternatives',[]):
                losses=alt.get('knowledge_losses',[])
                important=next((x for x in losses if x['phase'] not in ('input_or_value','unsupported_value')),None)
                firsts.append({'scenario':sid,'step':step['n'],'path_key':identity(alt),'entry':alt.get('entry'),
                    'outcome':alt.get('outcome'),'first_observed_unknown':losses[0] if losses else None,
                    'first_control_or_fallback_loss':important,'diagnostics_recorded':bool(losses),
                    'historical_absence_is_not_no_loss':not losses})
                for loss in losses:
                    phases[loss['phase']]+=1;loc=loss.get('location',{})
                    key=json.dumps([loss['phase'],loss['cause'],loc.get('file'),loc.get('line'),loc.get('method')])
                    group=groups.setdefault(key,{'phase':loss['phase'],'cause':loss['cause'],'location':loc,
                        'occurrences':0,'steps':set(),'scenarios':set(),'widened_locations':set(),
                        'possible_write_footprint':set(),'actual_effect_operations':set(),'example':loss})
                    group['occurrences']+=1;group['steps'].add((sid,step['n']));group['scenarios'].add(sid)
                    group['widened_locations'].update(map(str,loss.get('widened_locations',[])))
                    group['possible_write_footprint'].update(map(str,loss.get('possible_write_footprint',[])))
                    group['actual_effect_operations'].update(e['operation'] for e in loss.get('actual_effects',[]))
    rows=[]
    for group in groups.values():
        group={k:sorted(v) if isinstance(v,set) else v for k,v in group.items()};group['step_count']=len(group['steps']);group['scenario_count']=len(group['scenarios']);rows.append(group)
    return {'stage':stage,'grouped_by':'phase, original cause, source location/method; counts are not quality metrics',
        'phase_events':dict(phases),'groups':sorted(rows,key=lambda r:-r['occurrences']),'firsts':firsts,
        'limits':'Historical stages without these diagnostics cannot prove absence of knowledge loss. Actual effects and possible/invalidation footprints remain distinct.'}


def compare(before,after,left,right):
    rows=[];union=[]
    for sid in before['scenarios']:
        lsteps=before['scenarios'][sid]['steps'];rsteps=after['scenarios'][sid]['steps']
        assert [s['n'] for s in lsteps]==[s['n'] for s in rsteps]
        left_union=set();right_union=set()
        for b,a in zip(lsteps,rsteps):
            eb,ea=edge_set(b),edge_set(a);left_union|=eb;right_union|=ea
            def witnesses(step):
                return [{'path_key':identity(x),**{k:x.get(k) for k in ('entry','request','bindings','parameters','result','selected_objects','path_conditions','outcome','exploration')},
                    'source_events_tail':x.get('events',[])[-8:],'knowledge_losses':x.get('knowledge_losses',[]),
                    'state_join_losses':(x.get('state_after') or {}).get('join_losses',[])} for x in step.get('alternatives',[])]
            rows.append({'scenario':sid,'n':a['n'],'action':a['action'],'graph_changed':eb!=ea,
                'relations':{kind:{'added':sorted(e for e in ea-eb if e[1]==kind),'removed':sorted(e for e in eb-ea if e[1]==kind)} for kind in ('executes','calls','remote','data')},
                'before':witnesses(b),'after':witnesses(a),'value_alignment':'match path_key; unmatched guards/producers remain separate, never align by ordinal'})
        union.append({'scenario':sid,'relations':{kind:{'added':sorted(e for e in right_union-left_union if e[1]==kind),
            'removed':sorted(e for e in left_union-right_union if e[1]==kind)} for kind in ('executes','calls','remote','data')}})
    return {'before':left,'after':right,'steps':rows,'unions':union,'hidden_gold_used':False,
        'interpretation':'Prediction deltas and source witnesses; added/removed edges are not hidden correctness labels.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--stages',nargs='+',required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    assert not args.output.exists();args.output.mkdir(parents=True);previous=None;previous_name=None;summary=[]
    for stage in args.stages:
        report=read(stage);losses=ledger(report,stage)
        with gzip.open(args.output/(stage+'-loss-ledger.json.gz'),'wt') as stream:json.dump(losses,stream,ensure_ascii=True)
        row={'stage':stage,'phase_events':losses['phase_events'],'source_cause_groups':len(losses['groups'])}
        if previous is not None:
            delta=compare(previous,report,previous_name,stage)
            with gzip.open(args.output/(previous_name+'--'+stage+'.json.gz'),'wt') as stream:json.dump(delta,stream,ensure_ascii=True)
            row['changed_steps']=sum(s['graph_changed'] for s in delta['steps']);row['unions']=delta['unions']
        summary.append(row);previous,previous_name=report,stage
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps([{'stage':r['stage'],'groups':r['source_cause_groups'],'changed_steps':r.get('changed_steps')} for r in summary]))


if __name__=='__main__':main()
