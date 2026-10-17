"""Small domain-independent language roles, tied to declared/UI input fields."""
import re
from baseline_nlp import ntoks
from .units import mass_binding


ROLE_WORDS = {
    'origin': {'from', 'start', 'starting', 'origin', 'source'},
    'destination': {'to', 'end', 'terminal', 'destination', 'dest'},
    'via': {'via', 'intermediate'},
    'date': {'date', 'departure', 'departing'},
}


def words(value):
    return set(re.findall(r'[a-z]+', re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', value).lower()))


def field_role(field, expression=''):
    # A source form reference is stronger than an opaque transport field name.
    for source in (expression, field):
        if words(source) & {'date', 'time'}:
            return 'date'
        found = {role for role, vocabulary in ROLE_WORDS.items() if words(source) & vocabulary}
        if len(found) == 1:
            return next(iter(found))
    return None


def language_roles(action):
    result = {}
    route = re.search(r'\bfrom\s+([^,;()]+?)\s+to\s+(.+?)(?=\s+(?:departing|on\s+\d|for|with|without)\b|[,;()]|$)', action, re.I)
    if route and not re.search(r'\b(?:with|without)\b[^,;()]*$', action[:route.start()], re.I):
        origin = route[1].strip()
        via = re.split(r'\s+via\s+', origin, flags=re.I)
        result['origin'], result['destination'] = via[0], route[2].strip()
        if len(via) == 2:
            result['via'] = via[1]
    return result


def intermediate_field(fields):
    """One unqualified peer of the declared origin/destination name fields."""
    endpoints = [[key for key in fields if field_role(key) == role] for role in ('origin', 'destination')]
    if any(len(keys) != 1 for keys in endpoints):
        return None
    shared = set(ntoks(endpoints[0][0])) & set(ntoks(endpoints[1][0]))
    shared -= {'start', 'end', 'source', 'destination', 'terminal', 'origin', 'name'}
    if not shared:
        return None
    candidates = [key for key, typ in fields.items() if field_role(key) is None
                  and typ.split('.')[-1] == 'String' and set(ntoks(key)) - {'name'} == shared]
    return candidates[0] if len(candidates) == 1 else None


def canonical_ui_literal(value, site):
    """Preserve project spelling only for an exact space/punctuation-normalized match."""
    norm = lambda item: re.sub(r'[^a-z0-9]', '', item.lower())
    candidates = [v for source in ('defaults', 'dom_defaults') for v in (site or {}).get(source, {}).values()
                  if isinstance(v, str) and norm(v) == norm(value)]
    candidates = list(dict.fromkeys(candidates))
    return candidates[0] if len(candidates) == 1 else value


def introduced_value(project, mid, field, action):
    """Literal names introduced after source type labels, plus explicit mass units."""
    from .state import U
    labels = []
    if field == 'name':
        labels = [parameter['type'].split('.')[-1] for parameter in project.http_parameters(mid)
                  if parameter['kind'] == 'RequestBody']
    elif field.endswith('Id') and field != 'id':
        labels = [field[:-2]]
    elif field.endswith('Name'):
        labels = [field[:-4]]
    elif len(words(field)) >= 2:
        labels = [field]
    for label in labels:
        parts = re.findall(r'[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+', label)
        if not parts:
            continue
        phrase = r'[ _-]*'.join(map(re.escape, parts))
        match = re.search(r'\b(?i:' + phrase + r')\s+(?:named\s+)?(?:"([^"]+)"|([A-Z][\w.-]*(?:\s+[A-Z][\w.-]*)*))', action)
        if match:
            return match[1] or match[2], match[0]
    mass=mass_binding(field,action)
    if mass is not None:return mass[:2]
    return U, ''


def control_polarity(action, label):
    """Match explicit with/without clauses to a source control's concept words."""
    concepts = lambda value: {word[:-4] if word.endswith('ment') and len(word) > 7 else word for word in ntoks(value)}
    wanted = concepts(label) - {'need', 'not', 'or', 'is', 'has', 'enable', 'enabled', 'optional'}
    if not wanted:
        return None
    markers = list(re.finditer(r'\b(without|with|no)\b', action, re.I))
    found = set()
    for index, marker in enumerate(markers):
        phrase = action[marker.end():markers[index + 1].start() if index + 1 < len(markers) else len(action)]
        if wanted <= concepts(phrase):
            found.add(marker[1].lower() == 'with')
    return next(iter(found)) if len(found) == 1 else None
