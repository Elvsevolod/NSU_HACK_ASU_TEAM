# Решение №33 — source-http-entry-contracts

Рабочий этап E25:2418 code tests,159 checker tests и17 integrations; TT answers совпали с E21. [Изменения E22–E25](development/IMPLEMENTATION_E25.md), [stage diffs](development/request-history-review-e25/review.json). Доставленные ниже E21/v5 архивы сохраняют свой прежний код; [Компактный E25](solution-e25.zip) проверен фактическим извлечением; [receipt](benchmark/e25-candidate-replay/replay.json). Полный аналитический v5 относится к E21 и не содержит новых E22–E25 изменений. Цель активна.

Текущая редакция E21 продолжает очередь R01–R08. Сохранены исправления static/Stream/Set/ORM, source HTTP/Feign/Jackson и типизированных значений. Добавлены целое JSON-тело NL с порядком полей и ограниченный выбор чтения по завершённым ответам предыдущих шагов. Модель в стандартный запуск не включена.

| Показатель | Проверенный результат |
| --- | --- |
| Score сайта | —; №33 не отправлялся |
| Открытый S0 | 0,8008928571428572 |
| S0 E/C/R/D IoU | 0,8285714286 /0,625 /1 /0,75; remote oracle пуст |
| Проверки | 2370 code tests,158 checker tests,17 integrations |
| Восемь ответов TT | Совпали с E14 |
| TT wall / peak RSS | 47,970 с /526680064 bytes, Python3.11.9 |
| Полный semantic transfer | failed/partial; цель активна |

```sh
python -m pip install -r requirements.txt
python -B code/offline_run.py --source ../../tt-challenge/targets/trainticket --skeleton ../../tt-challenge/skeleton/trainticket.json.gz --context ../../tt-challenge/context --scenarios ../../tt-challenge/scenarios --output /tmp/answer33.json --report /tmp/report33.json
python -B -m pytest -q -p no:cacheprovider code/tests
```

Сеть, model weights и внешние API стандартному анализатору не нужны. Целевые приложения не запускаются; skeleton и начальное состояние — входные данные. Опциональный lexical режим включается `--retrieval lexical`. Он остаётся development-кандидатом; его новые правила не объявлены независимым transfer успехом.

[Текущие изменения](development/IMPLEMENTATION_E21.md), [JSON body E15–E16](development/IMPLEMENTATION_E16.md), [stage diffs/receipts](development/history-review-e21/review.json), [матрица](STATUS_MATRIX.md), [ограничения](LIMITATIONS.md), [команды](REPRODUCE.md), [единый causal review](CAUSAL_REVIEW.md).

UniXcoder, CodeT5+110M embedding, CodeRankEmbed и Qwen выполнены offline на этом Mac: [старое полное сравнение](development/review33-final/model-summary.json). Затем CodeRank проверен с прежними порогами на40 новых retrieval queries: R1 13/32 против6/32 у общего BM25; accept0/40 у обоих. [Ranking metrics](benchmark/real-retrieval-evaluation.json). Отдельный новый запуск на полных employment/healthcare цепочках дал lexical12/44 точно прошедших шагов выполнения против CodeRank5/44, плюс8/8 отказов у обоих. [Парные ошибки, типы, рёбра, состояние и стоимость](development/semantic-model-review-e20/review.json). Same-candidates и expanded результаты совпали; default adoption — experiment_rejected.

До первых inference были закреплены исходники двух новых реальных проектов и23 scenarios/74steps. Теперь они наблюдались и являются development для дальнейшей настройки. Explicit strong control: employment10/11, healthcare11/11. Полные NL/wire/origin gates не пройдены. [Строгий E21 checker](development/transport-checker-e21-lexical/checks.json). [Почему отсутствие route пока не превращается в404](development/missing-route-preflight/DECISION.md).

[Компактный E21](solution-e21.zip) проверен фактическим извлечением:2370 тестов, восемь совпавших ответов и offline counters0. [Replay receipt](benchmark/e21-candidate-replay/replay.json). [Полный аналитический E21 v5](../../exports/solution_33_source_contracts_models_analysis_v5.zip) проверен фактическим извлечением:16 427 hashes,matching code/eight answers,fresh S0/format,history/JSON и paired model metrics reproduced. [Финальный receipt](../../exports/solution_33_source_contracts_models_analysis_v5.check.json). Документы внутри ZIP сохранены до этой финальной проверки; receipt находится рядом. Последний ранее доставленный аналитический архив — [E14 v4](../../exports/solution_33_source_contracts_models_analysis_v4.zip) с [receipt](../../exports/solution_33_source_contracts_models_analysis_v4.check.json). Его код и прежние архивы не переписывались.

SHA256 текущего ответа: `95927fa5eb50b7d9f26d13a1c9e224bb2b803a9a6b07aa1c42996beaa15c371d`. Промежуточная потеря трёх рёбер S4 в E10–E13 исправлена в E14; история сохранена. №32, tt-challenge, sample и прежние runs неизменны. DeepSeek и целевые JVM не использовались. Полная совместимость Java/Spring и универсальность не заявлены.
