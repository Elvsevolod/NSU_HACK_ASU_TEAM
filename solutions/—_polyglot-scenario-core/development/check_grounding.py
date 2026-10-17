"""Evaluate handler retrieval separately; references are not runtime inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
from check_corpus import declarations
from polygraph.grounding import Grounder
from polygraph.project import Project


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--java', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reference_path = Path(__file__).with_name('request_reference.json')
    reference = json.loads(reference_path.read_text())
    report = {'reference_sha256': hashlib.sha256(reference_path.read_bytes()).hexdigest(), 'scope': reference['scope'],
              'engine': 'rank_bm25.BM25Plus(delta=0) with source operation evidence; scores are not probabilities', 'projects': {}}
    for language, root in [('java', args.java), ('python', args.python)]:
        skeleton, names, sources, errors = declarations(root, language, [])
        project = Project(root, skeleton)
        grounder = Grounder(project)
        results = []
        for case in reference[language]:
            expected = names[case['entry']]
            candidates = grounder.candidates(case['action'])
            ranked = [{'handler': project.methods[project.endpoints[i].method].skeleton_id, 'score': score} for i, score in candidates]
            actual = {row['handler'] for row in ranked}
            results.append({**case, 'expected': expected, 'candidates': ranked, 'top1_correct': bool(ranked) and ranked[0]['handler'] == expected,
                            'exact_set': actual == {expected}, 'candidate_recall': int(expected in actual),
                            'candidate_precision': int(expected in actual) / len(actual) if actual else None})
        report['projects'][language] = {'source_files': len(sources), 'source_sha256': sources, 'parse_errors': errors,
                                        'endpoints': len(project.endpoints), 'cases': results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({language: {'cases': len(info['cases']), 'top1_correct': sum(case['top1_correct'] for case in info['cases']),
                                 'exact_set': sum(case['exact_set'] for case in info['cases'])} for language, info in report['projects'].items()}))


if __name__ == '__main__':
    main()
