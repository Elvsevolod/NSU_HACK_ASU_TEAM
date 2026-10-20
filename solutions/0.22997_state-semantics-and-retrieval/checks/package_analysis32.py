"""Verify extracted runnable content, then freeze the complete solution32 handoff."""
import argparse
import gzip
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from archive_support import execute, verified_manifest

V = Path(__file__).resolve().parents[1]
ROOT = V.parents[1]
PREFIX = 'solution_32/'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def hashes(folder):
    return {p.relative_to(folder).as_posix(): sha(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and not {'__pycache__', '.pytest_cache'} & set(p.parts)
            and p.suffix != '.pyc' and p.name != '.DS_Store'}


def select():
    selected, omitted = {}, []
    for path in sorted(V.rglob('*')):
        if path.is_dir():
            continue
        assert not path.is_symlink(), path
        relative = path.relative_to(V).as_posix()
        parts = set(Path(relative).parts)
        if {'__pycache__', '.pytest_cache', '.git', '.venv'} & parts or path.suffix == '.pyc' or path.name == '.DS_Store':
            continue
        reason = None
        if relative.startswith('development/inputs/superseded/'):
            reason = 'Obsolete report explicitly replaced by the user; excluded from current authority and payload.'
        elif relative in ('benchmark/site/server-1666111.zip', 'benchmark/site/restored-server-1666114.zip'):
            reason = 'Exact duplicate candidate or historical best ZIP; verified hashes and visible receipts retained.'
        elif path.suffix == '.json' and path.with_suffix('.json.gz').exists():
            if gzip.decompress(path.with_suffix('.json.gz').read_bytes()) == path.read_bytes():
                reason = 'Byte-identical raw JSON duplicate; complete gzip payload retained.'
        if reason:
            omitted.append({'path':relative, 'sha256':sha(path), 'bytes':path.stat().st_size, 'reason':reason})
            continue
        assert path.name not in ('cookies.json', 'storage-state.json', 'session-state.json') and path.suffix != '.har', path
        if path.suffix in ('.json', '.txt', '.md', '.py', '.properties', '.sql'):
            import re
            assert not re.search(rb'participant_\d+@techarena_nsuts\.ru', path.read_bytes()), path
        selected[relative] = path
    return selected, omitted


def runnable_digest(selected):
    mapping = {name:sha(path) for name,path in selected.items()
               if name.startswith(('code/', 'checks/', 'validation_inputs/', 'development/oracles/'))
               or name == 'requirements.txt'}
    return hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--replay-label', default='analysis-archive-replay')
    args = parser.parse_args()
    output = args.output.resolve()
    assert not output.exists()
    output.parent.mkdir(parents=True, exist_ok=True)
    assert json.loads((V/'benchmark/packaging/judge-replay/verification.json').read_text())['passed']
    assert json.loads((V/'benchmark/server-verification.json').read_text())['passed']
    assert json.loads((V/'benchmark/site-best-restored.json').read_text())['passed']
    judged = json.loads((V/'benchmark/packaging/judge-build.json').read_text())
    assert sha(V/'solution.zip') == judged['sha256']
    assert sha(V/'submission.json') == judged['submission_sha256']
    assert hashes(V/'code') == hashes(V/'development/stages/E7-release/code')

    protected = json.loads((V/'development/protected-files.json').read_text())
    immutable = {name:digest for name,digest in protected.items() if name != 'solutions/README.md'}
    changed = [name for name,digest in immutable.items() if not (ROOT/name).exists() or sha(ROOT/name) != digest]
    parent = json.loads((V/'development/parent31-sha256.json').read_text())
    parent_changed = [name for name,digest in parent['files'].items() if sha(Path(parent['parent'])/name) != digest]
    assert not changed and not parent_changed, (changed, parent_changed)
    save(V/'development/integrity-post-site.json', {'passed':True, 'immutable_files':len(immutable),
         'changed_immutable_files':changed, 'parent_files':len(parent['files']), 'changed_parent_files':parent_changed,
         'mutable_registry':'solutions/README.md appended only; original bytes verified by registry-append.json'})

    model_indexes = ROOT/'.model-pilot32/qwen-index'
    for project in sorted(model_indexes.iterdir()):
        if not project.is_dir():
            continue
        target = V/'model_indexes'/project.name
        target.mkdir(parents=True, exist_ok=True)
        for name in ('manifest.json', 'vectors.json'):
            if (target/name).exists():
                assert sha(target/name) == sha(project/name)
            else:
                shutil.copyfile(project/name, target/name)
    selected, omitted = select()
    digest = runnable_digest(selected)
    assert Path(args.replay_label).name == args.replay_label
    evidence = V/'benchmark/packaging'/args.replay_label
    evidence.mkdir(exist_ok=False)
    replay = {'passed':False, 'runnable_content_sha256':digest, 'runs':{},
              'targets_started':False, 'model_inference_repeated':False,
              'scope':'Exact extracted current code/checks/fixtures; TT replay separately verified from assessed judge ZIP; model measurements retained from actual pilot.'}
    with tempfile.TemporaryDirectory(prefix='solution32-analysis-') as temporary:
        extracted = Path(temporary)/'solution_32'
        candidate = Path(temporary)/'preflight.zip'
        preflight_manifest = {PREFIX+name:sha(path) for name,path in selected.items()}
        with zipfile.ZipFile(candidate, 'x', zipfile.ZIP_STORED) as archive:
            for name,path in selected.items():
                archive.write(path, PREFIX+name)
            archive.writestr('MANIFEST.json', json.dumps(preflight_manifest))
        with zipfile.ZipFile(candidate) as archive:
            verified_manifest(archive, 'MANIFEST.json')
            archive.extractall(temporary)
        assert hashes(extracted/'code') == hashes(V/'code')
        environment = {**os.environ, 'PYTHONPATH':str(extracted/'code'), 'PYTHONDONTWRITEBYTECODE':'1'}
        commands = {
            'tests':[sys.executable, '-B', '-m', 'pytest', 'code/tests', 'checks/tests', '-q', '-p', 'no:cacheprovider'],
            'profiles':[sys.executable, '-B', 'checks/run_regression_gate.py', '--output', str(evidence/'profiles')],
        }
        for label,command in commands.items():
            replay['runs'][label] = execute(command, extracted, environment, evidence, label, 240)
            save(evidence/'verification.json', replay)
        replay['passed'] = all(run['returncode'] == 0 for run in replay['runs'].values())
        save(evidence/'verification.json', replay)
    assert replay['passed'], replay
    state_path = V/'development/implementation-state.json'
    state = json.loads(state_path.read_text())
    state['current_goal'] = 'real-transfer-inputs'
    state['next_action'] = 'Two untouched real Java/Spring ready packages are absent; transfer remains not_run. Before further model adoption, repair refusal/history selection using independent source evidence.'
    state['delivery'] = {'judge_replay':'benchmark/packaging/judge-replay/verification.json',
                         'analysis_runnable_replay':evidence.relative_to(V).as_posix()+'/verification.json',
                         'site':'benchmark/site-score.json', 'best_restored':'benchmark/site-best-restored.json'}
    state['updated_at'] = datetime.now(timezone.utc).isoformat()
    save(state_path, state)

    omissions = {'schema':'package-omissions/32', 'omitted_outputs':omitted,
        'external_inputs':[
            {'path':'tt-challenge/', 'reason':'Original read-only target/source/config/skeleton/context/scenarios; not copied into this version.', 'hashes':'development/protected-files.json and development/input-sha256.json'},
            {'path':'.model-pilot32/venv and qwen weights', 'reason':'Runtime and 1.19GB weights not bundled; exact revision, installed-wheel hashes and actual model file hashes retained. model_indexes holds vectors/manifests only; offline model use requires the matching downloaded snapshot.'},
            {'path':'two new real Java/Spring application holdouts', 'reason':'No ready source/config/skeleton/context/chain/oracle packages supplied; not_run, not a claimed successful transfer.'},
            {'path':'previous solution directories', 'reason':'No mutable dependency on their code. B00-parent31 is frozen inside this package; old best5 only represented by its verified ZIP hash and receipts.'}],
        'included':'All available stage snapshots, full measured stage traces, failed and successful runs, current report, local regression fixtures/oracles, Qwen pilot metrics/predictions and vector indexes, assessed solution.zip, site scores and restoration proof.',
        'credentials':'Live judge credentials, browser session/cookies and external account secrets excluded. Static credentials and keys in supplied source fixtures are test data.'}
    save(V/'PACKAGE_OMISSIONS.json', omissions)
    selected, ignored = select()
    assert runnable_digest(selected) == digest
    intro = '''# Аналитический архив решения № 32

Главный результат — [CAUSAL_REVIEW.md](solution_32/CAUSAL_REVIEW.md). Затем прочитайте [README](solution_32/README.md), [матрицу R01–R08](solution_32/STATUS_MATRIX.json), [ограничения](solution_32/LIMITATIONS.md) и [воспроизведение](solution_32/REPRODUCE.md).

Рабочая аналитика только одна: solution_31_models_and_static_analysis_review.md, SHA256 4a1c9f985808aacd4e35816d028779586407c13bf74f938df14a71b859a29592; она включена в solution_32/development/inputs. Заменённый пользователем прежний текст исключён.

Сайт: № 32 = **0.22997**, A, 1666111; № 31 = 0.39232, дельта **−0.16235**. Все семь сценариев ухудшились. Это реальная регрессия скрытого качества, несмотря на успешные bounded semantic checks. Лучшая неизменённая посылка № 5 восстановлена: 1666114, A, 0.90987. Точные сценарные оценки, дельты, исходные снимки и хеши — в benchmark/site-score.json и benchmark/site-best-restored.json. Оценённые code/submission/solution.zip после judgement не изменялись.

R01–R06 проверены в ограниченной области, а не как полная совместимость с JVM/Spring. R07 dataset/harness готовы; lexical B отклонён. Локальный Qwen3-Embedding-0.6B реально запущен: Recall@1 43/47 на development, но четыре false accepts и неверный downstream handler в cart NL; adoption отклонён. Основной retrieval — A. CodeRank и reranker не запускались. Два свежих реальных transfer-пакета отсутствуют; всю очередь нельзя объявить verified.

Проверены 2080 тестов и 17 интеграционных команд. Точный judge ZIP отдельно распакован и повторно дал побайтно тот же TT submission; 2012 тестов кода прошли из него. Аналитический пакет содержит полный code/checks/fixtures, актуальный отчёт, snapshots и причинные ledger всех 103 шагов, реальные неудачные эксперименты и модельные measurements. TT target и модельные weights/runtime не включены; model_indexes — только vectors/manifests. Полный список исключений — [PACKAGE_OMISSIONS.json](solution_32/PACKAGE_OMISSIONS.json).

Начальная задача следующего анализа: объяснить регрессию № 32 через stage/step deltas и новый first loss, проверить честность order/initializer boundaries и отдельно source-backed отказ/history при retrieval. Не считать потерянные рёбра готовым gold и не возвращать их вручную. Время отдельных прогонов не является доказательством ускорения одинаковой точной работы. Все проекты/парафразы текущего retrieval-набора — development/regression, а не untouched test.

MANIFEST.json покрывает все payload bytes. benchmark/packaging/analysis-archive-replay содержит реально выполненную проверку распакованного runnable content; внешний .check.json рядом с ZIP содержит hash именно конечного ZIP. README внутри вложенного judge ZIP — неизменённый pre-site snapshot, внешний README дополнен результатом сайта.
'''.encode()
    manifest = {PREFIX+name:sha(path) for name,path in selected.items()}
    manifest['START_HERE.md'] = hashlib.sha256(intro).hexdigest()
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name,path in selected.items():
            archive.write(path, PREFIX+name)
        archive.writestr('START_HERE.md', intro)
        archive.writestr('MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    with zipfile.ZipFile(output) as archive:
        verified_manifest(archive, 'MANIFEST.json')
        assert hashlib.sha256(archive.read(PREFIX+'solution.zip')).hexdigest() == judged['sha256']
        assert not any(name.startswith(PREFIX+'development/inputs/superseded/') for name in archive.namelist())
    result = {'passed':True, 'archive':str(output), 'sha256':sha(output), 'bytes':output.stat().st_size,
        'members':len(manifest)+1, 'all_member_hashes_and_crc_match':True,
        'runnable_content_sha256':digest, 'extracted_runnable_checks_passed':True,
        'inner_judge_zip_sha256':judged['sha256'], 'site_score':'0.22997', 'best_restored':'0.90987',
        'current_report_only':True, 'all_queues_verified':False,
        'weights_runtime_and_live_credentials_included':False}
    save(output.with_suffix('.check.json'), result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
