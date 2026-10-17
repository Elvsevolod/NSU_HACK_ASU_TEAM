"""Explicit field-labelled numeric scalars and numeric sequences only.

A value must directly follow a boundary-anchored field label (the camel/snake
split of the field name plus caller-supplied source labels), optionally
through is/of/=/:, and must be a whole finite numeric token. Lists require a
declared List<Integer>/List<Double> or int[]/double[] type and labelled
syntax. Repeated labelled occurrences must all parse to one value; a
malformed occurrence, invalid element or dangling separator yields U.
Nothing else is parsed: no times, no strings, no roles, no alias dictionaries.
"""
import math
import re

from .state import U

_INT = ('int', 'Integer', 'long', 'Long', 'short', 'Short', 'byte', 'Byte')
_FLOAT = ('double', 'Double', 'float', 'Float')
_STOP = re.compile(r';|\s+(?:with|for|from)\b', re.I)
_CONNECTOR = r'\s*(?:is|of|=|:)?\s*'
_NUMBER = {'int': r'-?\d+', 'double': r'-?(?:\d+(?:\.\d+)?|\.\d+)'}


def _words(value):
    split = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', str(value))
    return re.findall(r'[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+', split)


def _kind(name):
    name = name.split('.')[-1].strip()
    if name in _INT:
        return 'int'
    return 'double' if name in _FLOAT else None


def _sequence(typ):
    text = typ.strip()
    match = re.fullmatch(r'([\w.]+)\s*<\s*([\w.]+)\s*>', text)
    if match and match[1].split('.')[-1] == 'List':
        return _kind(match[2])
    return _kind(text[:-2]) if text.endswith('[]') else None


def _number(text, kind):
    try:
        value = int(text) if kind == 'int' else float(text)
    except ValueError:
        return None
    return value if kind == 'int' or math.isfinite(value) else None


def _elements(region, kind):
    parts = [part.strip() for part in region.split(',')]
    if parts[-1]:
        parts = parts[:-1] + [part.strip() for part in re.split(r'\s+and\s+', parts[-1], flags=re.I)]
    parts = [re.sub(r'^and\s+', '', part, flags=re.I) for part in parts]
    if any(not re.fullmatch(_NUMBER[kind], part) for part in parts):
        return None
    values = [_number(part, kind) for part in parts]
    return None if any(value is None for value in values) else values


def _occurrences(matches):
    """One entry per distinct label span; a span contained in another is a duplicate."""
    spans = {}
    for match in matches:
        spans.setdefault((match.start(), match.end()), match)
    return [match for span, match in sorted(spans.items())
            if not any(other != span and other[0] <= span[0] and span[1] <= other[1] for other in spans)]


def literal_value(action, field, typ, labels=()):
    """Return (value, exact quote) for explicit labelled numbers, else (U, '')."""
    if isinstance(labels, str):
        labels = (labels,)
    sequence = _sequence(typ)
    kind = sequence or _kind(typ)
    if kind is None:
        return U, ''
    matches = []
    for phrase in [str(field)] + [str(label) for label in labels if str(label).strip()]:
        words = _words(phrase)
        if words:
            label = r'\b' + r'[ _-]*'.join(re.escape(word) for word in words) + r'\b' + _CONNECTOR
            matches += list(re.finditer(label, action, re.I))
    matches = _occurrences(matches)
    found = {}
    for index, match in enumerate(matches):
        room = action[match.end():]
        if index + 1 < len(matches):
            room = re.sub(r'\s+and\s*$', '', room[:max(0, matches[index + 1].start() - match.end())], flags=re.I)
        if sequence:
            raw = _STOP.split(room, 1)[0]
            region = raw.strip()
            value = _elements(region, kind) if region else None
            end = match.end() + raw.index(region) + len(region) if region else match.end()
        else:
            token = re.match(_NUMBER[kind] + r'(?![\w.:-])', room)
            value = None if token is None else _number(token[0], kind)
            end = match.end() + token.end() if token else match.end()
        if value is None:
            return U, ''
        found.setdefault(repr(value), (value, action[match.start():end]))
    return next(iter(found.values())) if len(found) == 1 else (U, '')
