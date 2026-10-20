"""Replay only the Python analyzer to isolate alternative abstract states."""
from copy import deepcopy
from .engine import AlternativeRequired, Engine, merge
from .constraints import InfeasiblePath


def join_states(states):
    """Widen conflicting table contents; never choose one incompatible write."""
    joined = deepcopy(states[0])
    for other in states[1:]:
        for key in set(joined.database.tables) | set(other.database.tables):
            if joined.database.tables.get(key) != other.database.tables.get(key):
                joined.database.unknown_tables.add(key)
        joined.database.unknown_tables.update(other.database.unknown_tables)
        joined.browser = merge(joined.browser, other.browser)
        joined.history = [merge(a, b) for a, b in zip(joined.history, other.history)]
        joined.symbol_sequence = max(joined.symbol_sequence, other.symbol_sequence)
        joined.input_sequence = max(joined.input_sequence, other.input_sequence)
    joined.limitations.append('state budget widening: conflicting database tables are unknown')
    return joined


def run_paths(project, state, entry, params, limit=8, constraints=True):
    pending, completed, pruned = [{}], [], []
    while pending:
        decisions = pending.pop(0)
        engine = Engine(project, deepcopy(state), decisions=decisions, constraints=constraints)
        try:
            result = engine.run(entry, params)
        except InfeasiblePath as conflict:
            pruned.append({'reason': str(conflict), 'decisions': decisions, 'conditions': engine.conditions})
            continue
        except AlternativeRequired as branch:
            if len(completed) + len(pending) + len(branch.choices) <= limit:
                pending.extend({**decisions, branch.key: choice} for choice in branch.choices)
                continue
            engine = Engine(project, deepcopy(state), decisions=decisions, conservative=True, constraints=constraints)
            result = engine.run(entry, params)
        completed.append({'engine': engine, 'result': result, 'decisions': decisions,
                          'state': engine.state, 'approximate': engine.approximate})
    for outcome in completed:
        outcome['pruned_paths'] = pruned
    return completed
