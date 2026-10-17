from pathlib import Path
import json,subprocess,sys,time,os
root=Path('/Users/vsevolod/Desktop/NSU_HACK_ASU_TEAM');v=root/'solutions/—_polyglot-scenario-core';exp=root/'experiments/20261017-polyglot-scenario-core'
java=exp/'piggymetrics';python=exp/'fastapi-template/backend'
jobs=[('core', ['benchmark_core.py']),('ui',['benchmark_ui.py']),('oss',['benchmark_oss.py']),('corpus',['check_corpus.py','--java',str(java),'--python',str(python),'--output',str(v/'benchmark/public-corpus')]),('grounding',['check_grounding.py','--java',str(java),'--python',str(python),'--output',str(v/'benchmark/request-grounding.json')]),('retrieval',['benchmark_retrieval.py','--java',str(java),'--python',str(python)]),('http',['check_http_corpus.py','--source',str(python),'--output',str(v/'benchmark/public-http')])]
results=[]
for label,args in jobs:
 command=[sys.executable,'-B',str(v/'development'/args[0]),*args[1:]];start=time.perf_counter()
 process=subprocess.run(command,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0'})
 (v/('benchmark/'+label+'-final.stdout.txt')).write_text(process.stdout);(v/('benchmark/'+label+'-final.stderr.txt')).write_text(process.stderr)
 row={'label':label,'command':command,'returncode':process.returncode,'wall_seconds':time.perf_counter()-start};results.append(row);print(json.dumps(row),flush=True)
 (v/'benchmark/component-commands.json').write_text(json.dumps(results,indent=2)+'\n')
 if process.returncode:raise SystemExit(process.returncode)
