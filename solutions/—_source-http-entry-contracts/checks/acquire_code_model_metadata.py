"""Fetch public model metadata and non-weight files; execute no model code."""
import argparse
import dataclasses
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from huggingface_hub import HfApi

MODELS={
    'unixcoder':('microsoft/unixcoder-base','main'),
    'codet5p':('Salesforce/codet5p-110m-embedding','main'),
    'coderank':('nomic-ai/CodeRankEmbed','3c4b60807d71f79b43f3c4363786d9493691f8b1'),
}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--storage',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=False)
    args.storage.mkdir(parents=True,exist_ok=True)
    environment={**os.environ,'HF_HUB_DISABLE_IMPLICIT_TOKEN':'1','HF_HUB_DISABLE_TELEMETRY':'1','HF_HUB_DISABLE_XET':'1'}
    api=HfApi(token=False)
    records=[]
    for name,(repo,revision) in MODELS.items():
        info=api.model_info(repo,revision=revision,files_metadata=True)
        siblings=[]
        for file in info.siblings:
            row={'name':file.rfilename,'bytes':file.size,'blob_id':file.blob_id}
            if file.lfs is not None:row['lfs']=dataclasses.asdict(file.lfs) if dataclasses.is_dataclass(file.lfs) else vars(file.lfs)
            siblings.append(row)
        record={'name':name,'repo_id':repo,'requested_revision':revision,'revision':info.sha,
            'gated':info.gated,'private':info.private,'siblings':siblings,
            'stage':'metadata_only_no_model_code_execution','user_permission':'Direct user approved all three local model pilots in this thread.'}
        records.append(record)
        (args.evidence/'pins.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
        destination=args.storage/name
        command=[str(Path(sys.executable).parent/'hf'),'download',repo,'--revision',info.sha,
            '--local-dir',str(destination),'--cache-dir',str(args.storage/'hf-cache'),
            '--include','*.json','*.txt','*.py','*.md','vocab.*','merges.*','LICENSE*','--max-workers','2','--quiet']
        with (args.evidence/(name+'.stdout.txt')).open('w') as out,(args.evidence/(name+'.stderr.txt')).open('w') as err:
            result=subprocess.run(command,env=environment,stdout=out,stderr=err,timeout=180)
        record.update(metadata_command=command,metadata_returncode=result.returncode)
        record['downloaded_files']={p.relative_to(destination).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(destination.rglob('*')) if p.is_file() and '.cache' not in p.parts}
        (args.evidence/'pins.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'name':name,'revision':info.sha,'files':len(record['downloaded_files']),'returncode':result.returncode}),flush=True)
        if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
