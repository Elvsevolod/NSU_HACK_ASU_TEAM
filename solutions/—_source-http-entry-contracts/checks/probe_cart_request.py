"""One explicit real-source request from clean SQL, without any oracle input."""
import argparse,json,sys
from pathlib import Path
from datetime import datetime
V=Path(__file__).resolve().parents[1];sys.path.insert(0,str(V/'code'))
from analyzer.project import Project
from analyzer.state import Database,ScenarioState
from analyzer.request import Request
from analyzer.paths import run_paths
from analyzer.__main__ import serial
from offline_run import audit,audit_stats,declared_inputs
from evidence import trace_document


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--module',required=True);p.add_argument('--verb',required=True);p.add_argument('--url',required=True);a=p.parse_args()
    assert not a.output.exists();root=V/'validation_inputs/shopping-cart'
    declared_inputs.append((root.resolve(),True));sys.addaudithook(audit)
    project=Project(root/'skeleton.json',root);state=ScenarioState(Database(root/'initial.sql'),{**json.loads((root/'deployment-context-v2.json').read_text()),'clock':datetime(2026,10,18)})
    before=state.snapshot(full=True);request=Request.http(a.module,a.verb,a.url,headers={})
    candidates=project.ix.handlers_for(a.verb,list(request.path),a.module);assert len(candidates)==1
    rows=[]
    for path in run_paths(project,state,next(iter(candidates)),request,limit=4,entry_boundary='application_after_authentication'):
        e=path['engine'];rows.append({'result':path['result'],'outcome':e.outcome,'warnings':sorted(e.warnings),
           'requests':e.request_events,'responses':e.http_responses,'events':e.events,'edges':sorted(e.edges),
           'data_operations':e.data_operations,'state_after':e.state.snapshot(full=True)})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(trace_document({'request':request.record(),'state_before':before,'alternatives':rows,'offline_audit':audit_stats,
       'entry_boundary':'application_after_authentication','security_evaluated':False}),default=serial,indent=2)+'\n')
    print(json.dumps([{'outcome':r['outcome'],'result':r['result'],'warnings':r['warnings'][:4]} for r in rows],default=serial))


if __name__=='__main__':main()
