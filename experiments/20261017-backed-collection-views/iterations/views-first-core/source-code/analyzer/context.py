"""Evidence-checked facts extracted from provided context, not project defaults."""
from datetime import datetime
from itertools import zip_longest
import re


def dates_in(text):
    result = []
    patterns = (r'\b\d{4}-\d\d-\d\d(?:[ T]\d\d:\d\d(?::\d\d)?)?',
                r'\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b')
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            raw = match[0]
            for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%d %B %Y'):
                try:
                    result.append(datetime.strptime(raw, fmt))
                    break
                except ValueError:
                    pass
    return result


def supported_value(value, quote):
    if value is None:
        return bool(re.search(r'\bnull\b|\bnone\b|not specified|unspecified', quote, re.I))
    if isinstance(value, bool):
        negative = bool(re.search(r'\b(false|no|without|disabled)\b|\bnot\s+(?:\w+\s+){0,2}(?:enabled|true|yes)\b', quote, re.I))
        return not negative and bool(re.search(r'\b(true|yes|enabled)\b', quote, re.I)) if value else negative
    if value == '':
        return bool(re.search(r'\bno\b|\bwithout\b|empty|blank', quote, re.I))
    if isinstance(value, (int, float)):
        numeric = re.sub(r'(?<=\d)[ _](?=\d{3}(?:\D|$))', '', quote)
        return any(float(v) == value for v in re.findall(r'-?\d+(?:\.\d+)?', numeric))
    if not isinstance(value, str):
        return False
    if value.lower() in quote.lower():
        return True
    expected = dates_in(value)
    return bool(expected) and expected[0] in dates_in(quote)


def literal_quote(value, proposed, source):
    if proposed and proposed in source and supported_value(value, proposed):
        return proposed
    if isinstance(value, bool):
        # A canonical JSON boolean may have a noncanonical English spelling in the input.
        cues = [m[0] for m in re.finditer(r'\b(?:not\s+(?:\w+\s+){0,2}enabled|false|no|without|disabled|true|yes|enabled)\b', source, re.I)]
        if cues and all(supported_value(value, cue) for cue in cues):
            return cues[0]
    return None


def context_spans(raw):
    sources = raw.items() if isinstance(raw, dict) else [('context', raw)]
    spans, seen, words, credential_pairs = {}, {}, [], []

    def add(source, quote, value, typ, allowed):
        key = (str(source), quote, typ)
        if key not in seen:
            seen[key] = 'X' + str(len(spans))
            spans[seen[key]] = {'source': str(source), 'quote': quote, 'value': value,
                                'type': typ, 'allowed_kinds': allowed}
        return seen[key]

    for source, value in sources:
        text = str(value)
        date_ranges = []
        add(source, text, text, 'rule', ['choice'])
        if re.search(r'\b(account|user|username|login|credentials?)\b', str(source) + ' ' + text, re.I):
            for pair in re.finditer(r'([^\s/]+)\s+/\s+([^\s(),;]+)', text):
                left, right = [part.strip('\"\'') for part in pair.groups()]
                a = add(source, left, left, 'credential', ['credential'])
                b = add(source, right, right, 'credential', ['credential'])
                credential_pairs.append({'username': a, 'password': b})
        for match in re.finditer(r'\b\d{4}-\d\d-\d\d(?:[ T]\d\d:\d\d(?::\d\d)?)?|\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b', text):
            parsed = dates_in(match[0])
            if parsed:
                date_ranges.append(match.span())
                dt = parsed[0]
                iso = dt.isoformat() if dt.time() != datetime.min.time() else dt.date().isoformat()
                key = add(source, match[0], iso, 'date', ['clock', 'default'])
                spans[key]['label'] = re.split(r'[;.]', text[:match.start()])[-1][-40:] + match[0]
        for match in re.finditer(r'(?<!\w)([\"\'])(.{1,128}?)\1(?!\w)', text):
            add(source, match[2], match[2], 'text', ['default', 'credential', 'profile'])
        for match in re.finditer(r'-?\d+(?:[ _]\d{3})*(?:\.\d+)?', text):
            if any(start <= match.start() and match.end() <= end for start, end in date_ranges):
                continue
            number = re.sub(r'[ _]', '', match[0])
            add(source, match[0], float(number) if '.' in number else int(number), 'number', ['default'])
        tokens = list(dict.fromkeys(m[0].rstrip('.') for m in re.finditer(r'[\w@][\w@.+-]*', text)
                                   if not any(start <= m.start() and m.end() <= end for start, end in date_ranges)))
        for token in tokens:
            if re.search(r'[0-9_@]', token):
                add(source, token, token, 'text', ['default', 'credential', 'profile'])
        words.append([(source, token) for token in tokens if token])
    for group in zip_longest(*words):
        for item in group:
            if item:
                add(item[0], item[1], item[1], 'text', ['default', 'credential', 'profile'])
    limited = len(spans) > 192
    return dict(list(spans.items())[:192]), limited, credential_pairs


