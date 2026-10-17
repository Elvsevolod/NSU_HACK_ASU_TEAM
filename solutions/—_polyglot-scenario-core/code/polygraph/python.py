"""Python AST -> shared IR, plus source-derived FastAPI contracts. No imports run."""
import ast
from pathlib import PurePosixPath
from collections import defaultdict
from libcst import ParserSyntaxError

from .ir import Endpoint, Expr, Method, Parameter, Span, Stmt, TypeInfo
from .python_names import parse as parse_names


def name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return name(node.value) + "." + node.attr
    return ""


def literal(node, default=None):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return default


class PythonAdapter:
    def __init__(self, project):
        self.p = project
        self.trees, self.module_names, self.routers, self.mounts = {}, {}, {}, []
        self.roots, self.routes, self.raw_globals = set(), [], {}
        self.file = ""
        self.bindings = {}
        self.node_files = {}
        self.import_modules, self.deployments, self.scoped_modules = {}, {}, {}

    def span(self, node):
        return Span(self.file, getattr(node, "lineno", 0), getattr(node, "col_offset", 0) + 1)

    def qualified(self, value, file=None):
        file = file or self.file
        first = value.split(".")[0]
        target = self.p.imports.get(file, {}).get(first, self.module_names.get(file, "") + "." + first) + value[len(first):]
        return self.scoped(target, file)

    def scoped(self, value, file):
        if ":" in value:
            return value
        parts = value.split(".")
        for length in range(len(parts), 0, -1):
            module = self.scoped_modules.get((self.deployments.get(file, ""), ".".join(parts[:length])))
            if module:
                return module + ("." + ".".join(parts[length:]) if length < len(parts) else "")
        return value

    def references(self, node):
        file = self.node_files.get(id(node), self.file)
        values = self.bindings.get(file, {}).get((getattr(node, "lineno", 0), getattr(node, "col_offset", 0), type(node).__name__), ())
        return tuple(self.scoped(value, file) for value in values)

    def canonical(self, node):
        references = self.references(node)
        return references[0] if len(references) == 1 and not references[0].startswith("local:") else self.qualified(name(node), self.node_files.get(id(node), self.file)) if not references else ""

    def framework(self, node, choices):
        value = self.canonical(node)
        return value.split(".")[-1] if value.startswith(("fastapi.", "typing.", "typing_extensions.", "sqlmodel.", "pydantic.", "pydantic_settings.")) and value.split(".")[-1] in choices else ""

    def index(self):
        owners = defaultdict(set)
        for file in self.p.sources:
            if not file.endswith(".py"):
                continue
            path = PurePosixPath(file)
            # Recover the import package from __init__.py ancestry, not directory names.
            parts = [path.stem] if path.stem != "__init__" else []
            parent = path.parent
            while str(parent) != "." and (parent / "__init__.py").as_posix() in self.p.sources:
                parts.insert(0, parent.name)
                parent = parent.parent
            raw_module = ".".join(parts) or path.parent.name
            deployment = self.p.module(file)
            self.import_modules[file], self.deployments[file] = raw_module, deployment
            owners[raw_module].add(deployment)
        for file, raw_module in self.import_modules.items():
            deployment = self.deployments[file]
            module = "py@" + deployment + ":" + raw_module if len(owners[raw_module]) > 1 else raw_module
            self.module_names[file] = self.p.lexical_modules[file] = module
            self.scoped_modules[deployment, raw_module] = module
        for file, raw_module in self.import_modules.items():
            source = self.p.sources[file]
            self.file = file
            path = PurePosixPath(file)
            module = self.module_names[file]
            try:
                package = raw_module if path.stem == "__init__" else raw_module.rpartition(".")[0]
                normalized, self.bindings[file], changed = parse_names(source, raw_module, package)
                tree = ast.parse(normalized, filename=file)
                if changed:
                    self.p.warn("python-syntax-normalized", "LibCST parenthesized exception tuples in memory for the host AST parser", Span(file))
            except (SyntaxError, ParserSyntaxError, UnicodeDecodeError) as exc:
                self.p.warn("python-parse", str(exc), Span(file, getattr(exc, "lineno", 0) or 0))
                continue
            self.trees[file] = tree
            self.node_files.update((id(node), file) for node in ast.walk(tree))
            aliases = self.p.imports.setdefault(file, {})
            for node in tree.body:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        aliases[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]
                elif isinstance(node, ast.ImportFrom):
                    base = node.module or ""
                    if node.level:
                        prefix = raw_module.split(".") if path.stem == "__init__" else raw_module.split(".")[:-1]
                        prefix = prefix[:len(prefix) - node.level + 1]
                        base = ".".join(prefix + ([base] if base else []))
                    for alias in node.names:
                        if alias.name != "*":
                            aliases[alias.asname or alias.name] = base + "." + alias.name
                elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        if isinstance(target, ast.Name) and node.value is not None:
                            key = module + "." + target.id
                            self.raw_globals[key] = (file, node.value)
                            self.p.globals[key] = self.expr(node.value)
                elif isinstance(node, ast.ClassDef):
                    self.index_class(node, module)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.index_method(node, module, module)

    def index_class(self, node, module):
        key = module + "." + node.name
        info = TypeInfo(key, node.name, self.p.module(self.file), "python", self.span(node), parents=[name(b) for b in node.bases])
        info.annotations["model"] = any(self.framework(b, {"SQLModel", "BaseModel", "BaseSettings"}) for b in node.bases)
        info.annotations["custom_metaclass"] = any(k.arg == "metaclass" for k in node.keywords)
        info.annotations['field_options']={}
        info.annotations['default_factories']=[]
        self.p.add_type(info)
        is_table = any(k.arg == "table" and literal(k.value) is True for k in node.keywords)
        for field in node.body:
            if isinstance(field, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.index_method(field, key, module)
            elif isinstance(field, ast.AnnAssign) and isinstance(field.target, ast.Name):
                typ = ast.unparse(field.annotation)
                default = self.expr(field.value) if field.value else None
                if isinstance(field.value, ast.Call) and self.framework(field.value.func, {"Field"}):
                    options = {k.arg: k.value for k in field.value.keywords}
                    checked={'alias','serialization_alias','validation_alias','exclude','gt','ge','lt','le','min_length','max_length','pattern','strict','allow_inf_nan','multiple_of','max_digits','decimal_places','validate_default','coerce_numbers_to_str','union_mode','fail_fast','discriminator'}
                    metadata={'default','default_factory','title','description','examples','deprecated','repr'}
                    orm={'primary_key','foreign_key','ondelete','unique','nullable','index','sa_type','sa_column','sa_column_args','sa_column_kwargs'}
                    if set(options)-checked-metadata-orm:info.annotations['field_options_unknown']=True
                    info.annotations['field_options'][field.target.id]={key:self.expr(value) for key,value in options.items() if key in checked}
                    if literal(options.get("primary_key")) is True:
                        info.primary_key = field.target.id
                    factory = name(options.get("default_factory"))
                    if 'default_factory' in options and not factory and not (isinstance(options['default_factory'],ast.Constant) and options['default_factory'].value is None):
                        info.annotations['field_options_unknown']=True
                    if factory:
                        info.annotations['default_factories'].append(field.target.id)
                        info.generated_key = True
                        call=ast.copy_location(ast.Call(func=options['default_factory'],args=[],keywords=[]),field.value)
                        default=self.expr(call)
                    elif "default" in options:
                        default = self.expr(options["default"])
                    else:
                        default = None
                elif isinstance(field.value, ast.Call) and self.framework(field.value.func, {"Relationship"}):
                    default = Expr("const", value=[] if typ.startswith(("list[", "List[")) else None, span=self.span(field))
                info.fields[field.target.id] = (typ, default)
            elif isinstance(field, ast.Assign):
                for target in field.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        info.table = self.p.table_id(literal(field.value, ""))
                    if isinstance(target,ast.Name) and target.id=='model_config':
                        value=field.value
                        if isinstance(value,ast.Call) and self.framework(value.func,{'ConfigDict','SettingsConfigDict'}):
                            info.annotations['model_config']={k.arg:self.expr(k.value) for k in value.keywords}
                        elif isinstance(value,ast.Dict):
                            info.annotations['model_config']={literal(k):self.expr(v) for k,v in zip(value.keys,value.values)}
                        else:info.annotations['model_config_unknown']=True
        if is_table and not info.table:
            info.table = self.p.table_id(node.name.lower())
        info.annotations["table"] = is_table

    def annotation_parts(self, annotation):
        default_dep = ""
        metadata = []
        raw = annotation
        if isinstance(raw, ast.Name):
            global_name = self.qualified(raw.id)
            if global_name in self.raw_globals:
                file, raw = self.raw_globals[global_name]
        if isinstance(raw, ast.Subscript) and self.framework(raw.value, {"Annotated"}):
            elements = raw.slice.elts if isinstance(raw.slice, ast.Tuple) else [raw.slice]
            metadata = elements[1:]
            for item in elements[1:]:
                if isinstance(item, ast.Call) and self.framework(item.func, {"Depends", "Security"}) and item.args:
                    default_dep = self.canonical(item.args[0])
                elif isinstance(item,ast.Call) and self.framework(item.func,{'Depends','Security'}):
                    default_dep = self.canonical(elements[0])
            raw = elements[0]
        return (ast.unparse(raw) if raw else ""), default_dep, metadata

    def index_method(self, node, owner, module):
        key = owner + "." + node.name
        params, defaults = [], {}
        positional = node.args.posonlyargs + node.args.args
        for arg, default in zip(positional[-len(node.args.defaults):] if node.args.defaults else [], node.args.defaults):
            defaults[arg.arg] = default
        defaults.update({arg.arg: default for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults) if default is not None})
        for arg in positional + node.args.kwonlyargs:
            if arg.arg in {"self", "cls"} and owner in self.p.types:
                continue
            typ, dep, metadata = self.annotation_parts(arg.annotation)
            default = defaults.get(arg.arg)
            location, alias = "", arg.arg
            markers = [item for item in metadata if isinstance(item, ast.Call)] + ([default] if isinstance(default, ast.Call) else [])
            for marker in markers:
                short = self.framework(marker.func, {"Depends", "Security", "Query", "Path", "Header", "Body", "Cookie", "Form"})
                if short in {"Depends", "Security"} and marker.args:
                    dep = self.canonical(marker.args[0])
                    default = None
                elif short in {'Depends','Security'}:
                    dep=self.qualified(typ)
                    default=None
                elif short in {"Query", "Path", "Header", "Body", "Cookie", "Form"}:
                    location = short.lower()
                    options = {k.arg: k.value for k in marker.keywords}
                    alias = literal(options.get("alias"), arg.arg)
                    if marker is default:
                        default = marker.args[0] if marker.args and literal(marker.args[0], ...) is not ... else options.get("default")
            params.append(Parameter(arg.arg, typ, location, alias, self.expr(default) if default else None, dep))
        annotations = {"async": isinstance(node, ast.AsyncFunctionDef)}
        annotations["generator"] = any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node))
        annotations["property"] = any(name(d) == "property" for d in node.decorator_list)
        annotations['validation_hook']=any(self.framework(d.func if isinstance(d,ast.Call) else d,{'field_validator','model_validator','computed_field','field_serializer','model_serializer'}) for d in node.decorator_list)
        annotations["keyword_only"] = [a.arg for a in node.args.kwonlyargs]
        annotations["positional_only"] = [a.arg for a in node.args.posonlyargs]
        if any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "middleware" for d in node.decorator_list):
            annotations["middleware"] = True
        if node.args.vararg or node.args.kwarg:
            annotations["variadic"] = True
        method = Method(key, node.name, owner, self.p.module(self.file), "python", self.span(node), params,
                        ast.unparse(node.returns) if node.returns else "", doc=ast.get_docstring(node) or "", annotations=annotations)
        self.p.add_method(method, (node, min([node.lineno] + [d.lineno for d in node.decorator_list]), node.end_lineno))
        if owner in self.p.types:
            self.p.types[owner].methods.append(key)
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr in {"get", "post", "put", "patch", "delete", "head", "options", "api_route"}:
                route = literal(decorator.args[0], None) if decorator.args else None
                if not isinstance(route, str):
                    self.p.warn("dynamic-route", "FastAPI route path is not a literal", self.span(decorator))
                    continue
                options = {k.arg: k.value for k in decorator.keywords}
                verbs = literal(options.get("methods"), [decorator.func.attr.upper()])
                deps = self.dependencies(options.get("dependencies"))
                response=(self.qualified(name(options['response_model'])) if name(options.get('response_model')) else '') if 'response_model' in options else method.return_type
                flags={key:literal(value) for key,value in options.items() if key in {'response_model_by_alias','response_model_exclude_none','response_model_exclude_defaults','response_model_exclude_unset'}}
                self.routes.append((self.qualified(name(decorator.func.value)), method.key, route, verbs, literal(options.get("status_code"), 200), deps,response,flags))

    def dependencies(self, node):
        return [self.canonical(item.args[0]) for item in (node.elts if isinstance(node, (ast.List, ast.Tuple)) else [])
                if isinstance(item, ast.Call) and item.args and self.framework(item.func, {"Depends", "Security"})]

    def constant(self, node, file=None, seen=None):
        file = file or self.file
        seen = set() if seen is None else seen
        value = literal(node, ...)
        if value is not ...:
            return value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            a, b = self.constant(node.left, file, seen), self.constant(node.right, file, seen)
            return a + b if isinstance(a, str) and isinstance(b, str) else None
        key = self.qualified(name(node), file)
        if key in self.p.source_globals:return self.p.source_globals[key]
        if isinstance(node,ast.Attribute):
            parent=self.constant(node.value,file,set(seen))
            if isinstance(parent,dict) and node.attr in parent:return parent[node.attr]
        if key in seen:
            return None
        seen.add(key)
        if key in self.raw_globals:
            source, value = self.raw_globals[key]
            return self.constant(value, source, seen)
        # Pydantic settings fields are data declarations, never imported constructors.
        if isinstance(node, ast.Attribute):
            root_key = self.qualified(name(node.value), file)
            global_info = self.raw_globals.get(root_key)
            if global_info and isinstance(global_info[1], ast.Call):
                typ = self.p.resolve_type(name(global_info[1].func), self.p.module(global_info[0]), global_info[0])
                field = self.p.type_fields(typ).get(node.attr)
                if field and field[1] and field[1].op == "const":
                    return field[1].value
        return None

    def link(self):
        for key, (file, node) in self.raw_globals.items():
            self.file = file
            if isinstance(node, ast.Call) and self.framework(node.func, {"FastAPI", "APIRouter"}):
                opts = {k.arg: k.value for k in node.keywords}
                prefix = self.constant(opts.get("prefix")) if "prefix" in opts else ""
                self.routers[key] = (prefix, self.dependencies(opts.get("dependencies")))
                if self.framework(node.func, {"FastAPI"}):
                    self.roots.add(key)
        for file, tree in self.trees.items():
            self.file = file
            def includes(nodes, conditional=False):
                for node in nodes:
                    if isinstance(node, ast.If):
                        test = self.constant(node.test)
                        if type(test) is bool:
                            yield from includes(node.body if test else node.orelse, conditional)
                        else:
                            yield from includes(node.body + node.orelse, True)
                    elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                        yield node.value, conditional
            for call, conditional in includes(tree.body):
                if isinstance(call.func, ast.Attribute) and call.func.attr == "include_router" and call.args:
                    opts = {k.arg: k.value for k in call.keywords}
                    prefix = self.constant(opts.get("prefix")) if "prefix" in opts else ""
                    self.mounts.append((self.qualified(name(call.func.value)), self.qualified(name(call.args[0])), prefix, self.dependencies(opts.get("dependencies")), conditional))
        def mounted(router, seen):
            if router in seen:
                return []
            prefix, deps = self.routers.get(router, ("", []))
            if prefix is None:
                return []
            result = [(prefix, deps, False)] if router in self.roots else []
            for parent, child, extra, outer, conditional in self.mounts:
                if child == router and extra is not None:
                    result.extend((path + extra + prefix, inherited + outer + deps, unknown or conditional) for path, inherited, unknown in mounted(parent, seen | {router}))
            return result
        for router, mid, path, verbs, status, deps,response,flags in self.routes:
            mounts = mounted(router, set())
            if not mounts:
                self.p.warn("unmounted-router", "FastAPI router is not statically connected to an application", self.p.methods[mid].span, router)
            for mount_index, (prefix, outer_deps, conditional) in enumerate(mounts):
                for verb in verbs:
                    self.p.endpoints.append(Endpoint(mid, verb.upper(), prefix + path, self.p.methods[mid].module, "fastapi", status, outer_deps + deps, {"mount_unknown": conditional, "registration_group": (router, mount_index),**flags},response))
        for info in self.p.types.values():
            if info.language == "python" and not info.table:
                for parent in info.parents:
                    resolved = self.p.resolve_type(parent, info.module, info.span.file)
                    if resolved and self.p.types[resolved].table:
                        info.table = self.p.types[resolved].table
        for _ in range(4):
            for info in self.p.types.values():
                if info.language == "python" and not info.annotations.get("model"):
                    info.annotations["model"] = any(self.p.types[parent].annotations.get("model") for p in info.parents
                                                    if (parent := self.p.resolve_type(p, info.module, info.span.file)))

    def expr(self, node):
        if node is None:
            return Expr("const", value=None)
        s = self.span(node)
        if isinstance(node, ast.Constant):
            if node.value is ...:
                return Expr("unknown", value="ellipsis", span=s)
            return Expr("const", value=node.value, span=s)
        if isinstance(node, ast.Name):
            return Expr("var", value=node.id, span=s, bindings=self.references(node))
        if isinstance(node, ast.Attribute):
            return Expr("field", (self.expr(node.value),), node.attr, s)
        if isinstance(node, ast.Call):
            receiver = self.expr(node.func.value) if isinstance(node.func, ast.Attribute) else None
            callee = node.func.attr if isinstance(node.func, ast.Attribute) else name(node.func)
            return Expr("call", (receiver, tuple(self.expr(a) for a in node.args), tuple((k.arg, self.expr(k.value)) for k in node.keywords)), callee, s, bindings=self.references(node.func))
        if isinstance(node, ast.BinOp):
            return Expr("bin", (self.expr(node.left), self.expr(node.right)), self.operator(node.op), s)
        if isinstance(node, ast.BoolOp):
            return Expr("bool", tuple(self.expr(v) for v in node.values), "and" if isinstance(node.op, ast.And) else "or", s)
        if isinstance(node, ast.UnaryOp):
            return Expr("unary", (self.expr(node.operand),), {ast.Not: "not", ast.USub: "-", ast.UAdd: "+", ast.Invert: "~"}.get(type(node.op), "?"), s)
        if isinstance(node, ast.Compare):
            return Expr("compare", tuple(self.expr(v) for v in [node.left] + node.comparators), tuple(self.operator(op) for op in node.ops), s)
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return Expr("list", tuple(self.expr(v) for v in node.elts), span=s)
        if isinstance(node, ast.Dict):
            if any(k is None for k in node.keys):
                return Expr("unsupported", value="dynamic dictionary expansion", span=s)
            return Expr("dict", tuple((self.expr(k), self.expr(v)) for k, v in zip(node.keys, node.values)), span=s)
        if isinstance(node, ast.Subscript):
            return Expr("index", (self.expr(node.value), self.expr(node.slice)), span=s)
        if isinstance(node, ast.Slice):
            return Expr("slice", tuple(self.expr(v) for v in [node.lower, node.upper, node.step]), span=s)
        if isinstance(node, ast.IfExp):
            return Expr("choose", (self.expr(node.test), self.expr(node.body), self.expr(node.orelse)), span=s)
        if isinstance(node, ast.Await):
            return Expr("await", (self.expr(node.value),), span=s)
        if isinstance(node, ast.JoinedStr):
            return Expr("format", tuple(self.expr(v.value) if isinstance(v, ast.FormattedValue) else self.expr(v) for v in node.values), span=s)
        if isinstance(node, ast.NamedExpr):
            return Expr("assign", (self.expr(node.target), self.expr(node.value)), span=s)
        return Expr("unsupported", value=type(node).__name__, span=s)

    @staticmethod
    def operator(op):
        return {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%", ast.Pow: "**",
                ast.Eq: "==", ast.NotEq: "!=", ast.Is: "is", ast.IsNot: "is not", ast.In: "in", ast.NotIn: "not in",
                ast.Gt: ">", ast.Lt: "<", ast.GtE: ">=", ast.LtE: "<=", ast.BitAnd: "&", ast.BitOr: "|", ast.BitXor: "^",
                ast.LShift: "<<", ast.RShift: ">>"}.get(type(op), "?")

    def block(self, nodes):
        return tuple(statement for node in nodes for statement in self.stmt(node))

    def stmt(self, node):
        s = self.span(node)
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if node.value is None:
                return ()
            return (Stmt("assign", (tuple(self.expr(t) for t in targets), self.expr(node.value)), span=s),)
        if isinstance(node, ast.AugAssign):
            target = self.expr(node.target)
            return (Stmt("assign", ((target,), Expr("bin", (target, self.expr(node.value)), self.operator(node.op), s)), span=s),)
        if isinstance(node, ast.Expr):
            if isinstance(node.value, (ast.Yield, ast.YieldFrom)):
                return (Stmt("yield", (self.expr(node.value.value),), span=s),)
            return (Stmt("expr", (self.expr(node.value),), span=s),)
        if isinstance(node, ast.Return):
            return (Stmt("return", (self.expr(node.value),), span=s),)
        if isinstance(node, ast.Raise):
            return (Stmt("throw", (self.expr(node.exc),), span=s),)
        if isinstance(node, ast.If):
            return (Stmt("if", (self.expr(node.test),), self.block(node.body), self.block(node.orelse), span=s),)
        if isinstance(node, (ast.For, ast.AsyncFor)):
            return (Stmt("foreach", (self.expr(node.target), self.expr(node.iter)), self.block(node.body), self.block(node.orelse), span=s),)
        if isinstance(node, ast.While):
            return (Stmt("while", (self.expr(node.test),), self.block(node.body), self.block(node.orelse), span=s),)
        if isinstance(node, ast.Try):
            handlers = tuple((ast.unparse(h.type) if h.type else "*", h.name or "", self.block(h.body)) for h in node.handlers)
            return (Stmt("try", (handlers, self.block(node.finalbody)), self.block(node.body), self.block(node.orelse), span=s),)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            contexts = tuple((self.expr(i.context_expr), self.expr(i.optional_vars) if i.optional_vars else None) for i in node.items)
            return (Stmt("with", contexts, self.block(node.body), span=s),)
        if isinstance(node, ast.Assert):
            return (Stmt("if", (Expr("unary", (self.expr(node.test),), "not", s),), (Stmt("throw", (Expr("new", value="AssertionError", span=s),), span=s),), span=s),)
        if isinstance(node, (ast.Break, ast.Continue)):
            return (Stmt(type(node).__name__.lower(), span=s),)
        if isinstance(node, ast.Global):
            return (Stmt("global", value=node.names, span=s),)
        if isinstance(node, ast.Pass):
            return ()
        return (Stmt("unsupported", value=type(node).__name__, span=s),)

    def lower(self, method, node):
        self.file = method.span.file
        if method.annotations.get("variadic"):
            return (Stmt("unsupported", value="variadic Python function", span=method.span),)
        return self.block(node.body)
