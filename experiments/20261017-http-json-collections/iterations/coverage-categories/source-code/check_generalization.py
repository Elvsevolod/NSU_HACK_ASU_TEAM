"""Reproducible microprojects: changed domains, stateful requests and REST/data wiring."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'tests'))
from builders import build, INVENTORY, LIBRARY
from analyzer.__main__ import analyze, serial
from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.frontend import Frontend
from analyzer.project import Project
from analyzer.state import Database


def run(project, database, scenario):
    frontend = Frontend(project)
    block, report = analyze(project, frontend, ContractIndex(project, frontend), None, database,
                            {'facts': {}, 'unresolved': []}, scenario, grounder_type=ContractGrounder)
    return block, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    results = []
    for name, sources, actions, rows in [
        ('inventory', INVENTORY, ['Reserve key "r4" with enabled true', 'Reserve key "r5" with enabled false'], {'reservations': []}),
        ('library', LIBRARY, ['Add book key "b2" title "Second"', 'Lookup book key "b2"', 'Lookup book key "absent"'], {'books': []}),
    ]:
        project, database, ids = build(args.directory / 'fixtures' / name, sources, module=name, rows=rows)
        scenario = {'id': 'independent-' + name, 'steps': [{'n': i + 1, 'action': action} for i, action in enumerate(actions)]}
        before = deepcopy(database.tables)
        block, report = run(project, database, scenario)
        alternatives = [s['alternatives'][0] for s in report['steps']]
        assert database.tables == before
        if name == 'inventory':
            assert alternatives[0]['entry'] == ids['StockController.reserve']
            assert alternatives[0]['parameters'] == {'key': 'r4', 'enabled': True}
            assert alternatives[1]['parameters'] == {'key': 'r5', 'enabled': False}
            assert alternatives[0]['result']['key'] == 'r4'
            assert alternatives[1]['result'] is None
            assert alternatives[1]['state_after']['database_rows']['inventory.reservations'] == 1
        else:
            assert [a['entry'] for a in alternatives] == [ids['BookController.add'], ids['BookController.lookup'], ids['BookController.lookup']]
            assert alternatives[1]['result'] == 'Second'
            assert alternatives[2]['result'] == 'absent'
        renamed = deepcopy(scenario)
        renamed['id'] = 'another-arbitrary-name'
        other, _ = run(project, database, renamed)
        def normalize(answer):
            return {('scenario' if e['relation'] == 'executes' else e['source'], e['relation'], e['target']) for e in answer['edges']}
        assert normalize(block) == normalize(other)
        results.append({'project': name, 'passed': True, 'scenario': scenario, 'answer': block, 'report': report})

    # Two independently indexed services, merged into the supplied skeleton schema.
    sources = {
        'shop': {'Shop.java': '''@RestController class Shop {
          RestTemplate http;
          @PostMapping("/orders") Receipt place(@RequestBody Request input) {
            return http.postForObject("http://ledger/charges", new HttpEntity(new Charge(input.sku)), Receipt.class);
          }
        }
        class Request { String sku; }
        class Receipt { String key; }
        class Charge { String key; Charge(String key) { this.key = key; } }'''},
        'ledger': {'Ledger.java': '''@RestController class Ledger {
          Store repository;
          @PostMapping("/charges") Charge charge(@RequestBody Charge input) { repository.save(input); return input; }
          @GetMapping("/charges/{key}") Charge lookup(@PathVariable String key) { return repository.findByKey(key); }
        }
        @Entity @Table(name="charges") class Charge { @Id String key; }
        interface Store extends JpaRepository<Charge,String> { Charge save(Charge item); Charge findByKey(String key); }'''}
    }
    root = args.directory / 'fixtures' / 'remote'
    merged = {'project': 'fixture', 'nodes': {}, 'edges': [], 'context': {}}
    dump = []
    for module, files in sources.items():
        _, _, _ids = build(root / module, files, module=module, rows={'charges': []} if module == 'ledger' else {})
        skeleton = json.loads((root / module / 'skeleton.json').read_text())
        for node in skeleton['nodes'].values():
            if node.get('file'):
                node['file'] = module + '/' + node['file']
            for origin in node.get('origin', []):
                if origin.get('file'):
                    origin['file'] = module + '/' + origin['file']
        merged['nodes'].update(skeleton['nodes'])
        merged['edges'].extend(skeleton['edges'])
        dump.append((root / module / 'initial.sql').read_text())
    (root / 'skeleton.json').write_text(json.dumps(merged))
    (root / 'initial.sql').write_text('\n'.join(dump))
    project, database = Project(root / 'skeleton.json', root), Database(root / 'initial.sql')
    scenario = {'id': 'independent-remote', 'steps': [
        {'n': 1, 'action': 'Place order sku "item-7"'}, {'n': 2, 'action': 'Lookup charge key "item-7"'}]}
    block, report = run(project, database, scenario)
    assert any(e['relation'] == 'remote' and e['source'].startswith('method:shop:')
               and e['target'].startswith('method:ledger:') for e in block['edges'])
    assert any(e['relation'] == 'data' and e['target'] == 'res:table:ledger.charges' for e in block['edges'])
    assert report['steps'][1]['alternatives'][0]['result']['key'] == 'item-7'
    results.append({'project': 'remote', 'passed': True, 'scenario': scenario, 'answer': block, 'report': report})
    path = args.directory / 'generalization.json'
    path.write_text(json.dumps({'scope': 'independent microprojects, not evidence of general repository support',
                                'results': results}, ensure_ascii=False, indent=2, default=serial) + '\n')
    print(json.dumps({'passed': True, 'projects': [r['project'] for r in results]}))


if __name__ == '__main__':
    main()
