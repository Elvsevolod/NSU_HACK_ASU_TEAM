"""Immutable HTTP input shared by scenario grounding and remote transport."""
from dataclasses import dataclass
from enum import Enum
from urllib.parse import quote

from .state import U
from .java_collections import JsonText, is_symbolic
from .request_url import request_address


class Absence(Enum):
    MISSING = 'missing'


MISSING = Absence.MISSING


@dataclass(frozen=True)
class FrozenMap:
    items: tuple


@dataclass(frozen=True)
class FrozenList:
    items: tuple


def freeze(value):
    if isinstance(value, JsonText):
        return ('json_text', freeze(value.payload), value.exact)
    if isinstance(value, dict):
        return FrozenMap(tuple((key, freeze(child)) for key, child in value.items()))
    if isinstance(value, list):
        return FrozenList(tuple(freeze(child) for child in value))
    if isinstance(value, tuple):
        return FrozenList(tuple(freeze(child) for child in value))
    return value


def thaw(value):
    if isinstance(value, FrozenMap):
        return {key: thaw(child) for key, child in value.items}
    if isinstance(value, FrozenList):
        return [thaw(child) for child in value.items]
    if isinstance(value, tuple) and len(value) == 3 and value[0] == 'json_text':
        return JsonText(thaw(value[1]), value[2])
    return value


@dataclass(frozen=True)
class Request:
    deployment: str
    method: str
    address: object
    path: tuple | None
    query: FrozenMap
    query_complete: bool
    header_values: object
    body_value: object = MISSING
    actor: object = U
    session: object = U
    provenance: object = ()

    def __deepcopy__(self, memo):
        return self

    @classmethod
    def http(cls, deployment, method, url, headers=None, body=MISSING,
             actor=U, session=U, provenance=()):
        address = request_address(url)
        return cls(str(deployment), method, freeze(url),
                   tuple(freeze(part) for part in address['segments']) if address and address['segments'] is not None else None,
                   freeze(address['query'] if address else {}),
                   bool(address and address['query_complete']), freeze(headers if headers is not None else {}),
                   freeze(body), freeze(actor), freeze(session), freeze(provenance))

    @property
    def body(self):
        return thaw(self.body_value)

    @property
    def headers(self):
        return thaw(self.header_values)

    @property
    def url(self):
        return thaw(self.address)

    def record(self):
        return {'deployment': self.deployment, 'method': self.method, 'url': self.url,
                'path': [thaw(part) for part in self.path] if self.path is not None else U,
                'query': thaw(self.query), 'query_complete': self.query_complete,
                'headers': self.headers, 'body': self.body,
                'actor': thaw(self.actor), 'session': thaw(self.session),
                'provenance': thaw(self.provenance)}


class BoundParameters(dict):
    """Preserve the public parameter inspection API with its immutable wire input."""
    def __init__(self, parameters, request):
        super().__init__(parameters)
        self.request = request


def wire_text(value):
    if type(value) is bool:
        return str(value).lower()
    if type(value) in (str, int, float):
        return str(value)
    if type(value) is dict and value.get('__type__') in ('UUID', 'java.util.UUID'):
        return value.get('__uuid_literal__', value.get('__uuid_string__', U))
    return value if is_symbolic(value) else U


def grounded_request(project, entry, params, bindings=None, actor=U, session=U):
    """Preserve unknown presence; NL omission alone does not prove wire absence."""
    routes = [(verb, route) for mid, verb, route in project.ix.handlers if mid == entry]
    if len(routes) != 1:
        return None
    method, template = routes[0]
    parameters = project.http_parameters(entry)
    path_values, query, headers, body = {}, {}, {}, MISSING
    for parameter in parameters:
        name, kind = parameter['name'], parameter['kind']
        value = params.get(name, U)
        wire_name = parameter['wire_name']
        if kind == 'PathVariable':
            path_values[wire_name] = wire_text(value)
        elif kind in ('RequestParam', 'RequestHeader'):
            target = query if kind == 'RequestParam' else headers
            key = wire_name if kind == 'RequestParam' else wire_name.lower()
            target[key] = (None if value is MISSING or value is None else U if value is U else
                           [wire_text(child) for child in value] if isinstance(value, list) else [wire_text(value)])
        elif kind == 'RequestBody':
            if name in params:
                body = params[name]
            else:
                meta = project.methods[entry]
                tid = project.resolve_type(parameter['type'], meta['module'], meta['file'])
                body = {key: params.get(key, U) for key in project.type_fields[tid]} if tid in project.type_fields else U
    # An incomplete scenario header context is distinct from an empty map.
    headers['__rest_unknown__'] = True
    path = tuple(freeze(path_values.get(part[1:-1].split(':', 1)[0], U)) if part.startswith('{') else part
                 for part in template)
    concrete = all(isinstance(part, str) for part in path)
    url = '/' + '/'.join(quote(part, safe='') for part in path) if concrete else U
    return Request(str(project.ix.unit_of(entry)), method, freeze(url), path,
                   freeze(query), True, freeze(headers), freeze(body), freeze(actor), freeze(session),
                   freeze(bindings or {}))
