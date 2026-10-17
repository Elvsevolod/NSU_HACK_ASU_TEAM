"""Java syntax frontend and Spring fact provider. Execution belongs to the kernel."""
import json
import re

from tree_sitter import Language, Parser
import tree_sitter_java

from .ir import Endpoint, Expr, Method, Parameter, Span, Stmt, TypeInfo


def text(node):
    return node.text.decode("utf-8") if node is not None else ""


def walk(node):
    yield node
    for child in node.named_children:
        yield from walk(child)


def annotations(node):
    mods = next((c for c in node.named_children if c.type == "modifiers"), None)
    return {text(a.child_by_field_name("name")).split(".")[-1]: text(a.child_by_field_name("arguments"))
            for a in mods.named_children if a.type in {"annotation", "marker_annotation"}} if mods else {}


def full_annotations(node):
    mods=next((c for c in node.named_children if c.type=='modifiers'),None)
    return {text(a.child_by_field_name('name')):text(a.child_by_field_name('arguments')) for a in mods.named_children if a.type in {'annotation','marker_annotation'}} if mods else {}


def annotation_value(raw, key=""):
    if key:
        match = re.search(r"\b" + re.escape(key) + r'\s*=\s*("(?:\\.|[^"\\])*")', raw)
    else:
        match = re.search(r'("(?:\\.|[^"\\])*")', raw)
    if match:
        try:
            return json.loads(match[1])
        except ValueError:
            pass
    return ""


def paths(raw):
    if not raw:
        return [""]
    value = re.search(r"(?:\b(?:value|path)\s*=\s*)(\{[^}]*\}|\"(?:\\.|[^\"\\])*\")", raw)
    if value:
        return [json.loads(s) for s in re.findall(r'"(?:\\.|[^"\\])*"', value[1])]
    prefix = raw.lstrip("( ")
    if prefix.startswith('"') or prefix.startswith("{"):
        head = re.match(r'(\{[^}]*\}|"(?:\\.|[^"\\])*")', prefix)
        return [json.loads(s) for s in re.findall(r'"(?:\\.|[^"\\])*"', head[1])] if head else []
    return [""]


