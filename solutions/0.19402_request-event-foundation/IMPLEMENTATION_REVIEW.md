# Реализация инженерного разбора — вариант № 27

18 октября 2026 года. Исходная точка — № 23; контрольные линии № 5, 12, 23 и 26 сохранены. Требования взяты из всего доступного `analyzer_review_full_answer.docx`. Рекомендации о внешних движках выполнены как эксперименты с решением по результату, а не как интеграция каждого перечисленного инструмента. Численные SLA не назначались.

## Карта требований

| ID | Результат и проверка | Граница |
| --- | --- | --- |
| R01 | Заморожены входы и ручные oracles; № 5/12/23/26/27 сравнивались на одинаковых входах. `benchmark/final-synthetic-candidate/comparison.json`, `final-public-controls/comparison.json` | Небольшой корпус; исправления разметки публичных профилей сохранены в новой v2 |
| R02 | Actor ограничивает контракты по source-ролям; неподтверждённые равные варианты дают неоднозначность; username не подставляется вместо accountId. `test_review_request.py`, `test_review_history.py` | Произвольный NL остаётся эвристическим |
| R03 | Immutable Request, общий initial/remote binder, HTTP/UI/NL-эквивалентность, UUID/repeated query, media, missing/null. `request.py`, `http_binding.py`, `test_review_request.py` | Не полная Spring registration/security/converters |
| R04 | CollectionRef/ObjectRef: producer, FQN/deployment, контейнер, порядок; singleton/empty/unknown и UI scopes. `history_refs.py`, `test_review_history.py` | Произвольные frontend-фреймворки не поддержаны |
| R05 | do/while, continue/return/throw/finally, isBlank, split, receiver context, field/instance initializers. `test_review_java_control.py` | Java regex — явное подмножество, это не полная JVM |
| R06 | Общий fork state/env/args/receiver/history/heap; local/remote mixed completions продолжаются отдельно. `test_review_alternatives.py` | При completion budget продолжение останавливается с диагностикой, будущие связи только candidates |
| R07 | Версионированные opaque effects: reachable DTO/Map/List/closure, source footprint, callbacks, normal/throw; Logger определяется типом. `call_effects.py`, `test_review_effects.py` | Unknown global footprint остаётся явным предположением |
| R08 | Request/callsite/guard/value/assumption witnesses, отдельные static candidates. `event_values.py`, `verify_run.py`, `test_review_events.py`, `export-policy-comparison.json` | Условный прогноз не объявляется доказанным выполнением |
| R09 | Общая JSON/ORM-проекция reflection roots, сохранены direct source constructors и nested helper/setter effects. `test_review_projection.py` | Provider-generated effects вне профиля диагностируются |
| R10 | SQL отдельно от commit: deferred save/flush, REQUIRED, checked/runtime rollback, identity/cache/dirty checking, lazy references/collections. `persistence.py`, `test_review_persistence.py` | IDENTITY условен на Hibernate-compatible профиль; нестандартные propagation/associations не точны |
| R11 | Coherent перенос Python-дельт № 24–26 с тестами, conflict manifests и снимками. `development/merges/{24,25,26}` | Из № 13 взяты принципы Store/IR и границ; несовместимое ядро не портировано |
| R12 | Два закреплённых реальных проекта, отложенные сценарии и full synthetic journey | Petclinic Customers; PiggyMetrics read/duplicate, уже изученный проект. Нет чистого unseen-project holdout или real remote |
| R13 | Endpoint/args/status/result/state и TP/FP/FN, precision/recall/IoU четырёх отношений. `final-public-candidate/comparison.json`, `final-synthetic-candidate/comparison.json` | Пустой gold remote не измеряет межсервисную точность |
| R14 | Current/JavaParser: 28 файлов, 112/112 declarations. `optional-extractor-v2/comparison.json` | Symbol Solver/classpath не измерены; конечного выигрыша нет, Tree-sitter сохранён |
| R15 | Getter effect summaries с source/model/config/receiver версиями и alias/read-footprint proof; summary/no-summary и Z3 int32 pilot. `test_review_summaries.py`, `optional-summary-smt/experiments.json` | Общий heap/SMT executor не внедрён; Z3 не production dependency |
| R16 | Optional reranker typed contracts с Qwen, schema/index validation и трассами. `optional-local-reranker-metal/experiment.json` | Прироста нет; модель не обязательна и не создаёт параметры/рёбра |
| R17 | Холодный прогон, подготовка, повтор с индексом, RSS, model calls/time. `final/metadata.json`, `repeated-analysis-final.json` | GPU memory отдельно не измерена; историческое время не парный benchmark |
| R18 | Самостоятельный код, witness/format checks, manifest архива и повтор из распаковки | Итоговые записи: `benchmark/archive-check.json`, `archive-replay.json`, `protected-integrity.json`; после оценки ZIP сохраняется |

