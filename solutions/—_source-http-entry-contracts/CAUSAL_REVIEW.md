# №33: исполнение, конфигурация и четыре локальные модели

Текущий этап E21: [causal review E17–E21](development/IMPLEMENTATION_E21.md), [точные stage patches](development/history-review-e21/review.json), [новый парный model downstream](development/semantic-model-review-e20/review.json). 2370 code tests,158 checker tests,17 integrations; TT answers прежние. Ниже сохранены исторические выводы E2–E16, они не заменяют текущие результаты.

E15–E16: [отдельный causal review](development/IMPLEMENTATION_E16.md). 2339 code tests, 158 checker tests, 17 integrations; TT answers unchanged. Дальнейшие ограничения NL не объявлены исправленными. Исторический E14 ниже сохранён.

Приняты общие исправления HTTP/source/config и ограниченных native contracts. Модель по умолчанию не подключена: ranking стал лучше на части запросов, но реальные NL-цепочки не улучшились. Общая очередь R01–R08 ещё не закрыта: полные независимые semantic holdout не подтверждены. Это проверенный результат текущей итерации, а не заявление об универсальности.

Текущий код — E14: 2319 code tests, 158 checker tests и17 интеграций проходят. [Полный разбор E8–E14](development/IMPLEMENTATION_E14.md), [stage diffs и intermediate failures](development/transport-review-e14/review.json). Feign URL/query, source bean decoding, native builder и error/wire/origin witnesses проверены в ограниченном scope. Intermediate E10–E13 потеряли три ребра TT S4 из-за неверного constructor guard; E14 восстановил все восемь answers. Ниже результаты E2/E7 сохранены как историческая база. Новое ranking-only сравнение40 queries опубликовано отдельно; прежние четыре модельных пилота не переобъявляются новыми.

## База и происхождение

Рабочая аналитика заменена 19.10.2026 в 04:48:22 UTC. Её SHA256: `4a1c9f985808aacd4e35816d028779586407c13bf74f938df14a71b859a29592`. В хронологию входят только последующие команды. Черновые static cells уже существовали до этой отметки; их не приписываем новой фазе. После замены сохранены 73 записи команд №32 с датами, flags, code hashes и exit status, включая 25 неуспешных попыток. R02 отдельно дорабатывался до замены, затем проверялся общими R03/full regression gates. [Полная хронология команд](development/review33-final/parent32-after-report-replacement.json).

| Фаза после замены отчёта | Гипотеза и фактическая проверка |
| --- | --- |
| 04:49–04:52 UTC, №32 R01–R03 | Static cells, typed List search, Stream completion и Optional проверены source fixtures; после нескольких красных gates полный локальный набор прошёл. |
| 04:53–05:18 UTC, №32 R04/R05 | Проверены source/generated Set keys, first-loss и один stop-only readonly summary; общий engine rewrite не принимался. |
| 05:18–06:40 UTC, №32 R06–R08 | Order/producer controls, frozen A/B, Qwen preflight/pilot и release checks. Полные команды и промежуточные ошибки сохранены. |
| Последующий release №32 | На сайте 1666111, A, 0,22997; хуже №31 на 0,16235. Локальный S0 при этом 0,8008928571. Best №5 восстановлен отдельной прежней операцией. |
| Аналитический пакет №32 v4 | Та же оценённая реализация, дополненная source transfer пакетами и перепроверкой архивов. Его revision v4 не означает новую оценку или иной judged code. |
| №33 HTTP/source | Before: 9 failed / 5 passed; after: 14 passed. Отдельно 3 красных may-receiver примера, затем 17/17 с HTTP controls. Первую ошибку окружения tree_sitter не считали behavioral before. |
| №33 semantics/config | Non-null collection shapes; явная charset; конфигурация по deployment. Финал: 2065 code tests, 76 checker tests, 17 интеграционных запусков проходят. |
| №33 models | Все три дополнительно разрешённые модели и Qwen реально запущены; четыре downstream режима проверены одним interpreter на одном коде. |

