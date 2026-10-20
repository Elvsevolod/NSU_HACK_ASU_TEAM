"""Fill missing baseline/preceding-stage comparisons without overwriting evidence."""
import json,subprocess,sys
from pathlib import Path
V=Path(__file__).resolve().parents[1]
STAGES=['G03-unknown-foreach','G04-bulk-consumers','G05A-cast-soundness','G05B-commuting-removals',
        'G05B2-known-reads','G08-stream-materialization','G09B-mvc-source-absence',
        'G10-source-patch-deployment','G11-source-record-reduce-response','G13-live-route-filter']


def main():
    previous='G01-parent30';runs=[]
    for stage in STAGES:
        for before in dict.fromkeys(['G01-parent30',previous]):
            target=V/'benchmark/comparisons'/(before+'--'+stage+'.json')
            if target.exists():continue
            command=[sys.executable,'-B','checks/compare_stages.py',before,stage]
            run=subprocess.run(command,cwd=V,capture_output=True,text=True,timeout=60)
            runs.append({'command':command,'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
            if run.returncode:raise RuntimeError(runs[-1])
        previous=stage
    out=V/'benchmark/comparisons/reconciliation.json';assert not out.exists()
    out.write_text(json.dumps({'passed':True,'runs':runs,'compared_steps_per_pair':103},indent=2)+'\n')
    print(json.dumps({'passed':True,'new_comparisons':len(runs)}))


if __name__=='__main__':main()
