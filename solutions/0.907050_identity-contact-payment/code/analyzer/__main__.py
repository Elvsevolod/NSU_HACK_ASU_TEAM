import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import time

from .engine import Engine, member
from .grounding import Grounder, trip_number
from .project import Project
from .state import Database, ScenarioState, U


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(project, submission):
    for sid, block in submission['scenarios'].items():
        seen = set()
        for edge in block['edges']:
            source, relation, target = (edge[k] for k in ('source', 'relation', 'target'))
            assert relation in ('executes', 'calls', 'remote', 'data')
            if relation == 'executes':
                assert source == 'scenario:' + sid
            else:
                assert project.nodes[source]['kind'] == 'method'
            assert project.nodes[target]['kind'] == ('data_resource' if relation == 'data' else 'method')
            assert (source, relation, target) not in seen
            seen.add((source, relation, target))


def analyze(project, grounder, database, scenario):
    state = ScenarioState(database)
    edges, steps = set(), []
    evidence = {}
    for step in scenario['steps']:
        action = step['action']
        entry, params, selection = grounder.step(action, state)
        before = state.snapshot()
        engine = Engine(project, state)
        result = engine.run(entry, params)
        data = member(result, 'data')
        method_name = project.methods[entry]['name']
        if method_name == 'registerUser' and member(result, 'status') == 1 and isinstance(data, dict):
            state.user, state.account_id = member(data, 'userName'), member(data, 'userId')
            state.last_contact = U
            state.contacts, state.new_contacts = [], []
        if method_name == 'createNewContacts' and member(result, 'status') == 1 and isinstance(data, dict):
            state.new_contacts.append(deepcopy(data))
            state.last_contact = member(data, 'id')
        if method_name in ('getByCheapest', 'getByQuickest', 'getByMinStation') and isinstance(data, list):
            state.searches[method_name] = deepcopy(data)
        if method_name == 'addRoute' and isinstance(data, dict):
            state.created_route = member(data, 'id')
        if method_name == 'getFoodStoresOfStation' and isinstance(data, list) and data:
            store = data[0]
            state.last_food = {'stationName': params.get('stationName', U), 'storeName': member(store, 'storeName')}
            foods = member(store, 'foodList')
            if isinstance(foods, list) and foods:
                state.last_food.update(foodName=member(foods[0], 'foodName'), foodPrice=member(foods[0], 'price'))
        if method_name == 'getAllFood' and member(result, 'status') == 1:
            foods = member(data, 'trainFoodList')
            if isinstance(foods, list) and foods:
                state.last_food = {'foodName': member(foods[0], 'foodName'), 'foodPrice': member(foods[0], 'price')}
        if project.methods[entry]['module'] == 'ts-consign-service' and method_name in ('findByOrderId', 'updateConsign') and isinstance(data, dict):
            state.last_consign = deepcopy(data)
        if project.methods[entry]['module'] in ('ts-travel-service', 'ts-travel2-service'):
            if isinstance(data, list): state.search_results = deepcopy(data)
            candidate = data[0] if isinstance(data, list) and data else data
            trip = member(candidate, 'tripId')
            if trip is not U:
                state.last_trip = trip_number(trip)
            if isinstance(data, list) and data:
                start, end = member(candidate, 'startStation'), member(candidate, 'terminalStation')
                if isinstance(start, str) and isinstance(end, str):
                    # The booking UI forwards station names from the selected result.
                    for key in ('startPlace', 'startingPlace', 'startStation', 'startStationName', 'from'):
                        state.route[key] = start
                    for key in ('endPlace', 'endStation', 'endStationName', 'to'):
                        state.route[key] = end
        if project.methods[entry]['name'] == 'findContactsByAccountId' and isinstance(data, list) and data:
            state.contacts = deepcopy(data)
            state.last_contact = member(data[0], 'id')
        edges.update(engine.edges)
        for edge, reasons in engine.evidence.items():
            evidence.setdefault(edge, set()).update(reasons)
        steps.append({'n': step['n'], 'action': action, 'entry': entry,
                      'parameters': params, 'selection': selection,
                      'state_before': before, 'state_after': state.snapshot(),
                      'result': deepcopy(result), 'conditions': engine.conditions,
                      'warnings': sorted(engine.warnings), 'method_contexts': engine.calls,
                      'edge_counts': dict(Counter(e[1] for e in engine.edges)),
                      'edges': [{'source': source, 'relation': relation, 'target': target} for source, relation, target in sorted(engine.edges)]})
    sid = scenario['id']
    packed = [{'source': 'scenario:' + sid if relation == 'executes' else source,
               'relation': relation, 'target': target} for source, relation, target in sorted(edges)]
    report = {'steps': steps, 'evidence': [
        {'source': 'scenario:' + sid if relation == 'executes' else source,
         'relation': relation, 'target': target, 'reasons': sorted(reasons)}
        for (source, relation, target), reasons in sorted(evidence.items())]}
    return {'edges': packed}, report


def main():
    parser = argparse.ArgumentParser(description='Offline scenario graph prediction; never launches Train Ticket.')
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--skeleton', type=Path, required=True)
    parser.add_argument('--context', type=Path, required=True)
    parser.add_argument('--scenarios', type=Path, required=True, help='Directory of scenario JSON files, or one scenario JSON')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    project = Project(args.skeleton, args.source)
    grounder = Grounder(project)
    dump = args.context / 'db-after-warmup.sql.gz' if args.context.is_dir() else args.context
    database = Database(dump)
    paths = sorted(args.scenarios.glob('*.json')) if args.scenarios.is_dir() else [args.scenarios]
    if not paths:
        parser.error('No scenario files found')
    submission = {'project': project.skeleton['project'], 'scenarios': {}}
    report = {'python': platform.python_version(), 'platform': platform.platform(),
              'dependencies': {name: importlib.metadata.version(name) for name in ('tree-sitter', 'tree-sitter-java')},
              'input_sha256': {str(p): digest(p) for p in [args.skeleton, dump, *paths]},
              'database_rows': database.summary(), 'source_parse_errors': project.source_errors,
              'indexed_methods': len(project.ast), 'ui_sites': grounder.ui_sites, 'scenarios': {}}
    for path in paths:
        scenario = json.loads(path.read_text())
        if scenario.get('project') != submission['project']:
            parser.error('Scenario project does not match skeleton')
        if scenario['id'] in submission['scenarios']:
            parser.error('Duplicate scenario ID')
        block, detail = analyze(project, grounder, database, scenario)
        submission['scenarios'][scenario['id']] = block
        report['scenarios'][scenario['id']] = detail
        print(scenario['id'], dict(Counter(e['relation'] for e in block['edges'])), flush=True)
    validate(project, submission)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(submission, ensure_ascii=False, indent=2) + '\n')
    report['elapsed_seconds'] = time.perf_counter() - started
    report['submission_sha256'] = digest(args.output)
    report['format_valid'] = True
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=True, indent=2, default=lambda o: str(o)) + '\n')
    print(f"Finished in {report['elapsed_seconds']:.3f}s; {args.output}")


if __name__ == '__main__':
    main()
