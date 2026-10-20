"""Source-derived graph construction; reference scoring belongs to a separate process."""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal

from .grounding import Grounder
from .paths import run_paths, join_states
from .state import ScenarioState, U, JS_UNDEFINED
from .selection import selected_objects
from .request import BoundParameters, grounded_request, MISSING


def serial(value):
    if value is U:
        return {'unknown': True}
    if value is JS_UNDEFINED:
        return {'javascript_undefined': True}
    if value is MISSING:
        return {'missing': True}
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


def analyze(project, frontend, retrieval, parser, database, context, scenario, path_limit=8, grounder_type=Grounder, path_runner=run_paths, graph_policy='observed-union'):
    grounder = grounder_type(project, frontend, retrieval, parser, context)
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
                if not state.analysis_assumptions:
                    state.analysis_assumptions.append('step '+str(step['n'])+': no supported source request')
                state.unscoped_state_assumptions.append('step '+str(step['n'])+': unknown preceding request effects')
                next_states.append((state, previous_edges, previous_must))
            for proposal in proposals:
                request = proposal.get('request') or grounded_request(project, proposal['entry'], proposal['params'],
                    {**proposal['bindings'], '__assumptions__': proposal['unresolved']},
                    actor=proposal.get('actor', U), session=proposal['state'].browser.get('session',
                        {'storage':proposal['state'].browser['storage'],'actor':proposal['state'].browser.get('actor',U)}),
                    media_type=(proposal.get('site') or {}).get('content_type'),
                    source_headers=frontend.request_headers(proposal.get('site'),proposal['state']))
                inputs = BoundParameters(proposal['params'], request) if request else proposal['params']
                outcomes = path_runner(project, proposal['state'], proposal['entry'], inputs, path_limit)
                for outcome in outcomes:
                    engine, result, following = outcome['engine'], outcome['result'], outcome['state']
                    following.input_journal.append({'step':step['n'],'action':step['action'],'entry':proposal['entry'],
                        'actor':proposal.get('actor',U),'parameters':deepcopy(proposal['params']),'bindings':deepcopy(proposal['bindings'])})
                    if proposal['site'] and engine.outcome in ('returned','HTTP error response','HTTP binding failure','request stopped by filter','uncaught application exception'):
                        initial_responses=[response for response in engine.http_responses if response['request']==1]
                        status=initial_responses[-1]['status'] if initial_responses else U
                        if status is not U:frontend.apply_response(proposal['site'], result, following,status)
                    def observation(obj):
                        rid = obj['__resource__']
                        rows = following.database.rows(project.nodes[rid])
                        keys = project.id_fields.get(rid, [])
                        if rows is None or not keys:
                            return 'unknown'
                        from .models import key_equal
                        comparisons = [key_equal({key:project.materialize(following.database,rid,row).get(key,U) for key in keys},
                                                 {key:obj.get(key,U) for key in keys}) for row in rows]
                        return 'modeled_present' if True in comparisons else 'unknown' if U in comparisons else 'modeled_absent'
                    creations = [{**deepcopy(obj), '__persistence_observation__':observation(obj)} for obj in engine.created_objects]
                    if any(obj['__persistence_observation__'] == 'unknown' for obj in creations):
                        following.limitations.append('Historical creation identity retained; current persistence is unknown')
                    if any(obj['__persistence_observation__'] == 'modeled_absent' for obj in creations):
                        following.limitations.append('Historical creation identity retained; row is absent from the modeled current table')
                    following.history.append({'step': step['n'], 'action': step['action'],
                                              'ui_scope':(proposal.get('site') or {}).get('reference_scope'),
                                              'entry': proposal['entry'], 'parameters': proposal['params'],
                                              'created_objects': creations,
                                              'result': deepcopy(result)})
                    from .history_refs import references
                    following.history[-1]['response_refs'] = references(project, following.history[-1], len(following.history)-1)
                    following.history[-1]['selected_objects'] = selected_objects(
                        project, proposal['entry'], step['action'], following.history, proposal['params'],
                        ui_scope=(proposal.get('site') or {}).get('reference_scope'))
                    all_edges = previous_edges | engine.edges
                    if (engine.approximate or proposal['unresolved'] or following.limitations) and not following.analysis_assumptions:
                        following.analysis_assumptions.append('step '+str(step['n'])+': unresolved source/request/state assumptions')
                    certain = engine.confirmed_edges
                    next_states.append((following, all_edges, previous_must | certain))
                    for edge, reasons in engine.evidence.items():
                        evidence.setdefault(edge, []).append({'step': step['n'], 'entry': proposal['entry'],
                            'ui_site': proposal['site']['id'] if proposal['site'] else None,
                            'alternative': len(details), 'source_sites': sorted(reasons),
                            'approximate': engine.approximate, **source_grounds(project, edge, reasons)})
                    problems = proposal['unresolved'] + sorted(engine.warnings) + following.limitations
                    if state.analysis_assumptions:
                        problems.append('State depends on earlier analysis assumptions: '+';'.join(state.analysis_assumptions))
                    unresolved.extend(problems)
                    details.append({'entry': proposal['entry'], 'parameters': proposal['params'],
                                    'grounding_reason': proposal['reason'],
                                    'grounding_repairs': language_selection.get('repairs', []),
                                    'retrieval_candidates': selection['candidates'],
                                    'ui_site': proposal['site']['id'] if proposal['site'] else None,
                                    'bindings': proposal['bindings'], 'result': result,
                                    'request': request.record() if request else None,
                                    'created_objects': creations,
                                    'path_conditions': engine.conditions, 'decisions': outcome['decisions'],
                                    'pruned_paths': outcome.get('pruned_paths', []),
                                    'outcome': engine.outcome, 'unresolved': problems,
                                    'operation_issues':[{'kind':kind,'operation':name,'occurrences':count}
                                                        for (kind,name),count in sorted(engine.operation_issues.items())],
                                    'data_operations': engine.data_operations,
                                    'events': [{**event, 'edge': pack({tuple(event['edge'])}, scenario['id'])[0]} for event in engine.events],
                                    'assumptions': {key:value for value,key in engine.assumption_registry.items()},
                                    'event_contexts': engine.event_contexts,
                                    'requests': engine.request_events,
                                    'responses': engine.http_responses,
                                    'call_effects': engine.effect_events,
                                    'persistence': engine.persistence_events,
                                    'static_candidates': pack(engine.candidate_edges, scenario['id']),
                                    'state_after': following.snapshot(), 'edges': pack(engine.edges, scenario['id'])})
        if len(next_states) > path_limit:
            union = set().union(*(item[1] for item in next_states))
            must = set.intersection(*(item[2] for item in next_states))
            joined = join_states([item[0] for item in next_states])
            next_states = [(joined, union, must)]
            unresolved.append('Scenario state budget exceeded; widened conflicting states, retained graph union')
        states = next_states
        steps.append({'n': step['n'], 'action': step['action'], 'selection': language_selection,
                      'alternatives': details})
        print(scenario['id'], 'step', step['n'], 'paths', len(states), flush=True)
    union = set().union(*(item[1] for item in states))
    certain = set.intersection(*(item[2] for item in states)) if states else set()
    if graph_policy not in ('observed-union', 'confirmed'):
        raise ValueError('unknown graph export policy: '+graph_policy)
    return {'edges': pack(certain if graph_policy == 'confirmed' else union, scenario['id'])}, {
        'graph_policy': graph_policy,
        'analysis_status': 'partial' if unresolved else 'complete_in_supported_model',
        'certainty_scope': 'relative to supplied inputs, proposed bindings and supported semantics; not a runtime trace',
        'confirmed': pack(certain, scenario['id']), 'possible': pack(union - certain, scenario['id']),
        'unresolved': sorted(set(unresolved)), 'steps': steps,
        'evidence': [{'edge': pack({edge}, scenario['id'])[0], 'grounds': grounds}
                     for edge, grounds in sorted(evidence.items())]}


def main():
    from .portable import main as portable_main
    portable_main()


if __name__ == '__main__':
    main()
