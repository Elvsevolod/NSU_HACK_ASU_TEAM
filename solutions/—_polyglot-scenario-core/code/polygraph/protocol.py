"""Shared HTTP boundary: route selection, wire values, binding and error status."""
import re
from urllib.parse import parse_qs, unquote, urlsplit

from .ir import Span
from .values import Awaitable, Object, Raised, Response, Symbol, Text, Unknown, unknown, wire, wire_incomplete


def route_match(path, template):
    pieces, names, start = [], [], 0
    for match in re.finditer(r"\{([^}:]+)(?::([^}]+))?\}", template):
        pieces.append(re.escape(template[start:match.start()]))
        names.append(match[1])
        pieces.append("(" + (".+" if match[2] == "path" else "[^/]+") + ")")
        start = match.end()
    pieces.append(re.escape(template[start:]))
    matched = re.fullmatch("".join(pieces), path)
    return dict(zip(names, (unquote(v) for v in matched.groups()))) if matched else None


def scalar(value, typ, language):
    if unknown(value):
        return value
    raw = typ.strip().split(".")[-1]
    if raw == "UUID":
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value):
            raise Raised("RequestValidationError")
        return value.lower()
    if raw in {"int", "Integer", "long", "Long"}:
        try:
            if isinstance(value, bool):
                return int(value) if language == "python" else Unknown("invalid numeric parameter", typ)
            result = int(value)
            if language == "java" and not (-(2**(31 if raw in {"int", "Integer"} else 63)) <= result < 2**(31 if raw in {"int", "Integer"} else 63)):
                return Unknown("out-of-range HTTP integer", typ)
            return result
        except (ValueError, TypeError):
            raise Raised("RequestValidationError") from None
    if raw in {"bool", "boolean", "Boolean"}:
        if type(value) is bool:
            return value
        if str(value).lower() in {"true", "1", "on", "yes"}:
            return True
        if str(value).lower() in {"false", "0", "off", "no"}:
            return False
        raise Raised("RequestValidationError")
    if raw in {"float", "double", "Float", "Double"}:
        try:
            return float(value)
        except (ValueError, TypeError):
            raise Raised("RequestValidationError") from None
    return value


def bind_body(engine, value, typ, span):
    resolved = engine.p.resolve_type(typ, engine.p.module(span.file), span.file)
    if not resolved or value is None or unknown(value):
        return value
    if not isinstance(value, dict):
        raise Raised("RequestValidationError")
    if engine.p.types[resolved].language=='python' and engine.p.types[resolved].annotations.get('model'):
        from .pydantic_models import bind_body as native_body
        return native_body(engine,resolved,value,span)
    fields = engine.p.type_fields(resolved)
    kwargs = {}
    for name, (ftype, default) in fields.items():
        if name in value:
            kwargs[name] = scalar(value[name], ftype, engine.p.types[resolved].language)
        elif default is None:
            if engine.p.types[resolved].language == "python":
                raise Raised("RequestValidationError")
    obj = engine.create(resolved, kwargs=kwargs, span=span)
    if isinstance(obj, Object):
        obj.fields.update({k: v for k, v in kwargs.items()})
    return obj


