# Решение № 13 — polyglot-scenario-core

Проверяемый прототип общего ядра Java/Spring и Python/FastAPI. Архитектурный предшественник — № 11. Tree-sitter, LibCST, SQLGlot, Z3 и Rank-BM25 выполняют разбор, разрешение имён, SQL-планы, проверку ограничений и поиск контрактов. Добавлены Tree-sitter JavaScript, html5lib и QuickJS-NG для исходных UI-запросов и конкретной JS-семантики. FastAPI/Starlette, Pydantic/pydantic-core, PyJWT и pwdlib теперь выполняют ограниченные нативные контракты form/Bearer, validation/serialization, JWT и проверки паролей. Наш код связывает компоненты с IR, состоянием сценария и ID входного графа. Чистые компоненты контекста/UI перенесены самостоятельным снимком из № 14; его backend-движок не импортируется.

**Требуемое качество универсального анализатора пока не достигнуто.** Локальный S0 — **0,2929** против **0,3041** у раннего снимка № 13 и **0,9510** у № 11. UI-мост подтвердил конкретную смешанную цепочку, но перенос полного pipeline дал регрессию: неподдержанные callback chains, составные запросы и framework lifecycle ограничивают наблюдаемый префикс. Все восемь сценариев остаются `partial`; цель остаётся активной.

| Показатель | Значение |
| --- | --- |
| Score сайта | — (не получен) |
| Тестовый score S0 | 0,2928921568627451 |
| S0: executes / calls / remote / data, IoU | 0,08823529411764706 / 0,08333333333333333 / 1 / 0 |
| Формат S0–S7 | Проверен официальным валидатором; все ответы непусты и partial |
| Время построения ответа | 8,222 с внутри CLI; 8,553 с весь процесс, локально |
| Подготовка / анализ | 7,207 / 1,014 с |
| Пиковый RSS | 301744128 |
| Окружение | Python 3.11.9, macOS/Apple Silicon; версии пакетов закреплены |
| Обращения к моделям при анализе | 0, внешних LLM API нет |
| Проверки | 348 тестов; 8 FastAPI HTTP-трасс; 6/7 условных Spring-целей; 7 проверок тел и 10 проб поиска; смешанные CLI-интеграции |

`remote=1` у S0 означает два пустых множества. В S0 найдено 3 правильных executes из 34, 2 calls из 24 и ни одного data из 7; лишних рёбер S0 нет. Полнота ниже предыдущего снимка (5/34 и 3/24). Скрытые S1–S7 не оценены. Понижены только 5 тел из 3094 методов; малое время исполнения не доказывает скорость при нужном покрытии. Подготовка с новым UI стала существенно дороже.

SHA-256 ответа: `27f4aa4c3feb97206e9e45cdf3930b4f5cb2f4d0177d5845261400549ab5bf3b`. Повтор всех сценариев с `PYTHONHASHSEED=17` дал тот же файл. Полные значения и команды — [summary.json](benchmark/summary.json), [analysis-report.json](benchmark/analysis-report.json), [comparison.json](benchmark/comparison.json). Промежуточный неудачный прогон с пустым S0 и score 0,25 сохранён в experiments; он не скрыт выбором удачного результата.

Четвёртый этап проверяет исходную HTTP-цепочку публичного FastAPI Template: login → password verification → JWT/Bearer → CRUD → 404. Все 8 случаев прошли, без подготовленных Session/User; каждый повторён offline CLI с hash seed 7 и 31. Основная цепочка дала точные 13 executes, 5 calls, 6 data и пустой remote. Входы, source hashes, лицензия и проверочные исходники сохранены. Это явные HTTP-запросы; полный публичный путь от естественного языка/UI ещё не подтверждён. [Контракты и ограничения](FASTAPI.md), [результаты](benchmark/public-http/results.json). S0 после этого этапа не изменился; общая цель остаётся активной.

Пятый этап добавляет javaproperties/PyYAML для конфигурации отдельных deployment, исправляет выбор Feign proxy и индексирование enum methods, вводит ограниченные исходные MVC exception handlers, field Bean Validation и мост Java time через CPython/tzdata. **6/7** условных проверок PiggyMetrics проходят: чтение, отсутствие записи, неправильные servlet prefix/HTTP method, исходный advice и отказ validation до контроллера. Основная цепочка чтение → изменение → Feign → статистика **не проходит**: найдено 17/43 executes, 14/43 calls, 1/1 remote и 2/4 data; дальнейшему анализу мешают Streams/method references и другие неподдержанные механизмы. Все семь текущих результатов, включая провал, повторены offline CLI с seed 7 и 31. [Полный отчёт и входы](benchmark/public-spring/results.json), [ручной эталон](development/spring_http_reference.json).

