"""Download pinned public weights, hash them, and write an offline manifest."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from analyzer.local_models import sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).resolve().parents[1] / 'models-manifest.json')
    args = parser.parse_args()
    root = args.directory.resolve()
    root.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(args.manifest.read_text())
    for kind in ('embedding', 'parser'):
        spec = manifest[kind]
        repo, revision = spec['repo'], spec['revision']
        local = root / spec['path']
        destination = local if kind == 'embedding' else local.parent
        filenames = list(spec['sha256'])
        command = [str(Path(sys.executable).with_name('hf')), 'download', repo, *filenames,
                   '--revision', revision, '--local-dir', str(destination)]
        print('Downloading', kind, repo, revision, flush=True)
        subprocess.run(command, check=True)
        for filename, expected in spec['sha256'].items():
            asset = local / filename if kind == 'embedding' else local
            if sha256(asset) != expected:
                raise ValueError('Downloaded model checksum mismatch: ' + str(asset))
    (root / 'models.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(root / 'models.json', flush=True)


if __name__ == '__main__':
    main()