def dispatch(engine, request, caller=None, span=Span()):
    verb = request.get("method", "GET")
    url = request.get("url", request.get("path", ""))
    symbols = {}
    if isinstance(url, Text):
        literal_text = ''.join(part for part in url.parts if isinstance(part, str))
        salt = 0
        while '__polygraph_' + str(salt) + '_' in unquote(literal_text):
            salt += 1
        pieces = []
        for part in url.parts:
            if isinstance(part, Symbol):
                if part.typ.split(".")[-1] not in {"UUID", "int", "Integer", "long", "Long"}:
                    engine.note("symbolic-url-shape", "A symbolic string may change URL structure", span)
                    if not engine.choose((False, True), "symbolic URL remains one path segment"):
                        return Response(Unknown("symbolic URL routing"), Unknown("symbolic URL status"))
                token = '__polygraph_' + str(salt) + '_' + str(len(symbols)) + '__'
                symbols[token] = part
                pieces.append(token)
            elif isinstance(part, str):
                pieces.append(part)
            else:
                return Response(Unknown("unknown HTTP address piece"), Unknown("unknown HTTP status"))
        url = "".join(pieces)
    if not isinstance(url, str) or not isinstance(verb, str):
        engine.note("unknown-request-address", "HTTP method or address is unknown", span)
        return Response(Unknown("unknown HTTP address"), Unknown("unknown HTTP status"))
    address = urlsplit(url)
    path = address.path or "/"
    query = {k: v[-1] if len(v) == 1 else v for k, v in parse_qs(address.query, keep_blank_values=True).items()}
    def restore(value):
        if isinstance(value, list):
            return [restore(item) for item in value]
        if not isinstance(value, str) or not symbols:
            return value
        parts = re.split('(' + '|'.join(re.escape(token) for token in symbols) + ')', value)
        parts = tuple(symbols.get(part, part) for part in parts if part != '')
        return parts[0] if len(parts) == 1 else Text(parts) if any(isinstance(part, Symbol) for part in parts) else value
    if any(any(token in key for token in symbols) for key in query):
        engine.note('symbolic-query-name', 'A symbolic query parameter name is unsupported', span)
        return Response(Unknown('symbolic query parameter name'), Unknown('unknown HTTP status'))
    query = {key: restore(value) for key, value in query.items()}
    query.update(request.get("query", {}) if isinstance(request.get("query", {}), dict) else {})
    headers = {str(k).lower(): v for k, v in request.get("headers", {}).items()}
    module = request.get("module", "")
    if not module and address.hostname:
        services = engine.context.get("services", {})
        matches = []
        for key, meta in engine.p.modules.items():
            candidate = meta.get("name", key.removeprefix("module:"))
            hosts = {candidate, *meta.get("deployment_units", [])}
            configured = services.get(candidate)
            if isinstance(configured, str):
                hosts.add(urlsplit(configured).hostname)
            if address.hostname in hosts:
                matches.append(candidate)
        if len(matches) == 1:
            module = matches[0]
        elif address.hostname not in {"localhost", "127.0.0.1"}:
            engine.note("external-host", "HTTP host is not mapped to a source deployment", span, hostname=address.hostname)
            engine.state.store.havoc()
            return Response(Unknown("external service response"), Unknown("external service status"))
    candidates = []
    for endpoint in engine.p.endpoints:
        if module and module != endpoint.module:
            continue
        if endpoint.verb not in {"*", verb.upper()}:
            continue
        parameters = route_match(path, endpoint.path)
        if parameters is not None:
            candidates.append((endpoint, parameters))
    if not candidates:
        from .spring_http import no_handler
        response=no_handler(engine,module,path,verb,span)
        if response is not None:return response
        engine.note("unresolved-request", "No source-derived handler matches HTTP method/path/module", span, method=verb, url=url, module=module)
        return Response(Unknown("unresolved server response"), Unknown("unresolved server status"))
    # Spring prefers literal paths; Starlette/FastAPI uses registration order.
    spring = all(c[0].framework == "spring" for c in candidates)
    if spring:
        specificity = max(len(re.sub(r"\{[^}]+\}", "", c[0].path)) for c in candidates)
        candidates = [c for c in candidates if len(re.sub(r"\{[^}]+\}", "", c[0].path)) == specificity]
    elif all(c[0].framework == "fastapi" for c in candidates) and len({c[0].module for c in candidates}) == 1:
        groups = {c[0].conditions.get("registration_group") for c in candidates}
        files = {engine.p.methods[c[0].method].span.file for c in candidates}
        if len(groups) == 1 and None not in groups and len(files) == 1:
            candidates = candidates[:1]
        elif len(candidates) > 1:
            engine.note("registration-order-unknown", "Overlapping routers/mounts require module/registration order beyond this model", span)
    if len(candidates) > 1:
        engine.note("ambiguous-route", "All matching source handlers remain hypotheses", span, candidates=[c[0].method for c in candidates])
        choice = engine.choose(tuple(range(len(candidates))), "HTTP handler ambiguity")
    else:
        choice = 0
    endpoint, path_values = candidates[choice]
    path_values = {k: restore(v) for k, v in path_values.items()}
    path_values.update(request.get("path_params", {}))
    method = engine.p.methods[endpoint.method]
    if endpoint.conditions.get('context_path_unknown'):
        engine.unsupported('Servlet context path depends on unresolved deployment configuration',method.span)
    risks = [r for r in engine.p.framework_risks if r["module"] == endpoint.module and r["framework"] == endpoint.framework]
    if risks:
        engine.note("framework-lifecycle", "Handler graph is conditional on an unmodeled framework phase", method.span, risks=risks)
        if not engine.context.get("assumptions", {}).get("framework_entry"):
            engine.state.havoc()
            if not engine.choose((False, True), "unmodeled framework lifecycle permits handler"):
                return Response(Unknown("framework may terminate before handler"), Unknown("framework response status"))
    if endpoint.conditions.get("profile_unknown") or endpoint.conditions.get("mount_unknown"):
        engine.note("route-activation-unknown", "Route activation depends on an unspecified profile/condition", method.span)
        if not engine.choose((False, True), "profile activation"):
            return Response(None, 404)
    if endpoint.conditions.get("mapping_constraints"):
        engine.note("mapping-constraints", "Headers/media type route constraints are not fully modeled", method.span)
        if not engine.choose((False, True), "Spring request mapping constraints"):
            return Response(None, 404)
    if "PreAuthorize" in method.annotations:
        engine.note("authorization-precondition", "Spring authorization is outside the model", method.span)
        if not engine.context.get("assumptions", {}).get("authorization_passed") and not engine.choose((False, True), "authorization decision"):
            return Response(None, 403)
    if caller:
        engine.add(caller.skeleton_id, "remote", method.skeleton_id, span, "source HTTP call with method, path and service")
    values = {}
    body = wire(request.get("body", {}))
    form = request.get('form', {})
    if not isinstance(form, dict):
        form = {}
    old_dependencies = engine.dependency_cache
    old_teardown = engine.unknown_teardown
    old_input,old_exits=engine.request_input,engine.dependency_exits
    engine.request_input={'method':verb,'headers':headers,'body':body,'query':query,'form':form,'path_params':path_values}
    engine.dependency_exits=[]
    engine.unknown_teardown = False
    outer_frames = engine.frames
    engine.frames = []
    engine.dependency_cache = {}
    try:
        if request.get('body_decode_error'):
            raise Raised('RequestValidationError')
        for dependency in endpoint.dependencies:
            engine.dependency(dependency, span=method.span)
        for param in method.params:
            location = param.location
            alias = param.alias or param.name
            if param.dependency:
                values[param.name] = engine.dependency(param.dependency, param.typ, method.span)
                continue
            resolved_type = engine.p.resolve_type(param.typ, method.module, method.span.file)
            if location == "path" or alias in path_values:
                value = path_values.get(alias, Unknown("missing path variable", param.typ, alias))
            elif param.typ.split(".")[-1] == "HttpHeaders":
                value = engine.state.new('spring.HttpHeaders', {'values': {k: v if isinstance(v, list) else [v] for k, v in headers.items()}})
            elif location == "header":
                value = headers.get(alias.lower(), Unknown("header not supplied", param.typ, alias))
                if isinstance(value, list):
                    value = value[0] if len(value) == 1 else Unknown('Multiple header values require an unmodeled scalar converter', param.typ, alias)
            elif location == 'form':
                if alias in form:
                    value = form[alias]
                elif param.default is not None:
                    value = engine.parameter_default(method, param)
                else:
                    raise Raised('RequestValidationError')
            elif location == "body" or (endpoint.framework == "fastapi" and resolved_type):
                if 'form' in request and 'body' not in request:
                    raise Raised('UnsupportedMediaType' if endpoint.framework == 'spring' else 'RequestValidationError')
                value = bind_body(engine, body, param.typ, method.span)
            elif param.typ.split(".")[-1] == "BindingResult":
                value = engine.state.new("spring.BindingResult", {"errors": Unknown("validation has not been evaluated")})
            elif param.typ.split(".")[-1] == "Principal":
                principal = engine.context.get("principal", {})
                value = engine.state.new("java.security.Principal", {"name": principal.get("name", Unknown("authenticated principal not supplied"))})
            elif alias in query:
                value = query[alias]
                if endpoint.framework == 'spring' and alias in form:
                    engine.note('multiple-request-values', 'Query and form both supply a scalar parameter; its converter is unmodeled', method.span, parameter=alias)
                    value = Unknown('Multiple query/form values', param.typ, alias)
            elif endpoint.framework == 'spring' and alias in form:
                value = form[alias]
            elif param.default is not None:
                value = engine.parameter_default(method, param)
            else:
                value = Unknown("request input not supplied", param.typ, alias)
            values[param.name] = scalar(value, param.typ, method.language)
        if method.language=='java':
            from .java_validation import validate_parameter
            for param in method.params:validate_parameter(engine,param,values.get(param.name),method)
        receiver = engine.create(method.owner, span=method.span, bean=True) if method.owner in engine.p.types else None
        result = engine.execute_method(method.key, kwargs=values, receiver=receiver, span=span)
        response = result if isinstance(result, Response) else Response(result, endpoint.status)
        response_model=engine.p.resolve_type(endpoint.response_type,method.module,method.span.file) if endpoint.response_type else ''
        if endpoint.framework=='fastapi' and response_model and engine.p.types[response_model].annotations.get('model'):
            from .pydantic_models import project_response
            response.body=project_response(engine,response.body,response_model,endpoint.conditions,method.span)
        if isinstance(response.body, Awaitable):
            engine.note("unawaited-response", "A returned coroutine is not a serializable HTTP body", method.span)
            return Response(None, 500)
        # HTTP transfers values. Do not share the server's header map or its
        # client-library view policy with a caller in another deployment.
        response = Response(wire(response.body), response.status, wire(response.headers))
        if wire_incomplete(response.body):
            engine.note("serialization-unknown", "Response serialization may fail or require an unsupported codec", method.span)
            response.status = Unknown("unmodeled serialization status")
        engine.events.append({"kind": "http", "method": verb.upper(), "path": path, "handler": method.skeleton_id,
                              "bound": values, "status": response.status, "body": response.body})
        return response
    except Raised as exc:
        if endpoint.framework=='spring':
            from .spring_http import handle_exception
            handled=handle_exception(engine,exc,endpoint.module,method)
            if handled is not None:return handled
        if exc.typ in {"HTTPException", "fastapi.HTTPException", "starlette.exceptions.HTTPException"} and isinstance(exc.value, Object):
            detail=exc.value.fields.get('detail')
            return Response({'detail':detail} if endpoint.framework=='fastapi' else detail, exc.value.fields.get("status_code", 500),exc.value.fields.get('headers',{}))
        if exc.typ == "RequestValidationError":
            return Response({'detail':exc.value} if endpoint.framework=='fastapi' and isinstance(exc.value,list) else None, 422 if endpoint.framework == "fastapi" else 400)
        if exc.typ == 'UnsupportedMediaType':
            return Response(None, 415)
        if exc.typ=='MethodArgumentNotValidException':return Response(Unknown('Spring validation error response payload'),400)
        if exc.typ == 'ResponseValidationError':return Response(None,500)
        engine.note("unhandled-exception", "Request stops at an exception; HTTP error mapping may be incomplete", method.span, exception=exc.typ)
        return Response(Unknown("unhandled server exception"), 500)
    finally:
        from .models import call
        for frame,managers,manager_span in reversed(engine.dependency_exits):
            engine.frames.append(frame)
            try:
                for manager in reversed(managers):
                    if manager.typ in {'sqlmodel.Session','sqlalchemy.orm.Session'}:call(engine,manager,'close',(),{},manager_span)
            finally:engine.frames.pop()
        if engine.unknown_teardown:
            engine.state.havoc()
            engine.note("teardown-effects-unknown", "Unmodeled generator teardown invalidates state for later requests", method.span)
        engine.unknown_teardown = old_teardown
        engine.request_input,engine.dependency_exits=old_input,old_exits
        engine.dependency_cache = old_dependencies
        engine.frames = outer_frames
