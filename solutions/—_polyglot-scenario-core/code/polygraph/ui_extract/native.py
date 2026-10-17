"""QuickJS-NG semantics for generated, pure operations on concrete values.

No target scripts, modules, callbacks or host functions are evaluated here.
Only parser-confirmed primitive literals and our fixed operation table enter
the context. Abstract values never become invented JavaScript strings.
"""
import json
import math
import threading
import time

import quickjs
from tree_sitter import Language, Parser
import tree_sitter_javascript

from .state import JS_UNDEFINED, U, SymbolicValue, JSONObject


class JavaScriptError(Exception):
    def __init__(self, name, message):
        self.name, self.message = name, message
        super().__init__(name + ': ' + message)


class NativeUnavailable(Exception):
    pass


OPERATORS = ('+', '-', '*', '/', '%', '**', '<', '<=', '>', '>=', '==', '===', '!=', '!==', '&', '|', '^', '<<', '>>', '>>>')
METHODS = ('charAt', 'split', 'replace', 'indexOf', 'substr', 'substring', 'startsWith', 'endsWith', 'toLowerCase', 'toUpperCase', 'trim')


SCRIPT = r'''
function __unpack(p) {
  if(p.t==='undefined') return undefined;
  if(p.t==='number') return p.v==='-0' ? -0 : Number(p.v);
  if(p.t==='array') return p.v.map(__unpack);
  if(p.t==='object') {
    const result={};
    for(const [key,item] of p.v) Object.defineProperty(result,key,{value:__unpack(item),enumerable:true,writable:true,configurable:true});
    return result;
  }
  return p.v;
}
function __pack(v) {
  if(v===undefined) return {t:'undefined'};
  if(v===null) return {t:'null',v:null};
  if(typeof v==='number') return {t:'number',v:Object.is(v,-0)?'-0':String(v)};
  if(Array.isArray(v)) return {t:'array',v:v.map(__pack)};
  if(typeof v==='object') return {t:'object',v:Object.keys(v).map(k=>[k,__pack(v[k])])};
  if(typeof v==='string'||typeof v==='boolean') return {t:typeof v,v:v};
  return {t:'unsupported'};
}
function __result(fn) {
  try {return JSON.stringify(__pack(fn()));}
  catch(e) {return JSON.stringify({t:'error',name:e.name,message:e.message});}
}
const __ops = {OPERATIONS};
function __invoke(op,raw) {
  const args=JSON.parse(raw).map(__unpack);
  return __result(()=>__ops[op](...args));
}
'''


def concrete(value, active=frozenset()):
    if value is U or isinstance(value, SymbolicValue):
        return False
    if isinstance(value, (dict, list, tuple)):
        if id(value) in active or len(active) >= 64:
            return False
        active = active | {id(value)}
        return all(concrete(v, active) for v in (value.values() if isinstance(value, dict) else value))
    return value is JS_UNDEFINED or value is None or type(value) in (bool, int, float, str)


def encode(value):
    if value is JS_UNDEFINED:
        return {'t': 'undefined'}
    if value is None:
        return {'t': 'null', 'v': None}
    if type(value) in (int, float):
        text = '-0' if type(value) is float and value == 0 and math.copysign(1, value) < 0 else 'Infinity' if value == math.inf else '-Infinity' if value == -math.inf else str(value)
        return {'t': 'number', 'v': text}
    if isinstance(value, (list, tuple)):
        return {'t': 'array', 'v': [encode(v) for v in value]}
    if isinstance(value, dict):
        return {'t': 'object', 'v': [[str(k), encode(v)] for k, v in value.items()]}
    return {'t': 'boolean' if type(value) is bool else 'string', 'v': value}


def decode(packet):
    kind = packet['t']
    if kind == 'error':
        raise JavaScriptError(packet['name'], packet['message'])
    if kind == 'unsupported':
        return U
    if kind == 'undefined':
        return JS_UNDEFINED
    if kind == 'number':
        value = float(packet['v'])
        return int(value) if math.isfinite(value) and value.is_integer() and abs(value) <= 9007199254740991 and not (value == 0 and math.copysign(1, value) < 0) else value
    if kind == 'array':
        return [decode(v) for v in packet['v']]
    if kind == 'object':
        return JSONObject({k: decode(v) for k, v in packet['v']})
    return packet['v']


