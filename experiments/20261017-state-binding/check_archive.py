"""Exercise the packaged analyzer from an independent extracted directory."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
VARIANT = ROOT / 'solutions/—_request-state-linking'
PYTHON = Path('/private/tmp/nsu-alternatives-venv/bin/python')
archive = VARIANT / 'solution.zip'
with tempfile.TemporaryDirectory(prefix='nsu-v9-archive-') as directory:
    extracted = Path(directory)
    with zipfile.ZipFile(archive) as source:
        assert source.testzip() is None
        source.extractall(extracted)
    before = json.loads((extracted / 'benchmark/code-sha256.json').read_text())
    for path, expected in before.items():
        assert hashlib.sha256((extracted / path).read_bytes()).hexdigest() == expected
    with (VARIANT / 'benchmark/archive-smoke.stdout.txt').open('w') as out, (VARIANT / 'benchmark/archive-smoke.stderr.txt').open('w') as err:
        process = subprocess.run([str(PYTHON), '-B', str(extracted / 'code/offline_run.py'),
            '--source', str(ROOT / 'tt-challenge/targets/trainticket'),
            '--skeleton', str(ROOT / 'tt-challenge/skeleton/trainticket.json.gz'),
            '--context', str(ROOT / 'tt-challenge/context'),
            '--scenarios', str(ROOT / 'tt-challenge/scenarios/S0.json'),
            '--output', str(extracted / 'fresh-prediction.json'), '--report', str(extracted / 'fresh-report.json')],
            cwd=extracted, env={**os.environ, 'PYTHONPATH': str(extracted / 'code'),
                                'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '317'},
            stdout=out, stderr=err, check=False)
    assert process.returncode == 0
    fresh = json.loads((extracted / 'fresh-prediction.json').read_text())
    saved = json.loads((VARIANT / 'submission.json').read_text())
    assert fresh['scenarios']['S0'] == saved['scenarios']['S0']
    result = {'passed': True, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'all_archived_code_hashes_match': True, 'fresh_extracted_S0_matches': True,
              'PYTHONHASHSEED': 317, 'application_started': False}
    (VARIANT / 'benchmark/archive-smoke.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
