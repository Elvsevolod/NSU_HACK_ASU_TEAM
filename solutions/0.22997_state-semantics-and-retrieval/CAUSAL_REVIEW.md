# Causal review: решение № 32

Единственная рабочая аналитика: development/inputs/solution_31_models_and_static_analysis_review.md, SHA256 4a1c9f985808aacd4e35816d028779586407c13bf74f938df14a71b859a29592. Пользователь заменил старый файл в ходе работы. Новый §12.2 принят полностью; исходный аналитический текст не переписывался под новые результаты.

## Принятый результат

R01–R06 приняты в ограниченной проверенной области, с сохранением неопределённости и prefix effects. R07 benchmark/harness и R08 adapter/runtime приняты как инструменты проверки. Retrieval B и Qwen C не включены по умолчанию. Два real transfer gates остаются not_run; вся очередь не имеет статуса verified. Полная матрица — STATUS_MATRIX.json.

R01 переносит mutable statics в ScenarioState, выполняет source initializers по порядку, сохраняет ошибки/статус между обращениями и изолирует сценарии. Исходные source contexts не становятся graph methods. При финальном ревью воспроизведена и исправлена ошибка обёртки Error: before/after сохранены. Неизвестный subtype Throwable не выдаётся за точный ExceptionInInitializerError. Результирующий TT JSON от этого последнего ремонта не изменился.

R02 сохраняет int kinds indexOf/lastIndexOf, направление equals, -1 и downstream exceptions; source namesake не становится native. R03 реализует finite sequential forEach/forEachOrdered с реальными callback effects, failure prefix, Stream completion и Optional.isEmpty. Unknown callback/membership не превращается в выполненный normal suffix.

R04 использует source hashCode/equals либо доказанный default Lombok scalar leaf. Изменённый ключ сохраняет прежнее hash placement; reentrancy и неподдержанные генераторы — boundaries. Отдельный E2 восстановлен из reviewed R04-only diff поверх E1c и затем измерен; он не выдаётся за исторический снимок до R05.

R05 записывает первые unknown/control losses с source spans/hashes, guards, types, prefix, actual effects и widened footprint. Одно доказательство read-only residual сохраняет unrelated rows, но останавливает выполнение. Tiny equipment oracle экспортирован для трёх парных on/off случаев (шесть наблюдений) с полными E/C/R/D, wire и state. Во всех прочих опасных остатках остаётся консервативная invalidation. Source-cause ledger находится в benchmark/implementation/R05/stage-causal-ledger; поздний Error repair — в R01/E6-to-release-ledger. Количество предупреждений не используется как quality score.

R06 убирает dump-order proof. Числовое source ordering, ties/null и bounded permutations проходят через List/array/JSON/request; каждый путь сохраняет свою строку и выбранный ID. Полное producer agreement нельзя вывести из одного увиденного пути. Cart v4 сохраняет все v3 obligations и добавляет legal-order coverage; исторический v3 не изменён. Legacy step «Read first owner» теперь сохраняет unknown ID вместо ошибочного owner 1. Эта oracle delta описана отдельно; historical v2 не объявляется пройденной.

## Измерения и ошибки поиска

Заморожены 57 запросов: 55 NL и два explicit controls, 47 NL answer cases и восемь refusal cases. Train/test splits пусты; все available applications/families — development/regression. Labels выведены инженерным чтением source/config, не ответами текущего анализатора. Corpus: TT 280 contracts (262 canonical handlers), Piggy 9, cart 10, Petclinic 8 и synthetic Unicode 2. Корпус содержит разрешённые source facts/chunks, без gold/traces/обсуждений решения. Worker не читает labels; все три модельных сравнения имеют ноль сетевых попыток и forbidden reads.

| Retrieval | Recall@1 | Recall@3 | MRR | False accept / 8 | False reject / 47 | Wrong accepted handler |
|---|---:|---:|---:|---:|---:|---:|
| A, №31 | 21/47 | 26/47 | 0.514894 | 4 | 18 | 8 |
| B, Unicode lexical | 26/47 | 28/47 | 0.585816 | 1 | 19 | 5 |
| Qwen, тот же пул A | 28/47 | 30/47 | 0.617021 | 3 | 20 | 0 |
| Qwen, expanded corpus B | 43/47 | 47/47 | 0.957447 | 4 | 5 | 1 |

