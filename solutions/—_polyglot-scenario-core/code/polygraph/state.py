"""Copy-on-write table snapshots; immutable input rows are shared across paths."""
from copy import deepcopy
import gzip
import json

from .values import Object, Symbol, OpaqueString, Unknown, MethodRef


class Store:
    def __init__(self, base=None, changes=None, tainted=None, schemas=None):
        self.base = base if base is not None else {}
        self.changes = changes if changes is not None else {}
        self.tainted = tainted if tainted is not None else set()
        self.schemas = schemas if schemas is not None else {}

    def __deepcopy__(self, memo):
        result = Store(self.base, deepcopy(self.changes, memo), self.tainted.copy(), self.schemas)
        memo[id(self)] = result
        return result

    def read(self, table):
        if table in self.tainted:
            return Unknown("table may have been modified by unsupported code", origin=table)
        if table not in self.changes and table not in self.base:
            return Unknown("initial table contents were not supplied", origin=table)
        return list(deepcopy(self.changes.get(table, self.base.get(table, ()))))

    def replace(self, table, rows):
        self.changes[table] = deepcopy(rows)
        self.tainted.discard(table)

    def havoc(self):
        self.tainted.update(set(self.base) | set(self.changes))

    def snapshot(self):
        return {k: self.read(k) for k in sorted(set(self.base) | set(self.changes))}


class State:
    def __init__(self, store=None):
        self.store = store if store is not None else Store()
        self.globals = {}
        self.objects = {}
        self.sequence = 0
        self.pending = {}
        self.transactions = {}
        self.sessions = set()
        self.tainted_containers = {}
        self.globals_unknown = False
        self.immutable_globals = set()
        self.browser = None
        self.opaque_values = {}
        self.container_versions = {}
        self.box_cache = {}

    def mutated(self,value):
        previous=self.container_versions.get(id(value),(value,0))
        self.container_versions[id(value)]=(value,previous[1]+1)

    def mutation_version(self,value):return self.container_versions.get(id(value),(None,0))[1]

    def new(self, typ, fields=None):
        self.sequence += 1
        obj = Object(f"o{self.sequence}", typ, fields if fields is not None else {})
        self.objects[obj.identity] = obj
        return obj

    def symbol(self, typ, sort=""):
        self.sequence += 1
        return Symbol(f"fresh:{self.sequence}", typ, sort=sort)

    def opaque_string(self, value):
        self.sequence += 1
        symbol=OpaqueString(f'fresh:{self.sequence}','str')
        self.opaque_values[symbol.identity]=value
        return symbol

    def havoc(self, roots=()):
        self.store.havoc()
        for transaction in self.transactions.values():
            transaction.havoc()
        self.pending.clear()
        pending = [*roots, *self.globals.values(), *self.objects.values()]
        seen = set()
        while pending:
            value = pending.pop()
            if id(value) in seen:
                continue
            seen.add(id(value))
            if isinstance(value, Object):
                from .java_boxing import boxed
                if boxed(value):continue
                pending.extend(value.fields.values())
                value.fields = {key: Unknown("unknown call may modify reachable object", origin=value.identity) for key in value.fields}
            elif isinstance(value,MethodRef):
                pending.append(value.receiver)
            elif isinstance(value, (dict, list, set, tuple)):
                pending.extend(value.values() if isinstance(value, dict) else value)
                if not isinstance(value, tuple):
                    # Keep a reference so Python cannot reuse a tainted id.
                    self.tainted_containers[id(value)] = value
        self.globals = {key: value if key in self.immutable_globals else Unknown("unknown call may change module/class state", origin=key) for key, value in self.globals.items()}
        self.globals_unknown = True


def load_context(path, facts, dialect="mysql"):
    if path is None:
        return Store(), {}, ["No initial data context supplied"]
    if path.is_dir():
        candidates = sorted(p for p in path.iterdir() if p.suffix in {".sql", ".gz", ".json"})
        if len(candidates) != 1:
            raise ValueError("Select one context file explicitly when a directory is ambiguous")
        path = candidates[0]
    raw = path.read_bytes()
    if path.suffix == ".gz":
        raw = gzip.decompress(raw)
    if path.name.endswith(".json"):
        context = json.loads(raw)
        tables = context.get("tables", {})
        base = {}
        for name, rows in tables.items():
            rid = facts.table_id(name)
            if not rid:
                raise ValueError("Context table not mapped uniquely to skeleton: " + name)
            base[rid] = tuple(deepcopy(rows))
        schemas = {}
        for name, columns in context.get("table_schemas", {}).items():
            rid = facts.table_id(name)
            if not rid:
                raise ValueError("Context schema table not mapped uniquely to skeleton: " + name)
            schemas[rid] = columns
        return Store(base, schemas=schemas), context, []
    from .sql import snapshot
    base, schemas, tainted, warnings = snapshot(raw.decode("utf-8", errors="replace"), facts, dialect)
    return Store(base, tainted=tainted, schemas=schemas), {}, warnings
