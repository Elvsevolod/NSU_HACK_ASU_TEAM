"""Context spans reused from variant 14, independent of either language adapter.

The source snapshot and adaptation are recorded in development/reused-components.json.
"""
from datetime import datetime
from itertools import zip_longest
import re

from .values import Unknown


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


def normalized(name):
    return re.sub(r'[^\w]', '', name).replace('_', '').lower()


def facts(project, context):
    """Only designated context supplies defaults; scenario descriptions are not inputs."""
    raw = {**project.skeleton.get('context', {}), **context.get('narrative', {})}
    spans, limited, pairs = context_spans(raw)
    selected = {}
    for name in ('username', 'password'):
        values = {spans[pair[name]]['value'] for pair in pairs if pair[name] in spans}
        if values:
            refs = [pair[name] for pair in pairs if pair[name] in spans]
            value = next(iter(values)) if len(values) == 1 else Unknown('Conflicting context credentials', origin=name)
            selected[normalized(name)] = {'value': value, 'source': 'context', 'references': [spans[ref] for ref in refs]}
    dates = {'clock': [], 'request_date': []}
    for span in spans.values():
        if span['type'] == 'date':
            label = span.get('label', '')
            role = 'clock' if re.search(r'\b(?:system\s+clock|current\s+(?:date|time)|today)\b', label, re.I) else 'request_date'
            dates[role].append(span)
    for name, refs in dates.items():
        if refs:
            values = {span['value'] for span in refs}
            value = next(iter(values)) if len(values) == 1 else Unknown('Conflicting context dates', origin=name)
            selected[normalized(name)] = {'value': value, 'source': 'context', 'references': refs}
    for name, value in raw.items():
        # Named scalar context values are explicit. Long narrative fragments
        # cannot accidentally become strings for equally named request fields.
        if value is None or type(value) in (bool, int, float) or isinstance(value, str) and len(value.split()) == 1:
            selected[normalized(name)] = {'value': value, 'source': 'context', 'references': [{'source': name, 'quote': str(value)}]}
    return selected, raw, limited


def absence(name, raw):
    words = re.findall(r'[^\W_]+', re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name).lower())
    if not words:
        return None
    pattern = r'\b(?:no|without)\s+' + r'[ _-]*'.join(map(re.escape, words)) + r'\b'
    matches = []
    for source, value in raw.items():
        found = re.search(pattern, str(value), re.I)
        if found:
            matches.append({'source': source, 'quote': found[0]})
    return matches or None