class NativeJS:
    def __init__(self, memory_bytes=8 * 1024 * 1024, timeout_seconds=.02):
        started = time.perf_counter()
        self.memory_bytes, self.timeout_seconds = memory_bytes, timeout_seconds
        self.context = quickjs.Context()
        self.context.set_memory_limit(memory_bytes)
        self.context.set_max_stack_size(256 * 1024)
        self.context.set_time_limit(timeout_seconds)
        self.parser = Parser(Language(tree_sitter_javascript.language()))
        operations = {op: f'(a,b)=>a {op} b' for op in OPERATORS}
        operations.update({name: f'(a,...args)=>String.prototype.{name}.apply(a,args)' for name in METHODS})
        operations.update({'truth': '(a)=>!!a', 'String': '(a)=>String(a)', 'identity': '(a)=>a',
                           'parseInt': '(a,b)=>parseInt(a,b)', 'parseFloat': '(a)=>parseFloat(a)',
                           'JSON.parse': '(a)=>JSON.parse(a)', 'JSON.stringify': '(a)=>JSON.stringify(a)',
                           '!': '(a)=>!a', 'u+': '(a)=>+a', 'u-': '(a)=>-a', '~': '(a)=>~a'})
        script = SCRIPT.replace('{OPERATIONS}', '{' + ','.join(json.dumps(k) + ':' + v for k, v in operations.items()) + '}')
        self.context.eval(script)
        self.invoke = self.context.get('__invoke')
        self.allowed = set(operations)
        self.calls, self.seconds = 0, 0.0
        self.preparation_seconds = time.perf_counter() - started

    def run(self, op, *values):
        if op not in self.allowed or not all(concrete(v) for v in values):
            return U
        if op in {'==', '===', '!=', '!=='} and len(values) == 2 and all(isinstance(v, (dict, list, tuple)) for v in values):
            # JSON marshalling cannot preserve heap-reference equality. The
            # abstract UI evaluator checks its own object identities instead.
            return U
        started = time.perf_counter()
        self.calls += 1
        try:
            raw = json.dumps([encode(v) for v in values], ensure_ascii=True, allow_nan=False)
            return decode(json.loads(self.invoke(op, raw)))
        except (quickjs.JSException, MemoryError, RecursionError) as exc:
            raise NativeUnavailable(str(exc)) from exc
        finally:
            self.seconds += time.perf_counter() - started

    def literal(self, raw, kind):
        if kind not in {'string', 'number', 'true', 'false', 'null'}:
            return U
        root = self.parser.parse(raw.encode('utf-8')).root_node
        expression = root.named_children[0] if len(root.named_children) == 1 else None
        child = expression.named_children[0] if expression is not None and expression.type == 'expression_statement' and len(expression.named_children) == 1 else None
        if root.has_error or child is None or child.type != kind or child.text.decode('utf-8') != raw:
            return U
        self.calls += 1
        started = time.perf_counter()
        try:
            # raw is exactly one primitive CST node, never an expression/body.
            return decode(json.loads(self.context.eval('__result(()=>(' + raw + '))')))
        except (quickjs.JSException, MemoryError) as exc:
            raise NativeUnavailable(str(exc)) from exc
        finally:
            self.seconds += time.perf_counter() - started


_local = threading.local()


def engine():
    if not hasattr(_local, 'engine'):
        _local.engine = NativeJS()
    return _local.engine


def statistics():
    instance = getattr(_local, 'engine', None)
    if instance is None:
        return {'initialized':False, 'calls':0, 'seconds':0., 'preparation_seconds':0.}
    return {'initialized':True, 'calls':instance.calls, 'seconds':instance.seconds,
            'preparation_seconds':instance.preparation_seconds,
            'memory_bytes':instance.context.memory().get('memory_used_size'),
            'memory_limit_bytes':instance.memory_bytes, 'per_operation_time_limit_seconds':instance.timeout_seconds,
            'target_scripts_executed':False, 'host_functions_registered':False}
