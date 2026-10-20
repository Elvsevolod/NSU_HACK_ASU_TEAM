"""Small technology models shared across adapters. Unknown libraries stay opaque."""
import re
from contextlib import contextmanager
from copy import deepcopy
from urllib.parse import urljoin
from .java import annotation_value, paths

from .values import (Object, Predicate, Query, Raised, Response, Symbol,
                     Text, TypeRef, Unknown, binary, equal, unknown, wire, wire_incomplete)


NOT_HANDLED = object()
HTTP_HEADERS = {'spring.HttpHeaders', 'spring.ReadOnlyHttpHeaders'}
STATUSES = {"OK": 200, "CREATED": 201, "ACCEPTED": 202, "NO_CONTENT": 204,
            "BAD_REQUEST": 400, "UNAUTHORIZED": 401, "FORBIDDEN": 403, "NOT_FOUND": 404,
            "METHOD_NOT_ALLOWED": 405, "CONFLICT": 409, "UNPROCESSABLE_ENTITY": 422,
            "INTERNAL_SERVER_ERROR": 500, "SERVICE_UNAVAILABLE": 503}


def pure_global_definition(engine, expr):
    if expr.op != "call" or expr.value != "getLogger":
        return False
    receiver, args, keywords = expr.args
    return (receiver is not None and receiver.op == "var" and
            engine.p.imports.get(expr.span.file, {}).get(receiver.value) == "org.slf4j.LoggerFactory" and
            not keywords and all(arg.op in {"const", "type"} for arg in args))


def simple(typ):
    return re.sub(r"<.*>", "", typ).split(".")[-1]


def static_field(engine, receiver, name):
    typ = simple(receiver.name)
    from .java_boxing import WRAPPERS
    if typ in WRAPPERS and name=='TYPE':return TypeRef(WRAPPERS[typ])
    if typ == "HttpStatus" and name in STATUSES:
        return STATUSES[name]
    if typ in {"Integer", "Long"} and name in {"MAX_VALUE", "MIN_VALUE"}:
        bits = 31 if typ == "Integer" else 63
        return 2**bits - 1 if name == "MAX_VALUE" else -(2**bits)
    if typ == "HttpMethod" and name in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
        return name
    if typ == "status" and name.startswith("HTTP_"):
        match = re.match(r"HTTP_(\d+)_", name)
        if match:
            return int(match[1])
    return NOT_HANDLED


def construct(engine, typ, args, kwargs, span,argument_types=()):
    if engine.language=='java':
        from .java_boxing import construct as boxed_construct
        modeled=boxed_construct(engine,typ,args,kwargs,span,argument_types)
        if modeled is not NOT_HANDLED:return modeled
    from .java_time import date_construct
    modeled=date_construct(engine,typ,args,kwargs,span)
    if modeled is not NOT_HANDLED:return modeled
    if engine.language=='java':
        from .java_streams import construct as collection_construct
        modeled=collection_construct(engine,typ,args,kwargs,span)
        if modeled is not NOT_HANDLED:return modeled
    short = simple(typ)
    if short in {"ResponseEntity", "HttpEntity"}:
        status = args[-1] if args and type(args[-1]) is int and short == "ResponseEntity" else 200
        body = args[0] if args and not (short == 'ResponseEntity' and len(args) == 1 and type(args[0]) is int) else None
        header_arg = args[1] if len(args) >= (3 if short == 'ResponseEntity' else 2) else None
        if short == 'HttpEntity' and len(args) == 1 and isinstance(body, Object) and body.typ in HTTP_HEADERS:
            body, header_arg = None, body
        headers = header_arg.fields.get('values') if isinstance(header_arg, Object) and header_arg.typ in HTTP_HEADERS else header_arg
        return Response(body, status, headers if headers is not None else {})
    if typ in {"fastapi.HTTPException", "starlette.exceptions.HTTPException", "HTTPException"}:
        fields = dict(kwargs)
        if args:
            fields["status_code"] = args[0]
        return engine.state.new("HTTPException", fields)
    if short.endswith(("Exception", "Error")):
        return engine.state.new(short, {"message": args[0] if args else None, **kwargs})
    if short in {"ArrayList", "LinkedList", "HashSet", "LinkedHashSet", "List"}:
        if args and unknown(args[0]):
            return Unknown("unknown collection constructor input")
        return list(args[0]) if args and isinstance(args[0], (tuple, list)) else []
    if short == 'HttpHeaders':
        if args and isinstance(args[0], Object) and args[0].typ in HTTP_HEADERS:
            return engine.state.new(args[0].typ, {'values': args[0].fields.get('values')})
        if args and unknown(args[0]):
            return engine.state.new('spring.HttpHeaders', {'values': Unknown('Unknown initial HTTP headers')})
        if args and not isinstance(args[0], dict):
            return NOT_HANDLED
        values = args[0] if args and isinstance(args[0], dict) else {}
        return engine.state.new('spring.HttpHeaders', {'values': {str(k).lower(): list(v) if isinstance(v, list) else [v] for k, v in values.items()}})
    if short in {"HashMap", "LinkedHashMap", "Map"}:
        return dict(args[0]) if args and isinstance(args[0], dict) else {}
    if short == "Session":
        binding = args[0] if args else kwargs.get("bind")
        status = "unbound" if binding is None else "bound" if isinstance(binding, Object) and binding.typ == "sqlalchemy.Engine" else "unknown"
        return engine.state.new("sqlmodel.Session", {**kwargs, "bind": binding, "binding_status": status})
    aliases = {"RestTemplate": "spring.RestTemplate", "JdbcTemplate": "spring.JdbcTemplate", "NamedParameterJdbcTemplate": "spring.NamedParameterJdbcTemplate", "BindingResult": "spring.BindingResult"}
    if short in aliases:
        return engine.state.new(aliases[short], kwargs)
    if short in {"BigDecimal"}:
        if args and type(args[0]) in {int, float}:
            return args[0]
        return Unknown("unsupported decimal construction", "BigDecimal")
    if typ in {"sqlmodel.Session", "sqlalchemy.orm.Session", "httpx.Client", "httpx.AsyncClient"}:
        return engine.state.new(typ, kwargs)
    if short in {"FastAPI", "APIRouter"}:
        return engine.state.new("fastapi." + short, kwargs)
    return NOT_HANDLED


