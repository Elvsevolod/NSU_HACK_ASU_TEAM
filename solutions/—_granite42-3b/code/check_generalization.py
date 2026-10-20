"""Independent source fixtures and held-out retrieval/inference checks."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).parent / 'tests'))
from builders import build, INVENTORY, LIBRARY
from analyzer.__main__ import analyze, serial
from analyzer.context import read_context
from analyzer.frontend import Frontend
from analyzer.local_models import DenseEncoder, LocalParser, manifest_at
from analyzer.retrieval import Retrieval


CASES = {
    'inventory': [
        ('Reserve item1 with reservation enabled', 'StockController.reserve'),
        ('Allocate item1 in the stock system with reservation enabled', 'StockController.reserve'),
        ('Release the reservation for item1', 'StockController.release'),
        ('Undo the allocation of item1', 'StockController.release'),
        ('Inspect inventory availability for item1', 'StockController.inspect'),
        ('Show the stock status of item1', 'StockController.inspect')],
    'library': [
        ('Look up the book with key b1', 'BookController.lookup'),
        ('Read the details of book b1', 'BookController.lookup'),
        ('Search the library catalog for history', 'BookController.search'),
        ('Find catalog entries matching history', 'BookController.search'),
        ('Add a new book with key b2 and title Atlas', 'BookController.add'),
        ('Create a library book named Atlas with key b2', 'BookController.add')],
}

BEHAVIOR = {
    'inventory': ['Reserve item1 with reservation disabled'],
    'library': ['Add a new book with key b2 and title Atlas',
                'Add a new book with key b3 and title Ocean',
                'Look up the second book just created'],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model-manifest', type=Path)
    ap.add_argument('--directory', type=Path, required=True)
    ap.add_argument('--embedding-path', type=Path)
    ap.add_argument('--prepare-only', action='store_true')
    args = ap.parse_args()
    manifest = manifest_at(args.model_manifest) if args.model_manifest else None
    started = time.perf_counter()
    prepared, evaluations = [], []
    for name, sources, rows in (
            ('inventory', INVENTORY, {'reservations': []}),
            ('library', LIBRARY, {'books': [{'key': 'b1', 'title': 'A book'}]})):
        directory = args.directory / 'fixtures' / name
        project, db, ids = build(directory, sources, module=name, rows=rows,
                                  context={'date': 'The system clock is 3 February 2030.'})
        frontend, cases = Frontend(project), CASES[name]
        retrieval = Retrieval(project, frontend)
        spec = manifest['embedding'] if manifest else {'local_path': str(args.embedding_path.resolve())}
        encoder = DenseEncoder(spec)
        retrieval.prepare(list(dict.fromkeys([action for action, _ in cases] + BEHAVIOR[name])), encoder)
        encoder.close()
        retrieval.save(directory / 'retrieval.json', project)
        for action, expected in cases:
            ranking = retrieval.rankings[action]
            wanted = ids[expected]
            evaluations.append({'project': name, 'query': action, 'expected_from_source': wanted,
                                'bm25_rank': ranking['bm25'].index(wanted) + 1 if wanted in ranking['bm25'] else None,
                                'hybrid_rank': ranking['hybrid'].index(wanted) + 1 if wanted in ranking['hybrid'] else None})
        prepared.append((name, project, db, ids, frontend, retrieval))
    args.directory.mkdir(parents=True, exist_ok=True)
    metrics = {kind: {'top1': sum(row[kind + '_rank'] == 1 for row in evaluations) / len(evaluations),
                       'mrr': sum(1 / row[kind + '_rank'] if row[kind + '_rank'] else 0 for row in evaluations) / len(evaluations)}
               for kind in ('bm25', 'hybrid')}
    (args.directory / 'retrieval-comparison.json').write_text(json.dumps({'cases': evaluations, 'metrics': metrics,
        'notes': 'Queries fixed in source before model inference; no training or parameter selection on these labels.',
        'seconds': time.perf_counter() - started}, indent=2) + '\n')
    print('Retrieval:', metrics, flush=True)
    if args.prepare_only:
        return
    if not manifest:
        ap.error('--model-manifest is required for inference')
    parser = LocalParser(manifest['parser'])
    results = []
    for name, project, db, ids, frontend, retrieval in prepared:
        context = read_context(project.skeleton['context'], parser)
        action = CASES[name][0][0]
        scenario = {'id': 'independent-' + name, 'steps': [{'n': 1, 'action': action}]}
        answer, report = analyze(project, frontend, retrieval, parser, db, context, scenario)
        renamed = deepcopy(scenario)
        renamed['id'] = 'different-identifier'
        other, _ = analyze(project, frontend, retrieval, parser, db, context, renamed)
        normalize = lambda block: {(None if e['relation'] == 'executes' else e['source'], e['relation'], e['target']) for e in block['edges']}
        expected = ids[CASES[name][0][1]]
        execution = {e['target'] for e in answer['edges'] if e['relation'] == 'executes'}
        ok = expected in execution and normalize(answer) == normalize(other)
        alternatives = report['steps'][0]['alternatives']
        ok = ok and len(alternatives) == 1 and alternatives[0]['entry'] == expected
        if name == 'inventory':
            ok = (ok and ids['StockWorker.accept'] in execution and ids['Reservation.<init>'] in execution
                  and ids['StockWorker.reject'] not in execution
                  and alternatives[0]['parameters'].get('key') == 'item1'
                  and alternatives[0]['parameters'].get('enabled') is True)
        else:
            ok = (ok and ids['BookController.available'] in execution
                  and ids['BookController.missing'] not in execution
                  and alternatives[0]['result'] == 'A book')
        behavior_scenario = {'id': 'behavior-' + name, 'steps': [
            {'n': i + 1, 'action': action} for i, action in enumerate(BEHAVIOR[name])]}
        behavior_answer, behavior_report = analyze(project, frontend, retrieval, parser, db, context, behavior_scenario)
        if name == 'inventory':
            entries = {edge['target'] for edge in behavior_answer['edges'] if edge['relation'] == 'executes'}
            behavior_ok = (ids['StockWorker.reject'] in entries and ids['StockWorker.accept'] not in entries
                           and behavior_report['steps'][0]['alternatives'][0]['parameters'].get('enabled') is False)
            dependency = None
        else:
            last = behavior_report['steps'][-1]['alternatives']
            behavior_ok = bool(last) and all(item['parameters'].get('key') == 'b3' and item['result'] == 'Ocean' for item in last)
            reordered = {'id': 'missing-dependency', 'steps': [{'n': 1, 'action': BEHAVIOR[name][-1]}]}
            _, dependency = analyze(project, frontend, retrieval, parser, db, context, reordered)
            behavior_ok = behavior_ok and dependency['analysis_status'] == 'partial'
        results.append({'project': name, 'passed': ok and behavior_ok, 'basic_passed': ok,
                        'behavior_passed': behavior_ok, 'answer': answer, 'report': report,
                        'behavior_answer': behavior_answer, 'behavior_report': behavior_report,
                        'missing_dependency_report': dependency})
    (args.directory / 'generalization.json').write_text(json.dumps({'results': results, 'model_calls': parser.calls},
                                                                 indent=2, default=serial) + '\n')
    parser.close()
    if not all(row['passed'] for row in results):
        raise SystemExit('Independent model inference check failed; inspect generalization.json')
    print('Independent source projects passed', flush=True)


if __name__ == '__main__':
    main()
