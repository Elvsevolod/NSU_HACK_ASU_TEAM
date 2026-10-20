"""Exercise wrapper failure/timeout persistence on own tiny inert Python fixtures."""
import hashlib,json,subprocess,sys,zipfile
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def main():
    output=V/'benchmark/replay-negative';assert not output.exists();output.mkdir();rows=[]
    for label in ('unsafe-member','wrong-hash','timeout'):
        path=output/(label+'.zip');body=b'import time\nprint("probe-started",flush=True)\ntime.sleep(2)\n'
        files={'code/offline_run.py':body,'submission.json':b'{}'}
        if label=='unsafe-member':files['../escaped']=b'inert'
        manifest={n:hashlib.sha256(v).hexdigest() for n,v in files.items()}
        if label=='wrong-hash':manifest['submission.json']='0'*64
        with zipfile.ZipFile(path,'x') as z:
            for n,b in files.items():z.writestr(n,b)
            z.writestr('benchmark/package-manifest.json',json.dumps(manifest))
        target=output/label
        command=[sys.executable,'-B','checks/replay_archive.py','--archive',str(path),'--source','validation_inputs/shopping-cart',
            '--skeleton','validation_inputs/shopping-cart/skeleton.json','--context','validation_inputs/shopping-cart/initial.sql',
            '--scenarios','validation_inputs/shopping-cart/scenarios.json','--output',str(target),'--timeout','0.1']
        run=subprocess.run(command,cwd=V,capture_output=True,text=True,timeout=15)
        result=json.loads((target/'replay.json').read_text())
        valid=run.returncode!=0 and not result['passed'] and result['temporary_directory_removed']
        if label=='timeout':valid=valid and result['runs']['analyzer']['timed_out'] and (target/'analyzer.stdout.txt').read_text()=='probe-started\n'
        rows.append({'label':label,'expected_failure_recorded':bool(valid),'returncode':run.returncode,'command':command,'replay':result})
    result={'passed':all(r['expected_failure_recorded'] for r in rows),'cases':rows,'target_apps_started':False,
        'scope':'Tiny self-authored Python timeout wrapper fixture; not an analyzer correctness result.'}
    (output/'checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed']}));assert result['passed']


if __name__=='__main__':main()
