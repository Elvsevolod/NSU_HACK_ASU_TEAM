"""Deterministic source-contract retrieval and evidence-bearing request bindings."""
from copy import deepcopy
from pathlib import PurePosixPath
import json
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
from .frontend import json_value, truth
from .java_collections import JsonText
from .scenario_literals import structured_bindings, canonical_reference
from .structured_literals import literal_value
from .context_choices import choice_rules, default_choices
from .units import mass_binding
from .models import http_headers_type
from .request_inputs import RequestInputs
from .bean_properties import default_bean_plan


STOP = set('the a an all any some with without and or for of to from on in by this that their they first new one '
           'controller service api http org springframework request response java string'.split())
# Language-level synonyms only; project entities, routes and enum values come from source.
VERBS = [set('get find query lookup search read view open show list refresh inspect fetch'.split()),
         set('create add insert register save book reserve buy purchase'.split()),
         set('delete remove erase'.split()), set('update modify change edit amend alter revise replace rename'.split()),
         set('login signin authenticate'.split()), set('pay charge settle'.split())]
VERBS[0].update(('check', 'browse', 'look', 'ask', 'calculate', 'compute', 'estimate'))


def tokens(value):
    words = ntoks(re.sub(r'\blog\s+in\b', 'login', str(value), flags=re.I))
    extrema={'fewest':'min','minimum':'min','minimal':'min','least':'min',
             'most':'max','maximum':'max','maximal':'max'}
    words=[extrema.get(word,word) for word in words]
    output = [word for word in words if word not in STOP]
    output += ['prefix' + word[:6] for word in output if len(word) >= 7]
    return output


def intent(value):
    value = re.sub(r'^as\b.*?,\s*|^(?:try\s+to|please)\s+', '', value, flags=re.I)
    words = tokens(value)
    return next((i for i, group in enumerate(VERBS) if words and words[0] in group), None)


def normalized(value):
    return re.sub(r'[^a-z0-9]', '', value.lower())


def date_input(value,quote,typ):
    # A calendar date in the supplied text does not supply a time of day.
    return value.date().isoformat() if typ.split('.')[-1]=='String' and not re.search(r'\d{1,2}:\d{2}',quote) else value.isoformat()