def entity_info(engine, key, span):
    name = key.name if isinstance(key, TypeRef) else key
    resolved = engine.p.resolve_type(name, engine.method.module if engine.method else "", span.file)
    return engine.p.types.get(resolved)


def data_edge(engine, info, span, operation, source_id=None):
    if not info or not info.table:
        engine.note("unmapped-data", "Entity is not mapped to a skeleton table", span, operation=operation)
        return False
    engine.add(source_id or (engine.method.skeleton_id if engine.method else ""), "data", info.table, span, "source " + operation + " on declared entity/table")
    return True


def rows(engine, info, span):
    if not info or not info.table:
        return Unknown("unmapped entity table")
    raw = engine.state.store.read(info.table)
    if isinstance(raw, Unknown):
        return raw
    result = []
    for record in raw:
        fields = {field: record.get(info.columns.get(field, field), Unknown("column absent from supplied row", origin=field))
                  for field in engine.p.type_fields(info.key)}
        fields.update({k: v for k, v in record.items() if k not in info.columns.values() and k not in fields})
        result.append(engine.state.new(info.key, fields))
    return result


def save(engine, obj, info, span, delete=False, source_id=None):
    if not isinstance(obj, Object) or not info or not data_edge(engine, info, span, "delete" if delete else "save", source_id):
        return Unknown("unresolved entity write")
    initial = engine.state.store.read(info.table)
    if isinstance(initial, Unknown):
        return initial
    if info.generated_key and (obj.fields.get(info.primary_key) is None or isinstance(obj.fields.get(info.primary_key), Unknown)):
        obj.fields[info.primary_key] = engine.state.symbol(engine.p.type_fields(info.key).get(info.primary_key, ("id", None))[0])
    key = obj.fields.get(info.primary_key, Unknown("no entity key"))
    from .java_boxing import boxed,unbox
    if boxed(key):key=unbox(key)
    column = info.columns.get(info.primary_key, info.primary_key)
    new_rows, updated = [], False
    for record in initial:
        match = equal(record.get(column), key)
        if unknown(match):
            engine.note("unknown-write-key", "Write identity is uncertain; table state is invalidated", span)
            engine.state.store.tainted.add(info.table)
            return obj
        if match:
            updated = True
            if not delete:
                new_rows.append({info.columns.get(k, k): wire(v) for k, v in obj.fields.items()})
        else:
            new_rows.append(record)
    if not updated and not delete:
        new_rows.append({info.columns.get(k, k): wire(v) for k, v in obj.fields.items()})
    engine.state.store.replace(info.table, new_rows)
    return obj


@contextmanager
def session_scope(engine, session):
    status = session.fields.get("binding_status", "provided-bound-input")
    if status == "unbound":
        raise Raised("UnboundExecutionError")
    if not isinstance(status, str) or status == "unknown":
        engine.note("session-binding-unknown", "Session engine binding is unresolved", engine.method.span)
        if not engine.choose((False, True), "session has an engine binding"):
            raise Raised("UnboundExecutionError")
    outer = engine.state.store
    engine.state.store = engine.state.transactions.setdefault(session.identity, deepcopy(outer))
    try:
        yield
    finally:
        engine.state.transactions[session.identity] = engine.state.store
        engine.state.store = outer


def flush_session(engine, session):
    for obj, delete, source_id, span in engine.state.pending.get(session.identity, []):
        save(engine, obj, engine.p.types.get(obj.typ), span, delete, source_id)
    engine.state.pending[session.identity] = []


def select(engine, query, span):
    info = entity_info(engine, query.entity, span)
    if not data_edge(engine, info, span, "select"):
        return Unknown("unmapped query")
    result = rows(engine, info, span)
    if isinstance(result, Unknown):
        return result
    selected = []
    for obj in result:
        include = True
        for predicate in query.predicates:
            if not isinstance(predicate, Predicate):
                engine.note("unknown-query", "Unsupported query predicate", span)
                return Unknown("unsupported query predicate")
            field = predicate.field.split(".")[-1]
            value = binary(predicate.op, obj.fields.get(field, Unknown("query field missing")), predicate.value, "python")
            if not engine.condition(value, span):
                include = False
                break
        if include:
            selected.append(obj)
    if not isinstance(query.offset, int) or (query.limit is not None and not isinstance(query.limit, int)):
        return Unknown("unknown pagination")
    selected = selected[query.offset:None if query.limit is None else query.offset + query.limit]
    if query.delete:
        for obj in selected:
            save(engine, obj, info, span, delete=True)
    return len(selected) if query.count else selected


