"""Offline CLI oracle: source UI -> Java -> Python -> DB -> UI -> next request."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

VARIANT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(VARIANT/'code'),str(VARIANT/'code/tests')]
from test_ui_integration import ui_chain_fixture


def main():
    base=VARIANT/'benchmark/ui-integration'
    root=base/'fixture'
    base.mkdir(parents=True,exist_ok=True)
    if not (root/'src').exists():
        project,_,ids,scenario=ui_chain_fixture(root)
        (root/'ids.json').write_text(json.dumps(ids,indent=2)+'\n')
        (root/'scenario.json').write_text(json.dumps({**scenario,'project':project.skeleton['project']},indent=2)+'\n')
        (root/'context.json').write_text('{"tables":{"artifact_rows":[]}}\n')
    ids=json.loads((root/'ids.json').read_text())
    names=['Portal.create','Portal.read','main.database','main.add_item','main.read_item','main.lookup']
    expected={('scenario:ui-chain','executes',ids[name]) for name in names}
    expected|={(ids['Portal.create'],'remote',ids['main.add_item']),(ids['Portal.read'],'remote',ids['main.read_item']),
               (ids['main.read_item'],'calls',ids['main.lookup']),(ids['main.add_item'],'data','storage:artifact_rows'),(ids['main.lookup'],'data','storage:artifact_rows')}
    reference={'author':'Codex, manual, nonblind synthetic oracle; not an independent public project',
               'edges':[list(edge) for edge in sorted(expected)],'quantity':6,'title':'Draft'}
    (base/'reference.json').write_text(json.dumps(reference,indent=2)+'\n')
    common=[sys.executable,'-B',str(VARIANT/'code/offline_run.py'),'--source',str(root/'src'),'--skeleton',str(root/'skeleton.json'),
            '--context',str(root/'context.json'),'--scenarios',str(root/'scenario.json')]
    cache=base/'ir-cache.json'
    if cache.exists():cache.unlink()
    reports,outputs,commands,walls={},{},{},{}
    for mode,seed in [('cold','7'),('warm','31')]:
        output=base/(mode+'.json');report=base/(mode+'-report.json')
        command=common+['--output',str(output),'--report',str(report),'--cache',str(cache)]
        started=time.perf_counter()
        result=subprocess.run(command,env={**os.environ,'PYTHONHASHSEED':seed,'PYTHONDONTWRITEBYTECODE':'1'},text=True,capture_output=True)
        walls[mode]=time.perf_counter()-started
        (base/(mode+'.stdout.txt')).write_text(result.stdout);(base/(mode+'.stderr.txt')).write_text(result.stderr)
        assert result.returncode==0,result.stderr
        commands[mode]=command;outputs[mode]=json.loads(output.read_text());reports[mode]=json.loads(report.read_text())
        detail=reports[mode]['scenarios']['ui-chain'];steps=detail['paths'][0]['steps']
        actual={tuple(edge[key] for key in ['source','relation','target']) for edge in outputs[mode]['scenarios']['ui-chain']['edges']}
        assert actual==expected,(actual-expected,expected-actual)
        assert len(detail['paths'])==1 and len(steps)==2
        assert steps[0]['response']['body']==steps[1]['response']['body']
        assert steps[1]['response']['body']['quantity']==6
        assert detail['paths'][0]['state']['storage:artifact_rows'][0]['title']=='Draft'
        assert all(step['grounding']['ui'] for step in steps)
        assert reports[mode]['native_javascript']['calls']>0
        assert reports[mode]['application_executed'] is False
    assert outputs['cold']==outputs['warm']
    assert reports['warm']['IR_cache_hits']==6 and reports['warm']['lowered_methods']==0
    summary={'passed':True,'scope':reference['author'],'application_executed':False,'model_calls':0,
             'all_four_nonempty':True,'exact_manual_graph_match':True,'cold_warm_hashseeds_equal':True,
             'symbolic_id_through_json_storage':True,'edge_counts':{rel:sum(edge[1]==rel for edge in expected) for rel in ['executes','calls','remote','data']},
             'source_sha256':{p.relative_to(root/'src').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'src').rglob('*')) if p.is_file()},
             'reference_sha256':hashlib.sha256((base/'reference.json').read_bytes()).hexdigest(),
             'commands':commands,'wall_seconds':walls,'measurements':{mode:{key:report[key] for key in ['preparation_seconds','analysis_seconds','elapsed_seconds','peak_rss_bytes','lowered_methods','IR_cache_hits','native_javascript','submission_sha256']} for mode,report in reports.items()}}
    (base/'verification.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({key:summary[key] for key in ['passed','edge_counts','wall_seconds']}))


if __name__=='__main__':main()