def option_label_matches(label, action):
    if control_polarity(action,label) is False:
        return False
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
            if not project.enabled_type(project.methods[mid]['owner']):
                continue
            sites = []
            for site in frontend.sites.values():
                if mid not in site['handlers']:
                    continue
                for number, case in enumerate(site.get('url_cases', [{'handlers': site['handlers'], 'url': site['url'], 'conditions': []}])):
                    if mid in case['handlers']:
                        sites.append({**site, **case, 'base_id': site['id'], 'id': site['id'] + ':url' + str(number)})
            sites = sites or [None]
            for site in sites:
                from .result_contracts import result_shape
                result_types,result_collection=result_shape(project,mid)
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
                                       'owner_entity':entity_words(owner),
                                       'operation_words': set(tokens(name)),
                                       'input_entities': [entity_words(p['type']) for p in project.http_parameters(mid)
                                                          if p['kind'] == 'RequestBody' and project.resolve_type(p['type'], project.methods[mid]['module'], project.methods[mid]['file']) in project.type_fields],
                                       'result_collection':bool(re.search(r'\b(?:List|Collection|Set|Iterable|Page|Slice)\s*<|\[\]', project.methods[mid].get('return_raw', ''))),
                                       'inferred_result_collection':result_collection,
                                       'required_paths': [p['name'] for p in project.http_parameters(mid) if p['kind'] == 'PathVariable' and p['required']],
                                       'ui_inputs': set(tokens(' '.join(ui_fields))),
                                       'ui_action': set(tokens((site.get('action_label', '') + ' ' + ui_name) if site else '')),
                                       'result_entities':[entity_words(typ) for typ in re.findall(r'[\w.]+',project.methods[mid].get('return_raw','')) if project.resolve_type(typ,project.methods[mid]['module']) in project.type_fields],
                                       'inferred_result_entities':[entity_words(typ) for typ in sorted(result_types)]}
        self.bm25 = BM25(docs)
        self.extra = BM25(extra_docs)

    def rank(self, action, active_page=None, scenario_text=''):
        # Weight the direct object before qualifications about related entities.
        from .actors import actor_role, declared_roles
        actor = actor_role(action)
        action = re.sub(r'^as\b.*?,\s*|^(?:try\s+to|please)\s+', '', action, flags=re.I)
        focus = re.split(r'\b(?:for|with|without|from|departing|filtered|on|onto)\b', action, 1, flags=re.I)[0]
        if re.search(r'\b(?:record|instance|entry|details?)\s+of\b',focus,re.I):
            focus=re.split(r'\bof\b',focus,1,flags=re.I)[0]
        focus = re.sub(r'\([^)]*\)', ' ', focus)
        if re.match(r'^(?:open|view|show|inspect|read)\b', focus, re.I) and re.search(r'\bdetails?\b', focus, re.I):
            focus = re.sub(r'\b(?:cheapest|quickest|newest|oldest|latest)\b', '', focus, flags=re.I)
        query = tokens(focus)
        wanted = intent(action)
        verb_words = {word for group in VERBS for word in group}
        objects = [word for word in query if word not in verb_words]
        object_words = set(objects) - {'all', 'detail', 'first', 'second', 'third', 'new'}
        named = {frozenset(c['owner_entity']) for c in self.contracts.values() if c['owner_entity']}
        explicit = {entity for entity in named if entity <= object_words}
        contextual = {entity for entity in named if entity <= set(tokens(scenario_text))}
        contextual = contextual if len(contextual)==1 and not explicit else set()
        roles = language_roles(action)
        base = dict((key, score) for score, key in self.bm25.rank(query))
        extra = dict((key, score) for score, key in self.extra.rank(tokens(action)))
        result = []
        collection_action = wanted == 0 and bool(re.search(r'\b(?:list|all|browse)\b', action, re.I))
        use_payload_contract=(wanted==0 and not collection_action and bool(re.match(r'^(?:look\s+up|find|read|get|inspect|view|show|open)\b',action,re.I)))
        reference_matches=set()
        for key in set(base) | set(extra):
            contract = self.contracts[key]
            allowed_roles = declared_roles(self.project, contract['entry'])
            if actor is not U and allowed_roles and actor not in allowed_roles:
                continue
            score = base.get(key, 0) + 0.15 * extra.get(key, 0)
            if frozenset(contract['owner_entity']) in contextual:
                score *= 4
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
            entities = contract['inferred_result_entities'] if use_payload_contract else contract['result_entities']
            qualifier=re.split(r'\b(?:of|for)\b',action,1,flags=re.I)
            if use_payload_contract and len(qualifier)==2:
                reference_words=set(ntoks(qualifier[1]))
                parameter_entities=[entity_words(name) for name in contract['required_paths'] if entity_words(name)]
                by_name=re.search(r'By([A-Z][\w]*?)(?:Id|$)',self.project.methods[contract['entry']]['name'])
                if by_name and entity_words(by_name[1]):parameter_entities.append(entity_words(by_name[1]))
                if any(entity<=reference_words for entity in parameter_entities):
                    score*=1.5
                    reference_matches.add(key)
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
        # A source-proven payload satisfying the requested entity is stronger
        # than an untyped lexical match. Keep uncertainty explicit if no such
        # payload proof exists.
        semantic_words=lambda items:{word[:-4] if word.endswith('ment') and len(word)>7 else word for word in items}
        desired=semantic_words(object_words)-{'record','detail','bean','result'}
        def payload_match(contract):
            return any(semantic_words(entity)-{'record','bean'} and
                semantic_words(entity)-{'record','bean'} <= desired for entity in contract['inferred_result_entities'])
        if use_payload_contract and desired and any(payload_match(contract) for _,_,contract in result):
            result=[(score if payload_match(contract) else score*0.08,key,contract) for score,key,contract in result]
            # A stated related entity selects its source reference parameter,
            # rather than the returned record's own identifier. Lexical score
            # cannot reverse this distinction between two equal payloads.
            if any(key in reference_matches and payload_match(contract) for _,key,contract in result):
                result=[(score if key in reference_matches or not payload_match(contract) else score*0.08,key,contract)
                        for score,key,contract in result]
        return sorted(result, key=lambda item: (-item[0], bool(item[2].get('unmentioned_paths')), item[1]))

    def candidates(self, action, limit=6):
        return list(dict.fromkeys(c['entry'] for _, _, c in self.rank(action)))[:limit]