def repository(engine, receiver, name, args, span):
    if not isinstance(receiver, Object) or receiver.typ not in engine.p.types:
        return NOT_HANDLED
    info = engine.p.types[receiver.typ]
    if not info.repository_entity:
        return NOT_HANDLED
    from .java_boxing import boxed,unbox
    args=tuple(unbox(value) if boxed(value) else value for value in args)
    entity = entity_info(engine, info.repository_entity, span)
    if not entity:
        return Unknown("repository entity is unresolved")
    declarations = engine.p.methods_of(info.key, name, len(args))
    if len(declarations) == 1 and set(declarations[0].annotations) & {"Query", "NativeQuery"}:
        declaration = declarations[0]
        raw = declaration.annotations.get("NativeQuery", declaration.annotations.get("Query", ""))
        if "NativeQuery" not in declaration.annotations and not re.search(r"\bnativeQuery\s*=\s*true\b", raw):
            engine.note("jpql-unmodeled", "JPQL is not treated as native SQL or as a derived method query", span)
            return Unknown("JPQL semantics are outside this model")
        # A concatenated/computed annotation is not its first string literal.
        outside_strings = re.sub(r'"(?:\\.|[^"\\])*"', '""', raw)
        if "+" in outside_strings:
            engine.note("sql-query-unknown", "Computed native SQL annotation is not a single literal", span)
            return Unknown("computed SQL annotation")
        from .sql_queries import evaluate
        selected = evaluate(engine, annotation_value(raw, "value") or annotation_value(raw), {p.alias or p.name: value for p, value in zip(declaration.params, args)}, span)
        if isinstance(selected, Unknown):
            return selected
        returned = declaration.return_type
        if simple(returned) in {"long", "Long", "int", "Integer", "String"}:
            return next(iter(selected[0].values())) if selected else None
        values = [engine.state.new(entity.key, {field: row.get(entity.columns.get(field, field), Unknown("SQL projection omits entity field", origin=field)) for field in engine.p.type_fields(entity.key)}) for row in selected]
        if "Optional" in returned:
            return engine.state.new("java.util.Optional", {"value": values[0] if values else None})
        return values if any(part in returned for part in ["List<", "Set<", "Collection<", "Iterable<"]) else values[0] if values else None
    if name in {"save", "saveAndFlush", "insert"}:
        return save(engine, args[0] if args else None, entity, span)
    if name in {"delete", "deleteById"}:
        obj = args[0] if args and isinstance(args[0], Object) else engine.state.new(entity.key, {entity.primary_key: args[0] if args else Unknown("missing key")})
        save(engine, obj, entity, span, delete=True)
        return None
    predicates = []
    if name in {"findById", "getById", "existsById"}:
        predicates = [Predicate(entity.primary_key, "==", args[0] if args else Unknown("missing key"))]
    elif name.startswith(("findBy", "findAllBy", "existsBy", "countBy")):
        suffix = re.sub(r"^(?:findAllBy|findBy|existsBy|countBy)", "", name)
        parts = re.split("And", suffix)
        if len(parts) != len(args) or any(re.search(r"(?:Or|LessThan|GreaterThan|Containing|OrderBy)", p) for p in parts):
            return NOT_HANDLED
        predicates = [Predicate(field[0].lower() + field[1:], "==", arg) for field, arg in zip(parts, args)]
    elif name not in {"findAll", "count"}:
        return NOT_HANDLED
    selected = select(engine, Query(entity.key, predicates), span)
    if isinstance(selected, Unknown):
        return selected
    if name.startswith("exists"):
        return bool(selected)
    if name.startswith("count"):
        return len(selected)
    if name in {"findById", "getById"}:
        result = selected[0] if selected else None
        declarations = engine.p.methods_of(info.key, name, len(args))
        returns_optional = any("Optional" in m.return_type for m in declarations)
        if not declarations and any("JpaRepository" in p or "CrudRepository" in p for p in info.parents):
            returns_optional = name == "findById"
        return engine.state.new("java.util.Optional", {"value": result}) if returns_optional else result
    declarations = engine.p.methods_of(info.key, name, len(args))
    scalar_return = len(declarations) == 1 and declarations[0].return_type.split(".")[-1] == entity.name
    return selected[0] if selected and scalar_return else None if scalar_return else selected


