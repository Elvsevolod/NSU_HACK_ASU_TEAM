"""Only solution 30 and its evidence; no unused clones or all-history checkout."""
import argparse,hashlib,json,re,zipfile
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    assert not args.output.exists();args.output.parent.mkdir(parents=True,exist_ok=True)
    for name in ('benchmark/archive-replay/replay.json','benchmark/server-verification.json','benchmark/protected-integrity.json'):
        assert json.loads((V/name).read_text())['passed'],name
    omitted_roots={'holdout-source-repo','holdout-candidate-company','holdout-candidate-cart'}
    files=[file for file in sorted(V.rglob('*')) if file.is_file() and
        not ({'__pycache__','.pytest_cache','.git','.venv'}|omitted_roots)&set(file.parts) and
        file.suffix not in ('.pyc','.class','.jar') and file.name!='.DS_Store' and
        file.relative_to(V).as_posix() not in ('benchmark/restored-best-server.zip',)]
    # Never put the testing-system credentials in the analyst bundle.
    for file in files:
        if file.suffix in ('.json','.md','.txt','.py'):
            data=file.read_bytes()
            assert not re.search(rb'participant_\d+@techarena_nsuts\.ru',data),file.name
    manifest={'solution_30/'+file.relative_to(V).as_posix():sha(file) for file in files}
    intro='''# Решение № 30 после solution_29_next_steps_review.md

Начать с solution_30/IMPLEMENTATION_REVIEW.md и development/requirements.json.
В архиве одна новая реализация, все её стадии, полные traces, проверки,
новый отрицательный real-source профиль и неизменная оценённая solution.zip.
Это ограниченная итерация: TT поиск остаётся частичным, новый cart holdout
не пройден. Не выдавайте число тестов, формат, S0 или одни edge counts за
качество скрытых сценариев/универсальность. Code/state/read-effects регрессии,
неудачная E и её исправления E2/H сохранены.

Код: solution_30/code. Архив судье: solution_30/solution.zip (submission.json
в корне). Финальные 103 шага: benchmark/final/analysis-report.json.gz;
сравнения: benchmark/comparisons; состояния и source-producer witnesses:
benchmark/flow-witnesses-final, document-journey, legacy-final и tt-frontier.json.
Строгий Piggy 8+3: benchmark/real-final; старые v2/v3 oracle сохранены.
Новый real profile: validation_inputs/shopping-cart, cart-freeze-v2.json и
benchmark/cart-transfer-final/checks.json. Его oracle — required-edge subset,
precision/IoU не измерены, успех не заявлен.

Повтор: requirements.txt; из solution_30/:

PYTHONPATH=code python -B -m pytest -q code/tests
python -B checks/run_document_journey.py --output /tmp/documents30
python -B checks/check_document_mutations.py --input /tmp/documents30
python -B checks/run_cart_profile.py --output /tmp/cart30
python -B checks/check_cart_profile.py --trace /tmp/cart30 --output /tmp/cart30-check.json

Для TT нужен исходный tt-challenge той же версии; он намеренно не дублируется.
Сайт, серверная копия и восстановление лучшего № 5: benchmark/site-score.json,
server-verification.json и site-best-restored.json. Внутренний judge ZIP создан
до оценки; его README с ещё неизвестным score сохранён без пересборки.
Внешний README дополнен фактически полученной оценкой.

DeepSeek, внешние LLM API и целевые сервисы не запускались. Учетных данных
тестирующей системы нет. MANIFEST.json проверяет каждый файл, кроме самой
hash-карты и этой записки. Неиспользованные сетевые clones и вся история
других вариантов в архив не включены.
'''
    with zipfile.ZipFile(args.output,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in files:z.write(file,'solution_30/'+file.relative_to(V).as_posix())
        z.writestr('START_HERE.md',intro);z.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(args.output) as z:
        assert z.testzip() is None and all(hashlib.sha256(z.read(name)).hexdigest()==digest for name,digest in manifest.items())
    result={'passed':True,'archive':str(args.output.resolve()),'sha256':sha(args.output),'bytes':args.output.stat().st_size,
            'files':len(files)+2,'all_member_hashes_match':True,'judge_credentials_included':False,
            'previous_solution_trees_included':False,'unused_source_clones_included':False}
    args.output.with_suffix('.check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
