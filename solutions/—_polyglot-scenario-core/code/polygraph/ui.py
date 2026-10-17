"""Source UI facts and per-path browser state shared by all backend adapters."""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
from types import SimpleNamespace
from urllib.parse import parse_qsl

from rank_bm25 import BM25Plus

from .input_context import normalized
from .ir import Span
from .values import Symbol, Text, Unknown, equal
from .ui_extract.frontend import Frontend, FUNCTIONS, ancestor, dom_string, redeclares, truth
from .ui_extract.json_values import EncodedJSON, parse as parse_json, stringify as stringify_json, wire_json
from .ui_extract.native import JavaScriptError, NativeUnavailable, engine as native_engine
from .ui_extract.state import JS_UNDEFINED, U, SymbolicValue, JSONObject
from .ui_extract.symbolic_text import concat_text
from .ui_extract.nl_inputs import control_polarity


class BoundSymbol(SymbolicValue):
    def __init__(self, value):
        self.backend = value
        string = value.typ.split('.')[-1] in {'UUID', 'String', 'str'}
        token = hashlib.sha256(repr(value).encode()).hexdigest()
        super().__init__({'__symbol__': token, '__type__': 'String' if string else 'int',
                          '__category__': 'string' if string else 'number', '__nonnull__': value.nonnull})
        if value.typ.split('.')[-1] == 'UUID' and value.nonnull:
            self.update(__length__=36, __uuid_text__=True)


def to_browser(value, limitations, active=frozenset()):
    if isinstance(value, Unknown):
        limitations.append('Unknown backend value: ' + value.reason)
        return U
    if isinstance(value, Symbol):
        if value.typ.split('.')[-1] in {'UUID', 'String', 'str'} or value.sort == 'bv32':
            return BoundSymbol(value)
        limitations.append('Symbolic scalar cannot be represented exactly as a JS Number: ' + value.typ)
        return U
    if isinstance(value, Text):
        result = ''
        for part in value.parts:
            result = concat_text(result, to_browser(part, limitations, active))
        return result
    if isinstance(value, (dict, list, tuple)):
        if id(value) in active or len(active) >= 64:
            limitations.append('Browser transfer cycle/depth limit')
            return U
        active = active | {id(value)}
        if isinstance(value, dict):
            return JSONObject({str(k): to_browser(v, limitations, active) for k, v in value.items()})
        return [to_browser(v, limitations, active) for v in value]
    if type(value) in (int, float):
        return native_engine().run('identity', value)
    return value if value is None or type(value) in (str, bool) else U


def to_backend(value, active=frozenset()):
    if value is U or value is JS_UNDEFINED:
        return Unknown('Unresolved browser value' if value is U else 'JavaScript undefined has no JSON scalar')
    if isinstance(value, BoundSymbol):
        return value.backend
    if isinstance(value, EncodedJSON):
        return Unknown('JSON text contains opaque scalar values')
    if isinstance(value, SymbolicValue):
        parts = value.get('__text_parts__')
        return Text(tuple(to_backend(part, active) for part in parts)) if isinstance(parts, list) else Unknown('Unsupported abstract browser string')
    if isinstance(value, (dict, list, tuple)):
        if id(value) in active or len(active) >= 64:
            return Unknown('Browser state cycle/depth limit')
        active = active | {id(value)}
        if isinstance(value, dict):
            return {str(k): to_backend(v, active) for k, v in value.items()}
        return [to_backend(v, active) for v in value]
    return value


@dataclass
class BrowserFrame:
    browser: dict
    limitations: list
    now: object = None
    blocked_natives: frozenset = frozenset()
    angular_scope: bool = False


class EndpointFacts:
    def __init__(self, project):
        self.handlers = [(e.method, None if e.verb == '*' else e.verb, [p for p in e.path.split('/') if p]) for e in project.endpoints]

    @staticmethod
    def preferred_handlers(matches, verb):
        return {mid for mid, _, _ in matches}


