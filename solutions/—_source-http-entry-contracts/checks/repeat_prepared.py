"""Prepared source index reuse; expectations are read by the comparator only."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import resource
import sys
import time

VARIANT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(VARIANT/'code'))
from analyzer.project import Project
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex,ContractGrounder,read_static_context
from analyzer.state import Database
from analyzer.__main__ import analyze,serial
from analyzer.measurements import peak_rss
from analyzer.reporting import finite_report


def digest(value):
    return hashlib.sha256(json.dumps(finite_report(value),sort_keys=True,default=serial,separators=(',',':')).encode()).hexdigest()


def database_digest(database):
    return digest([[list(key),value] for key,value in sorted(database.tables.raw_items())])


def witnesses(detail):
    # Source callback/condition/event order stays intact. Diagnostic assumption
    # string order is irrelevant. Paths are compared as a semantic multiset.
    rows=[]
    for step in detail['steps']:
        alternatives=[]
        for a in step['alternatives']:
            row={k:a.get(k) for k in ('entry','ui_site','request','requests','parameters','bindings','result',
                                      'state_before','state_after','outcome','data_operations','conditions')}
            for key in ('state_before','state_after'):
                if isinstance(row[key],dict):
                    row[key]={**row[key]}
                    for name in ('limitations','assumptions'):
                        if isinstance(row[key].get(name),list):row[key][name]=sorted(row[key][name])
            alternatives.append(digest(row))
        rows.append({'n':step['n'],'alternatives':sorted(alternatives)})
    return rows


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','skeleton','context','scenarios','expected','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--repetitions',type=int,default=2);args=parser.parse_args()
    assert args.repetitions>=2 and not args.output.exists()
    started=time.perf_counter();project=Project(args.skeleton,args.source);frontend=Frontend(project);index=ContractIndex(project,frontend)
    context=read_static_context(project.skeleton.get('context',{}))
    dump=args.context/'db-after-warmup.sql.gz' if args.context.is_dir() else args.context
    database=Database(dump);database.schemas=project.schemas
    context['unresolved'].extend(frontend.unsupported)
    context['unresolved'].extend('Unsupported source route: '+message for message in project.route_warnings)
    context['unresolved'].extend(database.warnings)
    scenarios=[json.loads(path.read_text()) for path in sorted(args.scenarios.glob('*.json'))]
    prepare=time.perf_counter()-started
    initial_database=database_digest(database);initial_context=digest(context)
    expected=hashlib.sha256(args.expected.read_bytes()).hexdigest();runs=[];first_witness=None
    for repetition in range(args.repetitions):
        started=time.perf_counter();answer={'project':project.skeleton['project'],'scenarios':{}};evidence={};analysis=0.0;fingerprinting=0.0
        for scenario in scenarios:
            phase=time.perf_counter()
            block,detail=analyze(project,frontend,index,None,database,context,scenario,4,ContractGrounder)
            analysis+=time.perf_counter()-phase;phase=time.perf_counter()
            answer['scenarios'][scenario['id']]=block;evidence[scenario['id']]=witnesses(detail)
            fingerprinting+=time.perf_counter()-phase
        calculation=time.perf_counter()-started
        serialization_started=time.perf_counter()
        payload=(json.dumps(answer,ensure_ascii=False,indent=2)+'\n').encode()
        actual=hashlib.sha256(payload).hexdigest();witness_digest=digest(evidence)
        if first_witness is None:first_witness=witness_digest
        runs.append({'repetition':repetition+1,'analysis_seconds':analysis,'witness_fingerprinting_seconds':fingerprinting,'calculation_boundary_seconds':calculation,
            'submission_serialization_seconds':time.perf_counter()-serialization_started,
            'submission_sha256':actual,'matches_expected':actual==expected,'typed_witness_sha256':witness_digest,
            'matches_first_witness':witness_digest==first_witness,
            'initial_database_unchanged':initial_database==database_digest(database),
            'initial_context_unchanged':initial_context==digest(context)})
        print(json.dumps(runs[-1]),flush=True)
    result={'prepare_seconds':prepare,'index_constructions':1,'source_index_reused':True,
        'fresh_independent_scenario_state':True,'runs':runs,**peak_rss(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        'environment':{'python':platform.python_version(),'system':platform.system(),'machine':platform.machine()},
        'path_limit':4,'graph_policy':'observed-union','model_calls':0,'external_llm_api_calls':0,
        'target_applications_started':False,'excluded_phases':['full report serialization/writes','format/gold evaluation','audit and timing sidecars'],
        'os_cache_cleared':False}
    result['passed']=all(all(r[k] for k in ('matches_expected','matches_first_witness','initial_database_unchanged','initial_context_unchanged')) for r in runs)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
