"""Read-only analyzer review; generated inputs stay in this audit directory."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
VARIANT = ROOT / 'solutions/—_request-state-linking'
AUDIT = Path(__file__).resolve().parent
sys.path[:0] = [str(VARIANT / 'code'), str(VARIANT / 'code/tests')]

from builders import build
from analyzer.__main__ import analyze, serial
from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.frontend import Frontend
from analyzer.project import Project


def scenario_probe(label, sources, actions, rows=None):
    project, database, ids = build(AUDIT / 'fixtures' / label, sources,
                                   module=label, rows=rows)
    frontend = Frontend(project)
    block, report = analyze(
        project, frontend, ContractIndex(project, frontend), None, database,
        {'facts': {}, 'unresolved': []},
        {'id': label, 'steps': [{'n': i + 1, 'action': action}
                               for i, action in enumerate(actions)]},
        grounder_type=ContractGrounder)
    (AUDIT / (label + '-report.json')).write_text(
        json.dumps({'answer': block, 'report': report}, indent=2, default=serial) + '\n')
    return {
        'status': report['analysis_status'], 'unresolved': report['unresolved'],
        'confirmed_methods': [edge['target'] for edge in report['confirmed']
                              if edge['relation'] == 'executes'],
        'steps': [{'selected': step['alternatives'][0]['entry'],
                   'parameters': step['alternatives'][0]['parameters'],
                   'result': step['alternatives'][0]['result'],
                   'unresolved': step['alternatives'][0]['unresolved']}
                  for step in report['steps']],
    }


def main():
    results = {}
    catalog = {'Catalog.java': '''
        import java.util.List;
        @RestController class CatalogController {
          CatalogStore repository;
          @GetMapping("/catalog") String inspect() {
            if (repository.findAll().size() > 64) { return large(); }
            return small();
          }
          String large() { return "large"; }
          String small() { return "small"; }
        }
        @Entity @Table(name="entries") class CatalogEntry { @Id String key; }
        interface CatalogStore extends JpaRepository<CatalogEntry, String> {
          List<CatalogEntry> findAll();
        }
    '''}
    for count in (64, 65):
        label = 'catalog' + str(count)
        observed = scenario_probe(label, catalog, ['Inspect catalog'],
                                  {'entries': [{'key': 'k' + str(i)} for i in range(count)]})
        results[label] = {'expected_result': 'large' if count > 64 else 'small',
                          'actual': observed}

    for field in ('text', 'body'):
        sources = {'Memo.java': '''
            @RestController class MemoController {
              @PostMapping("/memos") Memo create(@RequestBody Memo input) { return input; }
              @GetMapping("/memos/{memoId}") String inspect(@PathVariable String memoId) {
                if (memoId.equals("m4")) { return found(); }
                return missing();
              }
              String found() { return "found"; }
              String missing() { return "missing"; }
            }
            class Memo { @Id String key; String FIELD; }
        '''.replace('FIELD', field)}
        observed = scenario_probe('memo' + field, sources,
                                  ['Create memo key "m4" ' + field + ' "Hello"',
                                   'Inspect the newly created memo'])
        results['memo' + field] = {
            'expected_first_result': {'__type__': 'Memo', 'key': 'm4', field: 'Hello'},
            'expected_second_parameters': {'memoId': 'm4'}, 'expected_second_result': 'found',
            'actual': observed,
        }

    clinic_root = AUDIT / 'petclinic-input'
    project = Project(clinic_root / 'skeleton.json', clinic_root)
    frontend = Frontend(project)
    grounder = ContractGrounder(project, frontend, ContractIndex(project, frontend),
                               None, {'facts': {}, 'unresolved': []})
    from analyzer.state import Database, ScenarioState
    database = Database(clinic_root / 'initial.sql')
    routing = []
    for verb, expected in [('GET', 'getPet'), ('PUT', 'updatePet'), ('DELETE', 'deletePet')]:
        actual = sorted(project.ix.handlers_for(verb, '/api/pets/12'))
        routing.append({'verb': verb, 'path': '/api/pets/12', 'expected_method_name': expected,
                        'actual': actual, 'passed': len(actual) == 1 and
                        project.methods[actual[0]]['name'] == expected})
    paraphrases = []
    for action, expected in [
            ('Get pet petId 12', 'getPet'),
            ('Show the pet whose identifier is 12', 'getPet'),
            ('View pet number 12', 'getPet'),
            ('Remove pet petId 12', 'deletePet'),
            ('Delete pet petId 12', 'deletePet'),
            ('Add a new pet named Luna', 'addPet'),
            ('List all pets', 'getPets'),
            ('Show all pets', 'getPets')]:
        choices, selection = grounder.step(action, ScenarioState(database))
        chosen = choices[0] if choices else {}
        mid = chosen.get('entry')
        paraphrases.append({'action': action, 'expected_method_name': expected,
                            'actual': mid, 'entry_correct': bool(mid) and project.methods[mid]['name'] == expected,
                            'parameters': chosen.get('params', {}),
                            'unresolved': chosen.get('unresolved', selection['unresolved'])})
    results['petclinic'] = {'route_probes': routing, 'language_probes': paraphrases}
    # These assertions reproduce the observed defects, not acceptance of them.
    assert results['catalog64']['actual']['steps'][0]['result'] == 'small'
    assert results['catalog65']['actual']['steps'][0]['result'] != 'large'
    assert results['catalog65']['actual']['status'] == 'complete_in_supported_model'
    assert results['catalog65']['actual']['unresolved'] == []
    assert results['memotext']['actual']['steps'][1]['parameters'] == {'memoId': 'm4'}
    assert results['memobody']['actual']['steps'][0]['result'] == 'Hello'
    assert results['memobody']['actual']['steps'][1]['parameters'] == {}
    assert all(not probe['passed'] and len(probe['actual']) == 3 for probe in routing)
    assert all(not probe['entry_correct'] for probe in paraphrases[-2:])
    (AUDIT / 'independent-probes.json').write_text(json.dumps(results, indent=2, default=serial) + '\n')
    print(json.dumps(results, indent=2, default=serial))


if __name__ == '__main__':
    main()
