"""Abstract JSON text retains opaque scalar identity without inventing bytes."""
from copy import deepcopy
import hashlib
import json

from .native import concrete, engine
from .state import JS_UNDEFINED, U, SymbolicValue, JSONObject


class EncodedJSON(SymbolicValue):
    def __init__(self, payload):
        self.payload = deepcopy(payload)
        digest = hashlib.sha256(json.dumps(payload, ensure_ascii=True, separators=(',', ':'), default=str).encode()).hexdigest()
        super().__init__({'__symbol__': 'json:' + digest, '__type__': 'String', '__nonnull__': True})


def serializable(value, active=frozenset()):
    if isinstance(value, SymbolicValue):
        return not isinstance(value, EncodedJSON) and value.get('__category__') in {'string', 'number'}
    if value is U:
        return False
    if isinstance(value, (dict, list)):
        if id(value) in active or len(active) >= 64:
            return False
        active = active | {id(value)}
        return all(serializable(v, active) for v in (value.values() if isinstance(value, dict) else value))
    return concrete(value)


def stringify(value):
    if concrete(value):
        return engine().run('JSON.stringify', value)
    return EncodedJSON(wire_json(value)) if serializable(value) else U


def parse(value):
    if isinstance(value, EncodedJSON):
        return complete(deepcopy(value.payload))
    return engine().run('JSON.parse', value)


def complete(value):
    if isinstance(value, SymbolicValue):return value
    if isinstance(value, dict):return JSONObject({k:complete(v) for k,v in value.items()})
    if isinstance(value, list):return [complete(v) for v in value]
    return value


def wire_json(value, active=frozenset()):
    """JSON.stringify semantics at an HTTP boundary, keeping symbolic leaves."""
    if isinstance(value, SymbolicValue):
        return value
    if value is U:
        return U
    if isinstance(value, (dict, list, tuple)):
        if id(value) in active or len(active) >= 64:
            return U
        active = active | {id(value)}
        if isinstance(value, dict):
            return {str(k): wire_json(v, active) for k, v in value.items() if v is not JS_UNDEFINED}
        return [None if v is JS_UNDEFINED else wire_json(v, active) for v in value]
    text = engine().run('JSON.stringify', value)
    return JS_UNDEFINED if text is JS_UNDEFINED else json.loads(text) if isinstance(text, str) else U
