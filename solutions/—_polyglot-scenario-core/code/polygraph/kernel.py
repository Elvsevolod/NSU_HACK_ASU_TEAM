"""One bounded evaluator for both frontends. No Java/Python parser dependencies."""
from dataclasses import dataclass
from copy import deepcopy
import re

from .ir import Span
from .state import State
from .constraints import PathSolver
from .values import (Awaitable, Formula, FunctionRef, Object, Predicate, Raised, Response, Symbol,
                     Text, TypeRef, Unknown, binary, equal, integer, serial, symbolic, truth, unknown)

GLOBAL_NAMES = object()
SCOPES = object()


class BranchPoint(Exception):
    def __init__(self, position, choices, label):
        self.position, self.choices, self.label = position, choices, label


class Incomplete(Exception):
    pass


class Infeasible(Exception):
    pass


@dataclass
class Completion:
    kind: str = "normal"
    value: object = None
    typ: str = ''


class Kernel:
    def __init__(self, project, state=None, decisions=(), loop_limit=32, depth_limit=32, step_limit=30000, context=None, smt=True, smt_timeout_ms=50):
        self.p, self.state = project, state if state is not None else State()
        self.decisions, self.choice_position = decisions, 0
        self.loop_limit, self.depth_limit, self.step_limit = loop_limit, depth_limit, step_limit
        self.context = context or {}
        self.frames, self.edges, self.diagnostics, self.events = [], {}, [], []
        self.operations, self.partial, self.last_exception = 0, False, None
        self.dependency_cache = {}
        self.resolving_dependencies = set()
        self.unknown_teardown = False
        self.request_input = {}
        self.dependency_exits = []
        self.safe_generators = set()
        self.initialization_language = ""
        self.solver = PathSolver(smt, smt_timeout_ms)
        self.state.immutable_globals.update(project.immutable_globals)

    @property
    def method(self):
        return self.frames[-1][0] if self.frames else None

    @property
    def language(self):
        return self.initialization_language or (self.method.language if self.method else "python")

    def note(self, code, message, span=Span(), **detail):
        self.partial = True
        record = {"code": code, "message": message, "file": span.file, "line": span.line, **serial(detail)}
        if record not in self.diagnostics:
            self.diagnostics.append(record)

    def tick(self, span):
        self.operations += 1
        if self.operations > self.step_limit:
            self.note("operation-budget", "Operation budget exhausted; remaining effects unknown", span)
            raise Incomplete()

    def choose(self, choices, label):
        position = self.choice_position
        self.choice_position += 1
        if position >= len(self.decisions):
            raise BranchPoint(position, tuple(choices), label)
        selected = self.decisions[position]
        if selected not in choices:
            raise ValueError("Invalid replay decision")
        return selected

    def condition(self, value, span):
        if self.language=='java':
            from .java_boxing import boxed,unbox
            if value is None:raise Raised('NullPointerException')
            if boxed(value) and value.typ=='java.lang.Boolean':value=unbox(value)
        if isinstance(value, Predicate):
            self.note("predicate-as-boolean", "A symbolic field predicate is not a concrete condition", span)
            value = Unknown("symbolic predicate outside query evaluation", "boolean")
        if isinstance(value, Object) and self.language == "python" and value.typ in self.p.types:
            for special in ["__bool__", "__len__"]:
                methods = self.p.methods_of(value.typ, special, 0)
                if len(methods) == 1:
                    value = self.execute_method(methods[0].key, receiver=value, span=span)
                    break
        result = truth(value, self.language)
        if result is None:
            choices, predicate = self.solver.outcomes(value) if symbolic(value) else ((False, True), None)
            if not choices:
                raise Infeasible()
            if len(choices) == 1:
                self.events.append({"kind": "solver-forced-condition", "file": span.file, "line": span.line, "outcome": choices[0], "value": value})
                selected = choices[0]
            else:
                self.note("unknown-condition", "Both feasible or unproved outcomes are considered", span, value=value)
                selected = self.choose(choices, f"{span.file}:{span.line}:condition")
            self.solver.assume(predicate, selected)
            return selected
        return result

    def add(self, source, relation, target, span=Span(), reason="source semantics"):
        if not source or not target:
            self.note("missing-skeleton-id", "Effect cannot be projected without a skeleton ID", span, relation=relation)
            return
        if relation != "executes" and source not in self.p.nodes:
            self.note("missing-skeleton-id", "Source effect ID is absent from skeleton", span)
            return
        if target not in self.p.nodes:
            self.note("missing-skeleton-id", "Target effect ID is absent from skeleton", span)
            return
        edge = (source, relation, target)
        evidence = {"file": span.file, "line": span.line, "reason": reason}
        self.edges.setdefault(edge, [])
        if evidence not in self.edges[edge]:
            self.edges[edge].append(evidence)

    def execute_method(self, key, args=(), kwargs=None, receiver=None, span=Span(),argument_types=()):
        method = self.p.methods[key]
        if method.abstract:
            return self.opaque("abstract or external method " + key, span)
        if len(self.frames) >= self.depth_limit:
            self.note("recursion-budget", "Call depth exhausted; tail effects unknown", span, method=key)
            raise Incomplete()
        caller = self.method
        env = {"self": receiver, "this": receiver, GLOBAL_NAMES: set()}
        supplied = dict(kwargs or {})
        if method.language == "python" and set(supplied) & set(method.annotations.get("positional_only", [])):
            raise Raised("TypeError", "keyword supplied for positional-only parameter")
        for param, value in zip(method.params, args):
            if param.name in supplied:
                raise Raised("TypeError", "duplicate argument")
            supplied[param.name] = value
        if len(args) > len(method.params):
            raise Raised("TypeError", "too many arguments")
        if method.language == "python" and any(p.name in method.annotations.get("keyword_only", []) for p in method.params[:len(args)]):
            raise Raised("TypeError", "positional argument supplied for keyword-only parameter")
        self.frames.append((method, env))
        checkpoint = None
        try:
            for param_index,param in enumerate(method.params):
                if param.name in supplied:
                    env[param.name] = supplied.pop(param.name)
                elif param.dependency:
                    self.note("dependency-marker", "A source call did not ask the framework to resolve Depends", method.span)
                    env[param.name] = Unknown("unresolved dependency marker", param.typ)
                elif param.default is not None:
                    env[param.name] = self.parameter_default(method, param, env)
                else:
                    if method.language == "python":
                        raise Raised("TypeError", "missing required argument " + param.name)
                    env[param.name] = Unknown("missing method argument", param.typ, param.name)
                if method.language=='java':
                    from .java_boxing import adapt
                    env[param.name]=adapt(self,env[param.name],param.typ,span,argument_types[param_index] if param_index<len(argument_types) else '')
                value = env[param.name]
                raw = param.typ.split(".")[-1]
                sort = "bool" if raw in {"bool", "boolean"} else "int" if method.language == "python" and raw == "int" else "bv32" if method.language == "java" and raw == "int" else "bv64" if method.language == "java" and raw == "long" else ""
                if isinstance(value, Unknown) and sort:
                    self.note("symbolic-input", "Typed unknown input is constrained symbolically", method.span, parameter=param.name, reason=value.reason)
                    env[param.name] = self.state.symbol(param.typ, sort)
            if supplied:
                raise Raised("TypeError", "unexpected keyword arguments")
            checkpoint = deepcopy(self.state.store) if method.transaction else None
            if caller:
                self.add(caller.skeleton_id, "calls", method.skeleton_id, span)
            self.add("scenario:" + self.scenario_id, "executes", method.skeleton_id, method.span)
            completion = self.block(self.p.lower(key), env)
            result=completion.value if completion.kind in {'return','yield'} else None
            if method.language=='java':
                from .java_boxing import adapt
                result=adapt(self,result,method.return_type,method.span,completion.typ)
            return result
        except Raised:
            if checkpoint is not None:
                self.state.store = checkpoint
                self.events.append({"kind": "rollback", "method": key, "attempted_edges_preserved": True})
            raise
        finally:
            self.frames.pop()

    def dependency(self, key, typ="", span=Span()):
        if key in self.dependency_cache:
            return self.dependency_cache[key]
        if key not in self.p.methods and key not in self.p.types and (key.startswith('fastapi.') or key in self.p.globals):
            from .fastapi_dependencies import dependency
            from .models import NOT_HANDLED
            native=dependency(self,key,span)
            if native is not NOT_HANDLED:
                self.dependency_cache[key]=native
                return native
        resolved = key if key in self.p.methods else self.p.resolve_function(key, span.file)
        if not resolved:
            return self.opaque("unresolved dependency " + key, span)
        if key in self.resolving_dependencies:
            self.unsupported("cyclic framework dependency", span)
        self.resolving_dependencies.add(key)
        body=self.p.lower(resolved)
        safe_generator=(len(body)==1 and body[0].op=='with' and len(body[0].body)==1 and body[0].body[0].op=='yield'
                        and len(body[0].args)==1 and body[0].args[0][1] is not None and body[0].args[0][1].op=='var'
                        and body[0].body[0].args[0].op=='var' and body[0].args[0][1].value==body[0].body[0].args[0].value)
        if safe_generator:self.safe_generators.add(resolved)
        try:
            values = {p.name: self.dependency(p.dependency, p.typ, self.p.methods[resolved].span)
                      for p in self.p.methods[resolved].params if p.dependency}
            value = self.execute_method(resolved, kwargs=values, span=span)
        finally:
            self.resolving_dependencies.remove(key)
            self.safe_generators.discard(resolved)
        self.dependency_cache[key] = value
        return value

    def source_call(self, key, args=(), kwargs=None, receiver=None, span=Span(),argument_types=()):
        if self.p.methods[key].annotations.get("generator"):
            return self.state.new("python.Generator", {"method": key})
        if self.p.methods[key].annotations.get("async"):
            return Awaitable(key, tuple(args), dict(kwargs or {}), receiver, span)
        return self.execute_method(key, args, kwargs, receiver, span,argument_types)

    def invoke_callable(self,callback,args=(),span=Span()):
        from .callbacks import invoke
        return invoke(self,callback,tuple(args),span)

    def opaque(self, reason, span=Span()):
        self.note("unknown-call", reason + "; reachable state and exceptional completion are unknown", span)
        self.state.havoc(value for _, env in self.frames for value in env.values())
        if self.choose(("normal", "throw"), f"{span.file}:{span.line}:opaque") == "throw":
            raise Raised("UnknownException", Unknown(reason))
        return Unknown(reason)

    def unsupported(self, reason, span):
        self.note("unsupported", reason + "; no claim about remaining effects", span)
        self.state.havoc()
        raise Incomplete()

    def create(self, typ, args=(), kwargs=None, span=Span(), bean=False, constructing=None,argument_types=()):
        from .models import construct, NOT_HANDLED
        module = self.method.module if self.method else self.p.module(span.file)
        resolved = self.p.resolve_type(typ, module, span.file)
        if not resolved:
            if bean:
                return self.state.new(self.p.imports.get(span.file, {}).get(typ, typ))
            modeled = construct(self, typ, args, kwargs or {}, span,argument_types)
            if modeled is not NOT_HANDLED:
                return modeled
            return self.opaque("unmodeled constructor " + typ, span)
        if bean:
            resolved = resolved if self.p.types[resolved].repository_entity else self.p.implementation(resolved)
            if not resolved:
                return self.opaque("ambiguous dependency injection for " + typ, span)
        info = self.p.types[resolved]
        if info.annotations.get("custom_metaclass") or self.p.methods_of(resolved, "__new__"):
            return self.opaque("custom Python object construction", span)
        constructing = set() if constructing is None else constructing
        if resolved in constructing:
            return Unknown("cyclic construction", resolved)
        constructing = constructing | {resolved}
        fields = {}
        obj = self.state.new(resolved, fields)
        previous_language = self.initialization_language
        self.initialization_language = info.language
        try:
            for field, (field_type, default) in self.p.type_fields(resolved).items():
                if info.language == "python" and field in (kwargs or {}):
                    fields[field] = kwargs[field]
                elif default is not None:
                    fields[field] = self.value(default, {"this": obj, "self": obj})
                    if info.language=='java':
                        from .java_boxing import adapt
                        fields[field]=adapt(self,fields[field],field_type,info.span,default.typ)
                elif info.language == "java":
                    fields[field] = False if field_type == "boolean" else 0 if field_type in {"byte", "short", "int", "long", "float", "double"} else None
                else:
                    if info.annotations.get("model"):
                        fields[field] = Unknown("required model field", field_type, field)
        finally:
            self.initialization_language = previous_language
        if bean:
            for field in info.annotations.get("inject", []):
                if field in self.p.type_fields(resolved):
                    field_type = self.p.type_fields(resolved)[field][0]
                    fields[field] = self.create(field_type, span=info.span, bean=True, constructing=constructing)
        if info.language == "python":
            if info.annotations.get("model"):
                fields.update(kwargs or {})
            obj.provided = set(kwargs or {})
            constructors = self.p.methods_of(resolved, "__init__")
        else:
            constructors = self.p.methods_of(resolved, "<init>", len(args))
        if constructors and not bean:
            if len(constructors) != 1:
                return self.opaque("ambiguous constructor overload " + typ, span)
            self.execute_method(constructors[0].key, args, kwargs, obj, span,argument_types)
        elif args and info.language == "python":
            self.note("model-positional", "Positional model construction is not supported", span)
            return Unknown("invalid model construction", resolved)
        elif kwargs and info.language == "python" and not info.annotations.get("model"):
            raise Raised("TypeError", "object constructor takes no keyword arguments")
        elif args:
            # Lombok constructors only when their declaration requests generation.
            if "AllArgsConstructor" in info.annotations and len(args) == len(fields):
                fields.update(zip(fields, args))
            else:
                return self.opaque("missing source constructor " + typ, span)
        return obj

    def definition_value(self, expr, key):
        if self.state.globals_unknown:
            return Unknown("unknown call may have changed definition-time state", expr.typ, key)
        provided = self.context.get("globals", {})
        if key in provided:
            return deepcopy(provided[key])

        def literal_tree(value):
            if hasattr(value, "op"):
                return value.op in {"const", "list", "dict", "bin", "unary", "slice"} and literal_tree(value.args)
            return all(literal_tree(item) for item in value) if isinstance(value, (tuple, list)) else True

        if literal_tree(expr):
            return self.value(expr, {})
        from .definition_models import supported
        if supported(self,expr):
            return self.value(expr,{})
        self.note("definition-time-value", "A nonliteral Python module/default value was evaluated before the scenario; its value is not supplied", expr.span, binding=key)
        return Unknown("definition-time Python value not supplied", expr.typ, key)

    def parameter_default(self, method, param, env=None):
        if method.language != "python":
            return self.value(param.default, env or {})
        key = method.key + ":default:" + param.name
        if key not in self.state.globals:
            self.state.globals[key] = self.definition_value(param.default, key)
        return self.state.globals[key]

    def resolve_name(self, name, env, span, bindings=()):
        if name in env:
            return env[name]
        if bindings and any(value.startswith("local:") for value in bindings):
            # Python decides local scope at compile time, before an assignment
            # executes. Falling back to a same-named imported function is wrong.
            raise Raised("UnboundLocalError", name)
        if len(bindings) > 1:
            self.note("ambiguous-name", "LibCST found several lexical bindings", span, name=name, bindings=bindings)
            return Unknown("ambiguous lexical binding", origin=name)
        method = self.method
        if method and method.language == "java":
            obj = env.get("this")
            if isinstance(obj, Object) and name in obj.fields:
                return obj.fields[name]
            static_key = method.owner + "." + name
            if static_key in self.p.globals:
                return self.field(TypeRef(method.owner), name, span)
        file = span.file or (method.span.file if method else "")
        py_module = self.p.lexical_modules.get(file, "")
        global_key = py_module + "." + name
        if method and name in env.get(GLOBAL_NAMES, set()):
            global_key = method.owner + "." + name
        if global_key in self.state.globals:
            return self.state.globals[global_key]
        if global_key in self.p.globals:
            value = self.definition_value(self.p.globals[global_key], global_key) if file.endswith(".py") else self.value(self.p.globals[global_key], {})
            self.state.globals[global_key] = value
            return value
        imported = bindings[0] if bindings else self.p.resolve_import(name, file)
        if imported:
            if imported.startswith("builtins."):
                return TypeRef(imported.removeprefix("builtins."))
            if imported in self.p.methods:
                return FunctionRef(imported)
            if imported in self.p.globals:
                if imported not in self.state.globals:
                    self.state.globals[imported] = self.definition_value(self.p.globals[imported], imported) if file.endswith(".py") else self.value(self.p.globals[imported], {})
                return self.state.globals[imported]
            if file.endswith('.java'):
                target=self.p.resolve_type(imported,method.module if method else self.p.module(file),file)
                if target:return TypeRef(target)
            return TypeRef(imported)
        function = self.p.resolve_function(name, file, method.module if method else "")
        if function:
            return FunctionRef(function)
        resolved = self.p.resolve_type(name, method.module if method else "", file)
        if resolved:
            return TypeRef(resolved)
        intrinsic = {"len", "str", "int", "float", "bool", "list", "dict", "set", "range", "enumerate", "isinstance",
                     "String", "Integer", "Long", "Byte", "Short", "Number", "Boolean", "Double", "Object", "System", "Math"}
        if name in intrinsic or name.endswith(("Exception", "Error")):
            from .java_boxing import WRAPPERS
            if file.endswith('.java') and name in set(WRAPPERS)|{'String','Object','Number'}:return TypeRef('java.lang.'+name)
            return TypeRef(name)
        self.note("unresolved-name", "Name is not bound by source facts or supplied context", span, name=name)
        return Unknown("unresolved source name", origin=name)

    def field(self, obj, name, span):
        if obj is None:
            raise Raised("NullPointerException" if self.language == "java" else "AttributeError")
        if isinstance(obj, Object):
            if obj.typ + "." + name in self.p.globals:
                return self.field(TypeRef(obj.typ), name, span)
            if obj.typ in self.p.types and self.p.types[obj.typ].language == "python":
                properties = [m for m in self.p.methods_of(obj.typ, name, 0) if m.annotations.get("property")]
                if len(properties) == 1:
                    return self.execute_method(properties[0].key, receiver=obj, span=span)
                if name not in obj.fields:
                    getters = self.p.methods_of(obj.typ, "__getattr__", 1)
                    if len(getters) == 1:
                        return self.execute_method(getters[0].key, (name,), receiver=obj, span=span)
                    raise Raised("AttributeError", name)
            return obj.fields.get(name, Unknown("unknown object field", origin=obj.typ + "." + name))
        if isinstance(obj, dict):
            return obj.get(name, Unknown("absent field", origin=name))
        if isinstance(obj, Response):
            return {"body": obj.body, "status_code": obj.status, "status": obj.status, "headers": obj.headers}.get(name, Unknown("response attribute"))
        if isinstance(obj, TypeRef):
            key = obj.name + "." + name
            if key in self.p.methods:
                return FunctionRef(key)
            if key in self.state.globals:
                return self.state.globals[key]
            if key in self.p.globals:
                definition = self.p.globals[key]
                # A Java final binding is immutable, while its referenced
                # mutable contents are still invalidated by State.havoc.
                immutable_literal = key in self.p.immutable_globals and definition.op == "const"
                from .models import pure_global_definition
                pure_definition = key in self.p.immutable_globals and pure_global_definition(self, definition)
                result = Unknown("unknown call may have changed class/module state", origin=key) if self.state.globals_unknown and not (immutable_literal or pure_definition) else self.definition_value(definition, key) if span.file.endswith(".py") else self.value(definition, {})
                self.state.globals[key] = result
                return result
            from .models import static_field, NOT_HANDLED
            result = static_field(self, obj, name)
            return TypeRef(key) if result is NOT_HANDLED else result
        if isinstance(obj, (list, str)) and name == "length":
            return len(obj)
        return Unknown("field on unknown receiver", origin=name)

    def assign(self, target, value, env, span,origin=''):
        if target.op == "var":
            if self.language == "java" and target.typ:
                from .java_boxing import adapt
                value=adapt(self,value,target.typ,span,origin)
            if target.value in env.get(GLOBAL_NAMES, set()):
                module = self.p.lexical_modules[self.method.span.file]
                self.state.globals[module + "." + target.value] = value
            elif self.language == "java" and target.value not in env and isinstance(env.get("this"), Object) and target.value in env["this"].fields:
                env["this"].fields[target.value] = value
            else:
                env[target.value] = value
        elif target.op == "field":
            if self.language=='java' and target.typ:
                from .java_boxing import adapt
                value=adapt(self,value,target.typ,span,origin)
            obj = self.value(target.args[0], env)
            if obj is None:
                raise Raised("NullPointerException" if self.language == "java" else "AttributeError")
            if isinstance(obj, Object):
                obj.fields[target.value] = value
            elif isinstance(obj, dict):
                obj[target.value] = value
            else:
                self.unsupported("assignment through an unknown receiver", span)
        elif target.op == "index":
            obj, index = (self.value(v, env) for v in target.args)
            if unknown(obj) or unknown(index):
                self.unsupported("unknown indexed assignment", span)
            try:
                obj[index] = value
            except (IndexError, KeyError, TypeError) as exc:
                raise Raised(type(exc).__name__) from None
        elif target.op == "list":
            if not isinstance(value, (list, tuple)) or len(target.args) != len(value):
                raise Raised("ValueError", "unpacking shape")
            for t, v in zip(target.args, value):
                self.assign(t, v, env, span)
        else:
            self.unsupported("unsupported assignment target " + target.op, span)
        return value

    def value(self, expr, env):
        result = self.evaluate(expr, env)
        return Unknown("container may have been mutated by unknown code") if id(result) in self.state.tainted_containers else result

    def evaluate(self, expr, env):
        self.tick(expr.span)
        op, args, span = expr.op, expr.args, expr.span
        if op == "const":
            return integer(expr.value, expr.typ) if self.language == "java" else expr.value
        if op == "var":
            return self.resolve_name(expr.value, env, span, expr.bindings)
        if op == "type":
            typ=self.p.resolve_type(expr.value,self.method.module if self.method else '',span.file) or self.p.resolve_import(expr.value,span.file) or expr.value
            from .java_boxing import WRAPPERS
            if span.file.endswith('.java') and typ in set(WRAPPERS)|{'String','Object','Number'}:typ='java.lang.'+typ
            return TypeRef(typ)
        if op == "unknown":
            self.note("unknown-value", expr.value, span)
            return Unknown(expr.value, expr.typ)
        if op == "fresh":
            return self.state.symbol(expr.value)
        if op == "field":
            return self.field(self.value(args[0], env), expr.value, span)
        if op == "list":
            return [self.value(a, env) for a in args]
        if op == "dict":
            return {self.value(k, env): self.value(v, env) for k, v in args}
        if op == "slice":
            return slice(*(self.value(a, env) for a in args))
        if op == "index":
            obj, index = (self.value(a, env) for a in args)
            if unknown(obj) or unknown(index):
                return Unknown("unknown index or collection")
            if obj is None:
                raise Raised("NullPointerException" if self.language == "java" else "TypeError")
            if isinstance(obj, Object) and self.language == "python":
                methods = self.p.methods_of(obj.typ, "__getitem__", 1)
                if len(methods) == 1:
                    return self.source_call(methods[0].key, (index,), receiver=obj, span=span)
            try:
                return obj[index]
            except (IndexError, KeyError, TypeError) as exc:
                raise Raised(type(exc).__name__) from None
        if op == "bin":
            left, right = (self.value(a, env) for a in args)
            operand_type=expr.operand_type or expr.typ;left_box=right_box=False
            if self.language=='java':
                from .java_boxing import boxed,unbox,WRAPPERS,PRIMITIVES,short,adapt
                left_box,right_box=boxed(left),boxed(right)
                if expr.value in {'==','!='}:
                    if any(short(arg.typ) in PRIMITIVES for arg in args):
                        for index,arg in enumerate(args):
                            if short(arg.typ) in WRAPPERS:
                                if index==0:left=adapt(self,left,WRAPPERS[short(arg.typ)],span)
                                else:right=adapt(self,right,WRAPPERS[short(arg.typ)],span)
                else:
                    if left_box or right_box:
                        if (left_box and left.typ=='java.lang.Long' or right_box and right.typ=='java.lang.Long') and expr.value not in {'<<','>>','>>>'}:operand_type='long'
                        if left_box:left=unbox(left)
                        if right_box:right=unbox(right)
            numeric = all(type(value) is int or symbolic(value) and value.sort != "bool" for value in (left, right))
            if self.language == "java" and numeric and any(arg.op in {"call", "field", "choose", "index"} and not arg.typ and not was_box for arg,was_box in zip(args,(left_box,right_box))):
                self.note("unknown-numeric-promotion", "Unresolved Java operand type cannot justify numeric narrowing or branch pruning", span)
                return Unknown("unresolved Java numeric operand type", expr.typ)
            if self.language == "java" and not (expr.value == "+" and "String" in {a.typ for a in args}):
                if args[0].typ == "char" and isinstance(left, str) and len(left) == 1:
                    left = ord(left)
                if args[1].typ == "char" and isinstance(right, str) and len(right) == 1:
                    right = ord(right)
            if expr.value in {"/", "//", "%"} and symbolic(right):
                # Z3 totalizes division by zero; language exceptions must be
                # forked explicitly before constructing the arithmetic term.
                if self.condition(binary("==", right, 0, self.language), span):
                    raise Raised("ArithmeticException" if self.language == "java" else "ZeroDivisionError")
            return binary(expr.value,left,right,self.language,operand_type)
        if op == "compare":
            previous = self.value(args[0], env)
            for index, (operator, arg) in enumerate(zip(expr.value, args[1:])):
                next_value = self.value(arg, env)
                result = binary(operator, previous, next_value, self.language)
                if isinstance(previous, Object) and self.language == "python" and operator in {"==", "!="}:
                    custom = self.p.methods_of(previous.typ, "__eq__", 1)
                    if len(custom) == 1:
                        result = self.execute_method(custom[0].key, (next_value,), receiver=previous, span=span)
                        if operator == "!=":
                            result = not self.condition(result, span)
                if index == len(expr.value) - 1:
                    return result
                if not self.condition(result, span):
                    return False
                previous = next_value
            return True
        if op == "bool":
            result = self.value(args[0], env)
            for argument in args[1:]:
                condition = self.condition(result, span)
                if (expr.value == "and" and not condition) or (expr.value == "or" and condition):
                    return condition if self.language == "java" else result
                result = self.value(argument, env)
            return result
        if op == "unary":
            value = self.value(args[0], env)
            if expr.value in {"!", "not"}:
                return not self.condition(value, span)
            if self.language=='java':
                from .java_boxing import boxed,unbox
                if boxed(value):value=unbox(value)
            if symbolic(value):
                return binary("-", 0, value, self.language, expr.typ) if expr.value == "-" else value if expr.value == "+" else binary("^", value, -1, self.language, expr.typ)
            if unknown(value):
                return Unknown("unary operand", expr.typ)
            try:
                return integer(-value if expr.value == "-" else +value if expr.value == "+" else ~value, expr.typ or "int") if self.language == "java" else -value if expr.value == "-" else +value if expr.value == "+" else ~value
            except TypeError:
                raise Raised("TypeError") from None
        if op == "choose":
            return self.value(args[1] if self.condition(self.value(args[0], env), span) else args[2], env)
        if op == "assign":
            return self.assign(args[0],self.value(args[1],env),env,span,args[1].typ)
        if op == "update":
            old = self.value(args[0], env)
            new = binary("+", old, 1 if expr.value.endswith("++") else -1, self.language, expr.typ or "int")
            assigned=self.assign(args[0],new,env,span)
            return assigned if expr.value.startswith('pre') else old
        if op == "cast":
            value = self.value(args[0], env)
            if self.language=='java':
                from .java_boxing import adapt,WRAPPERS,PRIMITIVES,short
                if short(expr.value) in set(WRAPPERS)|PRIMITIVES:return adapt(self,value,expr.value,span,args[0].typ)
            return integer(value, expr.value)
        if op == "instanceof":
            value = self.value(args[0], env)
            if unknown(value):
                return Unknown("instanceof unknown", "boolean")
            return isinstance(value, Object) and self.matches_type(value.typ, expr.value)
        if op == "format":
            values = [self.value(a, env) for a in args]
            if any(isinstance(v, Unknown) for v in values):
                return Unknown("unknown formatted string", "str")
            if any(isinstance(v, (Symbol, Text)) for v in values):
                return Text(tuple(p for v in values for p in (v.parts if isinstance(v, Text) else (v,) if isinstance(v, Symbol) else (str(v),))))
            return "".join(str(v) for v in values)
        if op == "await":
            value = self.value(args[0], env)
            if isinstance(value, Awaitable):
                if value.library:
                    from .models import call
                    return call(self, value.receiver, value.method, value.args, value.kwargs, value.span)
                return self.execute_method(value.method, value.args, value.kwargs, value.receiver, value.span)
            self.unsupported("await of an unmodeled awaitable", span)
        if op == "new":
            return self.create(expr.value,tuple(self.value(a,env) for a in args),span=span,argument_types=tuple(a.typ for a in args))
        if op=='method_ref':
            from .callbacks import reference
            return reference(self,expr,self.value(args[0],env))
        if op == "call":
            receiver_expr, positional, named = args
            receiver = self.value(receiver_expr, env) if receiver_expr is not None else None
            values = tuple(self.value(a, env) for a in positional)
            kwargs, index = {}, 0
            while index < len(named):
                name, expression = named[index]
                if name is None:
                    group = self.value(expression, env)
                    index += 1
                    if unknown(group):
                        self.unsupported('unknown keyword mapping', span)
                    if isinstance(group,Object):
                        self.unsupported('custom keyword mapping protocol',span)
                    if not isinstance(group, dict):
                        raise Raised('TypeError', 'keyword expansion requires a mapping')
                else:
                    # Python evaluates an adjacent explicit-keyword group
                    # before merging it with an earlier **mapping.
                    group = {}
                    while index < len(named) and named[index][0] is not None:
                        name, expression = named[index]
                        group[name] = self.value(expression, env)
                        index += 1
                if kwargs.keys() & group.keys():
                    raise Raised('TypeError', 'duplicate keyword argument')
                kwargs.update(group)
            if any(not isinstance(name,str) for name in kwargs):
                raise Raised('TypeError', 'keyword names must be strings')
            return self.call(receiver,expr.value,values,kwargs,span,env,receiver_expr is not None,expr.bindings,receiver_expr.typ if receiver_expr is not None else '',tuple(a.typ for a in positional))
        self.unsupported(str(expr.value or op), span)

    def call(self, receiver, name, args, kwargs, span, env, explicit_receiver=True, bindings=(),receiver_type='',argument_types=()):
        from .models import call, NOT_HANDLED
        if receiver is None and explicit_receiver:
            raise Raised("NullPointerException" if self.language == "java" else "AttributeError")
        if not explicit_receiver:
            if self.language == 'java' and (self.method or isinstance(env.get('this'), Object)):
                implicit = env.get('this')
                owner = implicit.typ if isinstance(implicit, Object) else self.method.owner
                targets = self.p.methods_of(owner, name, len(args))
                if len(targets) == 1:
                    return self.source_call(targets[0].key,args,kwargs,implicit,span,argument_types)
                if len(targets) > 1:
                    return self.opaque('ambiguous source dispatch ' + name, span)
                if name == 'getClass' and isinstance(implicit, Object):
                    return TypeRef(implicit.typ)
            resolved = self.resolve_name(name, env, span, bindings)
            if isinstance(resolved, FunctionRef):
                return self.source_call(resolved.name,args,kwargs,span=span,argument_types=argument_types)
            if isinstance(resolved, TypeRef):
                typ = self.p.resolve_type(resolved.name, self.method.module if self.method else "", span.file)
                if typ:
                    return self.create(typ,args,kwargs,span,argument_types=argument_types)
            if isinstance(resolved, Unknown):
                return self.opaque("unresolved callable " + name, span)
            receiver, name = None, resolved.name if isinstance(resolved, TypeRef) else name
        if isinstance(receiver, Object) and receiver.typ in self.p.types:
            info = self.p.types[receiver.typ]
            if not info.repository_entity and "FeignClient" not in info.annotations:
                targets = self.p.methods_of(receiver.typ, name, len(args) if self.language == "java" else None)
                if len(targets) == 1:
                    return self.source_call(targets[0].key,args,kwargs,receiver,span,argument_types)
                if len(targets) > 1:
                    return self.opaque("ambiguous source dispatch " + name, span)
        if isinstance(receiver, TypeRef):
            key = receiver.name + "." + name
            if key in self.p.methods:
                return self.source_call(key,args,kwargs,span=span,argument_types=argument_types)
            if key in self.p.types:
                return self.create(key,args,kwargs,span,argument_types=argument_types)
            if receiver.name in self.p.types:
                targets = self.p.methods_of(receiver.name, name, len(args) if self.language == "java" else None)
                if len(targets) == 1:
                    return self.source_call(targets[0].key,args,kwargs,span=span,argument_types=argument_types)
        if isinstance(receiver, Object) and receiver.typ == "httpx.AsyncClient" and name in {"get", "post", "put", "patch", "delete", "request"}:
            return Awaitable(name, tuple(args), dict(kwargs), receiver, span, True)
        result=call(self,receiver,name,args,kwargs,span,receiver_type,argument_types)
        return self.opaque("unmodeled call " + name, span) if result is NOT_HANDLED else result

    def matches_type(self, actual, expected):
        from .java_boxing import CLASSES
        if actual in CLASSES:
            parents={actual,'java.lang.Object','java.io.Serializable','java.lang.Comparable'}
            if actual!='java.lang.Boolean':parents.add('java.lang.Number')
            for candidate in re.split(r'[|,]',expected.strip('() ')):
                candidate=candidate.strip()
                if candidate=='*':return True
                if self.method and self.p.resolve_type(candidate,self.method.module,self.method.span.file):continue
                resolved=self.p.resolve_import(candidate,self.method.span.file) if self.method else ''
                canonical=resolved or (candidate if '.' in candidate else 'java.lang.'+candidate)
                if canonical in parents:return True
            return False
        if actual.startswith(('jwt.','pwdlib.','argon2.','pydantic.')):
            from .security_models import exception_matches
            for candidate in re.split(r'[|,]',expected.strip('() ')):
                candidate=candidate.strip()
                if candidate=='*':return True
                if self.method and self.p.resolve_type(candidate,self.method.module,self.method.span.file):continue
                resolved=self.p.resolve_import(candidate,self.method.span.file) if self.method else ''
                if exception_matches(actual,resolved or candidate):return True
            return False
        names = [v.strip().split(".")[-1] for v in re.split(r"[|,]", expected.strip("() "))]
        short = actual.split(".")[-1].split(":")[-1]
        if "*" in names or short in names:
            return True
        if "UnknownException" == short:
            return self.choose((False, True), "unknown exception catch")
        if actual in self.p.types:
            info = self.p.types[actual]
            if any(self.matches_type(parent, expected) for parent in info.parents if parent != actual):
                return True
        if "Throwable" in names or "BaseException" in names or "Exception" in names:
            return True
        runtime = {"ArithmeticException", "NullPointerException", "IllegalArgumentException", "NumberFormatException", "ClassCastException", "IllegalStateException", "IndexOutOfBoundsException", "NoSuchElementException", "HttpClientErrorException", "HttpServerErrorException"}
        return "RuntimeException" in names and short in runtime

    def block(self, statements, env):
        for stmt in statements:
            completion = self.statement(stmt, env)
            if completion.kind != "normal":
                return completion
        return Completion()

    def statement(self, stmt, env):
        self.tick(stmt.span)
        op, args, span = stmt.op, stmt.args, stmt.span
        if op == "expr":
            self.value(args[0], env)
        elif op in {"assign", "declare"}:
            value = self.value(args[1], env)
            for target in args[0]:
                if op == "declare" and target.op == "var":
                    if env.get(SCOPES):
                        env[SCOPES][-1].setdefault(target.value, (target.value in env, env.get(target.value)))
                    env[target.value] = Unknown("uninitialized local", target.typ)
                self.assign(target,value,env,span,args[1].typ)
        elif op == "scope":
            scope = {}
            env.setdefault(SCOPES, []).append(scope)
            try:
                return self.block(stmt.body, env)
            finally:
                env[SCOPES].pop()
                for name, (existed, value) in scope.items():
                    if existed:
                        env[name] = value
                    else:
                        env.pop(name, None)
        elif op == "global":
            env[GLOBAL_NAMES].update(stmt.value)
        elif op in {"return", "yield"}:
            if op == "yield" and self.method.key not in self.safe_generators:
                self.note("dependency-cleanup", "Generator dependency setup is modeled; teardown is not", span)
                self.unknown_teardown = True
            return Completion(op,self.value(args[0],env),args[0].typ)
        elif op == "throw":
            value = self.value(args[0], env)
            if value is None:
                if self.language == "python" and self.last_exception:
                    raise self.last_exception
                raise Raised("RuntimeError" if self.language == "python" else "NullPointerException")
            raise Raised(value.typ if isinstance(value, Object) else "UnknownException", value)
        elif op == "if":
            return self.block(stmt.body if self.condition(self.value(args[0], env), span) else stmt.other, env)
        elif op in {"break", "continue"}:
            return Completion(op)
        elif op in {"while", "do"}:
            count = 0
            while (op == "do" and count == 0) or self.condition(self.value(args[0], env), span):
                if count >= self.loop_limit:
                    self.note("loop-budget", "Loop tail effects are unknown", span)
                    raise Incomplete()
                count += 1
                completion = self.block(stmt.body, env)
                if completion.kind == "break":
                    return Completion()
                if completion.kind not in {"normal", "continue"}:
                    return completion
                if stmt.value == "for":
                    self.block(stmt.other, env)
            if stmt.value != "for":
                return self.block(stmt.other, env)
        elif op == "foreach":
            values = self.value(args[1], env)
            if unknown(values):
                self.unsupported("iteration over unknown collection", span)
            if not isinstance(values, (list, tuple, dict, str, range)):
                raise Raised("TypeError")
            for index, value in enumerate(values):
                if index >= self.loop_limit:
                    self.note("loop-budget", "Collection loop tail effects unknown", span)
                    raise Incomplete()
                self.assign(args[0], value, env, span)
                completion = self.block(stmt.body, env)
                if completion.kind == "break":
                    return Completion()
                if completion.kind not in {"normal", "continue"}:
                    return completion
            return self.block(stmt.other, env)
        elif op == "try":
            previous_exception = self.last_exception
            try:
                return self.try_statement(stmt, env)
            finally:
                self.last_exception = previous_exception
        elif op == "with":
            managers = []
            for context, target in args:
                value = self.value(context, env)
                if not isinstance(value, Object) or value.typ not in {"sqlmodel.Session", "sqlalchemy.orm.Session", "httpx.Client", "httpx.AsyncClient"}:
                    self.unsupported("unknown context manager", span)
                if target:
                    self.assign(target, value, env, span)
                managers.append(value)
            completion = None
            try:
                completion = self.block(stmt.body, env)
                return completion
            finally:
                if completion is None or completion.kind != "yield":
                    from .models import call
                    for value in reversed(managers):
                        if value.typ in {"sqlmodel.Session", "sqlalchemy.orm.Session"}:
                            call(self, value, "close", (), {}, span)
                elif self.method.key in self.safe_generators:
                    self.dependency_exits.append((self.frames[-1],managers,span))
        elif op == "switch":
            value, groups = self.value(args[0], env), args[1]
            selected, default = None, None
            for index, (labels, is_default, body, rule) in enumerate(groups):
                if is_default:
                    default = index
                for label in labels:
                    if self.condition(equal(value, self.value(label, env)), span):
                        selected = index
                        break
                if selected is not None:
                    break
            selected = selected if selected is not None else default
            if selected is not None:
                for labels, is_default, body, rule in groups[selected:]:
                    completion = self.block(body, env)
                    if completion.kind == "break":
                        return Completion()
                    if completion.kind != "normal":
                        return completion
                    if rule:
                        break
        else:
            self.unsupported(str(stmt.value or op), span)
        return Completion()

    def try_statement(self, stmt, env):
        args = stmt.args
        completion, raised = Completion(), None
        try:
            completion = self.block(stmt.body, env)
            if completion.kind == "normal":
                completion = self.block(stmt.other, env)
        except Raised as exc:
            handled = False
            self.last_exception = exc
            for expected, pname, body in args[0]:
                if self.matches_type(exc.typ, expected):
                    if pname:
                        env[pname] = exc.value if exc.value is not None else self.state.new(exc.typ)
                    try:
                        completion = self.block(body, env)
                    except Raised as new_exc:
                        raised = new_exc
                    handled = True
                    break
            if not handled:
                raised = exc
        final = self.block(args[1], env)
        if final.kind != "normal":
            return final
        if raised:
            raise raised
        return completion

    def request(self, request, caller=None, span=Span()):
        from .protocol import dispatch
        return dispatch(self, request, caller, span)
