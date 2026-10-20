"""Verify original inputs and variants; only the solution index may change."""
import argparse
import hashlib
import json
from pathlib import Path

VARIANT = Path(__file__).resolve().parents[1]
ROOT = VARIANT.parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=VARIANT/'benchmark/protected-integrity.json')
    output=parser.parse_args().output
    original = json.loads((VARIANT / 'development/protected-files.json').read_text())
    allowed = {'solutions/README.md'}
    os_metadata = {name for name in original if Path(name).name == '.DS_Store'}
    changed = [name for name, digest in original.items()
               if not (ROOT / name).is_file() or sha(ROOT / name) != digest]
    protected_roots = [ROOT / name for name in ('tt-challenge', 'sample', 'runs')]
    protected_roots += [p for p in (ROOT / 'solutions').iterdir() if p.is_dir() and p != VARIANT]
    # The baseline deliberately excluded environments and generated caches.
    excluded = {'.venv', '__pycache__', '.pytest_cache', '.git'}
    present = {p.relative_to(ROOT).as_posix() for folder in protected_roots
               for p in folder.rglob('*') if p.is_file() and not excluded & set(p.parts)}
    added = sorted(present - set(original))
    added_os_metadata=[name for name in added if Path(name).name=='.DS_Store']
    added_content=[name for name in added if name not in added_os_metadata]
    result = {'passed': not (set(changed) - allowed - os_metadata) and not added_content,
              'baseline_files': len(original), 'unchanged_files': len(original) - len(changed),
              'allowed_index_changes': sorted(set(changed) & allowed),
              'changed_os_metadata': sorted(set(changed) & os_metadata),
              'unexpected_changes': sorted(set(changed) - allowed - os_metadata), 'added_protected_files': added_content,
              'added_os_metadata':added_os_metadata,
              'addition_scan_exclusions': sorted(excluded),
              'scope': 'All baseline hashes checked; generated environments/caches excluded only from added-file scan. Finder metadata changes reported separately.'}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    assert result['passed']


if __name__ == '__main__':
    main()
