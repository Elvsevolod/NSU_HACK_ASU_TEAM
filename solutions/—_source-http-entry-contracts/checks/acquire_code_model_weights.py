"""Download only pinned, user-approved public weights and check their LFS hashes."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--storage',type=Path,required=True)
    parser.add_argument('--pins',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False)
    pins=json.loads(args.pins.read_text())
    def download(record):
        filename='model.safetensors' if record['name']=='coderank' else 'pytorch_model.bin'
        remote=next(row for row in record['siblings'] if row['name']==filename)
        command=[str(Path(sys.executable).parent/'hf'),'download',record['repo_id'],filename,
            '--revision',record['revision'],'--local-dir',str(args.storage/record['name']),
            '--cache-dir',str(args.storage/'hf-cache'),'--quiet']
        started=time.perf_counter()
        with (args.evidence/(record['name']+'.stdout.txt')).open('w') as out,(args.evidence/(record['name']+'.stderr.txt')).open('w') as err:
            result=subprocess.run(command,env={**os.environ,'HF_HUB_DISABLE_IMPLICIT_TOKEN':'1','HF_HUB_DISABLE_TELEMETRY':'1','HF_HUB_DISABLE_XET':'1'},stdout=out,stderr=err,timeout=600)
        path=args.storage/record['name']/filename
        digest=None
        if result.returncode==0:
            with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            assert path.stat().st_size==remote['bytes']
            assert digest==remote['lfs']['sha256']
        row={'name':record['name'],'repo_id':record['repo_id'],'revision':record['revision'],
            'command':command,'returncode':result.returncode,'seconds':time.perf_counter()-started,
            'file':str(path),'bytes':path.stat().st_size if path.exists() else None,'sha256':digest,
            'remote_lfs_sha256':remote['lfs']['sha256'],'model_code_executed':False}
        (args.evidence/(record['name']+'.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:row[k] for k in ('name','returncode','bytes','sha256')},ensure_ascii=False),flush=True)
        return row
    with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(download,pins))
    (args.evidence/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    if any(row['returncode'] for row in rows):raise SystemExit(1)


if __name__=='__main__':main()