def explicit_value(action, key, typ, raw=False):
    if raw:
        typ = 'String'
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
            value = match[1] if raw else Engine.coerce(match[1], typ)
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
        explicit = self.explicit_request(action, state)
        if explicit is not None:
            return explicit
        ranked = self.index.rank(action, state.browser.get('active_page'), scenario_text)
        candidates = [c['entry'] for _, _, c in ranked[:6]]
        detail = {'candidates': candidates, 'ranking': [
            {'entry': c['entry'], 'ui_site': c['site']['id'] if c['site'] else None, 'score': score}
            for score, _, c in ranked[:6]], 'proposal': {'hypotheses': []}, 'unresolved': []}
        detail['grounding_status'] = 'lexical_hypothesis'
        detail['certainty_note'] = 'Graph certainty is conditional on the selected source contract and validated bindings'
        if not ranked:
            detail['unresolved'] = ['No lexical evidence for a source request']
            return [], detail
        ambiguous=self.identity_ambiguity(action,state,ranked)
        if ambiguous:
            detail['grounding_status']='unresolved_semantic_ambiguity'
            detail['semantic_candidates']=ambiguous
            detail['unresolved']=['Unqualified entity lookup does not choose between current principal and named identity']
            return [],detail
        visited = set()
        blocked = None
        for score, _, contract in ranked:
            site = contract['site']
            if blocked and contract['entry'] != blocked['entry']:
                same_scope = site and site.get('file') == blocked['file'] and site.get('action_scope') == blocked['scope']
                if not same_scope or not blocked['selectors']:
                    continue
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
                guards = [truth(self.frontend.evaluate(c, proposal['state'], env, candidate_site['definitions'])) for c in conditions]
                if any(g is False for g in guards):
                    continue
                if any(g is not True for g in guards):
                    proposal['unresolved'].append('Unknown UI request guard: ' + candidate_site['id'])
                if proposal.get('wire_conflicts'):
                    # The selected source UI cannot express this grounded
                    # action. Use an explicitly diagnosed direct HTTP
                    # hypothesis; never claim that UI sent the missing field.
                    direct=self._bind(action,state,{**candidate,'site':None},candidate_score)
                    direct['unresolved'].append('Selected UI omits required grounded fields; direct HTTP hypothesis: '+
                        ','.join(proposal['wire_conflicts'])+' at '+candidate_site['id'])
                    proposals.append(direct)
                    continue
                proposals.append(proposal)
            if proposals:
                if blocked:
                    for proposal in proposals:
                        proposal['unresolved'].append('Source selector conflict or alternate UI path after blocked request: '+blocked['site'])
                from .actors import actor_role
                for proposal in proposals:
                    proposal['actor'] = actor_role(action)
                # Equal-scored endpoints are an ambiguity, not a lexical win.
                tied = [candidate for candidate_score, _, candidate in ranked
                        if abs(candidate_score-score) < 1e-9 and candidate['entry'] != contract['entry']]
                for candidate in tied:
                    if candidate['site'] is None:
                        alternative = self._bind(action, state, candidate, score)
                        alternative['actor'] = actor_role(action)
                        proposals.append(alternative)
                if tied:
                    detail['unresolved'].append('Ambiguous equally ranked source endpoints')
                    for proposal in proposals:
                        proposal['unresolved'].append('Ambiguous equally ranked source endpoints')
                return proposals, detail
            if site and site.get('conditions'):
                if blocked is None:
                    blocked = {'entry':contract['entry'],'site':site['id'],'file':site['file'],
                               'scope':site.get('action_scope'),'selectors':proposal.get('ui_selectors',{})}
                    detail['blocked_by_known_ui_guard'] = site['id']
        if blocked:
            detail['unresolved'].append('Selected source request blocked by known UI guard: '+blocked['site'])
        detail['unresolved'].append('No request with a satisfiable source UI guard')
        return [], detail

    def identity_ambiguity(self,action,state,ranked):
        """Two source identity contracts need a qualifier, even with unequal scores."""
        if intent(action)!=0 or state.history or self.context.get('facts') or state.browser.get('active_page'):
            return []
        words=set(tokens(action))-{word for group in VERBS for word in group}-{'up'}
        words={word for word in words if not word.startswith('prefix')}
        choices=[];kinds=set()
        for _,_,contract in ranked[:6]:
            if contract['site'] or contract['verb']!='GET' or contract['owner_entity']!=words:
                continue
            if not any(entity==words for entity in contract['inferred_result_entities']):
                continue
            parameters=self.project.http_parameters(contract['entry'])
            principal=any(p['type'].rsplit('.',1)[-1]=='Principal' for p in parameters)
            named=any(p['kind']=='PathVariable' for p in parameters)
            if principal or named:
                kinds.add('principal' if principal else 'named')
                choices.append(contract['entry'])
        return sorted(set(choices)) if kinds=={'principal','named'} else []

    def explicit_request(self, action, state):
        from .request import Request, MISSING
        match = re.match(r'^\s*(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(\S+)(?:\s*\n([\s\S]*))?\s*$', action, re.I)
        if not match:
            return None
        body = MISSING
        if match[3]:
            try:body = json.loads(match[3])
            except ValueError:return [], {'proposal': None, 'candidates': [], 'unresolved': ['Invalid explicit request JSON body']}
        address = Engine.request_address(match[2])
        handlers = self.project.ix.handlers_for(match[1].upper(), address['segments'], address['hostname']) if address and address['segments'] is not None else []
        proposals = []
        for entry in sorted(set(handlers)):
            if not self.project.enabled_type(self.project.methods[entry]['owner']):continue
            request = Request.http(self.project.ix.unit_of(entry), match[1].upper(), match[2],
                                   {'content-type': ['application/json']} if body is not MISSING else {}, body,
                                   provenance={'source': 'explicit_action', 'quote': action})
            params = Engine(self.project, state).path_parameters(entry, match[2])
            if isinstance(body, dict):params.update(body)
            proposals.append({'entry': entry, 'site': None, 'state': deepcopy(state), 'params': params,
                'bindings': {}, 'request': request, 'reason': 'Explicit HTTP matched against source routes',
                'unresolved': ['Ambiguous explicit HTTP deployment'] if len(handlers)>1 else []})
        return proposals, {'proposal': {'hypotheses': []}, 'candidates': [p['entry'] for p in proposals],
                            'unresolved': [] if proposals else ['Explicit HTTP has no matching supported source route']}

    def _bind(self, action, state, contract, score):
        mid, site = contract['entry'], contract['site']
        path_state = deepcopy(state)
        from .actors import actor_role
        path_state.select_actor(actor_role(action))
        fields = self.project.request_fields(mid)
        params, bindings, unresolved_units = {}, {}, {}
        dom_preparation = {}
        absence_problems = []
        selector_preparation = {}
        choices = {}

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
                    named = any(p['name'] == key and p['kind'] in ('PathVariable','RequestParam','RequestHeader')
                                for p in self.project.http_parameters(mid))
                    if not named:return
                    coerced = deepcopy(value)
                params[key] = coerced
                bindings[key] = {'source': source, 'reference': reference, 'quote': quote,
                                 'resolved': not contains_unknown(params[key])}

        if site:
            self.frontend.enter(site, path_state)
            preparation_state = deepcopy(path_state)
            rendered = [option for options in path_state.browser.get('options',{}).values()
                        if isinstance(options,list) for option in options]
            site = {**site,'options':site['options'] + rendered}
            event_values, event_reference = self.frontend.event_values(site, action, path_state)
            site = {**site, 'event_values': event_values, 'event_reference': event_reference}
            absence_problems = self.frontend.apply_absence(site, fields, action, path_state)
            expressions = ' '.join([*site['definitions'].values(), *site['body_fields'].values(), *site.get('conditional_fields', {}).values(),
                                    *site.get('dom_preparation',{}).get('properties',{}).values()])
            for _, selector, _ in re.findall(r'\$\(\s*([\"\'])([^\"\']+)\1\s*\)\.is\(\s*([\"\']):checked\3\s*\)', expressions):
                polarity = control_polarity(action, selector)
                if polarity is not None:
                    path_state.browser['dom'][selector.strip() + ':checked'] = polarity
            choices = {}
            for option in site['options']:
                label = set(tokens(option['label'])) if isinstance(option['label'], str) else set()
                if label and option_label_matches(option['label'], action) and not option.get('reference'):
                    space = 'form' if option.get('space') == 'form' else 'dom'
                    control = option['control'] if space == 'form' else '#'+option['control'].lstrip('#')
                    choices.setdefault((space,control), []).append(option['value'])
            for (space,control), values in choices.items():
                if len(values) == 1:
                    path_state.browser[space][control] = values[0]
            selector_preparation = self.frontend.source_selector_values(site,path_state,choices)
            for control,(value,_) in selector_preparation.items():
                path_state.browser['form'][control] = deepcopy(value)
            dom_preparation = self.frontend.prepared_dom_values(site,path_state)
            for (method,control),(value,_) in dom_preparation.items():
                space = path_state.browser.setdefault('dom_text',{}) if method == 'text' else path_state.browser['dom']
                space[control] = deepcopy(value)
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
                    params[key] = JsonText(json_value(body) if site.get('body_complete') or site.get('body_keys_complete') else U)
                    bindings[key] = {'source': 'ui', 'reference': site['id'] + ':JSON.stringify',
                                     'quote': '', 'resolved': not contains_unknown(params[key])}
            for key, value in partial_url_parameters(self.frontend, mid, site, path_state).items():
                if key in fields:
                    bind(key, value, 'ui', site['id'] + ':url')
        structured_inputs = structured_bindings(self.project, mid, action)
        for key, typ in fields.items():
            mass=mass_binding(key,action,self.frontend.unit_hints(site,key) if site and set(ntoks(key))&{'weight','mass'} else ())
            if mass is not None:
                value,quote,reference=mass
                if value is U:
                    params.pop(key,None)
                    bindings[key]={'source':'units','reference':reference,'quote':quote,'resolved':False}
                    unresolved_units[key]=bindings[key]
                else:bind(key,value,'units',reference,quote)
                continue
            raw = any(p['name'] == key and p['kind'] in ('PathVariable','RequestParam','RequestHeader')
                      for p in self.project.http_parameters(mid))
            value, quote = explicit_value(action, key, typ, raw=raw)
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
                    value, quote = date_input(dates[0],action,typ), action
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
            if re.search(r'\bnew\b',action,re.I) and intent(action)!=1 and any(
                    word in {'username','password','login','email'} for word in [normalized(key)]):
                actor=actor_role(action)
                for index in range(len(state.input_journal)-1,-1,-1):
                    item=state.input_journal[index]
                    if actor is not U and item.get('actor',U) not in (U,actor):continue
                    if intent(item.get('action',''))!=1:continue
                    matches=[(name,stored) for name,stored in item.get('parameters',{}).items() if normalized(name)==normalized(key)]
                    if len(matches)==1:
                        name,stored=matches[0]
                        bind(key,stored,'user_input','input_journal['+str(index)+'].parameters.'+name)
                        break
                if bindings.get(key,{}).get('source')=='user_input':continue
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
                    bind(key, date_input(dates[0],exact,typ), 'literal', 'action', exact)
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
                    bind(key, computed, 'ui', site['id'] + ':option-expression' +
                         (';'+option['reference'] if option.get('reference') else ''), option['label'])
            if key in params and not contains_unknown(params[key]):
                if not (params[key] == '' and intent(action) != 1 and (key.lower().endswith('id') or key in ('id', 'key'))):
                    continue
                if bindings.get(key, {}).get('source') == 'ui':
                    params.pop(key)
                    bindings[key]['resolved'] = False
            previous = history_value(self.project, mid, key, action, state.history,ui_scope=(site or {}).get('reference_scope'))
            if previous:
                bind(key, previous[1], 'history', previous[0])
        for key in fields:
            if key not in params or contains_unknown(params[key]) or params[key] == '':
                selected = selected_field(self.project, key, params, state.history, mid,ui_scope=(site or {}).get('reference_scope'))
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
        for key,binding in unresolved_units.items():
            params.pop(key,None)
            bindings[key]=binding
        if site:
            edited, excluded = unfilled_form_edits(self.frontend, site, action, bindings)
            for key in unresolved_units:
                expression={**site['body_fields'],**site.get('conditional_fields',{})}.get(key,'')
                excluded.update(self.frontend.input_controls(expression,site['definitions'])['form'])
            for control in excluded:
                path_state.browser['form'][control] = U
            for key in edited:
                params.pop(key, None)
                bindings[key] = {'source':'action', 'reference':'action:unspecified-new-value',
                                 'quote':action, 'resolved':False}
            expressions = {**site['body_fields'], **site.get('conditional_fields', {})}
            pending = {key for key in fields if key not in edited and key not in unresolved_units and
                       (key not in params or contains_unknown(params[key]) or
                        params[key] == '' and bindings.get(key, {}).get('source') == 'ui')}
            for key, expression in expressions.items():
                if key not in pending:
                    excluded.update(self.frontend.input_controls(expression, site['definitions'])['form'])
            anchors = {key:value for key,value in params.items() if bindings.get(key, {}).get('resolved')
                       and bindings[key]['source'] not in ('ui','ui_projection')}
            projections = self.frontend.projected_form_values(site, mid, action, preparation_state, anchors, excluded)
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
                    if (key not in params or contains_unknown(params[key])) and not http_headers_type(typ)]
        problems.extend('Unknown input unit: '+key for key,binding in bindings.items() if binding.get('reference')=='unit:unresolved')
        problems.extend(absence_problems)
        if site and len(site.get('compound_request_sites',[])) > 1:
            problems.append('Compound UI action has multiple source requests; scheduling is not fully modeled: '+
                            ';'.join(site['compound_request_sites']))
        if re.search(r'\bfilter(?:ed)?\b', action, re.I) and not lowered_filters:
            problems.append('Unsupported request filter: ' + action)
        if preparation:
            problems.append('Inferred row-to-form preparation; event execution is unobserved: ' + ';'.join(sorted(set(preparation))))
        if dom_preparation:
            problems.append('Inferred DOM preparation; callback execution and plugin effects are unobserved: '+
                            ';'.join(sorted({reference for _,reference in dom_preparation.values()})))
        if selector_preparation:
            problems.append('Inferred source selector from chosen request guard; UI selection is unobserved: '+
                            ';'.join(reference for _,reference in selector_preparation.values()))
        ui_value_conflicts=[]
        if site:
            for key, value in params.items():
                binding = bindings.get(key, {})
                expression = site['body_fields'].get(key)
                if expression and binding.get('resolved') and binding.get('source') != 'ui':
                    self.frontend.update_input(expression, value, path_state)
                    try:literal=json.loads(expression)
                    except (ValueError,TypeError):literal=U
                    if literal is not U:
                        from .models import key_equal
                        if key_equal(literal,value) is False:ui_value_conflicts.append(key)
        omissions={};flat_bodies=[];unknowns={}
        for parameter in self.project.http_parameters(mid):
            if parameter['kind']!='RequestBody':continue
            meta=self.project.methods[mid]
            owner=self.project.resolve_type(parameter['type'],meta['module'],meta['file'])
            if owner not in self.project.type_fields:continue
            plan=default_bean_plan(self.project,owner,'deserialize',Engine(self.project,path_state).standard_type)
            properties=plan['properties']
            changed_layout=plan['complete'] and bool(properties.keys()-self.project.type_fields[owner].keys())
            if changed_layout and site and (site.get('body_complete') or site.get('body_keys_complete')) and not site.get('conditional_fields'):
                body={}
                for key,expression in site['body_fields'].items():
                    value=params.get(key,U)
                    if value is U:value=self.frontend.evaluate(expression,path_state,site['event_values'],site['definitions'])
                    if value is not JS_UNDEFINED:body[key]=value
                named={p['name'] for p in self.project.http_parameters(mid) if p['kind']!='RequestBody'}
                old=set(self.project.type_fields[owner])-named
                params={key:value for key,value in params.items() if key not in old}
                params[parameter['name']]=body
                problems=[message for message in problems if not (message.startswith('Unknown input: ') and message[15:] in old)]
                problems.extend('Unknown input: '+key for key,value in body.items() if value is U)
                bindings[parameter['name']]={'source':'ui','reference':site['id'],'expression':'structured JSON property layout','resolved':all(value is not U for value in body.values())}
                continue
            if changed_layout:problems.append('JSON property layout needs an explicit structured request: '+parameter['name'])
            flat_bodies.append(parameter['name'])
            absent=set()
            if site:
                expressions={**site['body_fields'],**site.get('conditional_fields',{})}
                if site.get('body_complete') or site.get('body_keys_complete'):
                    absent.update(self.project.type_fields[owner].keys()-expressions.keys())
                absent.update(key for key,expression in expressions.items() if
                    self.frontend.evaluate(expression,path_state,site['event_values'],site['definitions']) is JS_UNDEFINED)
            omissions[parameter['name']]=absent
            unknowns[parameter['name']]={key:('present' if site and key in site['body_fields'] else 'unobserved')
                for key in (properties if changed_layout else self.project.type_fields[owner]) if key not in params and key not in absent}
        named={p['name'] for p in self.project.http_parameters(mid) if p['kind']!='RequestBody'}
        known_absent=set().union(*omissions.values())-named if omissions else set()
        problems=[message for message in problems if not (message.startswith('Unknown input: ') and message[15:] in known_absent)]
        wire_conflicts=list(ui_value_conflicts)
        for key in known_absent:
            reference=bindings.get(key,{}).get('reference','')
            from .absence_contracts import empty_equivalent
            equivalent=(bindings.get(key,{}).get('source')=='context' and params.get(key,U)==''
                        and absent_field(self.context.get('raw',{}),key) and empty_equivalent(Engine(self.project,path_state),mid,key))
            if key in params and bindings.get(key,{}).get('source')!='ui' and ':omitted' not in reference and not equivalent:
                wire_conflicts.append(key)
            if ':omitted' not in reference:params.pop(key,None)
            bindings[key]={'source':'ui_absence','reference':site['id']+':omitted-json-property','quote':'','resolved':True,
                           **({'consumer_equivalence':'default null and empty String satisfy Spring StringUtils.isEmpty'} if equivalent else {})}
        params=RequestInputs(params,omissions,flat_bodies,unknowns)
        return {'entry': mid, 'site': site, 'state': path_state, 'params': params, 'bindings': bindings,
                'body_omissions':{name:sorted(fields) for name,fields in omissions.items()},
                'wire_conflicts':wire_conflicts,
                'ui_selectors':{space+':'+control:values[0] for (space,control),values in choices.items() if len(values) == 1},
                'reason': 'Highest weighted source/UI contract score: ' + str(score), 'unresolved': problems}