## Независимый корпус

Синтетическая цепочка gateway → warehouse содержит 11 шагов: создание, список, удаление, свежий singleton/first, отказ, пустой список и запрет старого ordinal-ID. Oracle SHA-256 `7f5ff1040bd4fbc09fa31079417ad3e4f6dc8630b3920b2d92c2422fcafe8584` создан до сравнений; v2 исправляет канал UI на JSON, не меняя эталон рёбер. В № 27 точны результаты, состояние и все 18 рёбер: executes 9, calls 1, remote 4, data 4. № 23/26 дают тот же граф, но ошибаются в отдельных результатах шагов.

Petclinic Microservices закреплён на `1d76b00d683e86b62867a6bf59530f8ab301244f`. Профиль Customers: 7 шагов list/create/list/update/read/invalid binding/list; исходно Joe ID 1 и пустые pets. Generated IDs остаются символическими. Совпали endpoint, аргументы, status/result, состояние и 25 рёбер (11 executes, 7 calls, 7 data).

PiggyMetrics закреплён на `6bb2cf9ddbca980b664d3edbb6ff775d75369278`. Профиль account: 3 шага read/duplicate create/read с предварительно авторизованным пользователем. Source ControllerAdvice даёт 400 при повторном создании. Совпали те же измерения и 13 рёбер (8 executes, 3 calls, 2 data). Адаптер нормализует Mongo seed; datastore access не называется SQL. Успешные create/Feign/statistics, полный OAuth/validation не доказаны.

В основных трёх цепочках gold remote непуст в 1 синтетическом случае и 0 из 2 реальных; gold data непуст в 3 из 3. Проверка аргументов/результатов относится к полям, заданным oracle: пустой expected arguments не проверяет все возможные значения, `ignore_result` оставляет payload неизмеренным. Переходы состояния дополнительно проверяются числом записей и последующими чтениями, а не полным дампом heap. Готовый skeleton создаёт проверяющий адаптер отдельно от продукта. Grounder получает сценарий и входной контекст, но не oracle.

Два отложенных сценария запечатаны отдельно: отсутствующий owner при PUT и отсутствующий account при GET. Первый запуск обнаружил NameError в explicit JSON, исправленный с регрессионным тестом. Повтор точен в обоих случаях; это `heldout-repair-replay`, а не чистый blind success. V1 финансового oracle ошибочно ожидал 500 без ControllerAdvice; v2 исправляет его по исходнику, оригинал сохранён.

## Train Ticket и регресс качества

Финальный снимок 09: SHA-256 ответа `a24479ddc63892a75a1f0f6e4e9c740d0ef987c8799ac7a0d30b69d26af8995c`. Все 8 ответов проходят официальный format check; точность S1–S7 локально неизвестна. Пройдены 1574 теста, прежние тесты не исключались.

| S0 | TP | FP | FN | Precision | Recall | IoU |
| --- | --- | --- | --- | --- | --- | --- |
| executes | 31 | 1 | 3 | 0,968750 | 0,911765 | 0,885714 |
| calls | 17 | 0 | 7 | 1,000000 | 0,708333 | 0,708333 |
| remote | 0 | 0 | 0 | не измерено | не измерено | 1 по правилу пусто/пусто |
| data | 6 | 0 | 1 | 1,000000 | 0,857143 | 0,857143 |

Среднее организаторов 0,8627976190476191; у № 23 было 0,9509803921568627. Из проекции исчезли отражённые Order constructors и их исходящие связи. Сохранились пропуски JWTFilter из общего модуля, TokenService → User.getPassword и data для lazy roles; лишний executes OrderInfo.setLoginId. Эти расхождения не превращены в именные правила. Новая политика последовательнее по принятому reflection boundary, но её превосходство по разметке Train Ticket не доказано.

