"""Publish the tiny independent summary oracle and paired on/off observations."""
import argparse,json,sys
from pathlib import Path
V=Path(__file__).resolve().parents[1];sys.path[:0]=[str(V/'code'),str(V/'code/tests')]
from test_scoped_effects32 import fixture,run,prefix_oracle,INITIAL,RID
from analyzer.__main__ import serial
from analyzer.native_storage import JavaList
from evidence import heap,payload


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
    project,db,ids=fixture(args.output/'source')
    prefix=prefix_oracle(ids);complete=prefix|{('','executes',ids['Warehouse.reserve']),
        (ids['Approval.entry'],'remote',ids['Warehouse.reserve']),(ids['Warehouse.reserve'],'data',RID)}
    oracle={'source':'Source fixture and prefix_oracle independently written before R05 implementation',
        'initial':INITIAL,'full_prefix_edges':sorted(prefix),'full_success_edges':sorted(complete),
        'success_rows':[{'id':'A','status':'reserved'},INITIAL[1]],'remote_failure_rows':INITIAL,
        'boundary_contract':'Stop-only: prefix exact, no resumed return/throw, empty proven residual write footprint; off may over-invalidate',
        'scope':'tiny synthetic equipment example; not a real holdout'}
    (args.output/'oracle.json').write_text(json.dumps(oracle,indent=2)+'\n');rows=[]
    for enabled in (False,True):
        for case,kwargs in [('unknown-readonly',{}),('known-remote-save',{'values':JavaList(['one'],['String']),'inspect':False}),('remote-failure',{'id_':'missing'})]:
            result,e=run(project,db,ids,enabled,**kwargs)
            expected=complete if case=='known-remote-save' else prefix
            assert e.edges==expected
            if case!='unknown-readonly' or enabled:
                assert payload(e.state.database.rows(project.nodes[RID]))==(oracle['success_rows'] if case=='known-remote-save' else INITIAL)
            rows.append({'summary':enabled,'case':case,'result':result,'outcome':e.outcome,'edges':sorted(e.edges),
                'requests':e.request_events,'responses':e.http_responses,'guards':e.conditions,'knowledge_losses':e.loss_events,
                'actual_data_operations':e.data_operations,'effect_contracts':e.effect_events,'state_after':e.state.snapshot(full=True),'heap':heap(e.state)})
    (args.output/'observations.json').write_text(json.dumps(rows,default=serial,indent=2)+'\n')
    print(json.dumps({'paired_cases':len(rows),'full_tiny_oracle_verified':True,'target_apps_started':False}))


if __name__=='__main__':main()
