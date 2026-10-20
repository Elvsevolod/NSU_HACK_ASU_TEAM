"""Model-free CLI. The source index is built once and reused across all scenarios."""
import argparse
from collections import Counter
from functools import partial
import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import sys
import time

from .__main__ import analyze, serial, validate
from .contracts import ContractGrounder, ContractIndex, read_static_context
from .frontend import Frontend
from .hashing import sha256, fingerprint
from .project import Project
from .state import Database
from .paths import run_paths


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'skeleton', 'context', 'scenarios', 'output', 'report'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--path-limit', type=int, default=4)
    parser.add_argument('--no-constraints', action='store_true')
    args = parser.parse_args()
    if args.path_limit < 1:
        parser.error('--path-limit must be positive')
    started = time.perf_counter()
    project = Project(args.skeleton, args.source)
    frontend = Frontend(project)
    retrieval = ContractIndex(project, frontend)
    context = read_static_context(project.skeleton.get('context', {}))
    context['unresolved'].extend('Unsupported source route: ' + message for message in project.route_warnings)
    dump = args.context / 'db-after-warmup.sql.gz' if args.context.is_dir() else args.context
    database = Database(dump)
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
              'source_fingerprint': source_digest,
              'contracts': len(retrieval.contracts), 'input_sha256': {
                  str(path): sha256(path) for path in (args.skeleton, dump, *paths)},
              'environment': {'python': platform.python_version(), 'platform': platform.platform(),
                  'packages': {name: importlib.metadata.version(name) for name in
                               ('tree-sitter', 'tree-sitter-java', 'tree-sitter-javascript')}}}
    report['constraints'] = not args.no_constraints
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def save():
        validate(project, submission)
        args.output.write_text(json.dumps(submission, ensure_ascii=False, indent=2) + '\n')
        report['elapsed_seconds'] = time.perf_counter() - started
        report['analysis_seconds'] = report['elapsed_seconds'] - prepared
        report['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
        report['submission_sha256'] = sha256(args.output)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=serial) + '\n')

    for scenario in scenarios:
        block, detail = analyze(project, frontend, retrieval, None, database, context, scenario,
                                args.path_limit, ContractGrounder,
                                partial(run_paths, constraints=not args.no_constraints))
        submission['scenarios'][scenario['id']] = block
        report['scenarios'][scenario['id']] = detail
        save()
    report['run_complete'] = True
    save()
    print(json.dumps({'seconds': report['elapsed_seconds'], 'preparation_seconds': prepared,
                      'edges': dict(Counter(e['relation'] for b in submission['scenarios'].values() for e in b['edges']))}))