Этот Java-корпус предполагает успешный проход предшествующей framework/security-фазы. Это не полный HTTP-эталон: token services, Jackson accessors, persistence converters и собственные callback-контракты ещё не подтверждены. Ручной эталон составлен Codex, затем исправлен по исходному ControllerAdvice: предыдущий ошибочный статус 500 заменён на 400 с обязательным выполнением исходного обработчика. История исправления сохранена. Независимое авторство эталона не заявляется.

## Открытые компоненты

| Проект | Что реально используется |
| --- | --- |
| FastAPI/Starlette | Нативные OAuth2 form и Bearer на переданном запросе |
| Pydantic/pydantic-core | Схемы из исходных фактов, валидация, конкретный JSON |
| PyJWT и pwdlib | Подпись/claims, явное время, проверка паролей и hash upgrade |
| javaproperties / PyYAML | Настоящие парсеры `.properties` и YAML с исходными позициями, приоритеты и профили по deployment |
| CPython datetime/zoneinfo / tzdata | Ограниченные Java time-преобразования с явными часами и закреплённой IANA |
| Tree-sitter / tree-sitter-java / tree-sitter-javascript | Деревья Java и JavaScript, извлечение деклараций, выражений и запросов |
| QuickJS-NG / html5lib | Чистые конкретные JS-операции и HTML5-факты; исследуемые скрипты не запускаются |
| LibCST | CST, QualifiedNameProvider, ScopeProvider, import aliases и нормализация exception tuples Python 3.14 в памяти |
| SQLGlot | SQL AST контекста, upstream optimizer/planner/executor для ограниченных SELECT-планов над переданными снимками |
| Z3 | UNSAT-отсечение путей; Int для Python, BitVec для Java; сохранение альтернатив при unknown/таймауте |
| Rank-BM25 / NumPy | BM25 с насыщением частоты и положительным IDF через `BM25Plus(delta=0)`; векторные расчёты upstream |

Версии, лицензии и места подключения — [THIRD_PARTY.md](THIRD_PARTY.md). Upstream-пакеты не изменены. Joern, CodeQL, Semgrep и Spoon не выдаются за подключённые движки.

Сравнение с `--no-smt` на одинаковых исходниках Java и Python воспроизводит лишний вызов из ветви `n>10` и одновременно `n<5`; Z3 исключает его. Проверены overflow, division/remainder, нулевой делитель и числовая семантика после HTTP. [Сохранённая абляция](benchmark/oss-components.json). На полном Train Ticket решатель пока не получил формул — улучшение S0 за счёт SMT не заявляется.

SQLGlot используется JDBC, literal native `@Query` и SQLAlchemy `text/execute`. Один JOIN/GROUP/ORDER/COUNT-запрос из Java и Python даёт одинаковый проверенный результат. Подключения к базе нет. JPQL, неподдержанный AST, неизвестные SQL-параметры и типы значений диагностируются. Неизвестная мутация контекста не превращается в пустую таблицу.

Третий этап добавляет исходное выражение UI-запроса, отдельное состояние браузера и перенос результата через JSON/Storage. Синтетический CLI UI → Java → Python → БД → следующий запрос дал ровно 6 executes, 1 calls, 2 remote, 2 data и правильное состояние. Холодный/тёплый ответы совпали; весь процесс занял 0,345/0,342 с, NativeJS — 42 чистые операции. Это не публичный полный HTTP-эталон. Версии, границы и дополнительный входной контракт — [UI.md](UI.md), измерения — [ui-integration](benchmark/ui-integration/verification.json). Для исходников UI и кода вложенных адаптеров исправлена инвалидация ключа; отчёт содержит UI-хеши, неподдержанные конструкции и отдельную стоимость JS-операций.

Во втором этапе исправлена коллизия одинаковых Python-пакетов в разных сервисах: методы, классы и глобальные значения разделяются по deployment. Проверены относительные импорты, независимое состояние и цепочка со всеми четырьмя отношениями. Полные namespace packages, произвольные import roots и повторные определения одного имени пока не поддержаны.

Входной контекст теперь используется отдельно от исполнения: цитаты поддерживают учётные данные, явное отсутствие поля и даты. Модели часов и календаря пока не используют все выделенные факты. Конфликтующие значения остаются неизвестными; новые учётные данные не наследуют старые. Невычислимое значение с единицами или неполным числовым литералом не подменяется default. Java/Python различаются при неявном вызове метода; исправлены Java static calls и getClass в инициализаторе.

Модель заголовков проверяет case-insensitivity, несколько значений, `HttpEntity(body, headers)`, headers-only overload и передачу Java → Python. Read-only контракт `getHeaders` установлен для проверенных семейств Spring 5.3, 6.2 и 7.0. Без версии сохраняются обе возможности. Это первый ограниченный пример версионирования моделей, не полный реестр. Maven читается как XML: только явные зависимости и локальные свойства, без выполнения Maven, вывода версии из Boot BOM, profiles или Gradle. Read-only list views диагностируются как неподдержанные. [Источники контрактов](development/model-contracts.json).

