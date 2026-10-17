"""Paired formulas on fixed public requests, using identical project facts."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

VARIANT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VARIANT / 'code'))
from rank_bm25 import BM25L, BM25Plus
from check_corpus import declarations
from polygraph.grounding import Grounder
from polygraph.project import Project


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--java', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    args = parser.parse_args()
    reference_path = Path(__file__).with_name('request_reference.json')
    reference = json.loads(reference_path.read_text())
    report = {'scope': 'Fixed nonblind public handler-choice probes, not full execution quality',
              'reference_sha256': hashlib.sha256(reference_path.read_bytes()).hexdigest(),
              'grounding_code_sha256': hashlib.sha256((VARIANT / 'code/polygraph/grounding.py').read_bytes()).hexdigest(), 'formulas': {}}
    for language, root in [('java', args.java), ('python', args.python)]:
        skeleton, names, sources, errors = declarations(root, language, [])
        project = Project(root, skeleton)
        grounder = Grounder(project)
        for formula, factory in [('release-BM25L', BM25L), ('release-BM25Plus-delta0', lambda corpus: BM25Plus(corpus, delta=0))]:
            grounder.index = factory(grounder.documents)
            grounder.source_index = factory(grounder.extra)
            rows = []
            for case in reference[language]:
                actual = [project.methods[project.endpoints[i].method].skeleton_id for i, _ in grounder.candidates(case['action'])]
                rows.append({**case, 'expected': names[case['entry']], 'predicted': actual,
                             'top1_correct': bool(actual) and actual[0] == names[case['entry']], 'exact_set': set(actual) == {names[case['entry']]}})
            report['formulas'].setdefault(formula, {})[language] = {'source_sha256': sources, 'parse_errors': errors, 'cases': rows}
    (VARIANT / 'benchmark/retrieval-formulas.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({formula: {language: {'top1': sum(c['top1_correct'] for c in info['cases']), 'exact': sum(c['exact_set'] for c in info['cases'])} for language, info in result.items()} for formula, result in report['formulas'].items()}))


if __name__ == '__main__':
    main()