def http(engine, receiver, name, args, kwargs, span):
    typ = receiver.typ if isinstance(receiver, Object) else receiver.name if isinstance(receiver, TypeRef) else ""
    is_java = typ in {"spring.RestTemplate", "org.springframework.web.client.RestTemplate", "RestTemplate"}
    is_python = typ in {"requests", "httpx", "httpx.Client", "httpx.AsyncClient"}
    if not is_java and not is_python:
        return NOT_HANDLED
    method, body, url, headers = "GET", {}, None, kwargs.get('headers', {})
    if is_java:
        if name in {"getForObject", "getForEntity"}:
            url = args[0] if args else None
        elif name in {"postForObject", "postForEntity"}:
            method, url, body = "POST", args[0] if args else None, args[1] if len(args) > 1 else {}
        elif name in {"put", "delete"}:
            method, url = name.upper(), args[0] if args else None
            body = args[1] if name == "put" and len(args) > 1 else {}
        elif name == "exchange":
            url, method = args[:2] if len(args) >= 2 else (None, Unknown("missing HTTP verb"))
            body = args[2] if len(args) > 2 else {}
        else:
            return NOT_HANDLED
        if isinstance(body, Response):
            headers = body.headers
            body = body.body
    elif name in {"get", "post", "put", "patch", "delete", "head", "options", "request"}:
        if name == "request":
            method = args[0] if args else kwargs.get("method", "GET")
            url = args[1] if len(args) > 1 else kwargs.get("url")
        else:
            method, url = name.upper(), args[0] if args else kwargs.get("url")
        body = kwargs.get("json", kwargs.get("data", {}))
    else:
        return NOT_HANDLED
    if isinstance(receiver, Object) and "base_url" in receiver.fields and isinstance(url, str):
        base = receiver.fields["base_url"]
        url = urljoin(base, url) if isinstance(base, str) else Unknown("unknown HTTP client base URL")
    body = wire(body)
    if wire_incomplete(body):
        engine.unsupported("HTTP body serialization requires an unmodeled cyclic/deep codec", span)
    if not isinstance(headers, dict) or id(headers) in engine.state.tainted_containers:
        engine.unsupported('HTTP request header map is unknown', span)
    response = engine.request({"method": method, "url": url, "body": body, "query": kwargs.get("params", {}), "headers": headers}, engine.method, span)
    if is_java:
        status = response.status
        if type(status) is int and status >= 400:
            raise Raised("HttpClientErrorException" if status < 500 else "HttpServerErrorException", response)
        if unknown(status) and engine.choose((False, True), "RestTemplate unknown error status"):
            raise Raised("HttpClientErrorException", response)
        if name.endswith('ForObject'):
            from .java_boxing import decode_json
            target=args[-1].name if args and isinstance(args[-1],TypeRef) else ''
            return decode_json(engine,response.body,target,span)
        return response
    return response


