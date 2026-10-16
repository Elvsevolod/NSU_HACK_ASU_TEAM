"""Source-derived graph construction; reference scoring belongs to a separate process."""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import sys
import time

from .context import read_context
from .frontend import Frontend
from .grounding import Grounder
from .local_models import DenseEncoder, LocalParser, manifest_at, sha256
from .paths import run_paths, join_states
from .project import Project
from .retrieval import Retrieval
from .state import Database, ScenarioState, U


def serial(value):
    if value is U:
        return {'unknown': True}
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, set):
        return sorted(value)
    if hasattr(value, 'type') and hasattr(value, 'start_point'):
        return {'source_node': value.type, 'line': value.start_point.row + 1}
    raise TypeError(type(value).__name__)


def pack(edges, sid):
    return [{'source': 'scenario:' + sid if relation == 'executes' else source,
             'relation': relation, 'target': target} for source, relation, target in sorted(edges)]


def validate(project, submission):
    for sid, block in submission['scenarios'].items():
        seen = set()
        for e in block['edges']:
            source, relation, target = e['source'], e['relation'], e['target']
            assert relation in ('executes', 'calls', 'remote', 'data')
            assert source == 'scenario:' + sid if relation == 'executes' else source in project.methods
            assert target in project.nodes
            assert project.nodes[target]['kind'] == ('data_resource' if relation == 'data' else 'method')
            assert (source, relation, target) not in seen
            seen.add((source, relation, target))


def source_grounds(project, edge, reasons):
    locations, rules = [], set()
    for reason in sorted(reasons):
        site = project.nodes.get(reason, {})
        if site.get('kind') == 'call_site':
            locations.append({'file': site.get('file') or project.methods.get(site['method'], {}).get('file'),
                              'line': site['line'], 'call_site': reason})
            wiring = project.edges.get(reason, {})
            if wiring.get('runtime_dispatch'):
                rules.add('Java hierarchy dispatch constrained by Spring profiles and field qualifiers')
        if 'callback' in reason or 'filter' in reason:
            rules.add(reason)
        if 'closure' in reason:
            rules.add('Conservative static may-call closure')
    method = edge[0] if edge[0] else edge[2]
    meta = project.methods.get(method, {})
    if meta:
        locations.append({'file': meta['file'], 'line': meta['line'], 'method': method})
    if edge[1] == 'data':
        rules.add('Spring Data repository operation with source entity and primary-key mapping')
    elif edge[1] == 'remote':
        rules.add('Static HTTP wiring refined by declared Spring route and URL when known')
    elif not rules:
        rules.add('Source method invocation or scenario HTTP entry')
    return {'source_locations': locations, 'applied_rules': sorted(rules)}


def analyze(project, frontend, retrieval, parser, database, context, scenario, path_limit=8):
    grounder = Grounder(project, frontend, retrieval, parser, context)
    initial = ScenarioState(database, context)
    initial.now = context['clock'] if context.get('clock') else U
    states = [(initial, set(), set())]
    evidence, steps, unresolved = {}, [], list(context['unresolved'])
    scenario_text = scenario.get('title', '') + '\n' + scenario.get('description', '')
    for step in scenario['steps']:
        next_states, details = [], []
        language_state = join_states([item[0] for item in states]) if len(states) > 1 else states[0][0]
        _, language_selection = grounder.step(step['action'], language_state, scenario_text)
        template = language_selection['proposal'] or {'hypotheses': [], 'unresolved': language_selection['unresolved']}
        for state, previous_edges, previous_must in states:
            proposals, selection = grounder.step(step['action'], state, scenario_text, prepared_proposal=template)
            unresolved.extend(selection['unresolved'])
            if not proposals:
                unresolved.append('No supported request for step ' + str(step['n']))
                next_states.append((state, previous_edges, previous_must))
            for proposal in proposals:
                outcomes = run_paths(project, proposal['state'], proposal['entry'], proposal['params'], path_limit)
                for outcome in outcomes:
                    engine, result, following = outcome['engine'], outcome['result'], outcome['state']
                    if proposal['site']:
                        frontend.apply_response(proposal['site'], result, following)
                    following.history.append({'step': step['n'], 'action': step['action'],
                                              'entry': proposal['entry'], 'parameters': proposal['params'],
                                              'result': deepcopy(result)})
                    all_edges = previous_edges | engine.edges
                    certain = set() if engine.approximate or proposal['unresolved'] else engine.edges
                    next_states.append((following, all_edges, previous_must | certain))
                    for edge, reasons in engine.evidence.items():
                        evidence.setdefault(edge, []).append({'step': step['n'], 'entry': proposal['entry'],
                            'ui_site': proposal['site']['id'] if proposal['site'] else None,
                            'alternative': len(details), 'source_sites': sorted(reasons),
                            'approximate': engine.approximate, **source_grounds(project, edge, reasons)})
                    problems = proposal['unresolved'] + sorted(engine.warnings) + following.limitations
                    unresolved.extend(problems)
                    details.append({'entry': proposal['entry'], 'parameters': proposal['params'],
                                    'grounding_reason': proposal['reason'],
                                    'grounding_repairs': language_selection.get('repairs', []),
                                    'retrieval_candidates': selection['candidates'],
                                    'ui_site': proposal['site']['id'] if proposal['site'] else None,
                                    'bindings': proposal['bindings'], 'result': result,
                                    'path_conditions': engine.conditions, 'decisions': outcome['decisions'],
                                    'outcome': engine.outcome, 'unresolved': problems,
                                    'data_operations': engine.data_operations,
                                    'state_after': following.snapshot(), 'edges': pack(engine.edges, scenario['id'])})
        if len(next_states) > path_limit:
            union = set().union(*(item[1] for item in next_states))
            must = set.intersection(*(item[2] for item in next_states))
            joined = join_states([item[0] for item in next_states])
            next_states = [(joined, union, must)]
            unresolved.append('Scenario state budget exceeded; widened conflicting states, retained graph union')
        states = next_states
        steps.append({'n': step['n'], 'action': step['action'], 'alternatives': details})
        print(scenario['id'], 'step', step['n'], 'paths', len(states), flush=True)
    union = set().union(*(item[1] for item in states))
    certain = set.intersection(*(item[2] for item in states)) if states else set()
    return {'edges': pack(union, scenario['id'])}, {
        'analysis_status': 'partial' if unresolved else 'complete_in_supported_model',
        'certainty_scope': 'relative to supplied inputs, proposed bindings and supported semantics; not a runtime trace',
        'confirmed': pack(certain, scenario['id']), 'possible': pack(union - certain, scenario['id']),
        'unresolved': sorted(set(unresolved)), 'steps': steps,
        'evidence': [{'edge': pack({edge}, scenario['id'])[0], 'grounds': grounds}
                     for edge, grounds in sorted(evidence.items())]}


