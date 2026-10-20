"""Freeze an E27 recheck, preserving the completed E20 protocol and scripts."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

V = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stage = 'E27-readiness-witnesses'
    manifest = json.loads((V/'development/stages'/stage/'code-sha256.json').read_text())
    assert all(sha(V/'code'/name) == digest for name, digest in manifest.items())
    files = {}
    for original, target in [('shadow_semantic_models33.py', 'shadow_semantic_models_e27.py'),
                             ('review_semantic_models33.py', 'review_semantic_models_e27.py')]:
        source = V/'checks'/original; output = V/'checks'/target
        assert not output.exists()
        value = source.read_text().replace('E20-response-only-history', stage).replace('e20', 'e27').replace('E20', 'E27')
        output.write_text(value)
        files['checks/'+original] = sha(source)
        files['checks/'+target] = sha(output)
    original = V/'development/semantic-model-preregistration-e20.json'
    prereg = json.loads(original.read_text())
    assert all(sha(V/name) == digest for name, digest in prereg['files'].items())
    prereg.update(created_at=datetime.now(timezone.utc).isoformat(), stage=stage,
        reason='Final-core paired recheck after E22 literal constraint, E23 repeat intent, E24 response eligibility and E27 passive diagnostics. No model/threshold/context/label changes.',
        previous_protocol_sha256=sha(original), source_code_sha256=manifest)
    prereg['files'].update(files)
    output = V/'development/semantic-model-preregistration-e27.json'
    assert not output.exists(); output.write_text(json.dumps(prereg, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'stage': stage, 'preregistration_sha256': sha(output), 'files': files}))


if __name__ == '__main__':
    main()
