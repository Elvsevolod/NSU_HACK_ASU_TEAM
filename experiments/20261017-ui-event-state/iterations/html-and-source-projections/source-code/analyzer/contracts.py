"""Deterministic source-contract retrieval and evidence-bearing request bindings."""
from copy import deepcopy
from pathlib import PurePosixPath
import re

from baseline_closure import BM25
from baseline_nlp import ntoks
from .context import context_spans, dates_in
from .engine import Engine
from .grounding import references
from .project import text
from .state import U, JS_UNDEFINED
from .provenance import contains_unknown, history_value, source_string, history_role_value, selected_field
from .request_semantics import filter_bindings, partial_url_parameters, enum_scalar_binding, generated_omissions, enum_ordinal_binding
from .nl_inputs import field_role, language_roles, canonical_ui_literal, introduced_value, control_polarity, intermediate_field
from .provenance import entity_words
from .frontend import json_value
from .scenario_literals import structured_bindings, canonical_reference
from .structured_literals import literal_value
from .context_choices import choice_rules, default_choices


STOP = set('the a an all any some with without and or for of to from on in by this that their they first new one '
           'controller service api http org springframework request response java string'.split())
# Language-level synonyms only; project entities, routes and enum values come from source.
VERBS = [set('get find query lookup search read view open show list refresh inspect fetch'.split()),
         set('create add insert register save book reserve buy purchase'.split()),
         set('delete remove erase'.split()), set('update modify change edit'.split()),
         set('login signin authenticate'.split()), set('pay charge settle'.split())]
VERBS[0].update(('check', 'browse', 'look', 'ask', 'calculate', 'compute', 'estimate'))


def tokens(value):
    words = ntoks(re.sub(r'\blog\s+in\b', 'login', str(value), flags=re.I))
    output = [word for word in words if word not in STOP]
    output += ['prefix' + word[:6] for word in output if len(word) >= 7]
    return output


def intent(value):
    value = re.sub(r'^as\b.*?,\s*|^(?:try\s+to|please)\s+', '', value, flags=re.I)
    words = tokens(value)
    return next((i for i, group in enumerate(VERBS) if words and words[0] in group), None)


def normalized(value):
    return re.sub(r'[^a-z0-9]', '', value.lower())


def option_label_matches(label, action):
    wanted = set(tokens(label)) if isinstance(label, str) else set()
    clauses = re.split(r'[,;]|\b(?:with|without|for|and)\b', action, flags=re.I)
    return bool(wanted) and any(wanted <= set(tokens(clause)) for clause in clauses)


def unfilled_form_edits(frontend, site, action, bindings):
    """An explicitly edited field needs a new value, not its old form prefill."""
    if intent(action) != 3:
        return set(), set()
    page = frontend.pages.get(frontend.project.root / site['page'])
    editable = {value.split('.')[0] for value in getattr(page, 'editable_models', [])}
    if not editable:
        return set(), set()
    focus = re.split(r'\b(?:in|on|for|at)\b', re.sub(r"\b[\w-]+['’]s\b", '', action), 1, flags=re.I)[0]
    wanted = set(ntoks(focus))
    def label(name):
        words = ['number' if word in ('num','no') else word for word in ntoks(name)]
        return set(words[-2:] if len(words) > 1 and words[-1] in ('number','code','id','type','date','time') else words[-1:])
    fields, controls = set(), set()
    for field, expression in {**site['body_fields'], **site.get('conditional_fields', {})}.items():
        if bindings.get(field, {}).get('source') not in (None,'ui','ui_projection','history','context+history'):
            continue
        properties = frontend.input_controls(expression, site['definitions'])['form'] & editable
        if properties and any(label(name) <= wanted for name in [field,*properties] if label(name)):
            fields.add(field);controls.update(properties)
    return fields, controls