def call(engine, receiver, name, args, kwargs, span,receiver_type='',argument_types=()):
    from .values import MethodRef
    if isinstance(receiver,MethodRef):
        if name in {'apply','test','accept','get','run','compare','applyAsInt','applyAsLong','applyAsDouble','getAsInt','getAsLong','getAsDouble','getAsBoolean'}:
            from .java_boxing import argument
            values=tuple(argument(engine,value,argument_types[index] if index<len(argument_types) else '',span) for index,value in enumerate(args))
            result=engine.invoke_callable(receiver,values,span)
            return argument(engine,result,receiver.return_type,span) if name in {'apply','get'} else result
        engine.unsupported('Unmodeled functional-interface operation '+name,span)
    if engine.language=='java':
        from .java_boxing import call as boxed_call
        modeled=boxed_call(engine,receiver,name,args,kwargs,span,argument_types)
        if modeled is not NOT_HANDLED:return modeled
        from .java_streams import call as stream_call
        modeled=stream_call(engine,receiver,name,args,kwargs,span,receiver_type,argument_types)
        if modeled is not NOT_HANDLED:return modeled
    from .java_time import call as time_call
    modeled=time_call(engine,receiver,name,args,kwargs,span)
    if modeled is not NOT_HANDLED:return modeled
    prefix=receiver.name if isinstance(receiver,TypeRef) else receiver.typ if isinstance(receiver,Object) else name
    if prefix.startswith(('jwt','datetime','pwdlib')):
        from .security_models import call as security_call
        result=security_call(engine,receiver,name,args,kwargs,span)
        if result is not NOT_HANDLED:return result
    qualified=receiver.name+'.'+name if isinstance(receiver,TypeRef) else name
    if qualified.startswith('fastapi.security.'):
        from .fastapi_dependencies import construct as security_construct
        result=security_construct(engine,qualified,args,kwargs,span)
        if result is not NOT_HANDLED:return result
    if isinstance(receiver, Object) and receiver.typ in HTTP_HEADERS:
        if receiver.typ == 'spring.ReadOnlyHttpHeaders' and name in {'set', 'add', 'put'}:
            raise Raised('UnsupportedOperationException')
        if receiver.typ == 'spring.ReadOnlyHttpHeaders' and name == 'get':
            engine.unsupported('Read-only header list views are outside the modeled scalar header API', span)
        values = receiver.fields.get('values')
        if isinstance(values, Unknown) or args and unknown(args[0]):
            if name in {'set', 'add', 'put'}:
                receiver.fields['values'] = Unknown('Unknown header mutation')
            return Unknown('Unknown HTTP headers operation')
        key = str(args[0]).lower() if args else ''
        if name in {'get', 'getFirst', 'containsKey'}:
            found = values.get(key)
            if isinstance(found, Unknown):
                return found
            return key in values if name == 'containsKey' else found[0] if name == 'getFirst' and found else None if name == 'getFirst' else found
        if name in {'set', 'add', 'put'} and len(args) == 2:
            previous = values.get(key)
            if name == 'add':
                values.setdefault(key, []).append(args[1])
            else:
                values[key] = args[1] if name == 'put' else [args[1]]
            return previous if name == 'put' else None
        if name == 'isEmpty':
            return not values
    if isinstance(receiver, Object) and receiver.typ in {"spring.JdbcTemplate", "spring.NamedParameterJdbcTemplate"} and name in {"queryForList", "queryForObject", "queryForMap"}:
        from .sql_queries import evaluate
        parameters = args[1] if len(args) > 1 and isinstance(args[1], (dict, list, tuple)) else args[2:] if name == "queryForObject" else args[1:]
        selected = evaluate(engine, args[0] if args else None, parameters, span)
        if isinstance(selected, Unknown) or name == "queryForList":
            return selected
        if not selected:
            raise Raised("EmptyResultDataAccessException")
        if len(selected) != 1:
            raise Raised("IncorrectResultSizeDataAccessException")
        return next(iter(selected[0].values())) if name == "queryForObject" else selected[0]
    if isinstance(receiver, Object) and receiver.typ in engine.p.types:
        info = engine.p.types[receiver.typ]
        if "FeignClient" in info.annotations:
            declarations = engine.p.methods_of(info.key, name, len(args))
            if len(declarations) == 1:
                method = declarations[0]
                mapping = next(((k, v) for k, v in method.annotations.items() if k.endswith("Mapping")), None)
                if mapping:
                    attribute, raw = mapping
                    route = paths(raw)
                    verbs = re.findall(r"RequestMethod\.(\w+)", raw) if attribute == "RequestMapping" else [attribute.removesuffix("Mapping").upper()]
                    service = annotation_value(info.annotations["FeignClient"], "name") or annotation_value(info.annotations["FeignClient"], "value") or annotation_value(info.annotations["FeignClient"])
                    if len(route) == 1 and len(verbs) == 1 and service:
                        path, body = route[0], {}
                        for param, value in zip(method.params, args):
                            if param.location == "path":
                                if isinstance(value, str):
                                    path = path.replace("{" + (param.alias or param.name) + "}", value)
                                else:
                                    return engine.opaque("nonliteral Feign path variable", span)
                            else:
                                body = wire(value)
                        response = engine.request({"method": verbs[0], "url": "http://" + service + path, "body": body}, engine.method, span)
                        if type(response.status) is int and response.status >= 400:
                            if 'fallback' in info.annotations['FeignClient']:
                                engine.unsupported('Feign failure fallback requires an additional lifecycle contract',span)
                            raise Raised("FeignException", response)
                        if "fallback" in info.annotations["FeignClient"] and unknown(response.status):
                            engine.note("feign-fallback", "Feign fallback/circuit breaker behavior is outside the model", span)
                        return response.body
    result = repository(engine, receiver, name, args, span)
    if result is not NOT_HANDLED:
        return result
    result = http(engine, receiver, name, args, kwargs, span)
    if result is not NOT_HANDLED:
        return result
    if isinstance(receiver, Response):
        if name in {"getBody", "json"}:
            return receiver.body
        if name == 'getHeaders':
            from .java_contracts import entity_headers_readonly
            if receiver.headers_readonly is None:
                receiver.headers_readonly = entity_headers_readonly(engine, span)
            return engine.state.new('spring.ReadOnlyHttpHeaders' if receiver.headers_readonly else 'spring.HttpHeaders', {'values': receiver.headers})
        if name in {"getStatusCodeValue", "getStatusCode"}:
            return receiver.status
        if name == "raise_for_status":
            if unknown(receiver.status):
                if engine.choose((False, True), "unknown HTTP status"):
                    raise Raised("HTTPStatusError", receiver)
            elif receiver.status >= 400:
                raise Raised("HTTPStatusError", receiver)
            return None
    if isinstance(receiver, Query):
        if name in {"where", "filter"}:
            receiver.predicates.extend(args)
            return receiver
        if name in {"offset", "limit"}:
            setattr(receiver, name, args[0] if args else Unknown("pagination"))
            return receiver
    if isinstance(receiver, Object):
        if receiver.typ in {"sqlmodel.Session", "sqlalchemy.orm.Session"}:
            if name == "get" and len(args) >= 2:
                info = entity_info(engine, args[0], span)
                query = Query(info.key, [Predicate(info.primary_key, "==", args[1])]) if info else None
                with session_scope(engine, receiver):
                    if receiver.fields.get("autoflush", True):
                        flush_session(engine, receiver)
                    selected = select(engine, query, span) if query else Unknown("unknown session entity")
                return selected[0] if isinstance(selected, list) and selected else None if selected == [] else selected
            if name in {"add", "delete"}:
                if args and isinstance(args[0], Object):
                    engine.state.pending.setdefault(receiver.identity, []).append((args[0], name == "delete", engine.method.skeleton_id, span))
                    return None
                return Unknown("unknown session entity write")
            if name in {"exec", "execute"} and args and isinstance(args[0], Query):
                with session_scope(engine, receiver):
                    if receiver.fields.get("autoflush", True):
                        flush_session(engine, receiver)
                    selected = select(engine, args[0], span)
                return engine.state.new("sql.Result", {"value": selected})
            if name in {"exec", "execute"} and args and isinstance(args[0], Object) and args[0].typ == "sqlalchemy.TextClause":
                from .sql_queries import evaluate
                with session_scope(engine, receiver):
                    # Textual statements do not trigger ORM autoflush.
                    result = evaluate(engine, args[0].fields.get("text"), args[1] if len(args) > 1 else kwargs.get("params", {}), span)
                return engine.state.new("sql.Result", {"value": result, "mapping_rows": True})
            if name == "flush":
                if engine.state.pending.get(receiver.identity):
                    with session_scope(engine, receiver):
                        flush_session(engine, receiver)
                return None
            if name == "commit":
                if engine.state.pending.get(receiver.identity):
                    with session_scope(engine, receiver):
                        flush_session(engine, receiver)
                transaction = engine.state.transactions.pop(receiver.identity, None)
                if transaction is not None:
                    for table, records in transaction.changes.items():
                        engine.state.store.replace(table, records)
                    engine.state.store.tainted.update(transaction.tainted)
                engine.state.pending[receiver.identity] = []
                return None
            if name in {"rollback", "close"}:
                engine.state.pending[receiver.identity] = []
                engine.state.transactions.pop(receiver.identity, None)
                return None
            if name == "refresh" and args and isinstance(args[0], Object):
                obj = args[0]
                info = engine.p.types.get(obj.typ)
                if info:
                    with session_scope(engine, receiver):
                        selected = select(engine, Query(info.key, [Predicate(info.primary_key, "==", obj.fields.get(info.primary_key))]), span)
                    if isinstance(selected, list) and selected:
                        obj.fields.update(selected[0].fields)
                return None
        if receiver.typ in {"sql.Result", "sql.MappingResult", "sql.ScalarResult"}:
            value = receiver.fields["value"]
            if name == "mappings":
                return engine.state.new("sql.MappingResult", dict(receiver.fields))
            if name == "scalars":
                selected = [next(iter(row.values())) for row in value] if receiver.fields.get("mapping_rows") and isinstance(value, list) else value
                return engine.state.new("sql.ScalarResult", {"value": selected})
            if name in {"all", "first", "one", "one_or_none", "scalar", "scalar_one", "scalar_one_or_none"}:
                if not isinstance(value, list):
                    return value
                if name in {"one", "scalar_one"} and not value:
                    raise Raised("NoResultFound")
                if name in {"one", "scalar_one", "one_or_none", "scalar_one_or_none"} and len(value) > 1:
                    raise Raised("MultipleResultsFound")
                if receiver.fields.get("mapping_rows"):
                    selected = [next(iter(row.values())) for row in value] if name.startswith("scalar") else [tuple(row.values()) for row in value] if receiver.typ == "sql.Result" else value
                else:
                    selected = value
                return selected if name == "all" else selected[0] if selected else None
        if receiver.typ == "spring.BindingResult" and name == "hasErrors":
            return receiver.fields.get("errors", Unknown("validation result"))
        if receiver.typ == "java.util.Optional":
            value = receiver.fields.get("value")
            if name in {"isPresent", "isEmpty"}:
                return value is not None if name == "isPresent" else value is None
            if name in {"get", "orElseThrow"}:
                if value is None:
                    raise Raised("NoSuchElementException")
                return value
            if name == "orElse":
                return value if value is not None else args[0]
        if receiver.typ in engine.p.types:
            info = engine.p.types[receiver.typ]
            if name in {"model_dump", "dict"} and info.language == "python":
                exclude_unset = kwargs.get("exclude_unset", False)
                return {k: v for k, v in receiver.fields.items() if not exclude_unset or receiver.provided is None or k in receiver.provided}
            if name == "sqlmodel_update" and args and isinstance(args[0], dict):
                receiver.fields.update(args[0])
                return receiver
            if set(info.annotations) & {"Data", "Getter", "Setter"}:
                prefix = "get" if name.startswith("get") else "is" if name.startswith("is") else "set" if name.startswith("set") else ""
                field = name[len(prefix):]
                field = field[:1].lower() + field[1:]
                if prefix and field in receiver.fields:
                    if prefix == "set" and args:
                        receiver.fields[field] = args[0]
                        return None
                    return receiver.fields[field]
    if isinstance(receiver, TypeRef):
        typ = simple(receiver.name)
        qualified = receiver.name + "." + name
        if qualified in {"sqlalchemy.create_engine", "sqlmodel.create_engine"}:
            return engine.state.new("sqlalchemy.Engine", {"url": args[0] if args else Unknown("missing database URL"), **kwargs})
        if qualified in {"sqlalchemy.text", "sqlalchemy.sql.text", "sqlalchemy.sql.expression.text"}:
            return engine.state.new("sqlalchemy.TextClause", {"text": args[0] if args else Unknown("missing SQL text")})
        if qualified in {"httpx.Client", "httpx.AsyncClient", "sqlmodel.Session", "sqlalchemy.orm.Session", "fastapi.HTTPException"}:
            return construct(engine, qualified, args, kwargs, span)
        if receiver.name in engine.p.types:
            info = engine.p.types[receiver.name]
            if name in {"model_validate", "parse_obj"} and args:
                fields = wire(args[0])
                if not isinstance(fields, dict):
                    return Unknown("unknown model input")
                fields.update(kwargs.get("update", {}))
                return engine.create(info.key, kwargs=fields, span=span)
        if typ in {"ResponseEntity"}:
            if name == "ok":
                return Response(args[0] if args else None, 200) if args else engine.state.new("spring.ResponseBuilder", {"status": 200})
            if name in {"status", "notFound", "badRequest", "noContent"}:
                status = args[0] if name == "status" and args else {"notFound": 404, "badRequest": 400, "noContent": 204}.get(name, 200)
                return engine.state.new("spring.ResponseBuilder", {"status": status})
        if typ in {"List", "Arrays", "Collections", "Set"} and name in {"of", "asList", "singletonList", "emptyList", "singleton", "emptySet"}:
            if engine.language=='java':
                from .java_boxing import argument
                return [argument(engine,value,argument_types[index] if index<len(argument_types) else '',span) for index,value in enumerate(args)]
            return list(args)
        if typ in {"Map"} and name == "of":
            return dict(zip(args[::2], args[1::2]))
        if typ in {"Objects"} and name in {"equals", "nonNull", "isNull", "requireNonNull"}:
            if name == "equals":
                return equal(args[0], args[1])
            if name == "requireNonNull":
                if args[0] is None:
                    raise Raised("NullPointerException")
                return args[0]
            return args[0] is not None if name == "nonNull" else args[0] is None
        if typ == "Assert" and name in {"hasLength", "notNull", "isNull", "isTrue"}:
            value = args[0] if args else None
            valid = Unknown("unknown assertion condition", "boolean") if unknown(value) else bool(value) if name in {"hasLength", "isTrue"} else value is not None if name == "notNull" else value is None
            if not engine.condition(valid, span):
                raise Raised("IllegalArgumentException")
            return None
        if typ == "LoggerFactory" and name == "getLogger":
            return engine.state.new("org.slf4j.Logger")
        if typ in {"UUID", "uuid"} and name in {"randomUUID", "uuid4"}:
            return engine.state.symbol("UUID")
        if typ == "datetime" and name in {"now", "utcnow", "today"}:
            return engine.state.symbol("datetime")
        if typ in {"Optional"} and name in {"empty", "of", "ofNullable"}:
            return engine.state.new("java.util.Optional", {"value": args[0] if args else None})
        if name in {"valueOf", "parseInt", "parseLong"} and typ in {"Integer", "Long", "String"}:
            from .java_boxing import boxed,unbox
            if typ=='String' and boxed(args[0]):
                scalar=unbox(args[0])
                return Unknown('Unknown boxed string','String') if unknown(scalar) else str(scalar).lower() if type(scalar) is bool else str(scalar)
            if isinstance(args[0], TypeRef):
                return Unknown("unmodeled type/enum conversion", typ)
            if isinstance(args[0], Symbol) and typ == "String":
                return Text((args[0],))
            if unknown(args[0]):
                return Unknown("unknown conversion input", typ)
            try:
                return str(args[0]) if typ == "String" else int(args[0])
            except (ValueError, TypeError):
                raise Raised("NumberFormatException") from None
    if isinstance(receiver, Object) and receiver.typ == "spring.ResponseBuilder":
        if name in {"body", "build"}:
            return Response(args[0] if args else None, receiver.fields["status"])
    if isinstance(receiver, Object) and receiver.typ == "org.slf4j.Logger" and name in {"info", "debug", "warn", "error", "trace"}:
        return None
    if name == "getClass" and isinstance(receiver, Object):
        return TypeRef(receiver.typ)
    if isinstance(receiver, Object) and receiver.typ == "java.security.Principal" and name == "getName":
        return receiver.fields.get("name", Unknown("principal name"))
    if receiver is None:
        short = simple(name)
        if name in {"sqlalchemy.create_engine", "sqlmodel.create_engine"}:
            return engine.state.new("sqlalchemy.Engine", {"url": args[0] if args else Unknown("missing database URL"), **kwargs})
        if name in {"sqlalchemy.text", "sqlalchemy.sql.text", "sqlalchemy.sql.expression.text"}:
            return engine.state.new("sqlalchemy.TextClause", {"text": args[0] if args else Unknown("missing SQL text")})
        if name in engine.p.types:
            return engine.create(name, args, kwargs, span)
        if name in {"sqlmodel.select", "sqlalchemy.select", "select", "sqlmodel.delete", "sqlalchemy.delete"} and args:
            info = entity_info(engine, args[0], span)
            if info:
                return Query(info.key, delete=name.endswith("delete"))
        if name in {"sqlmodel.Session", "sqlalchemy.orm.Session", "httpx.Client", "httpx.AsyncClient", "fastapi.HTTPException", "HTTPException"}:
            return construct(engine, name, args, kwargs, span)
        if name in {"uuid.uuid4","uuid.uuid1"}:
            return engine.state.symbol("UUID")
        if short in {"len", "str", "int", "float", "bool", "list", "dict", "set", "range", "enumerate", "isinstance"}:
            if short == "str" and args and isinstance(args[0], Symbol):
                return Text((args[0],))
            if any(unknown(a) for a in args):
                return Unknown("builtin input unknown", short)
            try:
                if short == "isinstance":
                    return isinstance(args[0], Object) and engine.matches_type(args[0].typ, args[1].name if isinstance(args[1], TypeRef) else str(args[1]))
                if short == "enumerate":
                    return list(enumerate(args[0]))
                builtins = {"len": len, "str": str, "int": int, "float": float, "bool": bool, "list": list, "dict": dict, "set": list, "range": range}
                result = builtins[short](*args, **kwargs)
                return list(result) if isinstance(result, range) else result
            except (ValueError, TypeError) as exc:
                raise Raised(type(exc).__name__) from None
        result = construct(engine, name, args, kwargs, span)
        if result is not NOT_HANDLED:
            return result
    if name == "equals" and args:
        return equal(receiver, args[0])
    if name == "toString" and not args:
        if isinstance(receiver, TypeRef):
            return Unknown("unmodeled type/enum string representation", "String")
        return Text((receiver,)) if isinstance(receiver, Symbol) else str(receiver) if not unknown(receiver) else Unknown("symbolic string conversion", "String")
    if isinstance(receiver, (list, dict, str)):
        if name in {"size", "length"}:
            return len(receiver)
        if name in {"isEmpty"}:
            return not receiver
        if name in {"contains", "containsKey"} and args:
            if isinstance(receiver,dict) and engine.language=='java':
                from .java_boxing import argument,map_key
                return map_key(engine,argument(engine,args[0],argument_types[0] if argument_types else '',span),span) in receiver
            if isinstance(receiver, list) and engine.language == "java":
                from .java_boxing import argument
                sought=argument(engine,args[0],argument_types[0] if argument_types else '',span)
                for item in receiver:
                    value=engine.call(sought,'equals',(item,),{},span,{}) if isinstance(sought,Object) else equal(sought,item)
                    if engine.condition(value, span):
                        return True
                return False
            return args[0] in receiver if not unknown(args[0]) else Unknown("symbolic membership")
        if name == "get" and args:
            if isinstance(receiver, dict):
                key=args[0]
                if engine.language=='java':
                    from .java_boxing import argument,map_key
                    key=map_key(engine,argument(engine,key,argument_types[0] if argument_types else '',span),span)
                return receiver.get(key,args[1] if len(args)>1 else None)
            if isinstance(receiver, list):
                index=args[0]
                if engine.language=='java':
                    from .java_boxing import unbox
                    index=unbox(index)
                try:
                    if type(index) is int and index < 0 and engine.language == "java":
                        raise IndexError()
                    return receiver[index]
                except (IndexError, TypeError):
                    raise Raised("IndexOutOfBoundsException" if engine.language == "java" else "IndexError") from None
        if isinstance(receiver, dict) and name in {"put", "update"}:
            if name == "put" and len(args) >= 2:
                key,value=args[:2]
                if engine.language=='java':
                    from .java_boxing import argument,map_key
                    key=map_key(engine,argument(engine,key,argument_types[0] if argument_types else '',span),span)
                    value=argument(engine,value,argument_types[1] if len(argument_types)>1 else '',span)
                old=receiver.get(key)
                receiver[key]=value
                return old
            if name == "update" and args:
                receiver.update(args[0])
                return None
        if isinstance(receiver, list) and name in {"add", "append", "extend", "clear"}:
            if name == "clear":
                engine.state.mutated(receiver)
                receiver.clear()
            elif name == "extend":
                engine.state.mutated(receiver)
                receiver.extend(args[0])
            else:
                value=args[0]
                if engine.language=='java':
                    from .java_boxing import argument
                    value=argument(engine,value,argument_types[0] if argument_types else '',span)
                engine.state.mutated(receiver)
                receiver.append(value)
            return True if name == "add" else None
        if isinstance(receiver, str):
            if engine.language=='java' and name=='hashCode' and not args:
                from .java_sets import hash_string
                return hash_string(engine,receiver,span)
            if engine.language=='java' and name=='equalsIgnoreCase' and len(args)==1:
                if args[0] is None:return False
                if not isinstance(args[0],str) or not receiver.isascii() or not args[0].isascii():engine.unsupported('Non-ASCII/unknown Java equalsIgnoreCase needs a character-case contract',span)
                return receiver.lower()==args[0].lower()
            operations = {"toLowerCase": str.lower, "lower": str.lower, "toUpperCase": str.upper, "upper": str.upper,
                          "trim": str.strip, "strip": str.strip, "startsWith": str.startswith, "startswith": str.startswith,
                          "endsWith": str.endswith, "endswith": str.endswith, "replace": str.replace, "split": str.split}
            if name in operations and not any(unknown(a) for a in args):
                try:
                    return operations[name](receiver, *args)
                except (ValueError, TypeError):
                    raise Raised("IllegalArgumentException" if engine.language == "java" else "ValueError") from None
    return NOT_HANDLED
