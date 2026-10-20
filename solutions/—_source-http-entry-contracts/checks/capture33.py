"""Capture an own Python check in a new directory with the actual code hashes."""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

V=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--timeout',type=int,default=600)
    parser.add_argument('--code-root',type=Path,default=V/'code')
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    command=args.command[1:] if args.command[:1]==['--'] else args.command
    if not command:parser.error('missing Python command')
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    code=args.code_root.resolve();assert (code/'analyzer').is_dir()
    record={'command':[sys.executable,'-B',*command],'cwd':str(V),'python':sys.version,'platform':platform.platform(),
        'code_root':str(code),
        'code_sha256':{p.relative_to(code).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(code.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'},
        'argument_input_sha256':{arg:hashlib.sha256(Path(arg).read_bytes()).hexdigest() for arg in command if Path(arg).is_file()},
        'targets_started':False,'environment':{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(code)}}
    (output/'start.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    start=time.perf_counter()
    with (output/'stdout.txt').open('w') as out,(output/'stderr.txt').open('w') as err:
        try:
            result=subprocess.run(record['command'],cwd=V,env={**os.environ,**record['environment']},stdout=out,stderr=err,timeout=args.timeout)
            record.update(returncode=result.returncode,timed_out=False)
        except subprocess.TimeoutExpired:
            record.update(returncode=None,timed_out=True)
    record['seconds']=time.perf_counter()-start
    (output/'run.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('returncode','timed_out','seconds')}),flush=True)
    raise SystemExit(record['returncode'] if record['returncode'] is not None else 124)


if __name__=='__main__':main()
