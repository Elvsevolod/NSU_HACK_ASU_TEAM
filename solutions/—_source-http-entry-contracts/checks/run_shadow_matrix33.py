"""Paired downstream runs in one interpreter/environment, with one code snapshot."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--storage',type=Path,required=True);p.add_argument('--qwen',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);runs=[]
    manifest={f.relative_to(V/'code').as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((V/'code').rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
    for profile in ('baseline','lexical','dense-same','dense-expanded'):
        command=[sys.executable,'-B',str(V/'checks/shadow_model_transfer33.py'),'--profile',profile,'--output',str(a.output/profile)]
        if profile.startswith('dense'):command+=['--storage',str(a.storage),'--qwen',str(a.qwen),'--snapshot',str(V/'development/model-pilot/coderank-source-index-v2.json')]
        started=time.perf_counter()
        with (a.output/(profile+'.stdout.txt')).open('w') as out,(a.output/(profile+'.stderr.txt')).open('w') as err:
            completed=subprocess.run(command,stdout=out,stderr=err,cwd=V,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=600)
        runs.append({'profile':profile,'command':command,'returncode':completed.returncode,'seconds':time.perf_counter()-started})
        (a.output/'matrix.json').write_text(json.dumps({'runs':runs,'code_sha256':manifest,'same_environment':sys.executable,'targets_started':False},ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(runs[-1],ensure_ascii=False),flush=True)
    raise SystemExit(0 if all(r['returncode']==0 for r in runs) else 1)


if __name__=='__main__':main()