def absent_field(raw, key):
    words = re.findall(r'[a-z0-9]+', re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', key).lower())
    if not words:
        return None
    pattern = r'\b(?:no|without)\s+' + r'[ _-]*'.join(map(re.escape, words)) + r'\b'
    for source, value in raw.items() if isinstance(raw, dict) else []:
        found = re.search(pattern, str(value), re.I)
        if found:
            return str(source), found[0]
    return None


def read_static_context(raw):
    spans, limited, credentials = context_spans(raw)
    facts = {}
    clock = None
    for pair in credentials:
        for name, ref in pair.items():
            span = spans[ref]
            facts[name] = {**span, 'kind': 'credential', 'reference': ref}
    for ref, span in spans.items():
        if span['type'] != 'date':
            continue
        label = span.get('label', '')
        if re.search(r'\b(?:system\s+clock|current\s+(?:date|time)|today)\b', label, re.I):
            clock = dates_in(str(span['value']))[0]
        else:
            facts.setdefault('request_date', {**span, 'kind': 'default', 'reference': ref})
    for key, value in raw.items() if isinstance(raw, dict) else []:
        if isinstance(value, (bool, int, float)) or (isinstance(value, str) and len(value.split()) == 1):
            facts[str(key)] = {'value': value, 'kind': 'default', 'quote': str(value), 'source': str(key)}
    unresolved = ['System clock is unknown'] if clock is None else []
    if limited:
        unresolved.append('Context span budget exceeded')
    return {'facts': facts, 'clock': clock, 'unresolved': unresolved, 'raw': deepcopy(raw),
            'choice_rules': choice_rules(raw)}


class ContractIndex:
    def __init__(self, project, frontend):
        self.project, self.frontend = project, frontend
        self.contracts, docs, extra_docs = {}, {}, {}
        for mid, verb, route in project.ix.handlers:
            sites = []
            for site in frontend.sites.values():
                if mid not in site['handlers']:
                    continue
                for number, case in enumerate(site.get('url_cases', [{'handlers': site['handlers'], 'url': site['url'], 'conditions': []}])):
                    if mid in case['handlers']:
                        sites.append({**site, **case, 'base_id': site['id'], 'id': site['id'] + ':url' + str(number)})
            sites = sites or [None]
            for site in sites:
                key = mid + '|' + (site['id'] if site else '')
                name = project.methods[mid]['name']
                owner = project.nodes[project.methods[mid]['owner']]['fqn'].split('.')[-1]
                ui_name = PurePosixPath(site['file']).stem if site else ''
                primary = tokens(name + ' ' + owner + ' ' + ' '.join(route)
                                 + ' ' + (site.get('action_label', '') if site else '') + ' ' + ui_name)
                ui_fields = {**site['body_fields'], **site.get('conditional_fields', {})} if site else {}
                source = text(project.ast.get(mid))[:1800]
                ui = (site['source'][:1000] + ' ' + site['file']) if site else ''
                docs[key] = primary + tokens(' '.join(project.request_fields(mid)))
                extra_docs[key] = tokens(source) + tokens(ui)
                actual_intent = intent(site.get('action_label', '')) if site else None
                if actual_intent is None:
                    actual_intent = intent(name)
                if actual_intent is None and site:
                    nouns = set(tokens(owner + ' ' + ' '.join(route)))
                    hints = {i for word in tokens(ui_name) if word not in nouns for i, group in enumerate(VERBS) if word in group}
                    actual_intent = next(iter(hints)) if len(hints) == 1 else None
                self.contracts[key] = {'entry': mid, 'site': site, 'verb': verb,
                                       'route': route, 'primary': primary,
                                       'intent': actual_intent,
                                       'operation_words': set(tokens(name)),
                                       'input_entities': [entity_words(p['type']) for p in project.http_parameters(mid)
                                                          if p['kind'] == 'RequestBody' and project.resolve_type(p['type'], project.methods[mid]['module'], project.methods[mid]['file']) in project.type_fields],
                                       'result_collection': bool(re.search(r'\b(?:List|Collection|Set|Iterable|Page|Slice)\s*<|\[\]', project.methods[mid].get('return_raw', ''))),
                                       'required_paths': [p['name'] for p in project.http_parameters(mid) if p['kind'] == 'PathVariable' and p['required']],
                                       'ui_inputs': set(tokens(' '.join(ui_fields))),
                                       'ui_action': set(tokens((site.get('action_label', '') + ' ' + ui_name) if site else '')),
                                       'result_entities': [entity_words(typ) for typ in re.findall(r'[\w.]+', project.methods[mid].get('return_raw', ''))
                                                           if project.resolve_type(typ, project.methods[mid]['module']) in project.type_fields]}
        self.bm25 = BM25(docs)
        self.extra = BM25(extra_docs)

    def rank(self, action, active_page=None):
        # Weight the direct object before qualifications about related entities.
        action = re.sub(r'^as\b.*?,\s*|^(?:try\s+to|please)\s+', '', action, flags=re.I)
        focus = re.split(r'\b(?:for|with|without|from|departing|filtered|on|onto)\b', action, 1, flags=re.I)[0]
        focus = re.sub(r'\([^)]*\)', ' ', focus)
        if re.match(r'^(?:open|view|show|inspect|read)\b', focus, re.I) and re.search(r'\bdetails?\b', focus, re.I):
            focus = re.sub(r'\b(?:cheapest|quickest|newest|oldest|latest)\b', '', focus, flags=re.I)
        query = tokens(focus)
        wanted = intent(action)
        verb_words = {word for group in VERBS for word in group}
        objects = [word for word in query if word not in verb_words]
        object_words = set(objects) - {'all', 'detail', 'first', 'second', 'third', 'new'}
        roles = language_roles(action)
        base = dict((key, score) for score, key in self.bm25.rank(query))
        extra = dict((key, score) for score, key in self.extra.rank(tokens(action)))
        result = []
        collection_action = wanted == 0 and bool(re.search(r'\b(?:list|all|browse)\b', action, re.I))
        for key in set(base) | set(extra):
            contract = self.contracts[key]
            score = base.get(key, 0) + 0.15 * extra.get(key, 0)
            primary = set(contract['primary'])
            score += 2 * sum(self.bm25.idf.get(word, 0) for word in objects if word in primary)
            actual = contract['intent']
            if wanted is not None:
                score *= 1.8 if actual == wanted else 0.12 if actual is not None else 0.6
            elif query:
                score *= 2 if query[0] in primary else 0.35
            if wanted is None and query and query[0] in contract['operation_words']:
                score *= 2
            if contract['site']:
                fields = set(self.project.request_fields(contract['entry']))
                coverage = len(fields & set(contract['site']['body_fields'])) / max(1, len(fields))
                score *= 1.15 + 0.15 * coverage
                if query and query[0] in contract['ui_action'] and query[0] not in {'add', 'create', 'insert', 'register', 'save'} and object_words & contract['ui_inputs']:
                    score *= 2
                if wanted == 1 and active_page == contract['site']['page'] and actual == wanted:
                    score *= 1.5
                option_matches = [o for o in contract['site']['options'] if option_label_matches(o['label'], action)]
                if option_matches:
                    score *= 2
            entities = contract['result_entities']
            if entities and object_words:
                # A compound return type adds an entity qualifier. Repeated
                # lexical matches cannot turn PetType into the entity Pet.
                factors = [(0.5 + 1.5 * len(entity & object_words) / max(1, len(entity | object_words)))
                           / (1 + 3 * len(entity - object_words)) for entity in entities if entity]
                if factors:
                    score *= max(factors)
            if collection_action and contract['result_collection']:
                score *= 2.5
                action_words = set(tokens(action))
                missing_paths = [name for name in contract['required_paths']
                                 if not {word for word in tokens(name) if not word.startswith('prefix')} <= action_words]
                contract = {**contract, 'unmentioned_paths': missing_paths}
            if roles:
                site_fields = (contract['site'] or {}).get('body_fields', {})
                supported = {field_role(key, site_fields.get(key, '')) for key in self.project.request_fields(contract['entry'])}
                score *= 0.25 + 1.5 * len(roles.keys() & supported) / len(roles)
            result.append((score, key, contract))
        if query and query[0] in ('add', 'create', 'insert') and object_words:
            direct = lambda contract: any(entity and entity <= object_words for entity in contract['input_entities'])
            if any(direct(contract) for _, _, contract in result):
                result = [(score * (2 if direct(contract) else 0.5), key, contract) for score, key, contract in result]
        if collection_action:
            # An unqualified list has a source-compatible collection endpoint.
            # A filtered endpoint for that SAME entity must not win solely for
            # repeating the lexical verb "list" in its method name.
            compatible = {}
            for score, _, contract in result:
                if contract['result_collection'] and not contract.get('unmentioned_paths'):
                    for entity in contract['result_entities']:
                        if entity:
                            identity = frozenset(entity)
                            compatible[identity] = max(score, compatible.get(identity, 0))
            adjusted = []
            for score, key, contract in result:
                bounds = [compatible[frozenset(entity)] for entity in contract['result_entities']
                          if contract.get('unmentioned_paths') and frozenset(entity) in compatible]
                adjusted.append((min(score, max(bounds)) if bounds else score, key, contract))
            result = adjusted
        return sorted(result, key=lambda item: (-item[0], bool(item[2].get('unmentioned_paths')), item[1]))

    def candidates(self, action, limit=6):
        return list(dict.fromkeys(c['entry'] for _, _, c in self.rank(action)))[:limit]


def explicit_value(action, key, typ):
    if typ.split('.')[-1] in ('byte', 'Byte', 'short', 'Short', 'int', 'Integer', 'long', 'Long', 'float', 'Float', 'double', 'Double'):
        return literal_value(action, key, typ)
    words = re.findall(r'[a-z0-9]+', re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', key).lower())
    label = r'[ _-]*'.join(re.escape(word) for word in words)
    # Match field labels, never positional bare numbers that could be dates or ordinals.
    patterns = [r'\b' + re.escape(key) + r'\b\s*(?:is|=|:)?\s*[\"\']([^\"\']+)[\"\']'] if label else []
    if label:
        connector = r'(?:is|=|:)' if typ.split('.')[-1] in ('String', 'UUID') else r'(?:is|of|=|:)?'
        patterns.append(r'\b' + label + r'\b\s*' + connector + r'\s*([\w@.+-]+)')
    for pattern in patterns:
        match = re.search(pattern, action, re.I)
        if match and match[1].lower() not in {'and', 'or', 'with', 'of', 'for', 'to', 'from'}:
            value = Engine.coerce(match[1], typ)
            if typ.split('.')[-1] in ('String', 'UUID') or value is not U:
                return value, match[0]
    if typ.split('.')[-1] in ('boolean', 'Boolean'):
        field = r'\b' + label + r'\b'
        for match in re.finditer(field, action, re.I):
            before = action[max(0, match.start() - 24):match.start()]
            if re.search(r'\b(?:without|no|not|disable)\s*$', before, re.I):
                return False, before + match[0]
            after = action[match.end():match.end() + 16]
            if re.match(r'\s*(?:is\s+)?(?:false|disabled)\b', after, re.I):
                return False, match[0] + after
            if re.search(r'\b(?:with|enable)\s*$', before, re.I) or re.match(r'\s*(?:is\s+)?(?:true|enabled)\b', after, re.I):
                return True, before + match[0] + after
    return U, ''


class ContractGrounder:
    def __init__(self, project, frontend, retrieval, parser, context):
        self.project, self.frontend, self.index, self.context = project, frontend, retrieval, context

    def step(self, action, state, scenario_text='', prepared_proposal=None):
        ranked = self.index.rank(action, state.browser.get('active_page'))
        candidates = [c['entry'] for _, _, c in ranked[:6]]
        detail = {'candidates': candidates, 'ranking': [
            {'entry': c['entry'], 'ui_site': c['site']['id'] if c['site'] else None, 'score': score}
            for score, _, c in ranked[:6]], 'proposal': {'hypotheses': []}, 'unresolved': []}
        detail['grounding_status'] = 'lexical_hypothesis'
        detail['certainty_note'] = 'Graph certainty is conditional on the selected source contract and validated bindings'
        if not ranked:
            detail['unresolved'] = ['No lexical evidence for a source request']
            return [], detail
        visited = set()
        for score, _, contract in ranked:
            site = contract['site']
            group = site.get('base_id') if site else None
            if group and group in visited:
                continue
            if group:
                visited.add(group)
            related = [(score, contract)]
            if site and site.get('conditions'):
                related = [(s, c) for s, _, c in ranked if c['site'] and c['site'].get('base_id') == group]
            proposals = []
            for candidate_score, candidate in related:
                proposal = self._bind(action, state, candidate, candidate_score)
                candidate_site = candidate['site']
                conditions = (candidate_site or {}).get('conditions', [])
                env = dict((proposal['site'] or {}).get('event_values', {}))
                if candidate_site and candidate_site.get('body_owner'):
                    env[candidate_site['body_owner']] = proposal['params']
                guards = [self.frontend.evaluate(c, proposal['state'], env, candidate_site['definitions']) for c in conditions]
                if any(g is False for g in guards):
                    continue
                if any(g is not True for g in guards):
                    proposal['unresolved'].append('Unknown UI request guard: ' + candidate_site['id'])
                proposals.append(proposal)
            if proposals:
                return proposals, detail
        detail['unresolved'].append('No request with a satisfiable source UI guard')
        return [], detail

    def _bind(self, action, state, contract, score):
        mid, site = contract['entry'], contract['site']
        path_state = deepcopy(state)
        fields = self.project.request_fields(mid)
        params, bindings = {}, {}

        def bind(key, value, source, reference, quote=''):
            if value is not U:
                canonical = canonical_reference(self.project, mid, key, value, path_state.database)
                if canonical:
                    quote, value, reference, source = quote or value, canonical[0], canonical[1], 'state'
                if fields[key].split('.')[-1] == 'String' and isinstance(value, dict) and '__symbol__' not in value:
                    value = source_string(self.project, value)
                    reference += ':source-toString'
                coerced = Engine.coerce(deepcopy(value), fields[key])
                if coerced is U:
                    return
                params[key] = coerced
                bindings[key] = {'source': source, 'reference': reference, 'quote': quote,
                                 'resolved': not contains_unknown(params[key])}

        if site:
            self.frontend.enter(site, path_state)
            event_values, event_reference = self.frontend.event_values(site, action, path_state)
            site = {**site, 'event_values': event_values, 'event_reference': event_reference}
            self.frontend.apply_absence(site, fields, action, path_state)
            expressions = ' '.join([*site['definitions'].values(), *site['body_fields'].values(), *site.get('conditional_fields', {}).values()])
            for _, selector, _ in re.findall(r'\$\(\s*([\"\'])([^\"\']+)\1\s*\)\.is\(\s*([\"\']):checked\3\s*\)', expressions):
                polarity = control_polarity(action, selector)
                if polarity is not None:
                    path_state.browser['dom'][selector.strip() + ':checked'] = polarity
            choices = {}
            for option in site['options']:
                label = set(tokens(option['label'])) if isinstance(option['label'], str) else set()
                if label and option_label_matches(option['label'], action) and option.get('space') == 'form':
                    choices.setdefault(option['control'], []).append(option['value'])
            for control, values in choices.items():
                if len(values) == 1:
                    path_state.browser['form'][control] = values[0]
            for key, expression in {**site['body_fields'], **site.get('conditional_fields', {})}.items():
                if key in fields:
                    value = self.frontend.evaluate(expression, path_state, extra=site['event_values'], definitions=site['definitions'])
                    if value is JS_UNDEFINED:
                        defaults = self.project.request_body_defaults(mid)
                        if key in defaults:
                            bind(key, defaults[key], 'code', site['id'] + ':omitted-undefined-property')
                    else:
                        bind(key, value, 'ui', site['id'] + ':' + expression +
                             (';row=' + site['event_reference'] if site['event_reference'] else ''))
            if site.get('body_complete') or site.get('body_keys_complete'):
                for key, value in self.project.request_body_defaults(mid).items():
                    if key not in site['body_fields'] and key not in site.get('conditional_fields', {}) and key in fields:
                        bind(key, value, 'code', mid + ':omitted-json-property')
            for parameter in self.project.http_parameters(mid):
                if parameter['kind'] == 'RequestBody' and parameter['type'].split('.')[-1] == 'String' and site.get('stringified'):
                    body = {key: self.frontend.evaluate(expr, path_state, extra=site['event_values'], definitions=site['definitions'])
                            for key, expr in {**site['body_fields'], **site.get('conditional_fields', {})}.items()}
                    key = parameter['name']
                    params[key] = {'__json__': json_value(body) if site.get('body_complete') or site.get('body_keys_complete') else U}
                    bindings[key] = {'source': 'ui', 'reference': site['id'] + ':JSON.stringify',
                                     'quote': '', 'resolved': not contains_unknown(params[key])}
            for key, value in partial_url_parameters(self.frontend, mid, site, path_state).items():
                if key in fields:
                    bind(key, value, 'ui', site['id'] + ':url')
        structured_inputs = structured_bindings(self.project, mid, action)
        for key, typ in fields.items():
            value, quote = explicit_value(action, key, typ)
            structured = structured_inputs.get(key)
            if structured:
                bind(key, structured[0], 'literal', structured[1], structured[2])
                continue
            if value is U:
                for parameter in self.project.http_parameters(mid):
                    if parameter['name'] == key and parameter['wire_name'] != key:
                        value, quote = explicit_value(action, parameter['wire_name'], typ)
                        if value is not U:
                            break
            roles = language_roles(action)
            expression = (site or {}).get('body_fields', {}).get(key, '')
            role = field_role(key, expression)
            if role is None and key == intermediate_field(fields):
                role = 'via'
            if value is U and role in roles:
                value, quote = canonical_ui_literal(roles[role], site), roles[role]
            date_fields = [name for name in fields if set(tokens(name)) & {'date', 'time'}]
            if value is U and len(date_fields) == 1 and key in date_fields:
                dates = dates_in(action)
                if dates:
                    value, quote = dates[0].isoformat(), action
            if value is U and (intent(action) == 1 or 'weight' in tokens(key)):
                value, quote = introduced_value(self.project, mid, key, action)
            enum_value = enum_scalar_binding(self.project, mid, key, action) if value is U else None
            if value is U and enum_value is None and site:
                producers = self.frontend.option_producers(site, key)
                if len(producers) == 1:
                    producer, fact = producers[0]
                    enum_value = enum_ordinal_binding(self.project, mid, key, action,
                                                     producer['handlers'], fact['value_field'])
            if enum_value:
                value, reference, _ = enum_value
                bind(key, value, 'code', reference, action)
                continue
            if value is U and intent(action) == 1 and key not in params and key in generated_omissions(self.project, mid):
                provided = site and key in {**site['body_fields'], **site.get('conditional_fields', {})}
                label = r'[ _-]*'.join(re.findall(r'[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+', key))
                if not provided and not re.search(r'\b' + label + r'\b', action, re.I):
                    bind(key, None, 'code', generated_omissions(self.project, mid)[key], 'Optional identifier generated when omitted')
                    continue
            if value is not U:
                bind(key, value, 'literal', 'action', quote)
                continue
            absence = absent_field(self.context.get('raw', {}), key)
            if absence and typ.split('.')[-1] in ('String', 'boolean', 'Boolean'):
                bind(key, '' if typ.split('.')[-1] == 'String' else False,
                     'context', absence[0], absence[1])
                continue
            for name, fact in self.context['facts'].items():
                if normalized(name) == normalized(key):
                    if fact['kind'] == 'credential' and re.search(r'\bnew\b', action, re.I):
                        if intent(action) == 1:
                            value = path_state.fresh_input(key, typ)
                            if 'password' in normalized(key):
                                value['__constraints__'] = ['non_null']
                                value.pop('__distinct_from__', None)
                                value.pop('__distinct_symbols__', None)
                            bind(key, value, 'fresh', 'action', action)
                        else:
                            # Explicit new credentials cannot refer to the pre-existing account.
                            for i in range(len(state.history) - 1, -1, -1):
                                history_refs = references(state.history[i]['result'], 'history[' + str(i) + '].result')
                                matching = [(ref, val) for ref, val in history_refs.items()
                                            if normalized(ref.rsplit('.', 1)[-1]) == normalized(key) and val is not U]
                                if len(matching) == 1:
                                    bind(key, matching[0][1], 'history', matching[0][0])
                                    break
                        continue
                    bind(key, fact['value'], 'context', name, fact.get('quote', ''))
            if key in params and not contains_unknown(params[key]):
                if not (params[key] == '' and intent(action) != 1 and (key.lower().endswith('id') or key in ('id', 'key'))):
                    continue
            date_fields = [name for name in fields if set(tokens(name)) & {'date', 'time'}]
            if len(date_fields) == 1 and key in date_fields:
                dates = dates_in(action)
                if dates:
                    exact = next(m[0] for m in re.finditer(r'\b\d{4}-\d\d-\d\d(?:[ T]\d\d:\d\d(?::\d\d)?)?|\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b', action)
                                 if dates_in(m[0]))
                    bind(key, dates[0].isoformat(), 'literal', 'action', exact)
                elif ('request_date' in self.context['facts']
                      and set(ntoks(key)) <= {'date', 'time', 'departure', 'depart', 'travel', 'request'}):
                    bind(key, self.context['facts']['request_date']['value'], 'context', 'request_date')
            target = self.project.resolve_type(typ, self.project.methods[mid]['module'])
            enum = self.project.enum_members.get(target, [])
            matches = [e for e in enum if set(tokens(e.rsplit('.', 1)[-1])) <= set(tokens(action))]
            if len(matches) == 1:
                bind(key, self.project.enum_objects.get(matches[0], U), 'code', matches[0])
            # UI options keep the association to their actual form field.
            if site and key in {**site['body_fields'], **site.get('conditional_fields', {})}:
                expression = {**site['body_fields'], **site.get('conditional_fields', {})}[key]
                options = []
                controls = self.frontend.input_controls(expression, site['definitions'])
                for option in site['options']:
                    space = 'form' if option.get('space') == 'form' else 'dom'
                    associated = option['control'].lstrip('#') in controls[space]
                    label_words = set(tokens(option['label'])) if isinstance(option['label'], str) else set()
                    negative_option = bool(re.match(r'^\s*no\b', option['label'], re.I)) or option['label'].lower() in ('none', 'off', 'disabled')
                    literal_match = not negative_option and label_words and option_label_matches(option['label'], action)
                    negative_match = negative_option and control_polarity(action, key.replace('Type', '').replace('Mode', '')) is False
                    if associated and (literal_match or negative_match):
                        options.append(option)
                if len(options) == 1:
                    option = options[0]
                    control = option['control']
                    if option.get('space') == 'form':
                        path_state.browser['form'][control] = option['value']
                    else:
                        path_state.browser['dom'][control if control.startswith(('#', '.')) else '#' + control] = option['value']
                    computed = self.frontend.evaluate(expression, path_state, extra=site['event_values'], definitions=site['definitions'])
                    bind(key, computed, 'ui', site['id'] + ':option-expression', option['label'])
            if key in params and not contains_unknown(params[key]):
                if not (params[key] == '' and intent(action) != 1 and (key.lower().endswith('id') or key in ('id', 'key'))):
                    continue
                if bindings.get(key, {}).get('source') == 'ui':
                    params.pop(key)
                    bindings[key]['resolved'] = False
            previous = history_value(self.project, mid, key, action, state.history)
            if previous:
                bind(key, previous[1], 'history', previous[0])
        for key in fields:
            if key not in params or contains_unknown(params[key]) or params[key] == '':
                selected = selected_field(self.project, key, params, state.history, mid)
                if selected:
                    bind(key, selected[1], 'history', selected[0])
                carried = history_role_value(self.project, key, params, state.history)
                if carried:
                    bind(key, carried[1], 'history', carried[0])
        for key, (value, reference, quote) in default_choices(
                self.project, mid, fields, action, state.history,
                self.context.get('choice_rules', []), params).items():
            if key not in params or contains_unknown(params[key]):
                bind(key, value, 'context+history', reference, quote)
        lowered_filters = filter_bindings(self.project, mid, action, path_state.now)
        for key, value, reference, quote in lowered_filters:
            if key not in fields:
                continue
            if value is U:
                params.pop(key, None)
                bindings[key] = {'source': 'code', 'reference': reference, 'quote': quote, 'resolved': False}
            else:
                bind(key, value, 'code', reference, quote)
        preparation = []
        if site:
            edited, excluded = unfilled_form_edits(self.frontend, site, action, bindings)
            for control in excluded:
                path_state.browser['form'][control] = U
            for key in edited:
                params.pop(key, None)
                bindings[key] = {'source':'action', 'reference':'action:unspecified-new-value',
                                 'quote':action, 'resolved':False}
            expressions = {**site['body_fields'], **site.get('conditional_fields', {})}
            pending = {key for key in fields if key not in edited and
                       (key not in params or contains_unknown(params[key]) or
                        params[key] == '' and bindings.get(key, {}).get('source') == 'ui')}
            for key, expression in expressions.items():
                if key not in pending:
                    excluded.update(self.frontend.input_controls(expression, site['definitions'])['form'])
            anchors = {key:value for key,value in params.items() if bindings.get(key, {}).get('resolved')
                       and bindings[key]['source'] not in ('ui','ui_projection')}
            projections = self.frontend.projected_form_values(site, mid, action, path_state, anchors, excluded)
            if projections:
                for control, (value, _) in projections.items():
                    path_state.browser['form'][control] = deepcopy(value)
                for key in pending & expressions.keys():
                    expression = expressions[key]
                    controls = self.frontend.input_controls(expression, site['definitions'])['form'] & projections.keys()
                    if controls:
                        value = self.frontend.evaluate(expression, path_state, site['event_values'], site['definitions'])
                        refs = sorted({projections[control][1] for control in controls})
                        bind(key, value, 'ui_projection', ';'.join(refs))
                        if key in params and bindings[key].get('resolved'):
                            preparation.extend(refs)
        problems = ['Unknown input: ' + key for key, typ in fields.items()
                    if (key not in params or contains_unknown(params[key])) and 'Header' not in typ]
        if re.search(r'\bfilter(?:ed)?\b', action, re.I) and not lowered_filters:
            problems.append('Unsupported request filter: ' + action)
        if preparation:
            problems.append('Inferred row-to-form preparation; event execution is unobserved: ' + ';'.join(sorted(set(preparation))))
        if site:
            for key, value in params.items():
                binding = bindings.get(key, {})
                expression = site['body_fields'].get(key)
                if expression and binding.get('resolved') and binding.get('source') != 'ui':
                    self.frontend.update_input(expression, value, path_state)
        return {'entry': mid, 'site': site, 'state': path_state, 'params': params, 'bindings': bindings,
                'reason': 'Highest weighted source/UI contract score: ' + str(score), 'unresolved': problems}
