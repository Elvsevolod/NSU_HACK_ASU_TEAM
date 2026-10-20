"""Actor language constrains contracts without inventing an authenticated session."""
import re
from .state import U


def actor_role(action):
    match = re.match(r'^\s*as\s+(?:(?:a|an|the)\s+)?([\w-]+)\s*,', action, re.I)
    return match[1].lower() if match else U


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
