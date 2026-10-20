"""The bounded default MVC mapping/media/status contract, shared by both callers."""
import re
from .state import U
from .request import MISSING
from .models import status_code
from .http_binding import BindingFailure


def response_status(annotations):
    annotation = next((a for a in annotations if a['name'].split('.')[-1] == 'ResponseStatus'), None)
    if annotation is None:return None
    raw = annotation.get('args', '').strip('() ')
    match = re.search(r'(?:\b(?:code|value)\s*=\s*|^)(?:[\w.]+\.)?([A-Z_]+|\d{3})(?:\s*[,)]|\s*$)', raw)
    return status_code(int(match[1]) if match and match[1].isdigit() else match[1]) if match else U


def check_request(engine, target, request):
    routes = [(verb, route) for mid, verb, route in engine.p.ix.handlers if mid == target]
    if routes and request.path is not None:
        from .request import thaw
        parts = [thaw(part) for part in request.path]
        matching = [(verb, route) for verb, route in routes if len(parts) == len(route) and
                    all(part is U or str(template).startswith('{') or part == template for part, template in zip(parts, route))]
        if not matching:raise BindingFailure('URL does not match selected source route', 404)
        if isinstance(request.method, str) and not any(verb is None or verb == request.method for verb, _ in matching):
            raise BindingFailure('HTTP method does not match selected source route', 405)
    headers = request.headers
    media = headers.get('content-type', U if headers.get('__rest_unknown__') else []) if isinstance(headers, dict) else U
    if media is U or isinstance(media,list) and any(value is U for value in media):
        engine.assume('HTTP content type is unresolved: '+target)
        return
    media = media[0].split(';', 1)[0].lower() if media and isinstance(media[0], str) else 'application/octet-stream'
    meta = engine.p.methods[target]
    annotations = [*engine.p.nodes[meta['owner']].get('annotations', []), *meta.get('annotations', [])]
    consumes = None
    for annotation in annotations:
        if annotation['name'].split('.')[-1] not in ('RequestMapping','PostMapping','PutMapping','PatchMapping','GetMapping','DeleteMapping'):continue
        raw = re.search(r'\bconsumes\s*=\s*(\{[^}]*\}|"[^"]*"|[\w.]+)', annotation.get('args',''))
        if raw:
            consumes = re.findall(r'"([^"]+)"', raw[1])
            if not consumes:
                constant = raw[1].split('.')[-1]
                consumes = {'APPLICATION_JSON_VALUE':['application/json'], 'APPLICATION_FORM_URLENCODED_VALUE':['application/x-www-form-urlencoded']}.get(constant)
                if consumes is None:engine.assume('HTTP consumes constant is unresolved: '+target)
    if consumes and not any((media != value[1:] if value.startswith('!') else
                             value == '*/*' or value == media or value.endswith('/*') and media.startswith(value[:-1])) for value in consumes):
        raise BindingFailure('request content type does not match consumes', 415)
    if request.body is MISSING or request.body is None:return
    for parameter in engine.p.http_parameters(target):
        if parameter['kind'] != 'RequestBody':continue
        typ = parameter['type'].split('.')[-1]
        if typ in ('String','byte[]'):continue
        if media != 'application/json' and not media.endswith('+json'):
            raise BindingFailure('no modeled default JSON converter for '+media, 415)
