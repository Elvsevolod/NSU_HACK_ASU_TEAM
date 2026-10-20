"""Instrument invalidations/joins in a separate offline Python analysis process."""
import argparse
import json
from pathlib import Path
import runpy
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--code', type=Path, required=True)
    parser.add_argument('--diagnostic-output', type=Path, required=True)
    args, forwarded = parser.parse_known_args()
    if forwarded[:1] == ['--']:
        forwarded = forwarded[1:]
    sys.path.insert(0, str(args.code.resolve()))
    from analyzer.state import Database
    from analyzer.engine import Engine
    import analyzer.paths as paths
    import analyzer.__main__ as analysis
    events = []

    def stack():
        frame = sys._getframe(2)
        rows = []
        while frame and len(rows) < 9:
            rows.append({'file': Path(frame.f_code.co_filename).name,
                         'function': frame.f_code.co_name, 'line': frame.f_lineno})
            frame = frame.f_back
        return rows

    invalidate = Database.invalidate
    def observed_invalidate(database, rows):
        before = set(database.unknown_tables)
        invalidate(database, rows)
        events.append({'kind': 'invalidate', 'new_unknown': sorted(database.unknown_tables - before),
                       'resource_keys': sorted(k for k, v in database.tables.raw_items() if v is rows),
                       'stack': stack()})
    Database.invalidate = observed_invalidate
    fallback = Engine.fallback
    def observed_fallback(engine, method):
        before = set(engine.state.database.unknown_tables)
        fallback(engine, method)
        events.append({'kind': 'fallback', 'method': method,
                       'new_unknown': sorted(engine.state.database.unknown_tables - before),
                       'stack': stack()})
    Engine.fallback = observed_fallback
    join = paths.join_states
    def observed_join(states):
        result = join(states)
        events.append({'kind': 'join_states', 'before_unknown': [sorted(s.database.unknown_tables) for s in states],
                       'after_unknown': sorted(result.database.unknown_tables), 'stack': stack()})
        return result
    paths.join_states = observed_join
    analysis.join_states = observed_join
    execute = Engine.run
    def observed_run(engine, entry, params):
        start = len(events)
        before = sorted(engine.state.database.unknown_tables)
        result = execute(engine, entry, params)
        events.append({'kind': 'request_end', 'entry': entry, 'outcome': engine.outcome,
                       'start_event': start, 'before_unknown': before,
                       'after_unknown': sorted(engine.state.database.unknown_tables),
                       'decisions': engine.decisions})
        return result
    Engine.run = observed_run
    sys.argv = [str(args.code / 'offline_run.py'), *forwarded]
    try:
        runpy.run_path(str(args.code / 'offline_run.py'), run_name='__main__')
    finally:
        args.diagnostic_output.write_text(json.dumps({'schema': 'invalidation-join-trace/1',
            'instrumentation': 'observers only; original functions called with identical arguments',
            'events': events}, indent=2) + '\n')


if __name__ == '__main__':
    main()
