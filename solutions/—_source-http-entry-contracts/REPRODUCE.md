# Воспроизведение №33

Текущий E21: `benchmark/history-choice-guards-full/run.json`, `benchmark/history-choice-guards-checker/run.json`, `benchmark/history-choice-guards-integration/results.json`, `benchmark/stages/E21-history-choice-guards/summary.json`. [История и patches](development/history-review-e21/review.json). Модельные E20 receipts: `benchmark/semantic-model-e20-same-command/run.json` и `benchmark/semantic-model-e20-expanded-command/run.json`; повторный расчёт без весов: `python -B checks/review_semantic_models33.py --output /tmp/semantic-model-recheck33`. Ниже — исторические команды.

E16: текущие receipts `benchmark/json-wire-ownership-full/run.json`, `benchmark/json-wire-ownership-checker/run.json`, `benchmark/json-wire-ownership-integration/results.json`, `benchmark/stages/E16-json-wire-ownership/summary.json`. Подробности [E15–E16](development/IMPLEMENTATION_E16.md). Ниже сохранены команды исторических этапов.

Рабочая директория всех команд ниже — папка решения с `code/`, `checks/`, `development/`, `benchmark/`. Для повторных запусков используйте новые output paths: сохранённые результаты не перезаписываются. Точные фактически выполненные команды с исходным cwd/interpreter/code hashes находятся в `benchmark/*-capture/run.json`, test capture directories и `benchmark/final-model-matrix/matrix.json`.

## Основной анализатор

Проверен Python 3.11.9. Модельный runtime не требуется.

```sh
python -m pip install -r requirements.txt
python -B -m pytest -q -p no:cacheprovider code/tests checks/tests
python -B code/offline_run.py --source /path/to/tt-challenge/targets/trainticket --skeleton /path/to/tt-challenge/skeleton/trainticket.json.gz --context /path/to/tt-challenge/context --scenarios /path/to/tt-challenge/scenarios --output /tmp/answer33-replay.json --report /tmp/report33-replay.json
```

Ожидаемый SHA256 ответа: `95927fa5eb50b7d9f26d13a1c9e224bb2b803a9a6b07aa1c42996beaa15c371d`. Системный clock/charset и другие отсутствующие данные не добавляйте в настоящий контекст ради совпадения. `checks/stage_benchmark.py` отдельно вызывает открытый checker только после завершения inference; engine не читает gold.

Независимые собственные integration profiles:

```sh
python -B checks/run_regression_gate.py --output /tmp/integration33-new
```

Before/after tests для HTTP, receiver, repository shapes, charset и config сохранены в отдельных capture directories. Ошибка первого запуска tree_sitter и отсутствие скопированного cart artifact не считаются behavioral regressions; исправленные повторные прогоны сохранены отдельно. Неуспешный общий checker run обнаружил только старую ссылку на не скопированный G02 artifact; тест перепривязан к настоящему обычному evidence directory №33, после чего все 76 checker tests прошли.

Текущий E14: 2319 code tests, 158 checker tests, 17 integrations. Source snapshots E2–E14 в `development/stages/` неизменяемы; промежуточный S4 regression E10–E13 сохранён. Повторить актуальные локальные controls:

```sh
python -B -m pytest -q -p no:cacheprovider code/tests/test_feign_decoder33.py code/tests/test_lombok_builder33.py code/tests/test_http_error_values33.py code/tests/test_feign_error_message33.py
```

Прежние test assertions Feign были исправлены только в части формы диагностического события: Engine.run регистрирует внешний request, а публичный request сериализован как dict. Исправленные примеры отдельно выполнены на frozen E3 и по-прежнему дают 9 fail / 2 pass. Поведенческие ожидания URL, native values, отказа и Java dispatch сохранены.

Сохранённые новые graph/state/transport traces можно проверить без запуска приложения и моделей:

```sh
python -B checks/recheck_transport33.py --runs benchmark/semantic-holdout-e14-v1 --output /tmp/transport33-e14-recheck
python -B checks/recheck_transport33.py --runs benchmark/semantic-holdout-e14-lexical-v1 --output /tmp/transport33-e14-lexical-recheck
python -B checks/evaluate_real_retrieval33.py --mode evaluate --dense benchmark/real-retrieval-coderank-02/predictions.json --output /tmp/real-retrieval33-recomputed.json
```

Expected explicit counts: employment10/11, healthcare11/11; это известные ограничения, не full transfer pass. В A/B использован один E14 code. Fixed CodeRank selection и старые thresholds находятся в `benchmark/real-retrieval-fixed-selection.json`; новый test не используется для переизбрания. Для fresh model forward используется прежний worker с `--frozen development/real-retrieval-frozen-v1`; полный фактический command/cost/audit сохранён в `benchmark/real-retrieval-coderank-02-command/run.json` и `benchmark/real-retrieval-coderank-02/predictions.json`. Веса и runtime остаются вне архива.

## Проверка модельных метрик без весов

Можно повторить checker над сохранёнными исходными vectors/predictions. Это повторная проверка измерений, а не новый model forward. Инференс уже выполнен и имеет отдельные raw logs/audit counters.

