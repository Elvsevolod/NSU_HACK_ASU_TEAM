"""New solution and its evidence only; no all-history repository bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

VARIANT=Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists();args.output.parent.mkdir(parents=True,exist_ok=True)
    for name in ('archive-replay/replay.json','server-verification.json','protected-integrity.json'):
        assert json.loads((VARIANT/'benchmark'/name).read_text())['passed'],name
    omitted={'benchmark/restored-best-server-1665515.zip','development/analysis-package.txt'}
    files=[p for p in sorted(VARIANT.rglob('*')) if p.is_file() and
        p.relative_to(VARIANT).as_posix() not in omitted and
        not {'__pycache__','.pytest_cache','.git','.venv'}&set(p.parts)
        and p.suffix not in ('.pyc','.class','.jar') and p.name!='.DS_Store']
    manifest={'solution_29/'+p.relative_to(VARIANT).as_posix():sha(p) for p in files}
    intro='''# Решение № 29 после solution_28_failure_analysis.md

В архиве одна новая реализация и её проверочные материалы. Начать с
solution_29/IMPLEMENTATION_REVIEW.md и solution_29/development/requirements.json.
Это ограниченный ремонт на базе № 28; полное восстановление TT NL-цепочек и
универсальность не заявлены. Не засчитывайте format/S0/число тестов как скрытое
качество. Отдельно учитывайте неуспешные и неполные реальные NL-профили.

Код: solution_29/code. Оценённая посылка: solution_29/solution.zip.
Финальная полная трасса: solution_29/benchmark/final/analysis-report.json.gz.
Все этапы с полными Request/state: solution_29/benchmark/stages и development/stages.
Site verdict, серверная копия и восстановление лучшего варианта: benchmark/site-score.json.
Исходная аналитика и code.patch: development. Вся проверка обходится без DeepSeek.

Для PiggyMetrics используются validation_inputs/piggymetrics и независимые oracle
development/oracles/*.oracle-v3.json. V2 сохранён. Runner не читает oracle;
check_real_journey/check_semantic_projection читают его после inference.
Пример из solution_29/:

python -B checks/run_real_journey.py --input validation_inputs/piggymetrics --output /tmp/piggy29 --path-limit 4
python -B checks/check_real_journey.py --input validation_inputs/piggymetrics --oracle development/oracles/piggymetrics-main.oracle-v3.json --trace /tmp/piggy29/trace.json --output /tmp/piggy29-check.json
python -B checks/check_semantic_projection.py --input validation_inputs/piggymetrics --oracle development/oracles/piggymetrics-main.oracle-v3.json --trace /tmp/piggy29/trace.json --output /tmp/piggy29-semantic-check.json
python -B checks/run_document_journey.py --output /tmp/documents29
PYTHONPATH=code python -B -m pytest -q code/tests

Train Ticket целиком не дублируется: нужны исходные tt-challenge той же версии.
Input hashes, среда и команды указаны в benchmark/final. Целевые приложения не
запускались. MANIFEST.json покрывает все файлы; сам MANIFEST и эта записка вне
самоссылочной hash-карты. Учётных данных тестирующей системы в архиве нет.
'''
    with zipfile.ZipFile(args.output,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,'solution_29/'+p.relative_to(VARIANT).as_posix())
        z.writestr('START_HERE.md',intro)
        z.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(args.output) as z:
        assert z.testzip() is None
        assert all(hashlib.sha256(z.read(name)).hexdigest()==digest for name,digest in manifest.items())
    result={'passed':True,'archive':str(args.output.resolve()),'sha256':sha(args.output),
        'bytes':args.output.stat().st_size,'files':len(files)+2,'all_member_hashes_match':True,
        'previous_solution_trees_included':False,'judge_credentials_included':False,
        'omitted_redundant_artifacts':sorted(omitted)}
    args.output.with_suffix('.check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
