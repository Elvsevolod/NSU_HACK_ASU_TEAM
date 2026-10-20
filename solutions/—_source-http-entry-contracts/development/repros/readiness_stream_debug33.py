import runpy
import sys
from analyzer.engine import Engine
from analyzer.project import text

previous = Engine.stream_call


def observed(self, name, obj, args, receiver, reason, env, *extra):
    print('STREAM', name, type(obj).__name__, receiver, repr(obj)[:180], flush=True)
    return previous(self, name, obj, args, receiver, reason, env, *extra)


Engine.stream_call = observed
prior_call = Engine.call


def observed_call(self, node, env):
    name = text(node.child_by_field_name('name'))
    if name in ('stream', 'filter'):
        print('BEFORE', name, type(env.get('input')).__name__, repr(env.get('input')), flush=True)
    result = prior_call(self, node, env)
    if name in ('stream', 'filter'):
        print('AFTER', name, type(result).__name__, sorted(self.warnings), flush=True)
    return result


Engine.call = observed_call
sys.argv = ['checks/readiness_edge_probes33.py', '--output', 'benchmark/readiness-edge-probes-debug-02']
runpy.run_path(sys.argv[0], run_name='__main__')