def read_context(raw, parser, field_names=()):
    if not raw:
        return {'facts': {}, 'clock': None, 'unresolved': ['No execution context was provided']}
    spans, limited, credential_pairs = context_spans(raw)
    def fields_schema(allowed):
        names = sorted(set(field_names) | {'request_date'})
        return {'type': 'array', 'maxItems': 8, 'items': {'type': 'object', 'properties': {
            'parameter': {'enum': names} if field_names else {'type': 'string', 'maxLength': 40},
            'reference': {'enum': [key for key, span in spans.items() if span['type'] in allowed]}},
            'required': ['parameter', 'reference'], 'additionalProperties': False}}
    schema = {'type': 'object', 'properties': {
        'clock': {'enum': ['', *[key for key, span in spans.items() if span['type'] == 'date']]},
        'credentials': fields_schema({'credential'} if credential_pairs else {'text'}), 'defaults': fields_schema({'text', 'number', 'date'}),
        'rules': {'type': 'array', 'maxItems': 6, 'items': {'enum': [key for key, span in spans.items() if span['type'] == 'rule']}},
        'unresolved': {'type': 'array', 'maxItems': 4, 'items': {'type': 'string', 'maxLength': 120}}},
        'required': ['clock', 'credentials', 'defaults', 'rules', 'unresolved'], 'additionalProperties': False}
    if credential_pairs:
        schema['properties']['credentials']['minItems'] = 2
    try:
        proposal = parser.propose(
        'Extract the execution context using ONLY span references. Return clock as the reference to the '
        'explicit SYSTEM CLOCK date, not the requested business date. Use an empty clock if unspecified. '
        'credentials is a list of separate username/password or other credential parameter bindings. '
        'credential_pairs recognizes the explicit username / password notation; extract both sides as credentials '
        'and map their roles to actual request field names. '
        'defaults is a list of other request parameter bindings; use request_date for a general request date. '
        'A binding is {parameter: actual field name, reference: span ID}; never use span types as parameter names. '
        'rules is a list of whole-fragment rule references useful for later choices. '
        'Spans are [context field, type, quoted text or date clause]. Never generate values or copy paragraphs into bindings. '
        'Return only supported facts. Do not enumerate every span.',
            {'context': raw, 'request_fields': sorted(field_names), 'credential_pairs': credential_pairs,
             'spans': {key: [span['source'], span['type'], span.get('label', span['quote']) if span['type'] != 'rule' else '(whole fragment)']
                       for key, span in spans.items()}}, schema)
    except ValueError as exc:
        return {'facts': {}, 'clock': None, 'unresolved': ['Context model parsing failed: ' + str(exc)]}
    facts = {}
    unresolved = ['Context model reported uncertainty about ' + spans[item]['source'] + ': ' + spans[item]['quote'][:160]
                  if item in spans else item for item in proposal['unresolved']]
    if limited:
        unresolved.append('Context span budget exceeded; some literal values were not offered to the model')
    selected = []
    if proposal['clock']:
        selected.append({'name': 'system_clock', 'kind': 'clock', 'reference': proposal['clock']})
    selected.extend({'name': item['parameter'], 'kind': kind, 'reference': item['reference']}
                    for group, kind in (('credentials', 'credential'), ('defaults', 'default')) for item in proposal[group])
    selected.extend({'name': 'rule_' + str(i), 'kind': 'choice', 'reference': ref} for i, ref in enumerate(dict.fromkeys(proposal['rules'])))
    for fact in selected:
        span = spans.get(fact['reference'])
        if not span or fact['kind'] not in span['allowed_kinds']:
            unresolved.append('Rejected unsupported context fact: ' + fact['name'])
            continue
        if fact['name'] in facts:
            unresolved.append('Duplicate context fact: ' + fact['name'])
            continue
        facts[fact['name']] = {**fact, 'value': span['value'], 'quote': span['quote'],
                               'source': span['source'], 'value_type': span['type']}
    clocks = [dates_in(str(f['value'])) for f in facts.values() if f['kind'] == 'clock']
    clock = next((d[0] for d in clocks if d), None)
    if clock is None:
        unresolved.append('System clock is unknown')
    return {'facts': facts, 'clock': clock, 'unresolved': unresolved}