```sh
python -B checks/evaluate_code_models.py --mode evaluate --frozen development/model-pilot/frozen-v2 --predictions benchmark/model-common-bm25.json benchmark/model-unixcoder-02/predictions.json benchmark/model-codet5p/predictions.json benchmark/model-coderank-02/predictions.json benchmark/model-qwen/predictions.json --selection benchmark/model-selection-dev.json --context benchmark/model-coderank-neighbours/predictions.json --output /tmp/model33-recomputed.json
```

Checker проверяет полноту query IDs, canonical candidate pool, finite/sorted scores и frozen file hashes. Разрешимые, ambiguous и no-handler запросы имеют разные знаменатели. Eight checker controls отвергают empty/duplicate/foreign/nonfinite/unsorted output и проверяют разницу rank error, false accept и false reject. После усиления checker исходные результаты пересчитаны без изменения чисел.

## Новый локальный model forward

Нужен отдельный runtime с фактическими версиями из `development/model-metadata/runtime-freeze.txt`; einops 0.8.1 установлен отдельным overlay, его receipt сохранён. Веса в архив не включены. Их LFS SHA, revisions, лицензии и metadata snapshots приложены. Модельные испытания проведены на MPS; CPU-прогон здесь не заявлен.

Публичные download helpers для трёх дополнительных моделей:

```sh
python -B checks/acquire_code_model_metadata.py --storage /path/to/model-storage --evidence /tmp/model33-metadata-new
python -B checks/acquire_code_model_weights.py --storage /path/to/model-storage --pins development/model-metadata/pins.json --evidence /tmp/model33-weights-new
```

Далее используйте Python модельного окружения вместо `python`; Qwen directory должен содержать revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`. Для каждого model choice (`unixcoder`, `codet5p`, `coderank`, `qwen`) запускается один и тот же worker:

```sh
python -B checks/code_model_worker.py --model coderank --storage /path/to/model-storage --qwen /path/to/pinned-qwen --frozen development/model-pilot/frozen-v2 --cache /tmp/model33-cache-new --output /tmp/model33-coderank-new --device mps
```

Worker выставляет offline flags и запрещает network/process/oracle reads. Использует weights-only tensor loading либо safetensors. Query prefix/pooling и custom code hashes заданы в `checks/code_model_encoders.py`; непроверенный remote code не загружается. Source/DTO context ablation использует `development/model-pilot/frozen-context-v4` и `--context`. Не меняйте пороги или победителя по test outcomes и не называйте повторный licensing run новым untouched holdout.

## Парное исполнение

Source-only index содержит document vectors, не сохранённые query answers. При новом запуске CodeRank кодирует реальные actions цепочки; источники и canonical text сверяются перед использованием vectors. Из модельного окружения:

```sh
python -B checks/run_shadow_matrix33.py --output /tmp/model33-downstream-new --storage /path/to/model-storage --qwen /path/to/pinned-qwen
```

Полный source/SQL/scenarios/partial oracle для organization и library лежит в `development/transfer/`. Oracle читает только checker после inference. Сравнение двух готовых matrix outputs:

```sh
python -B checks/check_transfer_followup.py --before /tmp/model33-downstream-new/baseline --after /tmp/model33-downstream-new/dense-expanded --output /tmp/model33-comparison-new
```

Exit 0 у этого comparator означает успешное вычисление отчёта, а не зелёный transfer gate: смотрите явные `partial_passed`, `state_passed`, `full_semantic_transfer_verified=false`. Все четыре downstream режима используют path limit 4 и прежний completion budget; модель не управляет порядком путей.

## Проверка компактного ZIP

`checks/replay_archive.py` извлекает точный кандидат в отдельную временную папку, проверяет member hashes, строит S0–S7 и запускает code tests. Веса не требуются:

```sh
python -B checks/replay_archive.py --archive solution-e4.zip --source /path/to/tt-challenge/targets/trainticket --skeleton /path/to/tt-challenge/skeleton/trainticket.json.gz --context /path/to/tt-challenge/context --scenarios /path/to/tt-challenge/scenarios --output /tmp/archive33-e4-replay-new
```

Успех требует полного совпадения всех восьми ответов, зелёных code tests и нулевых offline audit counters. Финальный receipt проверки аналитического архива поставляется рядом с ZIP: архив не может содержать собственный итоговый SHA256. Внутри находятся manifest и программа повторной проверки.

Для аналитической редакции v2 выберите E4 candidate и metadata явно; сохранённый `solution.zip` относится к E2:

```sh
python -B checks/check_analysis33.py --archive /path/to/solution_33_source_contracts_models_analysis_v2.zip --extracted /tmp/analysis33-e4-extracted-new --output /tmp/analysis33-e4-check-new --candidate solution-e4.zip --metadata benchmark/e4-candidate-metadata.json
```

Новые frozen service slices и сценарии находятся в development/semantic-holdout-packages-v1. Повторить отдельный проект можно командой `python -B checks/run_semantic_holdouts33.py --project healthcare --output /tmp/healthcare33-new` (либо employment). --retrieval lexical меняет только ranker. Exit1 при выполненных дочерних процессах означает не пройденный semantic gate; checks.json разделяет runtime_succeeded и качество. Explicit-script — внешний тестовый клиент с source route templates и previous-response references; NL inputs этих recipes не содержат. Ожидаемые graph/state не читаются inference, network/process/reference audit равен0. Старые raw A/B checks сохраняют первоначальный checker; исправленный пересчёт всех трёх профилей — development/integral-http-review/*-checks.json.
