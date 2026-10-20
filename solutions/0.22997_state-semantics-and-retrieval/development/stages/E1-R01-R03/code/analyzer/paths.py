"""Replay only the Python analyzer to isolate alternative abstract states."""
from copy import deepcopy
from .engine import AlternativeRequired, CompletionRequired, Engine, merge
from .constraints import InfeasiblePath
from .heap_join import clone_execution


def join_states(states):
    """Widen conflicting table contents; never choose one incompatible write."""
    joined = deepcopy(states[0])
    for other in states[1:]:
        for key in set(joined.database.tables) | set(other.database.tables):
            if joined.database.tables.raw_get(key) != other.database.tables.raw_get(key):
                joined.database.unknown_tables.add(key)
        joined.database.unknown_tables.update(other.database.unknown_tables)
        joined.browser = merge(joined.browser, other.browser)
        joined.actor_browsers = merge(joined.actor_browsers,other.actor_browsers)
        joined.bean_instances = merge(joined.bean_instances,other.bean_instances)
        joined.static_fields = merge(joined.static_fields,other.static_fields)
        joined.class_initialization = merge(joined.class_initialization,other.class_initialization)
        joined.input_journal=[merge(a,b) for a,b in zip(joined.input_journal,other.input_journal)]
        joined.history = [merge(a, b) for a, b in zip(joined.history, other.history)]
        joined.symbol_sequence = max(joined.symbol_sequence, other.symbol_sequence)
        joined.input_sequence = max(joined.input_sequence, other.input_sequence)
        joined.analysis_assumptions = sorted(set(joined.analysis_assumptions+other.analysis_assumptions))
        joined.unscoped_state_assumptions = sorted(set(joined.unscoped_state_assumptions+other.unscoped_state_assumptions))
        for resource, assumptions in other.resource_assumptions.items():
            joined.resource_assumptions[resource] = sorted(set(joined.resource_assumptions.get(resource, [])+assumptions))
        for unit, frame in other.transactions.items():
            if unit not in joined.transactions:
                joined.transactions[unit] = deepcopy(frame)
                joined.transactions[unit]['supported'] = False
                continue
            target = joined.transactions[unit]
            target['writes'].update(frame['writes'])
            target['supported'] = target['supported'] and frame['supported']
            for operation in frame['pending']:
                if operation not in target['pending']:target['pending'].append(deepcopy(operation))
            target['managed'] = merge(target['managed'],frame['managed'])
        joined.limitations = list(dict.fromkeys(joined.limitations+other.limitations))
    joined.limitations.append('state budget widening: conflicting database tables are unknown')
    return joined


def run_paths(project, state, entry, params, limit=8, constraints=True, entry_boundary='http'):
    if entry_boundary not in ('http', 'application_after_authentication'):
        raise ValueError('Unsupported entry boundary: '+str(entry_boundary))
    pending, completed, pruned = [{}], [], []
    completion_splits=0
    completion_budget=max(8,limit)
    while pending:
        decisions = pending.pop(0)
        (owned_state,owned_params),_ = clone_execution(state,params)
        engine = Engine(project, owned_state, decisions=decisions, constraints=constraints)
        engine.path_replay = True
        engine.entry_boundary = entry_boundary
        try:
            result = engine.run(entry, owned_params)
        except InfeasiblePath as conflict:
            pruned.append({'reason': str(conflict), 'decisions': decisions, 'conditions': engine.conditions})
            continue
        except AlternativeRequired as branch:
            completion=isinstance(branch,CompletionRequired)
            if (completion and completion_splits+len(branch.choices)<=completion_budget or
                    not completion and len(completed)+len(pending)+len(branch.choices)<=limit):
                if completion:completion_splits+=len(branch.choices)
                pending.extend({**decisions, branch.key: choice} for choice in branch.choices)
                continue
            (owned_state,owned_params),_ = clone_execution(state,params)
            engine = Engine(project, owned_state, decisions=decisions, conservative=True, constraints=constraints)
            engine.path_replay = True
            engine.entry_boundary = entry_boundary
            engine.allow_completion_splits=completion_splits<completion_budget
            try:
                result = engine.run(entry, owned_params)
            except CompletionRequired as completion:
                if completion_splits+len(completion.choices)<=completion_budget:
                    completion_splits+=len(completion.choices)
                    pending.extend({**decisions,completion.key:choice} for choice in completion.choices)
                    continue
                (owned_state,owned_params),_=clone_execution(state,params)
                engine=Engine(project,owned_state,decisions=decisions,conservative=True,constraints=constraints)
                engine.path_replay=True;engine.allow_completion_splits=False
                engine.entry_boundary=entry_boundary
                result=engine.run(entry,owned_params)
        completed.append({'engine': engine, 'result': result, 'decisions': decisions,
                          'state': engine.state, 'approximate': engine.approximate})
    for outcome in completed:
        outcome['pruned_paths'] = pruned
    return completed