На этапе E2 все 6553 файла родителя №32 совпадали с зафиксированными hashes. Защищённые входы и прежние варианты также совпадали. Из исторического общего manifest выделена только разрешённая изменяемая сводная таблица `solutions/README.md`. [Аудит E2](development/review33-final/integrity.json), [19 изменённых файлов E2](development/review33-final/changed-code.json), [патч E2](development/review33-final/parent32-to33.patch). Дополнительные патчи E3/E4 и их source/input hashes сохранены в отдельных stage reviews.

## Принятые изменения

HTTP routing использует declared deployment units без substring alias и без произвольного первого unit. Explicit request сохраняет повторные headers, body/null/missing и native JSON kinds. В известном Boot deployment plain mapped class исключается из handler candidates; неизвестные registration механизмы остаются диагностикой. Broad source may-edges дополнительно ограничены доказанным типом receiver; неизвестный local type не угадывается.

Spring Data collection result сохраняет non-null carrier при неизвестных элементах. List, ArrayList, LinkedList, Set, HashSet и Collection проверены через return, поле, alias и параметр; source/default nullable method остаётся nullable. Конкретный runtime class абстрактного Set/Collection не выдумывается.

Computed static в №32 уже проходил несекретный пример `ab`, но с необоснованным ASCII-default. №33 разделяет source initialization и charset: при наблюдаемой кодировке возвращает `YWI=` либо `AGEAYg==`, при отсутствующей default charset показывает boundary. Два прежних positive fixtures получили явный UTF‑8 runtime input; их assertions не ослаблены, а отрицательный absent-charset control добавлен. Конструктор Java byte array остаётся отдельным неподдержанным механизмом; typed byte[] проверен как adapter input. Основание — [JDK String.getBytes](https://docs.oracle.com/javase/8/docs/api/java/lang/String.html#getBytes--).

Конфигурация стала локальной для deployment. Приоритет profile-файлов и документов, placeholders и supplied ordered propertySources проверены до/после; неизвестный Config Server не выдаётся за локальный environment. Использованы идеи №13 через текущий IR, без копирования старого ядра. [Карта доноров и границы](DONOR_MAP.md).

## Реальные проекты: что исправилось до модели

Organization и library взяты из зафиксированных публичных source snapshots другой предметной области. Oracle инженерный, частичный; target applications не запускались. Исходные сценарии/контекст и required facts не подгонялись к predictions. В №33 убран служебный `http_request` hint из NL-входа; explicit headers сериализованы в текст запроса. Parent №32 и №33 сравнивались на одинаковом изменённом пакете, а не на разных входах.

На paired №32 organization explicit выбирал handler в 8/10 шагов и проходил 2/10 всех частичных step checks. После HTTP entry repairs: handlers 10/10, step checks 3/10. После receiver constraints: step checks 5/10, state 6/10. Library explicit handler/wire поднялись с 0/11 до 11/11, но дальнейшие обязательства остаются красными. [Paired comparison](benchmark/transfer-receiver-comparison/comparison.json).

| Режим E2, один код №33 | Organization explicit / NL: partial step checks | Library explicit / NL |
| --- | --- | --- |
| Baseline A | 5/10 / 1/10 | 0/11 / 0/11 |
| Production lexical B | 5/10 / 1/10 | 0/11 / 0/11 |
| CodeRank, те же A-produced candidates | 5/10 / 0/10 | 0/11 / 0/11 |
| CodeRank, расширенный source pool | 5/10 / 0/10 | 0/11 / 0/11 |

Explicit mode в модельных режимах не вызвал encoder. По каждой попытке сохранены полный request/response/state/conditions и audit counters: network, target processes, oracle reads равны нулю. [Матрица команд](benchmark/final-model-matrix/matrix.json), [результаты](development/review33-final/downstream-summary.json).

Это не 24 retrieval actions. Здесь 21 execution step на режим: 10 organization и 11 library. Шесть старых gates означали 2 приложения × 3 retrieval profiles, каждый с explicit/NL проверкой. Эти знаменатели не взаимозаменяемы.

## Модели: одинаковый корпус, раздельные dev/test

Новый общий corpus содержит 101 canonical handler: organization 20, library 71, licensing 10. Каждая модель и common Unicode BM25 получили одинаковые handler IDs и тексты owner/method/HTTP/request fields/полного метода, с model cap 512 tokens. Это новый общий контроль, не переименование исторического retrieval B. Production B отдельно проверен в downstream таблице выше.

Development: 24 разрешимых и 8 отказных запросов, уже известных по прошлым проверкам. Test: новый licensing source snapshot, 12 разрешимых и 4 отказных запроса, RU/EN. Labels составлены по исходникам до inference. Публичное pretraining overlap неизвестно. Последующий tuning на этих результатах потребует нового untouched test. [Frozen protocol и hashes](development/model-pilot/frozen-v2/protocol.json).

| Модель | Revision | Pooling / input |
| --- | --- | --- |
| UniXcoder | `5604afdc964f6c53782a6813140ade5216b99006` | Официальный encoder-only token/mask, non-pad mean, L2; 768 dimensions |
| CodeT5+ 110M | `d9f3a534af4252f04b10cd9f78e05037542d10f6` | Обученная projection первого токена, L2; 256 dimensions |
| CodeRankEmbed | `3c4b60807d71f79b43f3c4363786d9493691f8b1` | CLS, официальный query prefix, L2; 768 dimensions |
| Qwen3-Embedding-0.6B | `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3` | Штатный last-token SentenceTransformer, instruction prefix, L2; 1024 dimensions |

CodeRank custom modules прочитаны полностью до импорта. Его custom Hub/torch loader не вызывался: direct audited class + strict local safetensors. CodeT5 воспроизведён stock T5 encoder с обученной projection, без исполнения remote code. Старый UniXcoder position_ids сверён с детерминированным буфером; strict загрузка не пропускает обученных параметров. Неудачные первые попытки сохранены. [Audit](development/model-metadata/AUDIT.md), [pins](development/model-metadata/pins.json), [weight checks](benchmark/model-weights-acquisition/results.json).

CodeRank выбран по development MRR до открытия test outcomes. Пороги тоже выбраны только на development и не исправлялись по test.

| Модель | Dev R@1 /24 | Dev MRR | Test R@1 /12 | R@3 /12 | R@6 /12 | Test MRR | Correct accepts /12 | False reject /12 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Common BM25 | 8 | 0,4012 | 4 | 7 | 9 | 0,4987 | 0 | 12 |
| UniXcoder | 6 | 0,4154 | 4 | 8 | 10 | 0,5245 | 0 | 12 |
| CodeT5+ | 8 | 0,5046 | 8 | 10 | 11 | 0,7813 | 4 | 8 |
| CodeRank | 11 | 0,6080 | 8 | 12 | 12 | 0,8194 | 2 | 10 |
| Qwen | 7 | 0,5910 | 9 | 10 | 11 | 0,8244 | 1 | 11 |
| CodeRank + source context | 11 | 0,6050 | 7 | 12 | 12 | 0,7778 | 2 | 10 |

На test все режимы имеют 0 false accepts /4 refusal queries и 0 accepted-wrong /12 answer queries. Это сопровождается низкой coverage, а не решённой задачей. На dev CodeRank допускает 2 wrong accepts; context variant — 1. Candidate availability 24/24 dev и 12/12 test у всех моделей. Test top1 по EN/RU, каждый /6: BM25 4/0, UniXcoder 3/1, CodeT5 5/3, CodeRank 5/3, Qwen 5/4; выбор победителя по этому test не переигрывался.

Первичная context ablation была no-op: same-method chunks уже содержались в полном методе. Она сохранена. До чтения test outcomes заморожена отдельная DTO/callee extension: максимум четыре AST chunks с ограничением 192 source lexical tokens, плюс FQN metadata; 64/101 документов расширены. Общий tokenizer cap 512 сохранён, 12/101 документов truncated. Качество не выросло. Не выдаём truncation за доказанную единственную причину. [Context provenance](development/model-pilot/frozen-context-v4/context-provenance.json).

## Фактическая стоимость

Один стенд: Apple M4 Pro, 24 ГиБ, macOS 15.7.3, Python 3.11.9; MPS, fp32, 4 threads, document batch 4/query batch 1. Fresh process — модель отсутствовала в процессе; OS page cache не очищался. Три отдельные warm forwards записаны в raw outputs. Для base пилотов cache hits 0/149. Для context extension 85 hits/64 misses; её query-time нельзя сравнивать с uncached encoding.

| Модель | Load, с | Index 101 units, с | Encoding 48 queries, с | Peak RSS, байт | MPS driver, байт |
| --- | --- | --- | --- | --- | --- |
| UniXcoder | 1,576 | 4,512 | 4,036 | 1 433 894 912 | 1 111 179 264 |
| CodeT5+ | 1,295 | 2,090 | 2,689 | 1 316 700 160 | 1 128 890 368 |
| CodeRank | 1,454 | 2,275 | 0,853 | 1 491 402 752 | 1 119 698 944 |
| Qwen | 1,677 | 6,043 | 1,637 | 3 966 435 328 | 5 302 927 360 |

RSS и MPS driver не суммируются как независимые физические области. Base vectors JSON занимает от 807 763 до 3 243 608 байт и включает document vectors плюс query cache; это не размер одних source embeddings. Размеры weights, provenance, model calls, truncation/UNK, per-language/family metrics и все batch timings: [machine-readable summary](development/review33-final/model-summary.json), [paired raw rows](benchmark/model-comparison-checked.json). Численный SLA не утверждался. CPU/другой Mac/quantization не измерены.

## Следующие доказанные границы

В [ledger из 168 записей](development/review33-final/causal-ledger.json) разделены source handler availability, записанный candidate pool, rank, отказ, request wire, JSON binding, execution/completion и состояние. Если trace не разделяет два слоя, они так и названы совместно.

1. В ledger E2 Library теряла DTO из-за `JsonProperty`. E3 устранил этот первый дефект; E4 восстановил literal Feign prefix. E6 проводит source interceptor header в Inventory; текущая граница — derived predicate по составному ID. Полная цепочка остаётся красной; исправленные binding/path/header сами по себе не подтверждают state/permissions. Это нельзя чинить повышением embedding score.
2. Organization remote/list/lambda цепочки упираются в generic consumer/cast и неизвестный Feign path. Требуется отдельный minimal source example и сохранение generic element type через `forEach`, а не восстановление broad may-targets.
3. В настоящем TT контексте clock не задан; login останавливается на JJWT/date frontier. Клиентский UI guard также блокирует выбранную форму. Отдельный runtime-input control с clock/charset проходит explicit login→contacts с фактическим userId, но не засчитывается S0 и не доказывает frontend. [Текущая проверка](benchmark/ui-lineage-02.json).
4. Для заявления о полном переносе нужны source-reviewed полные state/remote/refusal obligations на независимых проектах. Существующие partial oracle и licensing retrieval test эту работу не заменяют.

Финальное решение по этой итерации: принять проверенные HTTP/config/native repairs; сохранить baseline retrieval по умолчанию; отклонить включение CodeRank и context extension. GraphCodeBERT/GNN, новая тяжёлая архитектура, обучение и reranker не запущены. Три разрешённых дополнительных модели действительно выполнены, а не оставлены metadata-only планом.

Поставка должна проверяться по отдельному receipt распакованного архива. Документ фиксируется до этой проверки; [матрица статусов](STATUS_MATRIX.md) не подменяет последующий результат.

Исторический E7: source Long ID создавался, но следующий HTTP binder получал unknown. Canonical decimal carrier с обратной связью устранил потерю без выбора числового ID. [E6/E7 evidence](development/integral-http-review/review.json). В E14 strong explicit healthcare11/11, employment10/11; source absence-of-handler и NL gates не пройдены. Oracle остаётся source-engineered в заявленном deployment slice, без dynamic ground truth и второго автора.

На40 новых retrieval queries CodeRank с прежними thresholds дал raw R1 13/32 и MRR0.54535 против6/32 и0.36997 у общего Unicode BM25. Accept0/40 у обоих: ranking benefit не превратился в использование кандидатов. Новые query families после этого измерения становятся development. Модель не подключена к default и не получила права менять execution/values. [Новые paired rows и cost](benchmark/real-retrieval-evaluation.json).
