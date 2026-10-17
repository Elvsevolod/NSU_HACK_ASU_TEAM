import argparse
import json
from pathlib import Path
from analyzer.frontend import Frontend
from analyzer.local_models import DenseEncoder, manifest_at
from analyzer.project import Project
from analyzer.retrieval import Retrieval


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--skeleton', type=Path, required=True)
    parser.add_argument('--scenarios', type=Path, required=True)
    parser.add_argument('--model-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    project = Project(args.skeleton, args.source)
    frontend = Frontend(project)
    retrieval = Retrieval(project, frontend)
    paths = sorted(args.scenarios.glob('*.json')) if args.scenarios.is_dir() else [args.scenarios]
    actions = [s['action'] for path in paths for s in json.loads(path.read_text())['steps']]
    manifest = manifest_at(args.model_manifest)
    encoder = DenseEncoder(manifest['embedding'])
    retrieval.prepare(actions, encoder)
    encoder.close()
    retrieval.save(args.output, project)
    print(json.dumps({'handlers': len(retrieval.ids), 'ui_sites': len(frontend.sites),
                      'actions': len(set(actions)), 'index': str(args.output)}))


if __name__ == '__main__':
    main()
