"""Measure preparation once and repeat model-free analysis from fresh inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

VARIANT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(VARIANT/'code'))
from analyzer.project import Project
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex,ContractGrounder,read_static_context
from analyzer.state import Database
from analyzer.__main__ import analyze

parser=argparse.ArgumentParser()
for key in ('source','skeleton','context','scenarios','expected','output'):parser.add_argument('--'+key,type=Path,required=True)
parser.add_argument('--repetitions',type=int,default=2);args=parser.parse_args();assert not args.output.exists()
started=time.perf_counter();project=Project(args.skeleton,args.source);frontend=Frontend(project);index=ContractIndex(project,frontend)
context=read_static_context(project.skeleton.get('context',{}));database=Database(args.context/'db-after-warmup.sql.gz')
database.schemas=project.schemas
context['unresolved'].extend(frontend.unsupported)
context['unresolved'].extend('Unsupported source route: '+message for message in project.route_warnings)
context['unresolved'].extend(database.warnings)
prepare=time.perf_counter()-started
scenarios=[json.loads(path.read_text()) for path in sorted(args.scenarios.glob('*.json'))]
expected=hashlib.sha256(args.expected.read_bytes()).hexdigest();runs=[]
for repetition in range(args.repetitions):
    started=time.perf_counter();answer={'project':project.skeleton['project'],'scenarios':{}}
    for scenario in scenarios:
        block,_=analyze(project,frontend,index,None,database,context,scenario,4,ContractGrounder)
        answer['scenarios'][scenario['id']]=block
    calculation=time.perf_counter()-started
    serialization_started=time.perf_counter()
    payload=(json.dumps(answer,ensure_ascii=False,indent=2)+'\n').encode()
    digest=hashlib.sha256(payload).hexdigest()
    runs.append({'repetition':repetition+1,'analysis_seconds':calculation,'serialization_seconds':time.perf_counter()-serialization_started,
        'submission_sha256':digest,'matches_expected':digest==expected})
    print(json.dumps(runs[-1]),flush=True)
args.output.write_text(json.dumps({'prepare_seconds':prepare,'project_constructions':1,'source_index_reused':True,
    'fresh_independent_scenario_state':True,'runs':runs,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'model_calls':0,'external_llm_api_calls':0,'target_applications_started':False},indent=2)+'\n')
assert all(row['matches_expected'] for row in runs)
