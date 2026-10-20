"""Package a checked variant without virtual environments, caches or model weights."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def solution_number(readme):
    return re.search(r'Решение № (\d+(?:\.\d+)?)', readme).group(1)


def main():
    root = Path(__file__).resolve().parents[1]
    answer = json.loads((root / 'submission.json').read_text())
    report = json.loads((root / 'benchmark/analysis-report.json').read_text())
    evaluation = json.loads((root / 'benchmark/evaluation.json').read_text())
    format_check = json.loads((root / 'benchmark/format_check.json').read_text())
    if (not answer['scenarios'] or format_check['status'] != 'format_only'
            or not report.get('run_complete') or set(answer['scenarios']) != set(report['requested_scenarios'])):
        raise ValueError('Answer or saved format verification is missing')
    manifest = {'solution': solution_number((root / 'README.md').read_text()),
                'created_utc': datetime.now(timezone.utc).isoformat(),
                'site_score': None, 'local_score': evaluation['score'],
                'submission_sha256': digest(root / 'submission.json'),
                'seconds': report['elapsed_seconds'], 'peak_rss_bytes': report['peak_rss_bytes'],
                'analysis_status': {sid: r['analysis_status'] for sid, r in report['scenarios'].items()},
                'code_sha256': {p.relative_to(root).as_posix(): digest(p)
                                for p in sorted((root / 'code').rglob('*')) if p.is_file()
                                and not any(part in ('__pycache__', '.pytest_cache', 'cache') for part in p.parts)}}
    (root / 'benchmark/run.json').write_text(json.dumps(manifest, indent=2) + '\n')
    paths = [p for p in root.rglob('*') if p.is_file()
             and not any(part in ('.venv', '__pycache__', '.pytest_cache', 'cache') for part in p.relative_to(root).parts)
             and p.name not in ('.DS_Store', 'solution.zip', 'archive-check.json')
             and not p.name.startswith('reproduction-')]
    archive = root / 'solution.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(paths):
            zipped.write(path, path.relative_to(root).as_posix())
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() is not None or zipped.read('submission.json') != (root / 'submission.json').read_bytes():
            raise ValueError('Archive integrity check failed')
        check = {'sha256': digest(archive), 'bytes': archive.stat().st_size,
                 'files': len(zipped.namelist()), 'root_submission_matches': True, 'testzip': 'passed'}
    (root / 'benchmark/archive-check.json').write_text(json.dumps(check, indent=2) + '\n')
    print(json.dumps(check, indent=2))


if __name__ == '__main__':
    main()
