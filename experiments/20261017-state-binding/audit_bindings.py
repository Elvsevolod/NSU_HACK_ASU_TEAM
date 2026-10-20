"""Compare binding diagnostics without treating a stored unknown as resolved."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

p = argparse.ArgumentParser()
p.add_argument('variant', type=Path)
p.add_argument('--report', type=Path)
p.add_argument('--output', type=Path, required=True)
args = p.parse_args()
sys.path.insert(0, str(args.variant / 'code'))
from analyzer.project import Project
from analyzer.frontend import Frontend

root = Path(__file__).resolve().parents[2]
project = Project(root / 'tt-challenge/skeleton/trainticket.json.gz', root / 'tt-challenge/targets/trainticket')
frontend = Frontend(project)
report = json.loads((args.report or args.variant / 'benchmark/analysis-report.json').read_text())
counts, causes, rows = Counter(), Counter(), []
symbolic_steps, stored_unknown_steps = set(), set()


def unknown(value):
    if isinstance(value, dict):
        return value == {'unknown': True} or any(unknown(v) for k, v in value.items() if not k.startswith('__') or k == '__json__')
    return isinstance(value, list) and any(unknown(v) for v in value)


for sid, block in report['scenarios'].items():
    for step in block['steps']:
        alternatives = []
        for alternative_index, alt in enumerate(step['alternatives']):
            fields = project.request_fields(alt['entry'])
            missing = [k for k, typ in fields.items() if k not in alt['parameters'] and 'Header' not in typ]
            stored_unknown = [k for k, v in alt['parameters'].items() if unknown(v)]
            symbolic = [k for k, v in alt['parameters'].items() if isinstance(v, dict) and '__symbol__' in v]
            if symbolic:
                symbolic_steps.add((sid, step['n']))
            if stored_unknown:
                stored_unknown_steps.add((sid, step['n']))
            if not (missing or stored_unknown):
                continue
            site = frontend.sites.get(alt.get('ui_site'))
            path_fields = {part[1:-1] for mid, _, route in project.ix.handlers if mid == alt['entry']
                           for part in route if part.startswith('{')}
            for key in missing if alternative_index == 0 else []:
                cause = ('no_linked_ui_request' if not site else 'path_or_event_value_unknown' if key in path_fields
                         else 'ui_expression_unknown' if key in site['body_fields'] else 'field_absent_from_ui_body')
                causes[cause] += 1
                counts[key] += 1
            alternatives.append({'entry': alt['entry'], 'site': alt.get('ui_site'), 'absent': missing,
                                 'stored_unknown': stored_unknown, 'symbolic': symbolic})
        if alternatives:
            rows.append({'scenario': sid, 'step': step['n'], 'action': step['action'], 'alternatives': alternatives})
result = {'steps': sum(len(b['steps']) for b in report['scenarios'].values()),
          'occurrence_scope': 'first alternative per step; details retain all alternatives',
          'steps_with_absent_fields': sum(any(a['absent'] for a in r['alternatives']) for r in rows),
          'steps_with_stored_unknown': len(stored_unknown_steps),
          'steps_with_top_level_symbolic_params': len(symbolic_steps),
          'steps_with_absent_or_stored_unknown': len(rows), 'absent_field_occurrences': dict(counts),
          'absent_causes': dict(causes), 'frontend_sites': len(frontend.sites), 'details': rows}
args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'details'}, ensure_ascii=False))
