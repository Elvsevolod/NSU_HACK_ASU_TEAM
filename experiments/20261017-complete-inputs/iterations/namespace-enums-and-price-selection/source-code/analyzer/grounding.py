"""Propose request bindings from retrieved source contracts and check provenance."""
from copy import deepcopy
import hashlib
import json
import re
from .context import literal_quote
from .project import text
from .state import U


def references(value, prefix, depth=0):
    if isinstance(value, tuple) or hasattr(value, 'start_point') or depth > 6:
        return {}
    result = {prefix: value}
    if isinstance(value, dict):
        for key, val in value.items():
            if isinstance(key, str) and not key.startswith('__'):
                result.update(references(val, prefix + '.' + key, depth + 1))
    elif isinstance(value, list):
        for i, val in enumerate(value[:3]):
            result.update(references(val, prefix + '[' + str(i) + ']', depth + 1))
    return result


STEP_SCHEMA = {
    'type': 'object', 'properties': {
        'hypotheses': {'type': 'array', 'maxItems': 3, 'items': {'type': 'object', 'properties': {
            'handler': {'type': 'string'}, 'ui_site': {'type': 'string'}, 'reason': {'type': 'string'},
            'bindings': {'type': 'array', 'maxItems': 35, 'items': {'type': 'object', 'properties': {
                'parameter': {'type': 'string'},
                'source': {'enum': ['literal', 'context', 'history', 'database', 'code', 'ui', 'fresh', 'unknown']},
                'reference': {'type': 'string'}, 'value': {'type': ['string', 'number', 'boolean', 'null']},
                'quote': {'type': 'string'}},
                'required': ['parameter', 'source', 'reference', 'value', 'quote'], 'additionalProperties': False}}},
            'required': ['handler', 'ui_site', 'reason', 'bindings'], 'additionalProperties': False}},
        'unresolved': {'type': 'array', 'items': {'type': 'string'}}},
    'required': ['hypotheses', 'unresolved'], 'additionalProperties': False}


