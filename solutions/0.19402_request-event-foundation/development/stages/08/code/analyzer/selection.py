from .java_collections import schema_type
"""Explicit selection language links later requests to source-typed objects."""
from copy import deepcopy
import re

from baseline_nlp import ntoks
from .provenance import objects, entity_words, history_value, contains_unknown, source_string
from .state import U


def selected_objects(project, mid, action, history, params=None,ui_scope=None):
    selecting = bool(re.search(r'^(?:open|select|choose|take|inspect)\b|\band\s+take\b', action, re.I))
    focus = re.split(r'\b(?:for|with|without|from|on|onto)\b', action, 1, flags=re.I)[0]
    words = set(ntoks(focus))
    observed = []
    for index, item in enumerate(history):
        if ui_scope and item.get('ui_scope') and item['ui_scope']!=ui_scope:continue
        for name in ('result', 'created_objects'):
            observed.extend(objects(item.get(name, U), 'history[' + str(index) + '].' + name))
    groups = {tuple(sorted(entity_words(schema_type(obj)))) for _, obj in observed
              if entity_words(schema_type(obj)) and entity_words(schema_type(obj)) <= words}
    fields = project.request_fields(mid)
    groups.update(tuple(sorted(entity_words(field))) for field in fields
                  if field.lower().endswith('id') and entity_words(field) and entity_words(field) <= words)
    output = []
    for entity in sorted(groups if selecting else []):
        named = [key for key in fields if key.lower().endswith('id') and entity_words(key) == set(entity)]
        field = named[0] if len(named) == 1 else 'id'
        reference = history_value(project, mid, field, action, history, entity, use_selection=False,ui_scope=ui_scope)
        if reference is None:
            continue
        parent = reference[0].rsplit('.', 1)[0]
        obj = next((obj for path, obj in observed if path == parent), None)
        if obj is not None and not contains_unknown(reference[1]):
            value = source_string(project, reference[1]) if isinstance(reference[1], dict) and '__symbol__' not in reference[1] else reference[1]
            if value is not U:
                output.append({'entity': list(entity), 'value': deepcopy(value),
                               'reference': reference[0], 'object': deepcopy(obj)})
    # A later request reusing an observed typed identity establishes focus too:
    # paying an invoice must not forget which invoice the subsequent edit means.
    for field, expected in (params or {}).items():
        entity = entity_words(field) if field.lower().endswith('id') else set()
        if not entity or expected in ('', None, U) or contains_unknown(expected):
            continue
        matches = []
        for path, obj in observed:
            if entity_words(schema_type(obj)) != entity:
                continue
            tid = project.resolve_type(schema_type(obj), project.methods[mid]['module'])
            for key, info in project.type_fields.get(tid, {}).items():
                if not info.get('id'):
                    continue
                value = obj.get(key, U)
                rendered = source_string(project, value) if isinstance(value, dict) and '__symbol__' not in value else value
                if rendered is not U and rendered == expected:
                    matches.append({'entity': sorted(entity), 'value': deepcopy(expected),
                                    'reference': path + '.' + key, 'object': deepcopy(obj)})
        if matches and not any(item['entity'] == sorted(entity) for item in output):
            output.append(matches[-1])
    from .history_refs import object_scope
    for selected in output:
        match=re.match(r'history\[(\d+)\]',selected['reference'])
        item=history[int(match[1])] if match else {}
        deployment,fqn,_=object_scope(project,item,selected['object'])
        selected.update(deployment=deployment,qualified_type=fqn,producer_entry=item.get('entry'))
    return output
