"""Source-only integration probe on the pinned public Petclinic REST repository.

The test harness supplies a derived skeleton, not an execution reference. This
measures extraction/selection/binding coverage, never full graph precision.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

VARIANT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(VARIANT / 'code'), str(VARIANT / 'code/tests')]
from builders import build
from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.frontend import Frontend
from analyzer.state import ScenarioState
from analyzer.__main__ import serial

parser = argparse.ArgumentParser()
parser.add_argument('--repository', type=Path, required=True)
parser.add_argument('--work-dir', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
repo = args.repository.resolve()
if args.work_dir.exists():
    raise ValueError('Use a new work directory to preserve previous probes')
source_root = repo / 'src/main/java'
sources = {p.relative_to(repo).as_posix(): p.read_text() for p in sorted(source_root.rglob('*.java'))
           if p.name != 'package-info.java'}
hashes = {name: hashlib.sha256(source.encode()).hexdigest() for name, source in sources.items()}
started = time.perf_counter()
project, db, ids = build(args.work_dir, sources, module='clinic')
frontend = Frontend(project)
index = ContractIndex(project, frontend)
grounder = ContractGrounder(project, frontend, index, None, {'facts': {}})
probes = [('Get owner ownerId 7', 'OwnerRestController.getOwner', 'ownerId', 7),
          ('Get pet petId 12', 'PetRestController.getPet', 'petId', 12),
          ('Get visit visitId 3', 'VisitRestController.getVisit', 'visitId', 3),
          ('Get specialty specialtyId 2', 'SpecialtyRestController.getSpecialty', 'specialtyId', 2)]
results = []
for action, expected, parameter, value in probes:
    choices, detail = grounder.step(action, ScenarioState(db))
    choice = choices[0] if choices else {}
    results.append({'action': action, 'expected_entry_from_source': ids[expected],
                    'selected_entry': choice.get('entry'), 'parameters': choice.get('params', {}),
                    'entry_correct': choice.get('entry') == ids[expected],
                    'parameter_correct': choice.get('params', {}).get(parameter) == value,
                    'unresolved': choice.get('unresolved', detail['unresolved'])})
route_probes = []
for verb, expected in [('GET','PetRestController.getPet'), ('PUT','PetRestController.updatePet'), ('DELETE','PetRestController.deletePet')]:
    matched = project.ix.handlers_for(verb, '/api/pets/12')
    route_probes.append({'verb':verb,'path':'/api/pets/12','expected':[ids[expected]],
                         'selected':sorted(matched),'correct':matched == {ids[expected]}})
selection_probes=[]
for action, expected in [('List all pets','PetRestController.getPets'),
                         ('List all pet types','PetTypeRestController.getAllPetTypes'),
                         ('List all owners','OwnerRestController.getOwners'),
                         ('List all visits','VisitRestController.getAllVisits')]:
    ranked=index.rank(action)
    expected_mid=ids.get(expected)
    selected=ranked[0][2]['entry'] if ranked else None
    selection_probes.append({'action':action,'expected':expected_mid,'selected':selected,
                             'correct':expected_mid is not None and selected==expected_mid})
custom = [project.nodes[tid]['fqn'] for tid in project.type_fields
          if any(a['name'].split('.')[-1] == 'JsonDeserialize' for a in project.nodes[tid].get('annotations', []))]
report = {'repository': 'https://github.com/spring-petclinic/spring-petclinic-rest',
          'commit': '2cd2f9c7a3eee55d7c6d09fa100e02341ae27070', 'tag': 'v2.1.5',
          'source_files': len(sources), 'source_lines': sum(s.count('\n') for s in sources.values()),
          'source_sha256': hashes, 'indexed_types': len(project.type_fields),
          'indexed_methods': len(project.methods), 'indexed_handlers': len(project.ix.handlers),
          'source_parse_errors': project.source_errors, 'probes': results,
          'route_probes':route_probes,'selection_probes':selection_probes,
          'entry_selection_accuracy': sum(r['entry_correct'] for r in results) / len(results),
          'parameter_accuracy': sum(r['parameter_correct'] for r in results) / len(results),
          'custom_deserializers_detected': custom, 'elapsed_seconds': time.perf_counter() - started,
          'application_started': False, 'full_graph_precision_measured': False,
          'limits': ['Skeleton supplied by source-only test harness, not organizer metadata',
                     'Inherited JPA fields, custom Jackson codecs and EntityManager queries need further support',
                     'No reference execution trace or four-relation IoU available for Petclinic',
                     'Probes cover handler selection, HTTP dispatch and literal parameters; multi-request state remains covered by separate fixtures']}
args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=serial) + '\n')
print(json.dumps({k: v for k, v in report.items() if k not in ('source_sha256', 'probes')}, ensure_ascii=False))
print(json.dumps(results, ensure_ascii=False))
