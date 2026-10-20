"""Narrow, evidence-bearing first-item defaults stated in the supplied context."""
import re
from baseline_nlp import ntoks
from .provenance import entity_words, contains_unknown, new_for, ordinal_for
from .state import U
from .nl_inputs import control_polarity


# Ordinary language synonyms; this does not merge source entity identities.
def concepts(value):
    return {'food' if word == 'dish' else word for word in ntoks(value)}


def rule_matches(rule, typename):
    owner = concepts(' '.join(entity_words(typename)))
    ordered = ['food' if word == 'dish' else word for word in ntoks(typename.split('.')[-1])]
    ordered = [word for word in ordered if word in owner]
    return bool(ordered) and set(rule['entity']) <= owner and ordered[-1] in rule['entity']


def choice_rules(raw):
    output = []
    def visit(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, path + '.' + str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, path + '[' + str(index) + ']')
        elif isinstance(value, str):
            pattern = (r'\bwhere\s+(.+?)\s+(?:is|are)\s+not\s+(?:further\s+)?specified\s*,?\s*'
                       r'(?:the\s+)?first\s+(?:one\s+)?is\s+(?:taken|chosen|selected)\b')
            for match in re.finditer(pattern, value, re.I):
                for label in re.split(r'\s+(?:or|and)\s+|,', match[1]):
                    label = re.sub(r'^(?:a|an|the)\s+', '', label.strip(), flags=re.I)
                    words = concepts(label)
                    if words and len(words) <= 3 and re.fullmatch(r'[A-Za-z -]+', label):
                        output.append({'entity': sorted(words), 'reference': path, 'quote': match[0]})
    visit(raw, 'context')
    return output


def default_choices(project, mid, fields, action, history, rules, params):
    """Use a returned ordered collection, retaining parent/child selections.

    A map with several keys needs an explicitly mentioned key. No Java HashMap
    iteration order is inferred. Unknown rows/membership never establish a first.
    """
    if not rules or re.match(r'^(?:update|modify|change|edit|delete|remove|create|add)\b', action, re.I):
        return {}
    clauses = re.split(r'[,;]|\bwith\b', action, flags=re.I)
    active = [rule for rule in rules if set(rule['entity']) <= concepts(action)
              and not new_for(action, set(rule['entity']))
              and control_polarity(action, ' '.join(rule['entity'])) is not False]
    if not active:
        return {}
    candidates = []
    meta = project.methods[mid]
    for index in range(len(history) - 1, -1, -1):
        observed = []
        context_action = history[index].get('action', '')
        def visit(value, path, labels):
            if isinstance(value, list):
                if not value or any(child is U for child in value):
                    return
                typed = [child for child in value if isinstance(child, dict) and child.get('__type__')]
                if len(typed) != len(value):
                    return
                selecting = [rule for rule in active if all(rule_matches(rule, child['__type__']) for child in typed)]
                if selecting:
                    selected = selecting[-1]
                    ordinal = ordinal_for(action, set(selected['entity']))
                    position = ('first','second','third','fourth').index(ordinal[1].lower()) if ordinal else 0
                    if position < len(value):
                        visit(value[position], path + '[' + str(position) + ']', labels)
                else:
                    for position, child in enumerate(value):
                        visit(child, path + '[' + str(position) + ']', labels)
            elif isinstance(value, dict):
                mapping = value.get('__map__')
                if isinstance(mapping, dict):
                    keys = [key for key in mapping if isinstance(key, str) and concepts(key)
                            and concepts(key) <= concepts(context_action + ' ' + action)]
                    if not keys and len(mapping) == 1:
                        keys = list(mapping)
                    if len(keys) == 1:
                        visit(mapping[keys[0]], path + '[' + repr(keys[0]) + ']', labels)
                    return
                if value.get('__type__') and '__symbol__' not in value:
                    observed.append((path, value, labels))
                    labels = labels | concepts(' '.join(entity_words(value['__type__'])))
                for key, child in value.items():
                    if not str(key).startswith('__'):
                        visit(child, path + '.' + str(key), labels | concepts(str(key)))
        visit(history[index].get('result', U), 'history[' + str(index) + '].result', set())
        for path, obj, labels in observed:
            owner = concepts(' '.join(entity_words(obj['__type__'])))
            matching = [rule for rule in active if rule_matches(rule, obj['__type__'])]
            if not matching:
                continue
            tid = project.resolve_type(obj['__type__'], meta['module'], meta['file'])
            declared = project.type_fields.get(tid, {})
            children = set().union(*(concepts(part) for info in declared.values()
                                     for part in re.findall(r'<\s*([\w.]+)', info['type'])))
            # An explicit already-bound name/ID must refer to this same object.
            shared = [(key, value) for key, value in params.items() if key in declared
                      and concepts(key) & {'id','key','name'} and value not in ('', None, U)]
            if any(obj.get(key, U) != value for key, value in shared):
                continue
            for field in fields:
                wanted = concepts(field)
                properties = [key for key in declared
                              if (wanted == concepts(key) and bool(wanted - {'id','key','name','price','cost'}))
                              or (wanted == owner | concepts(key) and wanted != concepts(key))]
                if len(properties) != 1:
                    continue
                key = properties[0]
                value = obj.get(key, U)
                if value is None or contains_unknown(value) or not isinstance(value, (str, int, float, bool)):
                    continue
                rule = matching[-1]
                focused = [clause for clause in clauses if set(rule['entity']) <= concepts(clause)]
                focus = concepts(' '.join(focused)) if focused else concepts(action)
                qualifiers = [set(other['entity']) for other in active
                              if set(other['entity']) <= focus and not set(other['entity']) <= children]
                if any(not qualifier <= labels | owner for qualifier in qualifiers):
                    continue
                score = len((labels | owner) & focus)
                candidates.append((field, score, value, path + '.' + key, rule))
        if candidates:
            break
    output = {}
    for field in fields:
        options = [candidate for candidate in candidates if candidate[0] == field]
        maximum = max((candidate[1] for candidate in options), default=-1)
        best = [candidate for candidate in options if candidate[1] == maximum]
        if len({repr(candidate[2]) for candidate in best}) == 1:
            _, _, value, reference, rule = best[0]
            output[field] = (value, reference + ';' + rule['reference'], rule['quote'])
    return output
