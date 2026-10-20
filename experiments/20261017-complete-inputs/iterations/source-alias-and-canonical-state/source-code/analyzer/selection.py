"""Explicit selection language links later requests to source-typed objects."""
from copy import deepcopy
import re

from baseline_nlp import ntoks
from .provenance import objects, entity_words, history_value, contains_unknown, source_string
from .state import U


def selected_objects(project, mid, action, history):
    if not re.search(r'^(?:open|select|choose|take|inspect)\b|\band\s+take\b', action, re.I):
        return []
    focus = re.split(r'\b(?:for|with|without|from|on|onto)\b', action, 1, flags=re.I)[0]
    words = set(ntoks(focus))
    observed = []
    for index, item in enumerate(history):
        for name in ('result', 'created_objects'):
            observed.extend(objects(item.get(name, U), 'history[' + str(index) + '].' + name))
    groups = {tuple(sorted(entity_words(obj['__type__']))) for _, obj in observed
              if entity_words(obj['__type__']) and entity_words(obj['__type__']) <= words}
    fields = project.request_fields(mid)
    output = []
    for entity in sorted(groups):
        named = [key for key in fields if key.lower().endswith('id') and entity_words(key) == set(entity)]
        field = named[0] if len(named) == 1 else 'id'
        reference = history_value(project, mid, field, action, history, entity, use_selection=False)
        if reference is None:
            continue
        parent = reference[0].rsplit('.', 1)[0]
        obj = next((obj for path, obj in observed if path == parent), None)
        if obj is not None and not contains_unknown(reference[1]):
            value = source_string(project, reference[1]) if isinstance(reference[1], dict) and '__symbol__' not in reference[1] else reference[1]
            if value is not U:
                output.append({'entity': list(entity), 'value': deepcopy(value),
                               'reference': reference[0], 'object': deepcopy(obj)})
    return output
