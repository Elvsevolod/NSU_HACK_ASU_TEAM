"""Input fingerprints and artifact checksums for reproducible static analysis."""
import hashlib
import json
from pathlib import Path
from baseline_nlp import front_files


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(project):
    digest = hashlib.sha256(json.dumps(project.skeleton, sort_keys=True).encode())
    for file, source in sorted(project.sources.items()):
        digest.update(file.encode())
        digest.update(source)
    for file in sorted(front_files(str(project.root))):
        digest.update(str(Path(file).relative_to(project.root)).encode())
        digest.update(Path(file).read_bytes())
    return digest.hexdigest()