class JavaAdapter:
    def __init__(self, project):
        self.p = project
        self.parser = Parser(Language(tree_sitter_java.language()))
        self.trees, self.raw_types = {}, {}
        self.file, self.local_types = "", {}
        self.owner = ""
        self.callback_owner=''
        self.package_names={};self.custom_constraints=set()

    def span(self, node):
        return Span(self.file, node.start_point.row + 1, node.start_point.column + 1)

    def index(self):
        for file, source in self.p.sources.items():
            if not file.endswith(".java"):
                continue
            self.file = file
            tree = self.parser.parse(source)
            self.trees[file] = tree
            if tree.root_node.has_error:
                self.p.warn("java-parse", "Java parser reported an unsupported or invalid construct", Span(file))
            package = next((text(n).removeprefix("package ").rstrip(";").strip() for n in tree.root_node.named_children if n.type == "package_declaration"), "")
            self.package_names[file]=package
            imported = self.p.imports.setdefault(file, {})
            for node in tree.root_node.named_children:
                if node.type == "import_declaration":
                    value = text(node).removeprefix("import ").removeprefix("static ").rstrip(";").strip()
                    if not value.endswith(".*"):
                        imported[value.split(".")[-1]] = value
                    else:
                        self.p.import_wildcards[file].append(value[:-2])
            module = self.p.module(file)
            for node in walk(tree.root_node):
                if node.type=='annotation_type_declaration' and 'Constraint' in annotations(node):
                    self.custom_constraints.add((package+'.' if package else '')+text(node.child_by_field_name('name')))
                if node.type not in {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"}:
                    continue
                short = text(node.child_by_field_name("name"))
                fqn = package + "." + short if package else short
                key = module + ":" + fqn
                parents = []
                for field in ["superclass", "interfaces"]:
                    raw = text(node.child_by_field_name(field))
                    raw = re.sub(r"^(?:extends|implements)\s+", "", raw)
                    parents.extend(re.findall(r"[\w.]+(?:\s*<[^>]+>)?", raw))
                if node.type == "interface_declaration":
                    ext = next((c for c in node.named_children if c.type == "extends_interfaces"), None)
                    if ext:
                        parents.extend(re.findall(r"[\w.]+(?:\s*<[^>]+>)?", re.sub(r"^extends\s+", "", text(ext))))
                meta = annotations(node)
                meta['validation_annotations']=full_annotations(node)
                meta["kind"] = node.type
                info = TypeInfo(key, short, module, "java", self.span(node), parents=parents, annotations=meta)
                self.p.add_type(info)
                self.raw_types[key] = node
                body = node.child_by_field_name("body")
                members=[member for child in body.named_children for member in (child.named_children if child.type=='enum_body_declarations' else [child])] if body else []
                for child in members:
                    if child.type == "field_declaration":
                        typ = text(child.child_by_field_name("type"))
                        ann = annotations(child)
                        modifiers = next((c for c in child.named_children if c.type == "modifiers"), None)
                        is_static = modifiers is not None and any(c.type == "static" for c in modifiers.children)
                        for var in child.named_children:
                            if var.type != "variable_declarator":
                                continue
                            field = text(var.child_by_field_name("name"))
                            default_node = var.child_by_field_name("value")
                            if is_static:
                                if default_node:
                                    default = self.expr(default_node)
                                elif any(c.type == "static_initializer" for c in body.named_children):
                                    default = Expr("unknown", value="static initializer value not modeled", span=self.span(var), typ=typ)
                                else:
                                    default = Expr("const", value=False if typ == "boolean" else 0 if typ in {"byte", "short", "int", "long", "float", "double"} else None, span=self.span(var), typ=typ)
                                self.p.globals[key + "." + field] = default
                                if any(c.type == "final" for c in modifiers.children):
                                    self.p.immutable_globals.add(key + "." + field)
                                continue
                            info.fields[field] = (typ, self.expr(default_node) if default_node else None)
                            if ann:info.annotations.setdefault('field_annotations',{})[field]=full_annotations(child)
                            if "Column" in ann:
                                info.columns[field] = annotation_value(ann["Column"], "name") or field
                            if "Id" in ann:
                                info.primary_key = field
                            if "GeneratedValue" in ann:
                                info.generated_key = True
                            if set(ann) & {"Autowired", "Inject", "Resource"}:
                                info.annotations.setdefault("inject", []).append(field)
                    elif child.type in {"method_declaration", "constructor_declaration"}:
                        self.index_method(child, info)
                if "Table" in meta:
                    info.table = self.p.table_id(annotation_value(meta["Table"], "name") or short.lower())
                elif "Entity" in meta:
                    info.table = self.p.table_id(re.sub(r"(?<!^)(?=[A-Z])", "_", short).lower()) or self.p.table_id(short.lower())
                elif "Document" in meta:
                    info.table = self.p.table_id(annotation_value(meta["Document"], "collection") or short[:1].lower() + short[1:])
                for parent in parents:
                    match = re.search(r"(?:JpaRepository|CrudRepository|PagingAndSortingRepository|Repository)\s*<\s*([\w.]+)", parent)
                    if match:
                        info.repository_entity = match[1]

    def index_method(self, node, owner):
        name = "<init>" if node.type == "constructor_declaration" else text(node.child_by_field_name("name"))
        params = []
        raw_params = node.child_by_field_name("parameters")
        for par in raw_params.named_children if raw_params else []:
            if par.type not in {"formal_parameter", "spread_parameter"}:
                continue
            typ, pname = text(par.child_by_field_name("type")), text(par.child_by_field_name("name"))
            ann = annotations(par)
            location, alias, default = "", pname, None
            if "Param" in ann:
                alias = annotation_value(ann["Param"], "value") or annotation_value(ann["Param"]) or pname
            for attribute, loc in [("PathVariable", "path"), ("RequestParam", "query"), ("RequestHeader", "header"), ("RequestBody", "body")]:
                if attribute in ann:
                    location = loc
                    alias = annotation_value(ann[attribute], "name") or annotation_value(ann[attribute], "value") or annotation_value(ann[attribute]) or pname
                    value = annotation_value(ann[attribute], "defaultValue")
                    if value:
                        default = Expr("const", value=value, span=self.span(par))
            params.append(Parameter(pname, typ, location, alias, default,annotations=full_annotations(par)))
        key = owner.key + "#" + name + "(" + ",".join(p.typ for p in params) + ")"
        ann = annotations(node)
        ann['validation_annotations']=full_annotations(node)
        modifiers=next((c for c in node.named_children if c.type=='modifiers'),None)
        for flag in ['static','private']:
            ann[flag]=bool(modifiers is not None and any(c.type==flag for c in modifiers.children))
        method = Method(key, name, owner.key, owner.module, "java", self.span(node), params,
                        text(node.child_by_field_name("type")), abstract=node.child_by_field_name("body") is None,
                        transaction="Transactional" in ann or "Transactional" in owner.annotations, annotations=ann)
        self.p.add_method(method, (node, node.start_point.row + 1, node.end_point.row + 1))
        owner.methods.append(key)
        # Constructor assignments are generic dependency wiring facts, not execution.
        if name == "<init>":
            names = {p.name for p in params}
            for assignment in walk(node):
                if assignment.type == "assignment_expression":
                    lhs, rhs = text(assignment.child_by_field_name("left")), text(assignment.child_by_field_name("right"))
                    if lhs.startswith("this.") and rhs in names:
                        owner.annotations.setdefault("inject", []).append(lhs[5:])

    def link(self):
        # Repository<Entity> can be declared by a derived Spring Data interface.
        for _ in range(4):
            for info in list(self.p.types.values()):
                if info.language != "java" or not info.repository_entity:
                    continue
                for parent in info.parents:
                    resolved = self.p.resolve_type(parent, info.module, info.span.file)
                    if resolved and not self.p.types[resolved].repository_entity:
                        self.p.types[resolved].repository_entity = info.repository_entity
        for info in self.p.types.values():
            if info.language != "java":
                continue
            if not set(info.annotations) & {"RestController", "Controller"}:
                continue
            enabled = self.p.enabled(info)
            if enabled is False:
                continue
            for mid in info.methods:
                method = self.p.methods[mid]
                ann = method.annotations
                if self.p.enabled(method) is False:
                    continue
                for attribute, args in ann.items():
                    if attribute not in {"RequestMapping", "GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping"}:
                        continue
                    class_paths = paths(info.annotations.get("RequestMapping", ""))
                    verbs = re.findall(r"RequestMethod\.(\w+)", args) if attribute == "RequestMapping" else [attribute.removesuffix("Mapping").upper()]
                    verbs = verbs or ["*"]
                    for prefix in class_paths:
                        for suffix in paths(args):
                            path = "/" + "/".join(part.strip("/") for part in [prefix, suffix] if part.strip("/"))
                            for verb in verbs:
                                conditions = {"profile_unknown": enabled is None}
                                context_path=self.p.configuration.context_path(info.module)
                                from .values import unknown
                                if unknown(context_path):conditions['context_path_unknown']=True
                                full_path=path if unknown(context_path) else context_path+path
                                if re.search(r"\b(?:params|headers|consumes|produces)\s*=", args):
                                    conditions["mapping_constraints"] = args
                                from .spring_http import response_status
                                self.p.endpoints.append(Endpoint(mid, verb, full_path, info.module, "spring",status=response_status({**info.annotations,**ann}),conditions=conditions))

    def expr(self, node):
        if node is None:
            return Expr("const", value=None)
        kind, raw, s = node.type, text(node), self.span(node)
        if kind in {'field_access','scoped_type_identifier'} and raw.split('.')[0] not in self.local_types:
            from .java_contracts import TYPES
            resolved=self.p.resolve_type(raw,self.p.module(self.file),self.file)
            if raw in TYPES or resolved and resolved.split(':',1)[-1]==raw:return Expr('type',value=raw,span=s)
        if kind in {"string_literal", "character_literal", "decimal_integer_literal", "hex_integer_literal", "octal_integer_literal", "binary_integer_literal", "decimal_floating_point_literal", "hex_floating_point_literal", "true", "false", "null_literal"}:
            try:
                if kind == "string_literal":
                    value, typ = json.loads(raw), "String"
                elif kind == "character_literal":
                    value, typ = json.loads('"' + raw[1:-1].replace('"', '\\"') + '"'), "char"
                elif kind in {"true", "false", "null_literal"}:
                    value, typ = {"true": True, "false": False, "null": None}[raw], "boolean" if raw != "null" else "null"
                elif "floating" in kind:
                    value, typ = float(raw.rstrip("dDfF").replace("_", "")), "double"
                else:
                    token = raw.rstrip("lL").replace("_", "")
                    base = 16 if token.lower().startswith("0x") else 2 if token.lower().startswith("0b") else 8 if len(token) > 1 and token.startswith("0") else 10
                    value, typ = int(token, base), "long" if raw[-1:] in "lL" else "int"
                return Expr("const", value=value, span=s, typ=typ)
            except ValueError:
                return Expr("unsupported", value="Java literal " + kind, span=s)
        if kind in {"identifier", "this", "super", "type_identifier", "scoped_type_identifier"}:
            if '.' in raw:
                from .java_contracts import TYPES
                if raw in TYPES:return Expr('type',value=raw,span=s)
            return Expr("var", value=raw, span=s, typ=self.local_types.get(raw, ""))
        if kind == "field_access":
            owner, field = node.child_by_field_name("object"), text(node.child_by_field_name("field"))
            receiver = self.expr(owner)
            typ = "long" if text(owner) == "Long" and field in {"MAX_VALUE", "MIN_VALUE"} else "int" if text(owner) == "Integer" and field in {"MAX_VALUE", "MIN_VALUE"} else ""
            resolved = self.p.resolve_type(receiver.typ or (self.owner if receiver.value == "this" else text(owner)), self.p.module(self.file), self.file)
            typ = self.p.type_fields(resolved).get(field, (typ, None))[0]
            return Expr("field", (receiver,), field, s, typ)
        if kind=='method_reference':
            if any(c.type in {'type_arguments','super'} for c in node.named_children):return Expr('unsupported',value='Generic/super method reference',span=s)
            qualifier=node.named_children[0];name='new' if node.children[-1].type=='new' else text(node.named_children[-1])
            receiver=self.expr(qualifier)
            owner=self.owner if text(qualifier)=='this' else self.p.resolve_type(receiver.typ or text(qualifier),self.p.module(self.file),self.file)
            returns={m.return_type for m in self.p.methods_of(owner,name)}
            result=next(iter(returns)) if len(returns)==1 else ''
            if name=='new':result=owner
            return Expr('method_ref',(receiver,),(name,self.callback_owner,owner),s,result)
        if kind == "method_invocation":
            obj = node.child_by_field_name("object")
            args = node.child_by_field_name("arguments")
            receiver = self.expr(obj) if obj else None
            arguments = tuple(self.expr(a) for a in args.named_children) if args else ()
            name = text(node.child_by_field_name("name"))
            owner = self.owner if receiver is None else self.p.resolve_type(receiver.typ or (self.owner if receiver.value == "this" else text(obj)), self.p.module(self.file), self.file)
            returns = {method.return_type for method in self.p.methods_of(owner, name, len(arguments))}
            if not returns and receiver is not None:
                from .java_contracts import RETURNS
                raw_type = re.sub(r'<.*>', '', receiver.typ).strip()
                canonical = raw_type if '.' in raw_type else self.p.resolve_import(raw_type, self.file) or 'java.lang.' + raw_type
                if name in RETURNS.get(canonical, {}):
                    returns.add(RETURNS[canonical][name])
                canonical=self.p.resolve_import(text(obj),self.file) or (text(obj) if '.' in text(obj) else 'java.lang.'+text(obj))
                if name in RETURNS.get(canonical,{}):returns.add(RETURNS[canonical][name])
                if name=='stream':returns.add('java.util.stream.Stream<'+(re.search(r'<(.+)>',receiver.typ)[1] if re.search(r'<(.+)>',receiver.typ) else 'Object')+'>')
                if name=='collect' and raw_type=='java.util.stream.Stream' and len(arguments)==1:
                    collector=arguments[0]
                    if collector.op=='call' and collector.value in {'toList','toSet'}:
                        qualifier=collector.args[0]
                        if qualifier is not None and qualifier.op=='var' and (self.p.resolve_import(qualifier.value,self.file) or qualifier.value)=='java.util.stream.Collectors':
                            returns.add('java.util.List' if collector.value=='toList' else 'java.util.Set')
                if name=='get':
                    generic=re.fullmatch(r'(?:[\w.]+)<\s*([\w.]+)\s*>',receiver.typ)
                    mapping=re.fullmatch(r'(?:[\w.]+)<\s*[\w.]+\s*,\s*([\w.]+)\s*>',receiver.typ)
                    if generic and raw_type.split('.')[-1] in {'List','ArrayList','LinkedList','Optional'}:returns.add(generic[1])
                    if mapping and raw_type.split('.')[-1] in {'Map','HashMap','LinkedHashMap'}:returns.add(mapping[1])
            if not owner and receiver is not None and receiver.op == "var":
                canonical = self.p.imports.get(self.file, {}).get(receiver.value, "java.lang." + receiver.value)
                primitive_returns = {("java.lang.Long", "parseLong"): "long", ("java.lang.Long", "valueOf"): "Long",
                                     ("java.lang.Integer", "parseInt"): "int", ("java.lang.Integer", "valueOf"): "Integer"}
                if (canonical, name) in primitive_returns:
                    returns.add(primitive_returns[canonical, name])
            if not returns and not arguments and owner in self.p.types and set(self.p.types[owner].annotations) & {"Data", "Getter"}:
                field = name[3:] if name.startswith("get") else name[2:] if name.startswith("is") else ""
                field = field[:1].lower() + field[1:]
                if field in self.p.type_fields(owner):
                    returns.add(self.p.type_fields(owner)[field][0])
            return Expr("call", (receiver, arguments, ()), name, s, next(iter(returns)) if len(returns) == 1 else "")
        if kind == "object_creation_expression":
            args = node.child_by_field_name("arguments")
            typ = text(node.child_by_field_name("type"))
            return Expr("new", tuple(self.expr(a) for a in args.named_children) if args else (), typ, s, typ)
        if kind == "binary_expression":
            left, right = node.child_by_field_name("left"), node.child_by_field_name("right")
            op = text(node.child_by_field_name("operator")) or raw[left.end_byte - node.start_byte:right.start_byte - node.start_byte].strip()
            left_expr, right_expr = self.expr(left), self.expr(right)
            operand_types = {value.typ.split(".")[-1] for value in (left_expr, right_expr)}
            typ = "long" if operand_types & {"long", "Long"} else "int" if operand_types & {"int", "Integer", "byte", "Byte", "short", "Short", "char", "Character"} else ""
            if op in {"<<", ">>", ">>>"}:
                typ = "long" if left_expr.typ.split(".")[-1] in {"long", "Long"} else "int"
            result_type = "boolean" if op in {"&&", "||", "==", "!=", "<", ">", "<=", ">="} else typ
            return Expr("bool" if op in {"&&", "||"} else "bin", (left_expr, right_expr), {"&&": "and", "||": "or"}.get(op, op), s, result_type, operand_type=typ)
        if kind == "unary_expression":
            operand = self.expr(node.child_by_field_name("operand") or node.named_children[-1])
            operator = text(node.child_by_field_name("operator")) or raw[0]
            return Expr("unary", (operand,), operator, s, "boolean" if operator == "!" else operand.typ)
        if kind == "parenthesized_expression":
            return self.expr(node.named_children[0])
        if kind == "ternary_expression":
            return Expr("choose", tuple(self.expr(node.child_by_field_name(f)) for f in ["condition", "consequence", "alternative"]), span=s)
        if kind == "cast_expression":
            typ = text(node.child_by_field_name("type"))
            return Expr("cast", (self.expr(node.child_by_field_name("value")),), typ, s, typ)
        if kind == "array_access":
            return Expr("index", (self.expr(node.child_by_field_name("array")), self.expr(node.child_by_field_name("index"))), span=s)
        if kind == "array_initializer":
            return Expr("list", tuple(self.expr(n) for n in node.named_children), span=s)
        if kind == "class_literal":
            return Expr("type", value=raw.removesuffix(".class"), span=s)
        if kind == "assignment_expression":
            left, right = self.expr(node.child_by_field_name("left")), self.expr(node.child_by_field_name("right"))
            op = text(node.child_by_field_name("operator"))
            if op != "=":
                right = Expr("bin", (left, right), op.removesuffix("="), s, left.typ)
            return Expr("assign", (left, right), span=s)
        if kind == "update_expression":
            target = self.expr(node.named_children[0])
            operation = "++" if "++" in raw else "--"
            return Expr("update", (target,), ("pre" if raw.startswith(operation) else "post") + operation, s, target.typ)
        if kind == "instanceof_expression":
            return Expr("instanceof", (self.expr(node.child_by_field_name("left")),), text(node.child_by_field_name("right")), s, "boolean")
        return Expr("unsupported", value=kind, span=s)

    def block(self, node):
        if node is None:
            return ()
        if node.type in {"block", "constructor_body"}:
            return (Stmt("scope", body=tuple(s for child in node.named_children for s in self.stmt(child)), span=self.span(node)),)
        return self.stmt(node)

    def stmt(self, node):
        kind, s = node.type, self.span(node)
        if kind in {"block", "constructor_body"}:
            return self.block(node)
        if kind == "local_variable_declaration":
            typ = text(node.child_by_field_name("type"))
            result = []
            for var in node.named_children:
                if var.type == "variable_declarator":
                    pname = text(var.child_by_field_name("name"))
                    self.local_types[pname] = typ
                    value = self.expr(var.child_by_field_name("value")) if var.child_by_field_name("value") else Expr("unknown", value="uninitialized local", typ=typ, span=s)
                    result.append(Stmt("declare", ((Expr("var", value=pname, typ=typ, span=s),), value), value=typ, span=s))
            return tuple(result)
        if kind == "expression_statement":
            return (Stmt("expr", (self.expr(node.named_children[0]),), span=s),)
        if kind in {"return_statement", "throw_statement"}:
            return (Stmt("return" if kind == "return_statement" else "throw", (self.expr(node.named_children[0]) if node.named_children else Expr("const", value=None, span=s),), span=s),)
        if kind == "if_statement":
            return (Stmt("if", (self.expr(node.child_by_field_name("condition")),), self.block(node.child_by_field_name("consequence")), self.block(node.child_by_field_name("alternative")), span=s),)
        if kind in {"while_statement", "do_statement"}:
            return (Stmt("do" if kind == "do_statement" else "while", (self.expr(node.child_by_field_name("condition")),), self.block(node.child_by_field_name("body")), span=s),)
        if kind == "enhanced_for_statement":
            return (Stmt("foreach", (Expr("var", value=text(node.child_by_field_name("name")), span=s), self.expr(node.child_by_field_name("value"))), self.block(node.child_by_field_name("body")), span=s),)
        if kind == "for_statement":
            init = node.child_by_field_name("init")
            condition = self.expr(node.child_by_field_name("condition")) if node.child_by_field_name("condition") else Expr("const", value=True, span=s)
            updates = tuple(Stmt("expr", (self.expr(c),), span=self.span(c)) for c in node.children_by_field_name("update"))
            setup = self.stmt(init) if init and init.type == "local_variable_declaration" else (Stmt("expr", (self.expr(init),), span=s),) if init else ()
            return (Stmt("scope", body=setup + (Stmt("while", (condition,), self.block(node.child_by_field_name("body")), updates, value="for", span=s),), span=s),)
        if kind == "try_statement" or kind == "try_with_resources_statement":
            if kind == "try_with_resources_statement":
                return (Stmt("unsupported", value="Java try-with-resources", span=s),)
            handlers, final = [], ()
            for child in node.named_children:
                if child.type == "catch_clause":
                    parameter = next(c for c in child.named_children if c.type == "catch_formal_parameter")
                    pname = text(parameter.child_by_field_name("name"))
                    types = text(next((c for c in parameter.named_children if c.type == "catch_type"), None))
                    handlers.append((types, pname, self.block(child.child_by_field_name("body"))))
                elif child.type == "finally_clause":
                    final = self.block(child.named_children[-1])
            return (Stmt("try", (tuple(handlers), final), self.block(node.child_by_field_name("body")), span=s),)
        if kind in {"switch_expression", "switch_statement"}:
            groups = []
            block = node.child_by_field_name("body")
            for group in block.named_children if block else []:
                labels, body, default = [], [], False
                for child in group.named_children:
                    if child.type == "switch_label":
                        default = text(child).startswith("default")
                        labels.extend(self.expr(c) for c in child.named_children)
                    else:
                        body.extend(self.stmt(child))
                groups.append((tuple(labels), default, tuple(body), group.type == "switch_rule"))
            return (Stmt("switch", (self.expr(node.child_by_field_name("condition")), tuple(groups)), span=s),)
        if kind in {"break_statement", "continue_statement"}:
            return (Stmt("break" if kind.startswith("break") else "continue", span=s),)
        if kind in {"line_comment", "block_comment", "empty_statement"}:
            return ()
        return (Stmt("unsupported", value=kind, span=s),)

    def lower(self, method, node):
        self.file = method.span.file
        self.owner = method.owner
        self.callback_owner=method.key
        self.local_types = {p.name: p.typ for p in method.params}
        info = self.p.types.get(method.owner)
        if info:
            self.local_types.update({k: v[0] for k, v in self.p.type_fields(info.key).items()})
        return self.block(node.child_by_field_name("body"))