Все сценарии `partial`; no-request steps отсутствуют, однако unknown, условные эффекты и остановленные продолжения остаются. Экспорт: executes 515 / calls 403 / remote 37 / data 71. Есть локально подтверждённые события; остальные несут условия. Потенциальная достижимость не добавляется в ответ целиком.

Абляция `confirmed` на тех же трёх executions потеряла ожидаемые рёбра во всех случаях; `observed-union` точен. Оставлен union поддержанных условных событий. Это не доказывает все неопределённые endpoint-альтернативы или будущие остановленные продолжения.

## Ресурсы и решения по экспериментам

Финальный CLI 28,847015457984526 с: подготовка 6,135425749991555 с, анализ 22,71158970799297 с; RSS 355090432 байта. Внешний runner 29,944394917052705 с. Python 3.11.9, Darwin 24.6 arm64, path limit 4, completion split budget 8. Повторный стенд: подготовка 5,815015791973565 с, анализы 17,728244750003796 / 16,845592833997216 с, RSS 283410432 байта; ответы совпадают. Каждый сценарий получает независимое исходное состояние.

Ранние неудачные прогоны сохранены: stage01 runtime error, stage02 timeout с большим report, stage03 падение при native stack sampling, stage06 остановлен из-за роста mixed completions. Это не финальные числа. Введены interned contexts, streaming JSON и COW. Исторический № 23 в другом окружении не служит парным доказательством ускорения.

JavaParser core 3.28.2: 28 файлов, 112/112 методов. Extractor process 0,2640 с, текущая полная metadata-подготовка 0,0328 с: объёмы различны, это не рейтинг скорости парсеров. Исследуемые приложения не собирались/запускались; исполнялся наш development probe. Выигрыша конечных сценариев нет, dependency не принята.

Summary ablation: 12 прогонов, два профиля × enabled/disabled × 3 повтора. Source getter effect summaries устраняют потерю точности Petclinic при сериализации независимых getter; PiggyMetrics не меняется. Это summaries независимости с footprints/aliases, не кеширование результатов. Z3 4.16.0 проверил 6 int32 bitvector условий, включая переполнение. Польза на реальном корпусе не доказана; production Z3 не импортирует.

Qwen3-4B-Instruct-2507-Q4_K_M, llama-cpp-python 0.3.36: 9 обращений; load 10,241997875040397 с, generation 15,598742499074433 с, всего 26,894048334041145 с, RSS 3545579520 байт. Два профиля точны, но baseline уже был точен: прироста нет. GPU memory отдельно не измерена и к RSS не прибавляется. Модель локально выбирает индекс существующего контракта; production model calls 0, external LLM API 0, DeepSeek 0.

## Оставшиеся границы

Это bounded source execution, не полный Java/Spring/JPA runtime. Не поддержанные точно propagation, security/registration, custom converters/record creators, сложные regex/SQL/associations получают диагностику и candidates. При completion budget сохраняется префикс, touched state становится unknown; полный будущий граф не обещается. Другой стек, полноценная real interservice journey и unseen-project holdout остаются будущими проверками переносимости.

Сопутствующий HTML из DOCX не предоставлен; его карта переноса и глубина чтения не восстановлены. Пункты доступного разбора реализованы либо проверены экспериментом с решением и границами. Это не заявление об интеграции всего каталога инструментов или достижении нулевой ошибки.

## Проверка сайта после завершения реализации

№ 27 отправлен по прямому разрешению пользователя: **1665138, A, 0,19402**. Δ к родителю № 23 −0,46783; к лучшему № 5 −0,71585. Все S1–S7 ухудшились: по трёхзначным меткам к № 23 −0,458 / −0,427 / −0,453 / −0,495 / −0,524 / −0,611 / −0,307. Отрицательный результат сохранён и не заменяется успешными компонентными тестами. Новый вариант не продвинут. Статусы partial и частые остановки completion budget видны в собственной диагностике, но без скрытого oracle точная причинная декомпозиция падения не установлена.

В зачёт восстановлен исходный архив № 5: **1665145, A, 0,90987**; текущий рейтинг подтвердил 0,909870. Код/ответ/ZIP № 27 после отправки не менялись. Обратное скачивание № 27 не удалось из-за тайм-аутов браузера; серверный round-trip hash не подтверждён. Скриншоты, точные tooltip, сравнения и хеши — в `benchmark/site-score.json` и `site-best-restored.json`.