class Grounder:
    def __init__(self, project, frontend, retrieval, parser, context):
        self.project, self.frontend, self.retrieval, self.parser = project, frontend, retrieval, parser
        self.context = context

    def code_values(self, sites, action='', field_names=()):
        values = {'enum:' + key: self.project.enums.get(key, value)
                  for key, value in self.project.enum_objects.items()}
        values.update({'constant:' + k: v for k, v in self.project.constants.items()})
        for site in sites:
            values.update({'default:' + site['id'] + ':' + key: value
                           for key, value in site['defaults'].items() if value is not U})
            values.update({'option:' + site['id'] + ':' + str(i): option['value']
                           for i, option in enumerate(site['options'])})
        self.value_labels = {key: key.split(':', 1)[-1] for key in values}
        for site in sites:
            for i, option in enumerate(site['options']):
                self.value_labels['option:' + site['id'] + ':' + str(i)] = option.get('control', '') + ' ' + option['label']
        words = re.findall(r'[a-z0-9]+', action.lower())
        fields = re.findall(r'[a-z0-9]+', ' '.join(field_names).lower())
        def relevance(key):
            label = self.value_labels[key].lower()
            return -(4 * sum(len(w) > 2 and w in label for w in words)
                     + sum(len(w) > 2 and w in label for w in fields))
        selected = sorted(values, key=lambda key: (relevance(key), key))[:32]
        return {key: values[key] for key in selected}

    def step(self, action, state, scenario_text='', prepared_proposal=None):
        # A missing explicitly referenced prior creation is a missing dependency, not a DB default.
        if not state.history and re.search(r'\b(?:just|newly|previously)\s+(?:created|added|registered|saved)\b', action, re.I):
            return [], {'candidates': [], 'proposal': None, 'unresolved': ['Referenced prior creation is absent from the scenario history']}
        candidates = self.retrieval.candidates(action)
        sites = [s for s in self.frontend.sites.values() if set(s['handlers']) & set(candidates)]
        # The model sees contracts, not the whole repository or previously scored answers.
        docs = []
        for mid in candidates:
            matches = [s for s in sites if mid in s['handlers']][:1]
            docs.append({'handler': mid, 'parameters': self.project.request_fields(mid),
                         'source': text(self.project.ast.get(mid))[:350],
                         'ui': [{'id': s['id'], 'url': s['url'], 'body_fields': s['body_fields'],
                                 'labels': s['labels'][:120], 'source': s['source'][:350],
                                 'options': s['options'][:6]} for s in matches]})
        refs = references({key: value for key, value in state.browser.items() if key != 'pages'}, 'browser')
        database_refs = {}
        resources = set()
        desired = {re.sub(r'[^a-z0-9]', '', key.lower()) for mid in candidates for key in self.project.request_fields(mid)}
        for mid in candidates:
            resources.update(rid for _, rid in self.project.ix.closure({mid})[3])
        ranked_resources = []
        for rid in resources:
            rows = state.database.rows(self.project.nodes[rid])
            if rows:
                fields = {re.sub(r'[^a-z0-9]', '', key.lower()) for key in rows[0]}
                ranked_resources.append((-len(fields & desired), rid, rows))
        for _, rid, rows in sorted(ranked_resources, key=lambda item: (item[0], item[1]))[:4]:
            for row in rows[:3]:
                record = self.project.materialize(state.database, rid, row)
                keys = self.project.id_fields.get(rid, [])
                identity = {key: record.get(key, U) for key in keys} if keys else record
                token = hashlib.sha256(json.dumps(identity, sort_keys=True, default=str).encode()).hexdigest()[:16]
                database_refs.update(references(record, 'database:' + rid + '@' + token))
        refs.update(database_refs)
        for i, item in enumerate(state.history):
            refs.update(references(item['result'], 'history[' + str(i) + '].result'))
        # Prefer recent values while retaining the first objects for ordinal references.
        keys = list(refs)
        shown = list(dict.fromkeys(keys[:20] + keys[-28:]))
        values = self.code_values(sites, action, {key for mid in candidates for key in self.project.request_fields(mid)})
        handler_aliases = {'H' + str(i): mid for i, mid in enumerate(candidates)}
        ui_aliases = {'U' + str(i): site['id'] for i, site in enumerate(sites)}
        ref_aliases = {'R' + str(i): key for i, key in enumerate(shown)}
        fact_aliases = {'F' + str(i): key for i, key in enumerate(self.context['facts'])}
        code_aliases = {'C' + str(i): key for i, key in enumerate(values)}
        for doc in docs:
            doc['source_handler'] = doc['handler']
            doc['handler'] = next(key for key, mid in handler_aliases.items() if mid == doc['handler'])
            for ui in doc['ui']:
                ui['id'] = next(key for key, sid in ui_aliases.items() if sid == ui['id'])
        payload = {'action': action, 'scenario_context': scenario_text[:1200],
                   'execution_context': {alias: {k: v for k, v in self.context['facts'][key].items() if k != 'quote'} for alias, key in fact_aliases.items()}, 'candidates': docs,
                   'code_values': {alias: {'label': self.value_labels[key].split(':')[-1], 'value': values[key]} for alias, key in code_aliases.items()},
                   'references': {alias: {'path': key, 'value': str(refs[key])[:90]} for alias, key in ref_aliases.items()},
                   'prior_results': [{'step': item['step'], 'action': item['action'],
                                      'returned_references': {key: alias for alias, key in ref_aliases.items()
                                                              if key.startswith('history[' + str(i) + '].result')}}
                                     for i, item in enumerate(state.history)]}
        schema = deepcopy(STEP_SCHEMA)
        item = schema['properties']['hypotheses']['items']['properties']
        item['handler'] = {'enum': list(handler_aliases)}
        item['ui_site'] = {'enum': ['', *ui_aliases]}
        item['bindings']['items']['properties']['parameter'] = {
            'enum': sorted({name for mid in candidates for name in self.project.request_fields(mid)}) or ['']}
        base_binding = item['bindings']['items']
        variants = []
        references_by_source = {
            'literal': [''], 'context': [alias for alias, key in fact_aliases.items() if self.context['facts'][key]['kind'] != 'choice'],
            'history': [alias for alias, key in ref_aliases.items() if not key.startswith('database:')],
            'database': [alias for alias, key in ref_aliases.items() if key.startswith('database:')],
            'code': list(code_aliases), 'ui': sorted({k for site in sites for k in site['body_fields']
                                                   if any(k in self.project.request_fields(mid) for mid in candidates)}),
            'fresh': [''], 'unknown': ['']}
        for source, allowed in references_by_source.items():
            if not allowed:
                continue
            variant = deepcopy(base_binding)
            variant['properties']['source'] = {'const': source}
            variant['properties']['reference'] = {'enum': allowed}
            if source in ('context', 'history', 'database', 'code', 'ui', 'fresh', 'unknown'):
                variant['properties']['value'] = {'type': 'null'}
            variants.append(variant)
        item['bindings']['items'] = {'oneOf': variants}
        payload['binding_sources'] = references_by_source
        task = (
            'Choose executable HTTP requests from the supplied contracts. A hypothesis must match the action. '
            'Return one hypothesis unless the intent is truly ambiguous; never list nonmatching candidates. '
            'Each binding has parameter, source, reference, value, quote. Explicitly bind stated booleans, including negations. '
            'Literal: reference="", value is an explicit value in current action/scenario text, quote is exact. '
            'Example: action "read document Z9" gives '
            '{"parameter":"key","source":"literal","reference":"","value":"Z9","quote":"Z9"}. '
            'Reference sources: value=null, reference is one allowed alias in binding_sources. '
            'Example: if references contains R7 with path history[1].result.key, a prior-object key uses '
            '{"parameter":"key","source":"history","reference":"R7","value":null,"quote":""}. '
            'For first/second/previous/newly created objects, select the matching returned object in prior_results '
            'by creation order. If no matching prior result exists, use source="unknown", reference="", value=null. '
            'Use context aliases for defaults, code aliases for enums/options/constants, database aliases for provided records, '
            'ui for fields computable from a selected UI request. Never turn a prior result or database value into a literal. '
            'fresh is only for explicitly requested new input that was not specified. '
            'Use actual server parameter/DTO names. Respect roles and dependencies. Give one short sentence as reason. '
            'Do not invent credentials, dates, IDs, enum values or successful execution results.')
        try:
            proposal = deepcopy(prepared_proposal) if prepared_proposal is not None else self.parser.propose(
                task, payload, schema)
        except (ValueError, KeyError) as exc:
            return [], {'candidates': candidates, 'proposal': None,
                        'unresolved': ['Local parser could not produce a supported request: ' + str(exc)]}
        raw_proposal = deepcopy(proposal)
        accepted, rejected = [], list(proposal['unresolved'])
        for hypothesis in proposal['hypotheses']:
            mid = handler_aliases.get(hypothesis['handler'], hypothesis['handler'])
            if mid not in candidates:
                rejected.append('Rejected handler not present in retrieved source contracts')
                continue
            site_id = ui_aliases.get(hypothesis['ui_site'], hypothesis['ui_site'])
            site = self.frontend.sites.get(site_id)
            if hypothesis['ui_site'] and (site is None or mid not in site['handlers']):
                rejected.append('Rejected UI site not linked to the selected handler')
                continue
            path_state = deepcopy(state)
            params, evidence, problems = {}, {}, []
            fields = self.project.request_fields(mid)
            if site:
                self.frontend.enter(site, path_state)
                for key, expression in site['body_fields'].items():
                    if key in fields:
                        value = self.frontend.evaluate(expression, path_state, definitions=site['definitions'])
                        if value is not U:
                            params[key] = value
                            evidence[key] = {'source': 'ui', 'reference': site['id'], 'expression': expression}
                url = self.frontend.evaluate(site['url'], path_state, definitions=site['definitions'])
                if isinstance(url, str):
                    from .engine import Engine
                    params.update(Engine(self.project, path_state).path_parameters(mid, url))
            bound = set()
            for binding in hypothesis['bindings']:
                key = binding['parameter']
                if key not in fields or key in bound:
                    problems.append('Rejected unknown or duplicate parameter: ' + key)
                    continue
                bound.add(key)
                source, ref, quote = binding['source'], binding['reference'], binding['quote']
                if source == 'context':
                    ref = fact_aliases.get(ref, ref)
                elif source in ('history', 'database'):
                    ref = ref_aliases.get(ref, ref)
                elif source == 'code':
                    ref = code_aliases.get(ref, ref)
                binding['reference'] = ref
                value = U
                if source == 'literal':
                    literal_value = binding['value']
                    if fields[key].split('.')[-1] in ('boolean', 'Boolean'):
                        from .engine import Engine
                        if isinstance(literal_value, str):
                            literal_value = {'enabled': True, 'disabled': False, 'yes': True, 'no': False}.get(literal_value.lower(), literal_value)
                        literal_value = Engine.coerce(literal_value, fields[key])
                    checked_quote = literal_quote(literal_value, quote, action + '\n' + scenario_text)
                    if checked_quote:
                        value = literal_value
                        if checked_quote != quote:
                            binding['model_quote'] = quote
                            binding['quote'] = checked_quote
                            binding['normalization'] = 'canonical boolean grounded in an exact input phrase'
                elif source == 'context':
                    fact = self.context['facts'].get(ref)
                    if fact and fact['kind'] != 'choice':
                        value = deepcopy(fact['value'])
                elif source in ('history', 'database'):
                    value = deepcopy(refs.get(ref, U))
                elif source == 'code':
                    value = deepcopy(values.get(ref, U))
                elif source == 'ui' and site:
                    expression = site['body_fields'].get(ref or key)
                    if expression:
                        value = self.frontend.evaluate(expression, path_state, definitions=site['definitions'])
                elif source == 'fresh' and quote and quote in action and re.search(r'\bnew\b|\bcreate\b|\bregister\b|\badd\b', action, re.I):
                    value = path_state.fresh_input(key, fields[key])
                if value is not U:
                    from .engine import Engine
                    value = Engine.coerce(value, fields[key])
                if value is U:
                    if source != 'unknown':
                        problems.append('Unsupported parameter binding: ' + key + ' from ' + source)
                    params.pop(key, None)
                else:
                    params[key] = value
                evidence[key] = {**binding, 'resolved': value is not U}
            # No default values are copied from another request or method name.
            missing = [key for key, typ in fields.items() if key not in params and 'Header' not in typ]
            if site:
                for key, expression in site['body_fields'].items():
                    if key not in params:
                        continue
                    form = re.fullmatch(r'(?:this|that)\.(\w+)', expression)
                    dom = re.fullmatch(r'\$\(([\"\'].*?[\"\'])\)\.val\(\)', expression)
                    if form:
                        path_state.browser['form'][form[1]] = deepcopy(params[key])
                    elif dom:
                        path_state.browser['dom'][dom[1][1:-1]] = deepcopy(params[key])
            accepted.append({'entry': mid, 'params': params, 'state': path_state, 'site': site,
                             'bindings': evidence, 'reason': hypothesis['reason'],
                             'unresolved': problems + ['Unknown input: ' + k for k in missing]})
        # Prepared templates use stable actual references, not aliases whose numbering changes with path state.
        for hypothesis in proposal['hypotheses']:
            hypothesis['handler'] = handler_aliases.get(hypothesis['handler'], hypothesis['handler'])
            hypothesis['ui_site'] = ui_aliases.get(hypothesis['ui_site'], hypothesis['ui_site'])
        repair_errors = rejected + [problem for choice in accepted for problem in choice['unresolved']
            if not problem.startswith('Unknown input: ') or choice['bindings'].get(problem.split(': ', 1)[-1], {}).get('source') != 'unknown']
        if prepared_proposal is None and repair_errors:
            try:
                repaired = self.parser.propose(task + ' Correct the previous proposal using the validation errors. '
                    'Use a supported reference or explicit unknown for rejected bindings. Do not repeat invalid quotes.',
                    {**payload, 'previous_proposal': raw_proposal, 'validation_errors': repair_errors}, schema)
                accepted, detail = self.step(action, state, scenario_text, prepared_proposal=repaired)
                detail['repairs'] = [{'previous_proposal': raw_proposal, 'validation_errors': repair_errors}]
                return accepted, detail
            except (ValueError, KeyError):
                pass
        return accepted, {'candidates': candidates, 'proposal': proposal, 'raw_proposal': raw_proposal,
                          'unresolved': rejected}
