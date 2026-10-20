"""External explicit HTTP controls. Input recipes never contain expected edges.

This client-side test adapter does not participate in NL retrieval. A recipe
selects an existing source route by method/template/deployment, then transports
only explicit literals or a complete previous response property through the
normal Request and server-binding code. It never modifies application state.
"""
from copy import deepcopy
from dataclasses import replace
from analyzer.contracts import ContractGrounder
from analyzer.history_agreement import key, observation
from analyzer.models import unwrap
from analyzer.request import grounded_request, freeze, normalized_headers
from analyzer.state import U


class ScriptInputError(ValueError):
    pass


def value(spec, history):
    if isinstance(spec, dict) and '$response' in spec:
        if set(spec) != {'$response', 'path', 'native_kind'}:
            raise ScriptInputError('Unsupported response-reference fields')
        number, path = spec['$response'], spec['path']
        if type(number) is not int or not 1 <= number <= len(history):
            raise ScriptInputError('Previous response is absent')
        item = history[number - 1]
        if item.get('outcome') != 'returned' or item.get('exploration', {}).get('complete') is not True:
            raise ScriptInputError('Previous response has no complete successful producer')
        if not isinstance(path, list) or not path or any(type(part) not in (str, int) for part in path):
            raise ScriptInputError('Invalid response property path')
        actual = unwrap(item.get('result', U))
        try:
            for part in path:
                if type(part) is str and (not isinstance(actual, dict) or part.startswith('__')):
                    raise KeyError(part)
                if type(part) is int and (not isinstance(actual, list) or part < 0):
                    raise KeyError(part)
                actual = actual[part]
        except (KeyError, IndexError, TypeError):
            raise ScriptInputError('Previous response property is absent') from None
        if key(actual) is None or actual is None:
            raise ScriptInputError('Previous response property is unresolved')
        kind = spec['native_kind']
        symbolic = isinstance(actual, dict) and '__symbol__' in actual
        if kind != 'Long' or not (symbolic and actual.get('__type__') in ('Long', 'long', 'java.lang.Long')
                                 or type(actual) is int and -(2**63) <= actual < 2**63):
            raise ScriptInputError('Response reference is outside the declared Long contract')
        return deepcopy(actual), {'source': 'history', 'reference': 'history[' + str(number - 1) + '].result.' + '.'.join(map(str, path)),
            'resolved': True, 'producer_observation': {'step': item.get('step'), 'entry': item.get('entry'),
                'digest': observation(item), 'exploration': deepcopy(item.get('exploration', {}))}}
    if isinstance(spec, dict):
        if any(str(k).startswith('$') for k in spec):
            raise ScriptInputError('Unknown client recipe operator')
        return {k: value(v, history)[0] for k, v in spec.items()}, {'source': 'explicit_script', 'resolved': True}
    if isinstance(spec, list):
        return [value(v, history)[0] for v in spec], {'source': 'explicit_script', 'resolved': True}
    if spec is not None and type(spec) not in (str, int, float, bool):
        raise ScriptInputError('Unsupported explicit input value')
    return deepcopy(spec), {'source': 'explicit_script', 'resolved': True}


def script_grounder(recipes):
    recipes = deepcopy(recipes)

    class ExplicitScriptGrounder(ContractGrounder):
        def step(self, action, state, scenario_text='', prepared_proposal=None):
            if not action.startswith('@http-script:'):
                raise ScriptInputError('This control driver accepts explicit HTTP recipes only')
            detail = {'candidates': [], 'proposal': {'hypotheses': []}, 'unresolved': [],
                      'grounding_status': 'external_explicit_http_script'}
            try:
                recipe = recipes[action.removeprefix('@http-script:')]
                allowed = {'deployment', 'method', 'route_template', 'parameters', 'headers', 'body'}
                if not set(recipe) <= allowed or not allowed - {'body'} <= set(recipe):
                    raise ScriptInputError('Invalid explicit HTTP recipe schema')
                template = recipe['route_template'].strip('/').split('/') if recipe['route_template'].strip('/') else []
                entries = {mid for mid, verb, route in self.project.ix.handlers if verb == recipe['method'] and list(route) == template
                           and recipe['deployment'] in self.project.ix.deployments_for(mid, recipe['deployment'])
                           and self.project.enabled_type(self.project.methods[mid]['owner'])}
                if len(entries) != 1:
                    raise ScriptInputError('Explicit method/template/deployment has no unique source handler')
                entry = entries.pop()
                params, bindings = {}, {}
                for name, spec in recipe['parameters'].items():
                    params[name], bindings[name] = value(spec, state.history)
                declared = self.project.http_parameters(entry)
                named = {item['name'] for item in declared if item['kind'] != 'RequestBody'}
                if set(params) - named:
                    raise ScriptInputError('Explicit parameter has no source HTTP binding')
                if 'body' in recipe:
                    bodies = [item for item in declared if item['kind'] == 'RequestBody']
                    if len(bodies) != 1:
                        raise ScriptInputError('Explicit body has no unique source RequestBody')
                    params[bodies[0]['name']], bindings[bodies[0]['name']] = value(recipe['body'], state.history)
                owned = deepcopy(state)
                request = grounded_request(self.project, entry, params, bindings)
                if request is None:
                    raise ScriptInputError('Source HTTP request could not be constructed')
                request = replace(request, header_values=freeze(normalized_headers(recipe['headers'])),
                                  provenance=freeze({'source': 'explicit_http_script', 'recipe': action, 'bindings': bindings}))
                detail['candidates'] = [entry]
                return [{'entry': entry, 'site': None, 'state': owned, 'params': params, 'bindings': bindings,
                         'request': request, 'reason': 'External explicit HTTP input matched against source routes', 'unresolved': []}], detail
            except (KeyError, ScriptInputError) as error:
                detail['unresolved'] = [str(error)]
                return [], detail

    return ExplicitScriptGrounder