B отклонён: при более высоком ranking растёт false reject; в cart NL пропущены steps 3–4. Qwen резко улучшает межъязыковое совпадение, но не доказывает наличие handler для no-handler действия. Cart step 3 выбирает неверный controller; последующая history lineage расходится. Ни binding, ни execution engine не получают права выдумать поля/IDs из model score. Explicit control проходит; это изолирует ошибку выбора. Эти результаты не исправлялись под сохранённый oracle. Все raw predictions, paired errors и denominators по project/language/family находятся в R07/R08 evidence. nDCG не вычислялась: graded labels нет. Нулевой ranking у explicit controls в старой grouped таблице означает bypass, а не retrieval failure; обе wire-проверки успешны.

Qwen revision, tokenizer, pooling, файлы и runtime закреплены; собственный код модели не исполнялся. Model load при построении индекса 1.202 с, все пять индексов построены за 52.982 с; peak RSS 3927425024 байта. TT document encoding — 39.082 с, шесть из 560 units длиннее 512 tokens и усечены tokenizer. Это локальный MPS прогон, не CPU/cloud benchmark. Два platform process probes заблокированы при подготовке; target processes не запускались. Warm samples и fresh-process measurements опубликованы раздельно, OS cache не контролируется. CodeRank и D не измерены, поэтому не названы проигравшими моделями.

## Train Ticket и S6

S0 остаётся 0.8008928571428572; E/C/R/D — 0.8285714285714286/0.625/1.0/0.75. Submission SHA256 `7c9e2664e30368f7509f871941070c72c721ef2f76fefa1340f334ee4c3f75ce`. Все 103 шага сопоставлены по source/request/guard provenance, а не ordinal alternative. Последний Error repair не изменил union. S6 prediction delta к №31: `{"executes": {"added": 1, "removed": 16}, "calls": {"added": 1, "removed": 11}, "remote": {"added": 0, "removed": 6}, "data": {"added": 0, "removed": 5}}`. Это изменение прогнозов, а не hidden gold.

Known-input search, полный NL scenario и UI lineage различаются. Финальные isolated probes показывают collection-order completion budget и unresolved source initializer effects; R06 может открыть честную неопределённость раньше прежнего HTTP Set<Ticket> frontier. Сохранённое R04 продвижение за Set frontier не означает финальную успешную search→booking→payment цепочку. UI payMyOrder отправляет orderId/tripId; userId/price не добавлены. Source token/login/session producer для полной цепочки остаётся незавершённым обязательством. Отдельный source-UI payload success при известном исходном order не доказывает этот общий путь.

## Проверки и следующий шаг

2080 tests/checkers и 17 release integration runs проходят; известные source-only fixtures/negative mutations сохранены. 24137 immutable файлов прежнего protected manifest и 534 parent files не изменены. solutions/README.md — разрешённый изменяемый registry, уже изменённый до начала этого turn; он отдельно исключён из исторического inherited integrity comparison. Все core code/input/stage hashes, команды, stderr, time/RSS и diffs сохранены.

Следующая работа с наибольшим обоснованием — source-backed отказ и history-aware выбор handler, затем два новых real ready packages по подготовленной схеме. Сначала нужны независимые данные и полный oracle, а не более крупная модель, увеличение path budget или ручное восстановление S6 edges. Сайт и упаковка записываются отдельными artifacts после их фактической проверки.

## Реальная оценка сайта

№ 32 отправлен как 1666111: A, **0.22997**. По сравнению с № 31 общий score снизился на **0.16235**, все семь сценариев ухудшились. Точные значения и дельты сохранены в benchmark/site-score.json; локальный S0 не изменился. Скачанный серверный ZIP совпал с оценённым solution.zip побайтно. Это регрессия скрытого качества; локальная корректность отдельных native-контрактов не доказывает полноту сценарных графов. Прямых оснований приписывать падение одному ремонту без hidden gold нет. Причинные stage deltas и новые first-loss witnesses позволяют поставить следующий независимый эксперимент; возвращать исчезнувшие рёбра вручную нельзя.

Восстановлен исходный ZIP лучшего № 5: посылка 1666114, A, 0.90987. Серверный архив восстановления имеет исходный SHA256 f574de87739df8a679fff57d632b792c3a4742de7cb1d146d9b92fd2d7db0e46. Результат № 32 не заменён этой оценкой. Новая реализация после site judgement не менялась.