def main():
    ap = argparse.ArgumentParser()
    for name in ('source', 'skeleton', 'context', 'scenarios', 'output', 'report', 'model-manifest'):
        ap.add_argument('--' + name, type=Path, required=True)
    ap.add_argument('--index', type=Path)
    ap.add_argument('--cpu', action='store_true')
    args = ap.parse_args()
    started = time.perf_counter()
    project = Project(args.skeleton, args.source)
    frontend = Frontend(project)
    retrieval = Retrieval(project, frontend)
    paths = sorted(args.scenarios.glob('*.json')) if args.scenarios.is_dir() else [args.scenarios]
    scenarios = [json.loads(p.read_text()) for p in paths]
    if not scenarios or any(s['project'] != project.skeleton['project'] for s in scenarios):
        ap.error('Missing scenarios or project mismatch')
    if len({s['id'] for s in scenarios}) != len(scenarios):
        ap.error('Duplicate scenario identifiers')
    manifest = manifest_at(args.model_manifest)
    if args.index:
        retrieval.load(args.index, project)
    else:
        encoder = DenseEncoder(manifest['embedding'])
        retrieval.prepare([step['action'] for s in scenarios for step in s['steps']], encoder)
        encoder.close()
    parser = LocalParser(manifest['parser'], cpu=args.cpu, trace_path=args.report.with_name(args.report.stem + '-model-trace.jsonl'))
    context = read_context(project.skeleton.get('context', {}), parser,
                           {key for mid, _, _ in project.ix.handlers for key in project.request_fields(mid)})
    dump = args.context / 'db-after-warmup.sql.gz' if args.context.is_dir() else args.context
    database = Database(dump)
    database.schemas = project.schemas
    submission = {'project': project.skeleton['project'], 'scenarios': {}}
    report = {'context': context, 'frontend_warnings': frontend.warnings, 'scenarios': {},
              'source_parse_errors': project.source_errors, 'model_manifest': manifest,
              'run_complete': False, 'requested_scenarios': [s['id'] for s in scenarios],
              'environment': {'python': platform.python_version(), 'platform': platform.platform(),
                  'packages': {name: importlib.metadata.version(name) for name in
                               ('tree-sitter', 'tree-sitter-java', 'tree-sitter-javascript', 'sentence-transformers', 'llama-cpp-python')}}}
    report['input_sha256'] = {str(p): sha256(p) for p in (args.skeleton, dump, *paths)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def save_progress():
        validate(project, submission)
        args.output.write_text(json.dumps(submission, ensure_ascii=False, indent=2) + '\n')
        report['elapsed_seconds'] = time.perf_counter() - started
        report['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
        report['submission_sha256'] = sha256(args.output)
        report['model_calls'] = parser.calls
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=serial) + '\n')

    for scenario in scenarios:
        block, detail = analyze(project, frontend, retrieval, parser, database, context, scenario)
        submission['scenarios'][scenario['id']] = block
        report['scenarios'][scenario['id']] = detail
        save_progress()
    parser.close()
    report['run_complete'] = True
    save_progress()
    print('Finished', report['elapsed_seconds'], 'seconds;', dict(Counter(e['relation'] for b in submission['scenarios'].values() for e in b['edges'])))


if __name__ == '__main__':
    main()
