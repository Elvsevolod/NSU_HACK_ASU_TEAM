"""Actor language constrains contracts without inventing an authenticated session."""
import re
from .state import U


def canonical_role(role):
    return {'administrator':'admin'}.get(role.lower(),role.lower())


def actor_role(action):
    match = re.match(r'^\s*as\s+(?:(?:a|an|the)\s+)?([\w-]+)\s*,', action, re.I)
    if match:return canonical_role(match[1])
    patterns=(r'\b(?:log\s*in|sign\s*in)\s+as\s+(?:(?:a|an|the)\s+)?([\w-]+)',
        r'\b(?:log\s*in|sign\s*in)\b.*?\bwith\s+(?:the\s+)?([\w-]+)[\x27’]s\s+(?:username|credentials?|account)',
        r'\b(?:log\s*in|sign\s*in)\s+with\s+(?:the\s+)?([\w-]+)\s+(?:account|credentials?)',
        r'^\s*(?:switch|return)\s+(?:back\s+)?to\s+(?:the\s+)?([\w-]+)(?:\s+account)?[,.]?\s*$')
    for pattern in patterns:
        match=re.search(pattern,action,re.I)
        if match:return canonical_role(match[1])
    return U


def declared_roles(project, entry):
    meta = project.methods[entry]
    annotations = [*meta.get('annotations', []), *project.nodes[meta['owner']].get('annotations', [])]
    roles = set()
    for annotation in annotations:
        kind, args = annotation['name'].rsplit('.', 1)[-1], annotation.get('args', '')
        if kind in ('Secured', 'RolesAllowed'):
            values = re.findall(r'["\']([^"\']+)["\']', args)
        elif kind == 'PreAuthorize':
            # Compound expressions need the actual security context.
            match = re.fullmatch(r'\(\s*"has(?:Any)?Role\(([^()]*)\)"\s*\)', args)
            values = re.findall(r"'([^']+)'", match[1]) if match else []
        else:
            values = []
        roles.update(value.removeprefix('ROLE_').lower() for value in values)
    return roles
