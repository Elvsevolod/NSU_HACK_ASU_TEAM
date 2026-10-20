"""Model-free CLI. The source index is built once and reused across all scenarios."""
import argparse
from collections import Counter
from functools import partial
import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import time

from .__main__ import analyze, serial, validate
from .contracts import ContractGrounder, ContractIndex, read_static_context
from .frontend import Frontend
from .hashing import sha256, fingerprint
from .project import Project
from .state import Database
from .paths import run_paths
from .measurements import peak_rss
from .reporting import dump_report


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'skeleton', 'context', 'scenarios', 'output', 'report'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--path-limit', type=int, default=4)
    parser.add_argument('--no-constraints', action='store_true')
    parser.add_argument('--graph-policy', choices=('observed-union', 'confirmed'), default='observed-union')
    parser.add_argument('--retrieval',choices=('baseline','lexical','offline-dense'),default='baseline')
    parser.add_argument('--model-snapshot',type=Path)
    args = parser.parse_args()
    if args.path_limit < 1:
        parser.error('--path-limit must be positive')
    started = time.perf_counter()
    project = Project(args.skeleton, args.source)
    frontend = Frontend(project)
    if args.retrieval=='lexical':
        from .lexical_retrieval import LexicalContractIndex
        retrieval=LexicalContractIndex(project,frontend)
    elif args.retrieval=='offline-dense':
        from .offline_retrieval import OfflineDenseIndex
        retrieval=OfflineDenseIndex(project,frontend,args.model_snapshot)
    else:retrieval = ContractIndex(project, frontend)
    context = read_static_context(project.skeleton.get('context', {}))
    context['unresolved'].extend(frontend.unsupported)
    context['unresolved'].extend('Unsupported source route: ' + message for message in project.route_warnings)
    dump = args.context / 'db-after-warmup.sql.gz' if args.context.is_dir() else args.context
    database = Database(dump)
    context['unresolved'].extend(database.warnings)
    database.schemas = project.schemas
    paths = sorted(args.scenarios.glob('*.json')) if args.scenarios.is_dir() else [args.scenarios]
    scenarios = [json.loads(path.read_text()) for path in paths]
    if not scenarios or any(s['project'] != project.skeleton['project'] for s in scenarios):
        parser.error('Missing scenarios or project mismatch')
    if len({s['id'] for s in scenarios}) != len(scenarios):
        parser.error('Duplicate scenario identifiers')
    source_digest = fingerprint(project)
    prepared = time.perf_counter() - started
    submission = {'project': project.skeleton['project'], 'scenarios': {}}
    report = {'context': context, 'scenarios': {}, 'run_complete': False,
              'requested_scenarios': [s['id'] for s in scenarios],
              'preparation_seconds': prepared, 'model_calls': [], 'path_limit': args.path_limit,
              'frontend_warnings': frontend.warnings, 'source_parse_errors': project.source_errors,
              'route_warnings': project.route_warnings,
              'handler_registration': project.handler_registration,
              'source_fingerprint': source_digest,
              'contracts': len(retrieval.contracts), 'input_sha256': {
                  str(path): sha256(path) for path in (args.skeleton, dump, *paths)},
              'environment': {'python': platform.python_version(), 'platform': '-'.join((platform.system(),platform.release(),platform.machine())),
                  'packages': {name: importlib.metadata.version(name) for name in
                               ('tree-sitter', 'tree-sitter-java', 'tree-sitter-javascript', 'html5lib', 'webencodings', 'six')}}}
    report['constraints'] = not args.no_constraints
    report['retrieval_profile']=args.retrieval
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    timings={'analysis_seconds':0.0,'submission_validation_seconds':0.0,
             'submission_serialization_seconds':0.0,'report_serialization_seconds':0.0}

    def save():
        phase=time.perf_counter()
        validate(project, submission)
        timings['submission_validation_seconds']+=time.perf_counter()-phase
        phase=time.perf_counter()
        args.output.write_text(json.dumps(submission, ensure_ascii=False, indent=2) + '\n')
        timings['submission_serialization_seconds']+=time.perf_counter()-phase
        report['elapsed_seconds'] = time.perf_counter() - started
        report['analysis_seconds'] = timings['analysis_seconds']
        report['elapsed_boundary']='before current report write; complete phase timings are in the adjacent -timings.json'
        report['serialization_seconds_before_current_report_write']={key:value for key,value in timings.items() if 'serialization' in key}
        report.update(peak_rss(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
        report['submission_sha256'] = sha256(args.output)
        report['retrieval_model_calls']=getattr(retrieval,'model_calls',0)
        phase=time.perf_counter()
        with args.report.open('w') as stream:
            dump_report(report,stream,ensure_ascii=True,separators=(',',':'),default=serial)
            stream.write('\n')
        timings['report_serialization_seconds']+=time.perf_counter()-phase

    for scenario in scenarios:
        phase=time.perf_counter()
        block, detail = analyze(project, frontend, retrieval, None, database, context, scenario,
                                args.path_limit, ContractGrounder,
                                partial(run_paths, constraints=not args.no_constraints), args.graph_policy)
        timings['analysis_seconds']+=time.perf_counter()-phase
        submission['scenarios'][scenario['id']] = block
        report['scenarios'][scenario['id']] = detail
        save()
    report['run_complete'] = True
    save()
    timings.update(preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-started,
                   end_boundary='after final report write, before timing/audit sidecars',
                   index_constructions=1,scenario_count=len(scenarios),model_calls=getattr(retrieval,'model_calls',0),external_llm_api_calls=0)
    timings.update(peak_rss(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
    args.report.with_name(args.report.stem+'-timings.json').write_text(json.dumps(timings,indent=2)+'\n')
    print(json.dumps({'seconds': report['elapsed_seconds'], 'preparation_seconds': prepared,
                      'edges': dict(Counter(e['relation'] for b in submission['scenarios'].values() for e in b['edges']))}))