class UIModel:
    def __init__(self, project, tokenize):
        self.p, self.tokens = project, tokenize
        self.frontend = Frontend(SimpleNamespace(root=project.root, ix=EndpointFacts(project)))
        for message in dict.fromkeys(self.frontend.unsupported + self.frontend.warnings):
            project.warn('frontend-extraction-partial', message)
        self.sites = list(self.frontend.sites.values())
        self.documents = [tokenize(' '.join([s['action_label'], s['file'], s['source'], *[o['label'] for o in s['options'] if isinstance(o.get('label'), str)]])) or ['__empty_ui__'] for s in self.sites]
        self.index = BM25Plus(self.documents, delta=0) if self.documents else None
        self.by_method = {}
        for index, site in enumerate(self.sites):
            for method in site['handlers']:
                self.by_method.setdefault(method, []).append(index)

    def summary(self):
        return {'source_hashes':self.p.frontend_hashes, 'scripts_parsed':len(self.frontend.trees),
                'pages_parsed':len(self.frontend.pages), 'request_sites':len(self.sites),
                'unsupported':list(dict.fromkeys(self.frontend.unsupported)), 'warnings':list(dict.fromkeys(self.frontend.warnings)),
                'unmodeled_ajax_hooks':self.frontend.ajax_hooks}

    def text(self, method):
        return ' '.join(self.sites[i]['action_label'] + ' ' + self.sites[i]['file'] for i in self.by_method.get(method, []))

    def frame(self, engine):
        if engine.state.browser is None:
            browser = {key: {} for key in ['form', 'dom', 'dom_text', 'storage', 'url', 'pages', 'script', 'options']}
            browser['storage'] = {'sessionStorage': {}, 'localStorage': {}}
            limitations = []
            supplied = engine.context.get('browser', {})
            browser.update(to_browser(deepcopy(supplied), limitations))
            browser['storage_complete'] = {name: name in supplied.get('storage', {}) for name in ('sessionStorage', 'localStorage')}
            for name in ('sessionStorage', 'localStorage'):
                browser['storage'].setdefault(name, {})
            engine.state.browser = BrowserFrame(browser, limitations)
        return engine.state.browser

    def note(self, engine, frame, site):
        if frame.limitations:
            engine.note('browser-limitations', 'Browser values/effects are partly unknown', Span(site['file'], site['line']), limitations=list(dict.fromkeys(frame.limitations)))

    def select(self, engine, method, action):
        indices = self.by_method.get(method, [])
        if not indices:
            words=set(self.tokens(action))
            indices=[i for i,site in enumerate(self.sites) if len(self.tokens(site['action_label']))>=2 and set(self.tokens(site['action_label'])) <= words]
            if not indices:
                return None
            engine.note('ui-handler-unmapped', 'A matching source action has no link to the retrieved backend handler; its actual HTTP request is checked', candidates=[self.sites[i]['id'] for i in indices])
        scores = self.index.get_scores(self.tokens(action))
        ranked = sorted(indices, key=lambda i: (-float(scores[i]), self.sites[i]['id']))
        choices = [i for i in ranked if scores[i] >= scores[ranked[0]] - max(.15, scores[ranked[0]] * .08)]
        if len(choices) > 1:
            engine.note('ui-site-hypotheses', 'Several UI request sites remain possible', candidates=[self.sites[i]['id'] for i in choices])
        index = choices[engine.choose(tuple(range(len(choices))), 'UI request site')] if len(choices) > 1 else choices[0]
        return self.sites[index]

    def bind(self, engine, method, action, base, provenance, ui_inputs):
        site = self.select(engine, method, action)
        if site is None:
            return base, None
        span = Span(site['file'], site['line'])
        frame = self.frame(engine)
        frame.angular_scope = site.get('client') == 'angular-http'
        detail = {'id': site['id'], 'source': {'file': site['file'], 'line': site['line']}, 'guards': [], 'projections': []}
        if site['verb'] == str(U).upper():
            engine.note('ui-method-unknown', 'The source HTTP method is not a known string', span)
            return None, detail
        if site.get('unsupported_ajax_options') or self.frontend.ajax_hooks:
            engine.note('ui-transport-unknown', 'Source AJAX hooks/options may cancel or transform this request', span,
                        options=site.get('unsupported_ajax_options'), hooks=self.frontend.ajax_hooks)
            return None, detail
        if len(site.get('compound_request_sites', [])) > 1:
            engine.note('ui-compound-unsupported', 'An action issues several source requests whose ordering is not yet lowered', span, sites=site['compound_request_sites'])
            return None, detail
        tree = self.frontend.trees[self.p.root / site['file']]
        if tree.root_node.has_error:
            engine.note('ui-parse-unknown', 'Cannot validate a request in a script with parse errors', span)
            return None, detail
        call = next((n for n in self._walk(tree.root_node) if n.start_byte == site['start_byte'] and n.type == 'call_expression'), None)
        scopes = []
        scope = ancestor(call, (*FUNCTIONS, 'program')) if call is not None else tree.root_node
        while scope is not None:
            scopes.append(scope)
            scope = ancestor(scope.parent, (*FUNCTIONS, 'program')) if scope.type != 'program' else None
        if any(redeclares(s, name, None) for s in scopes for name in ('$', 'jQuery')):
            engine.note('ui-client-shadowed', 'The request receiver is shadowed by source code', span)
            return None, detail
        frame.blocked_natives = frozenset(name for name in ('JSON', 'parseInt', 'parseFloat', 'Date','Object') if any(redeclares(s, name, None) for s in scopes))
        if frame.blocked_natives:
            engine.note('ui-native-shadowed', 'Source bindings replace operations assumed by the expression model', span, names=sorted(frame.blocked_natives))
            return None, detail
        if site.get('with_credentials') is True:
            engine.note('ui-cookie-context', 'Browser credential cookies are an unresolved framework precondition', span)
        try:
            self.frontend.enter(site, frame)
            options = site['options'] + [option for group in frame.browser.get('options', {}).values() if isinstance(group, list) for option in group]
            chosen = {}
            for option in options:
                label = set(self.tokens(option['label'])) if isinstance(option.get('label'), str) else set()
                if label and label <= set(self.tokens(action)) and control_polarity(action, option['label']) is not False:
                    chosen.setdefault((option.get('space', 'dom'), option['control']), []).append(option['value'])
            for (space, control), values in chosen.items():
                if len(set(map(str, values))) == 1:
                    frame.browser[space][control if space == 'form' else '#' + control.lstrip('#')] = values[0]
            expressions = {**site['body_fields'], **site.get('conditional_fields', {})}
            for binding in provenance:
                if binding['source'] == 'unresolved':
                    continue
                expression = expressions.get(binding['field'])
                if expression is None:
                    continue
                projected = expression
                for _ in range(8):
                    if projected not in site['definitions']:
                        break
                    projected = site['definitions'][projected]
                value = to_browser(binding['value'], frame.limitations)
                self.frontend.update_input(projected, value, frame)
                controls = self.frontend.input_controls(expression, site['definitions'])
                if value is not U:
                    for space in ('form', 'dom'):
                        for control in controls[space]:
                            if normalized(control.lstrip('#')) == normalized(binding['field']):
                                key = control if space == 'form' else '#' + control.lstrip('#')
                                frame.browser[space][key] = value if space == 'form' else dom_string(value)
                if value is U:
                    for space in ('form', 'dom'):
                        for control in controls[space]:
                            key = control if space == 'form' else '#' + control.lstrip('#')
                            frame.browser[space][key] = U
                detail['projections'].append({'field': binding['field'], 'expression': projected, 'source': binding['source']})
            for space, values in (ui_inputs or {}).items():
                if space in {'form', 'dom', 'dom_text', 'storage', 'url'} and isinstance(values, dict):
                    supplied = to_browser(values, frame.limitations)
                    if space == 'storage':
                        for kind, items in supplied.items():
                            if kind in ('sessionStorage', 'localStorage') and isinstance(items, dict):
                                frame.browser['storage'].setdefault(kind, {}).update(items)
                    else:
                        frame.browser[space].update(supplied)
            extra = self.frontend.script_values(site, frame)
            for (mode, control), (value, _) in self.frontend.prepared_dom_values(site, frame).items():
                frame.browser['dom_text' if mode == 'text' else 'dom'][control] = value
            for check in site.get('request_checks', []):
                guards = [truth(self.frontend.evaluate(c, frame, extra, check['definitions'])) for c in check['conditions']]
                if False in guards:
                    continue
                uncertain = any(value is U for value in guards) or check['unsupported_control']
                try:
                    value = U if check['unsupported_control'] else self.frontend.check_completion(check, frame, extra, check['definitions'])
                except JavaScriptError:
                    if not uncertain:
                        raise
                    value = U
                if uncertain or value is U:
                    engine.note('ui-prelude-unknown', 'HTTP depends on an unresolved JavaScript prefix', span)
                    if not engine.choose((False, True), 'UI prefix reaches request'):
                        return None, detail
                elif check['completion'] in {'return', 'throw'}:
                    engine.note('ui-prelude-stops', 'Source control flow stops before the request', span, completion=check['completion'])
                    return None, detail
            cases = []
            for case in site['url_cases']:
                guards = [truth(self.frontend.evaluate(c, frame, extra, site['definitions'])) for c in case['conditions']]
                detail['guards'].append({'conditions': case['conditions'], 'outcomes': [None if value is U else value for value in guards]})
                if False not in guards:
                    cases.append((case, guards))
            if not cases:
                engine.note('ui-request-blocked', 'Known UI guards prevent this request', span)
                return None, detail
            case, guards = cases[engine.choose(tuple(range(len(cases))), 'UI URL alternative')] if len(cases) > 1 else cases[0]
            if any(value is U for value in guards):
                engine.note('ui-guard-unknown', 'UI request execution depends on an unknown guard', span)
                if not engine.choose((False, True), 'UI request guard permits HTTP'):
                    return None, detail
            url = self.frontend.evaluate(case['url'], frame, extra, site['definitions'])
            headers = self.frontend.evaluate(site['headers_expression'], frame, extra, site['definitions']) if site.get('headers_expression') else {}
            if not isinstance(headers, dict) or isinstance(headers, SymbolicValue):
                engine.note('ui-headers-unknown', 'Source header map cannot be validated', span)
                return None, detail
            headers = {str(key).lower():dom_string(value) for key,value in headers.items()}
            payload = self.frontend.evaluate(site['data_expression'], frame, extra, site['definitions']) if site.get('data_present') else {}
            angular = site.get('client') == 'angular-http'
            if angular and site['verb'] in {'GET','HEAD'}:
                payload = self.frontend.evaluate(site['params_expression'],frame,extra,site['definitions']) if site.get('params_expression') else {}
            content_type = site.get('content_type') if site.get('content_type_present') else 'application/json;charset=utf-8' if angular and site['verb'] in {'POST','PUT','PATCH'} else 'application/x-www-form-urlencoded; charset=UTF-8'
            content_type = headers.get('content-type', content_type)
            if not isinstance(content_type, str):
                engine.note('ui-media-type-unknown', 'Source contentType cannot establish the request encoding', span)
                return None, detail
            media_type = content_type.split(';',1)[0].strip().lower()
            json_body = (media_type == 'application/json' or media_type.endswith('+json')) and site['verb'] not in {'GET','HEAD'}
            if angular and site.get('data_present') and site['verb'] not in {'GET','HEAD'} and isinstance(payload,(dict,list)):
                payload = stringify_json(payload)
            invalid_json = json_body and payload is not U and not isinstance(payload, (str, EncodedJSON)) and site.get('data_present')
            if json_body and not invalid_json and site.get('data_present'):
                try:
                    payload = parse_json(payload)
                except JavaScriptError:
                    invalid_json = True
            if isinstance(payload, EncodedJSON):
                engine.note('ui-form-shape-unknown', 'Opaque JSON text sent as form data has an unresolved field shape', span)
                return None, detail
            for binding in provenance:
                if binding['source'] not in {'unresolved'} and not isinstance(binding['value'], Unknown) and isinstance(payload, dict) and binding['field'] in payload:
                    actual = to_backend(payload[binding['field']])
                    if equal(actual, binding['value']) is not True:
                        engine.note('ui-input-conflict', 'Source UI payload does not validate the proposed input', span, field=binding['field'])
                        return None, detail
            request = {'method': site['verb'] if site['verb'] != str(U).upper() else base['method'], 'url': to_backend(url), 'headers': to_backend(headers)}
            if site.get('content_type_present') or site.get('data_present') and request['method'] not in {'GET','HEAD'}:
                request['headers'].setdefault('content-type', content_type)
            if request['method'] in {'GET', 'HEAD'}:
                if isinstance(payload,str):
                    pairs = parse_qsl(payload,keep_blank_values=True)
                    if len({key for key,_ in pairs}) != len(pairs):
                        engine.note('ui-repeated-query-unsupported', 'Repeated URL-encoded fields require a framework-specific multi-value converter', span)
                        return None, detail
                    payload = dict(pairs)
                if site.get('process_data') is not True or not isinstance(payload, dict) or any(isinstance(value,(dict,list)) and not isinstance(value,SymbolicValue) for value in payload.values()):
                    engine.note('ui-query-unsupported', 'Only flat source query payloads are modeled', span)
                    return None, detail
                request['query'] = to_backend({key:'' if value is None or value is JS_UNDEFINED else dom_string(value) for key,value in payload.items()})
            elif json_body:
                request['body'] = to_backend(wire_json(payload))
                if invalid_json:
                    request['body_decode_error'] = True
            else:
                if isinstance(payload,str):
                    pairs = parse_qsl(payload,keep_blank_values=True)
                    if len({key for key,_ in pairs}) != len(pairs):
                        engine.note('ui-repeated-form-unsupported', 'Repeated URL-encoded fields require a framework-specific multi-value converter', span)
                        return None, detail
                    payload = dict(pairs)
                if site.get('process_data') is not True or not isinstance(payload, dict) or any(isinstance(value, (dict, list)) and not isinstance(value,SymbolicValue) for value in payload.values()):
                    engine.note('ui-form-unsupported', 'Only flat source form payloads are modeled', span)
                    return None, detail
                request['form'] = to_backend({key: '' if value is None or value is JS_UNDEFINED else dom_string(value) for key, value in payload.items()})
            if site.get('data_present') and not site.get('body_keys_complete') and isinstance(payload, dict):
                engine.note('ui-payload-shape-unknown', 'Source UI may supply additional request fields', span)
            self.note(engine, frame, site)
            return request, detail
        except (JavaScriptError, NativeUnavailable) as exc:
            engine.note('ui-preparation-exception', 'UI preparation cannot reach the HTTP request', span, reason=str(exc))
            return None, detail

    @staticmethod
    def _walk(node):
        yield node
        for child in node.named_children:
            yield from UIModel._walk(child)

    def apply_response(self, engine, ui_site, response):
        if not ui_site:
            return True
        site = self.frontend.sites[ui_site['id']]
        frame = self.frame(engine)
        if site.get('unmodeled_callback_chain'):
            engine.note('ui-callback-chain-unsupported', 'Observed HTTP prefix ends before an unmodeled response callback chain', Span(site['file'],site['line']), chain=site['unmodeled_callback_chain'])
            return False
        if site.get('response_data_type') not in (U,'json'):
            frame.browser = self._unknown_effects(frame.browser, site)
            engine.note('ui-response-codec-unknown', 'An explicit response converter is outside the browser model', Span(site['file'],site['line']))
            return True
        if type(response.status) is int and not (200 <= response.status < 300 or response.status == 304):
            return True
        if type(response.status) is not int:
            frame.browser = self._unknown_effects(frame.browser, site)
            engine.note('ui-callback-status-unknown', 'Callback effects cannot be confirmed without a success status', Span(site['file'], site['line']))
            return True
        try:
            body = JS_UNDEFINED if response.status == 204 else to_browser(response.body, frame.limitations)
            self.frontend.apply_response(site, body, frame)
            self.note(engine, frame, site)
            return True
        except (JavaScriptError, NativeUnavailable) as exc:
            engine.note('ui-callback-exception', 'Scenario stops at a browser response exception', Span(site['file'], site['line']), reason=str(exc))
            return False

    @staticmethod
    def _unknown_effects(browser, site):
        for effect in site['effects']:
            space, key = effect['space'], effect['key']
            if space == 'completion':
                continue
            if space == 'navigation':
                browser['url'] = {key: U for key in browser['url']}
            elif isinstance(key, str):
                if space == 'storage':
                    browser['storage'].setdefault(effect['storage_kind'], {})[key] = U
                else:
                    browser.setdefault(space, {})[key] = U
        return browser