## Запуск

Из каталога варианта; зависимости устанавливаются до анализа:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
NSU_CASE_ROOT=../../tt-challenge
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B code/offline_run.py \
  --source "$NSU_CASE_ROOT/targets/trainticket" \
  --skeleton "$NSU_CASE_ROOT/skeleton/trainticket.json.gz" \
  --context "$NSU_CASE_ROOT/context/db-after-warmup.sql.gz" \
  --scenarios "$NSU_CASE_ROOT/scenarios" \
  --output submission.json --report benchmark/analysis-report.json
```

Для другого проекта меняются четыре входных пути. Готовый граф-скелет обязателен. JSON-контекст принимает `clock`, `tables`, `table_schemas`, `inputs`, `services`, `principal`, `globals`, `narrative`, `framework_versions`, `browser`, явные `assumptions`; неоднозначные таблицы отвергаются. Например, `framework_versions: {"gateway":{"spring":"5.3.4"}}` уточняет библиотеку конкретного сервиса. `narrative` — объект текстовых полей, дополняющий `skeleton.context`; извлечение ограничено поддержанными фактами, не произвольным пониманием текста. SQL-контекст — `.sql`/`.sql.gz`, диалект задаётся `--sql-dialect` (mysql по умолчанию). Для невычислимых значений времени определения Python можно передать `globals`: ключ модуля, например `main.VALUE`, или `main.read:default:value`. При коллизии deployment префикс — например `py@client:app.main.VALUE`. Вызовы инициализации не считаются выполнением сценария; без значения остаётся unknown.

Параметры: `--cache PATH`, `--profile NAME`, `--policy may|must`, `--path-limit 16`, `--loop-limit 32`, `--depth-limit 32`, `--step-limit 30000`, `--smt-timeout-ms 50`, `--no-smt`. Ключ IR-кеша включает исходники, скелет, конфигурацию, profiles, код и версии библиотек. Состояние и ответ вычисляются заново; подготовка пока повторяется даже при тёплом кеше.

Явный HTTP-`request` в шаге позволяет отдельно проверить выполнение. Ссылка `{"$ref":"steps.1.body.id"}` в `request`/`inputs` переносит результат предыдущего шага. Это дополнительный контракт; текстовые сценарии принимаются, их текущая точность отражена в S0. ID сценария влияет только на `scenario:<id>`. Строковая композиция истории: `{"$concat":["Bearer ",{"$ref":"steps.1.body.access_token"}]}`. Для временных проверок JWT нужен `clock` с timezone; без него неизвестный хвост останавливается.

Для внешней конфигурации Spring передаётся полный resolved Environment по имени deployment. Пример части context: `{"configuration":{"app":{"profiles":["prod"],"propertySources":[{"name":"resolved-runtime","source":{"server.servlet.context-path":"/api"}}]}}}`. Более ранний source имеет приоритет; соседний сервис его не использует. Без снимка внешний Config Server остаётся неизвестным. Локально поддержаны conventional classpath `application`/`bootstrap`, простые profile selectors и placeholders; custom locations/imports/profile groups и DispatcherServlet path не поддержаны. Снимок участвует в ключе индекса; его изменение требует нового Project.

Java time требует явных `clock` и `timezone`, например `"2026-01-02T10:00:00Z"` и `"UTC"`. Для региональных зон нужна соответствующая `timezone_database: "2026e"`; версия tzdata закреплена. Проверены выбранные LocalDate/LocalDateTime/ZoneId/Instant/Date-преобразования, DST gaps/overlaps, epoch milliseconds. Nanoseconds, расширенные годы, остальные overloads/aliases и неизвестные codecs сохраняют диагностическую границу. Полная `java.time` не реализована.

## Проверки

```bash
PYTHONPATH=code PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest code/tests -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B development/benchmark_core.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B development/benchmark_oss.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B development/benchmark_ui.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B development/run_benchmark.py --case-root "$NSU_CASE_ROOT"
```

- [348 тестов](benchmark/tests.xml): управление, исключения, области видимости, алиасы, HTTP/Depends, SQL/Session, неизвестные эффекты, бюджеты, состояние, кеш, OSS, контекст, коллизии Python-сервисов и версии моделей. Проверяются значения и рёбра, не только формат.
- [Смешанная интеграция](benchmark/core-integration/verification.json): Java → Python, создание → чтение по символическому UUID; ровно 6 executes, 1 calls, 2 remote, 2 data. Все четыре множества непусты, граф совпал с ручным эталоном. Пример синтетический.
- Холодный/тёплый результаты совпали, повтор дал 6 IR hits и 0 новых понижений. Переменованы все ID скелета и сценария — нормализованный граф сохранился. Значимое ускорение кешем не установлено.
- [PiggyMetrics](https://github.com/sqshq/piggymetrics), commit `6bb2cf9ddbca980b664d3edbb6ff775d75369278`: 72 производственных Java-файла под хешами; 2 проверки — чтение аккаунта через контроллер/сервис/репозиторий и отказ при пустом имени.
- [FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template), commit `b1125d8839482cb7bbae603ddc6d0081bf87532e`: 25 производственных Python-файлов под хешами; 5 проверок — владелец, чужой объект, отсутствие, частичное обновление → чтение, удаление → отсутствие. Новый exception-синтаксис разобран, parse errors этих файлов — 0.

Все 7 публичных проверок прошли: [результаты](benchmark/public-corpus/corpus-results.json), [эталоны](development/corpus_reference.json), [воспроизведение](development/check_corpus.py). Команда: `python -B development/check_corpus.py --java ROOT --python BACKEND --output DIR`. Нужны исходники по указанным commit; в рабочем репозитории они сохранены в `experiments/20261017-polyglot-scenario-core/`.

Условные Spring-проверки вместе с 91 исходным Java/config/Maven-файлом и лицензией включены в `benchmark/public-spring/fixture/`; приложение не запускается. Полный публичный репозиторий не копируется. Воспроизведение компонента: `python -B development/check_spring_http.py --source ROOT --license ROOT/LICENCE --output DIR`. Команда сохраняет непрошедшие цели в results.json; успешный выход команды не означает успех всех целей. `development/verify_artifacts.py` проверяет также сохранение провала полного сценария и не объявляет Spring-поддержку готовой. `development/check_archive.py` повторяет все 8 FastAPI и 7 Spring результатов из распакованного ZIP.

Отдельно измерен выбор обработчика по 10 простым текстовым действиям на тех же публичных проектах: top-1 верен 10/10, точный набор кандидатов — 9/10; один запрос возвращает лишнюю гипотезу. [Результаты](benchmark/request-grounding.json), [ручной эталон](development/request_reference.json), [воспроизведение](development/check_grounding.py). Это проверка поиска, не полного выполнения. Все лексические решения отмечаются как гипотезы и дают partial. Сравнение формул, исключившее BM25L релиза 0.2.2 с ненасыщающим множителем частоты, сохранено в [retrieval-formulas.json](benchmark/retrieval-formulas.json); тест с повторяющимися логами независим от Train Ticket.

Публичные пробы ограничены телами методов с предоставленными Session/User и состоянием. Они не доказывают полный HTTP/security/validation-граф приложений. Эталоны составлены Codex до первого сравнения; отдельного независимого автора нет. Пустые remote-множества этих проб не выдаются за межсервисное качество. Приложения и сервисы не запускались.

## Границы и статус цели

Устройство — [ARCHITECTURE.md](ARCHITECTURE.md), требования — [SUPPORT_MATRIX.md](SUPPORT_MATRIX.md). Выполнение ограничено поддержанными конструкциями. `must` пуст при необследованных путях; `may` — объединение обнаруженных эффектов, не доказанная полная верхняя оценка произвольной программы.

Для качества продукта необходимы дальнейшее UI/контекстное связывание, упорядоченные составные запросы/callback chains, фазы Spring/FastAPI и расширение моделей. Не реализованы полный JVM/Python, reflection, Streams/lambdas, ORM relationships/cascades/identity map/dirty tracking, произвольный SQL, фоновые задачи, summaries с footprint, fixpoint/widening и точная инкрементальная инвалидация. Третий язык потребует адаптера и проверки. Поддержка любого языка и аппаратная переносимость вне проверенного macOS/ARM не заявляются. Общая цель качественного универсального анализатора остаётся открытой.

DeepSeek консультировал архитектуру в режиме только чтения. Попытка отдельной проверки эталонов завершилась HTTP 403 FreeTierError; выполненным независимым ревью она не считается. Дополнительное OSS-ревью прочитало файлы, затем остановилось без итогового ответа; оно тоже не засчитано как пройденное. Новая попытка UI-ревью не вернула содержательного ответа за 75 с; она не засчитана. DeepSeek не изменял файлы. Принятые изменения и проверки просмотрены Codex. [Аудит](development/deepseek-audit.json), [замечания](development/deepseek-review.txt).

На пятом этапе повторно запрошено read-only мнение о Spring configuration, security и lazy callbacks. За 45 с содержательного ответа не получено; независимая проверка этого этапа DeepSeek не засчитана, другая модель не подставлялась. Реализация и контрпримеры проверены Codex.

В [solution.zip](solution.zip) находятся `submission.json` в корне, код, зависимости, лицензии и инструкции. На сайт не отправлялся. Старые варианты, исходный пакет, sample и прежние runs этой работой не редактировались; изменения параллельного чата сохранены.
