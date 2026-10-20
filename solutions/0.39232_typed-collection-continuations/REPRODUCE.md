# Воспроизведение №31

CWD — корень извлечённого solution_31 либо соответствующая solutions/<score>_typed-collection-continuations. Python3.11.9 и exact packages — requirements.txt и benchmark/final/metadata.json. Все Java fixtures только парсятся. Исторические команды установки/сервисов/моделей не запускать.

Фактически выполненные команды, CWD, UTC timestamp, exit/timeout, code/input hashes, stdout/stderr находятся в benchmark/command-index.json и связанных benchmark/overnight/Gxx/<label>/run.json. Ошибки предыдущих попыток сохранены. После переименования папки исходные абсолютные historical CWD остаются свидетельством; для нового запуска использовать текущий CWD и новые output paths. Не перезаписывать benchmark/final или assessed ZIP.

Полный tt-challenge нужен отдельно: skeleton/trainticket.json.gz, context/db-after-warmup.sql.gz, scenarios/S0–S7.json, targets/trainticket. Точные хеши основных файлов входа — development/input-sha256.json; source fingerprint — benchmark/final/summary.json, hashes исходников TT — development/protected-files.json. Исходники TT не включены: без них full TT replay не воспроизводится. Real regression source/config/skeleton/context/oracle в validation_inputs и development/oracles включены полностью. Они не являются секретной judge-разметкой.

Без запуска target apps:

```sh
PYTHONPATH=code python -B -m pytest -q -p no:cacheprovider code/tests checks/tests
python -B checks/run_regression_gate.py --output /tmp/regressions31-new
python -B checks/run_cart_profile.py --output /tmp/cart31-new
python -B checks/check_cart_profile.py --trace /tmp/cart31-new --output /tmp/cart31-new/checks.json
python -B checks/check_cart_mutations.py --trace /tmp/cart31-new --output /tmp/cart31-new/mutations
```

Это интерфейсы действительно выполненных проверок с заменённым output. Результаты текущего прогона — benchmark/regressions-final; actual exit0 основного набора1953 passed — benchmark/overnight/G14/exact-final-all-unit-checkers. Исправленный упаковщик добавляет2 meaningful negative/link controls; итоговый extracted run —1955 passed в benchmark/analytical-corrected-verification-logs/tests.stdout.txt. Format/gold — отдельные checker-процессы; inference не читает oracle/expected.

TT и точный judge archive, где TT_CHALLENGE — абсолютная папка исходного challenge:

```sh
python -B code/offline_run.py --source "$TT_CHALLENGE/targets/trainticket" --skeleton "$TT_CHALLENGE/skeleton/trainticket.json.gz" --context "$TT_CHALLENGE/context" --scenarios "$TT_CHALLENGE/scenarios" --output /tmp/answer31-new.json --report /tmp/report31-new.json
python -B "$TT_CHALLENGE/platform/evaluate_golden.py" --check "$TT_CHALLENGE/skeleton/trainticket.json.gz" /tmp/answer31-new.json --json
python -B "$TT_CHALLENGE/platform/evaluate_golden.py" "$TT_CHALLENGE/gold/S0.json" /tmp/answer31-new.json --json
python -B checks/replay_archive.py --archive solution.zip --source "$TT_CHALLENGE/targets/trainticket" --skeleton "$TT_CHALLENGE/skeleton/trainticket.json.gz" --context "$TT_CHALLENGE/context" --scenarios "$TT_CHALLENGE/scenarios" --output /tmp/archive31-new
python -B checks/repeat_prepared.py --source "$TT_CHALLENGE/targets/trainticket" --skeleton "$TT_CHALLENGE/skeleton/trainticket.json.gz" --context "$TT_CHALLENGE/context" --scenarios "$TT_CHALLENGE/scenarios" --expected submission.json --output /tmp/repeat31-new.json --repetitions 2
```

Path limit4, constraints on, observed-union. Prepared expected — comparator only; DB/context остаются исходными. Prepared measured code отличается от final только report-write helper/test; analyze/finite_report и inference state не менялись (benchmark/prepared-report-only-delta.json). Последующий exact ZIP replay проверяет final code.

Для восстановления исключённого промежуточного full report: python -B checks/stage_benchmark.py G02-bulk-contract-only --existing-snapshot --challenge "$TT_CHALLENGE" --output /tmp/G02-report31-new. Интерфейс с --output добавлен после основного прогона; именно эта команда ещё не выполнялась. Исходная фактическая команда без этого flag сохранена в command-index. Для новой current-code стадии использовать новый stage-name либо явный offline CLI. Сохранённые development/stages и benchmark/stages неизменяемы. В компактном analytical ZIP избыточные промежуточные full reports могут отсутствовать; точные omission hashes и влияние перечисляет PACKAGE_OMISSIONS.json, snapshots/comparisons и ключевые baseline/final traces сохранены.

Ещё не выполнено: свежий real holdout (точные отсутствующие входы в benchmark/holdout-availability.json), полный TT цепочный успех за локализованной границей, target/JVM execution (вне разрешённого scope). Следующий допустимый semantic эксперимент — source-generic Set<object> equals/hash callback MRE перед дальнейшим TT поиском. Ни одна из этих проверок не записана как passed.
