Я прочитал `PLAN_TRAIN_TICKET_ANALYZER.md` целиком и независимо проверил материалы из `tt-challenge/` (это распакованный `1.zip`) и `sample/` (это `2.zip`). Ниже — результат проверки и исправленный план. Файлы я не менял.

---

# Часть A. Что подтверждено по файлам (свидетельства)

Все проверки выполнены запуском только предоставленных статических скриптов и чтением материалов; Train Ticket не запускался.

## A1. Воспроизведена исходная линия (T7)

```
python3 platform/baseline_nlp.py skeleton/trainticket.json.gz targets/trainticket scenarios/*.json -o ans.json --explain
python3 platform/evaluate_golden.py gold/S0.json ans.json
```

Результат — ровно как в `REFERENCE.md` §«Формула оценки»:

| Сценарий | executes | calls | remote | data | балл |
|---|---|---|---|---|---|
| S0 | IoU 0.475 | 0.533 | 0.000 | 0.714 | **0.431** |

`exit=0` для `gold/S0.json`, `exit=3` для `--check skeleton/...` («только формат»). Время полного прогона 8 сценариев — **2.3 с**. Эталон S0: **34 executes / 24 calls / 0 remote / 7 data** — совпадает с открытым эталоном. S0 не входит в итоговый балл; итог — среднее по 7 скрытым сценариям.

Собственных скрытых чисел мы по-прежнему не знаем и не предсказываем.

## A2. Схема скелета (T5) — уточнена

- `schema = v6-skeleton/2.1`, `commit = 313886e99befb94be6cd45f085c98e0019f59829`.
- `nodes` — словарь из **15 229** узлов, вид в поле `kind`: `call_site` 8961, `parameter` 2176, `method` 1538, `field` 1066, `type` 512, `config_entry` 459, `file` 442, `module` 42, `data_resource` 33.
- `edges` — **19 573**: `declares` 11676, `has_parameter` 2176, `contains` 1302, `calls` 1240, `references_type` 1084, `creates` 749, `remote_call` 415, `data_access` 319, `runtime_dispatch` 287, `overrides` 240, `depends_on` 40, `implements` 40, **`message_delivery` 4**, `extends` 1.
- `call_site` содержит `method`, `callee`, `receiver`, `receiver_type`, `arg_count`, `args_text`, `string_args`, `method_ref`, `line`, `col`.
- Узлы `method` содержат готовые аннотации с аргументами: `[{"name":"GetMapping","args":"(path = \"/welcome\")"}]` (402 `Override`, 134 `GetMapping`, 75 `PostMapping`, 26 `DeleteMapping`, 26 `PutMapping`, 1 `PatchMapping`).
- Узлы `config_entry` для `ts-gateway-service` (**121 запись**) содержат реальные gateway-маршруты: `spring.cloud.gateway.routes[0].predicates[0] = Path=/api/v1/adminbasicservice/**`, `uri = lb://${...}`.

## A3. Три технических факта, которые меняют границы работы

**(1) Резолв имён в скелете уже выполнен.** У всех **1240/1240** рёбер `calls` поле `receiver_type` узла-места вызова **точно совпадает с FQN владельца целевого метода**. То есть скелет даёт готовый `(callee, receiver FQN, arg_count) → method ID`. Значит JavaParser нужен не для поиска маршрутов и не для разрешения имён, а только для потока управления, значений, порядка операторов и недостающих рёбер.

**(2) Скелет — авторитетный whitelist, Lombok уже исключён.** `User` объявлен с `@Data`, но `method:ts-auth-service:auth.entity.User#getUserId()` в скелете **отсутствует**, а явно написанные `getPassword/getUsername/getAuthorities/isEnabled/...` — присутствуют. `OrderInfo` с `@Data`: `getLoginId/getState/isEnableBoughtDateQuery/...` (написаны вручную) присутствуют, а `setTravelDateStart` (сгенерирован) отсутствует. Объявленных конструкторов в скелете 129, и они входят в `ids.methods` (`Order#<init>()` есть, `User#<init>()` нет).
Следствие: правило «не включать сгенерированные геттеры» реализуется самим фактом «ID должен существовать среди `nodes`»; `gold/S0.json → ids.methods` — это ровно те же 1538 ID, что в скелете (и `ids.tables` = 33 = число `data_resource`).

**(3) 18 методов помечены `unresolved: true` с `?` в дескрипторе.** Все — с последним параметром `HttpHeaders`, `params_as_written: ["...","HttpHeaders"]`. Например:
`method:ts-contacts-service:contacts.controller.ContactsController#findContactsByAccountId(java.lang.String,?HttpHeaders)`.
**Этот ID есть и в скелете, и в `gold/S0.json → ids.methods`, и gold использует его дословно** (и в `executes`, и как источник `calls`). То есть канонический ID берётся из скелета, а не пересобирается из исходника.

## A4. Покрытие gold S0 скелетом (потолок «may»-обхода)

| Множество | gold | покрыто скелетом | чего не хватает |
|---|---|---|---|
| `data` | 7 | **7/7** (`data_access` из того же метода) | — |
| `calls` | 24 | 19 (`calls`+`runtime_dispatch`) | 5: `TokenServiceImpl#getToken → User#getPassword()`, `Order#<init>() → OrderStatus#getCode()`, `Order#<init>() → SeatClass#getCode()`, то же для `order-other` |
| `executes` | 34 | 21 (замыкание по любым рёбрам от 5 входов) | 13: 7 методов `User` (UserDetails), `UserDetailsServiceImpl#loadUserByUsername`, `JWTFilter#doFilterInternal`, `OrderStatus#getCode`, `SeatClass#getCode`, `StringUtils#Date2String`, `Order#<init>()` (×2 модуля) |
| `remote` | **0** | baseline даёт 1 (FP) | FP = ровно verify-code переход |

Это подтверждает гарантию из `REFERENCE.md` («все `data`-пары эталона есть среди `data_access`») и показывает, что 13 недостающих `executes` — это **вызовы фреймворка и явный код конструктора**, а не «магия».

## A5. Ключевой сценарий S0 в исходнике (проверено построчно)

`ts-auth-service/.../TokenServiceImpl.java`:
```java
String verifyCode = dto.getVerificationCode();
if (!StringUtils.isEmpty(verifyCode)) {          // ~стр. 56
    ... restTemplate.exchange(                  // call:...@67:55  (remote_call → VerifyCodeController#verifyCode)
    if (!id) return new Response<>(0, "Verification failed.", null);
}
... authenticationManager.authenticate(upat);   // → UserDetailsServiceImpl#loadUserByUsername (через Spring Security)
User user = userRepository.findByUsername(username)...;  // → auth_user, user_roles
String token = jwtProvider.createToken(user);   // → User#getUsername()
```
Подтверждено: `remote_call` из `TokenServiceImpl#getToken` идёт только к `ts-verification-code-service:verifycode.controller.VerifyCodeController#verifyCode(...)`. Пустой verification code (context: «no verification code at login») доказуемо выключает это единственное remote-ребро. **Baseline даёт здесь FP `remote=1`; gold — 0.**

## A6. Модель данных (T3, T8) — есть ловушка

Дамп: mysqldump 8.0.46, **25 баз** (`ts_auth`, `ts_consign`, `ts_order`, …), 32 `CREATE TABLE`, INSERT с многострочными кортежами, экранированием, NULL, смешанными типами. `split(',')` недопустим.

**Ловушка:** `schema` в скелете — это не имя БД в дампе:
- `res:table:ts-consign-mysql.consign_record` ↔ БД `ts_consign`, таблица `consign_record`;
- `res:table:ts-auth-service.auth_user` ↔ БД `ts_auth`;
- `res:table:ts-consign-price-service.consign_price` ↔ БД `ts_consign_price`.

При этом **имена таблиц глобально уникальны** (32 таблицы, дублей нет), а 33-й ресурс скелета `wait_list_order` в дампе **отсутствует вовсе** (в дампе есть только пустая БД `ts_wait_order`). 4 таблицы имеют `CREATE TABLE` без `INSERT` (`money`, `notify_item`…). Правило: маппинг состояние↔ресурс по имени таблицы, модуль как вторичный ключ; отсутствие таблицы в дампе — это «неизвестно/пусто», а не ошибка покрытия.

## A7. Фронтенд (T9) — 91 место вызова ≠ 91 настоящий путь

`ts-ui-dashboard/` (137 файлов, 73 `.js`, 22 `.html`) содержит **два семейства**:
- реальные клиентские потоки `flow*.js` — используют gateway-префикс: `/api/v1/travelplanservice/travelPlan/cheapest` (`flowAdvancedSearch.js:84`), `/api/v1/rebookservice/rebook/difference` (`orderRebook.js:37`);
- per-service тестовые страницы (`login.js`, `contacts.js`, `order.js`, …) — используют **не-gateway** пути: `url: "/login"`, `url: "/contacts/create"`.

Отсюда: grounder должен предпочитать `/api/v1/<service>/…` (маршрут выводим из `config_entry` gateway), а не «все JS одинаково».

## A8. Объём и конструкции корпуса (T9)

532 Java-файла в `src/main` (~37 945 строк); 635 включая `src/test`. Census по конструкциям:

| конструкция | вхождений | конструкция | вхождений |
|---|---|---|---|
| `switch` | **1** | `catch` | 75 |
| `lambda ->` | 55 | `finally` | 24 |
| method ref `::` | 9 | `for` | 157 |
| `.stream()` | 30 | `while` | 65 |
| `enum` | 12 | `break`/`continue` | 22 / 4 |
| `interface` | 93 | анонимный класс | 45 |
| `instanceof` | 29 | тернарный `?:` | 33 |

Корпус маленький → полнопроектный анализ по исходникам реалистичен. `switch` практически отсутствует; реальные затраты — `for`/`try-catch`/лямбды.

## A9. Приложение A плана проверено построчно

Все 14 путей из «Приложения A» существуют, **включая опечатки** `ts-preserve-other-service/.../preserveOther/...` и `ts-execute-service/src/main/java/execute/serivce/ExecuteServiceImpl.java` (в дереве действительно каталог `execute/serivce`, а не `service`).

## A10. Оценщик (T7) — его предупреждения это бесплатный инвариант-чек

`platform/evaluate_golden.py` отвергает: неверное `relation` (с подсказкой), `executes` не от `scenario:<id>`, цель `executes` не `method:`, несуществующий ID (с подсказкой «похожая вершина скелета»), `data` не к `res:`. И даёт warnings: «remote внутри одного сервиса» (remote обязан быть межсервисным), «методов в calls/remote/data, но не в executes», «похоже на „сдать всё“». Коды выхода: 0 scored, 1 не принято, 2 неверный вызов, 3 «только формат». Начисление: `|P∩G|/|P∪G|`, пусто-пусто = 1, пусто-непусто = 0; `HINT_RELATION` терпит `runtime_dispatch→calls`, `remote_call/message_delivery→remote`, `data_access→data`.

## A11. 2.zip (T10) — подтверждено

`sample/` = `README.md` + `submission.json` + `code/baseline_nlp.py`.
- `code/baseline_nlp.py` **побайтово идентичен** `platform/baseline_nlp.py` (270 строк, `diff -q` без вывода).
- Он делает `from baseline_closure import Index, BM25, toks, path_segs, load_json`, а `baseline_closure.py` в `sample/code/` **нет** → пример **не запускается как есть**. Прежний вывод про «копию NLP-бейзлайна без `baseline_closure.py`» подтверждён.
- `sample/submission.json` содержит все S0–S7 и в точности воспроизводит наш прогон nlp+closure (S0: 25/22/1/5). Это образец формата, а не второй движок.

## A12. Среда (не из материалов, но важна для воспроизводимости)

JDK 21 есть (`/opt/homebrew/opt/openjdk@21`). **Maven и Gradle отсутствуют**, `~/.m2` без JavaParser, Python 3.12.7.

Проверено по Maven Central: актуальная версия семейства — **JavaParser 3.27.0**; `javaparser-core` требует Java 8+; `javaparser-symbol-solver-core` дополнительно тянет `com.google.guava:guava:33.4.8-jre`, `org.javassist:javassist:3.30.2-GA`, `org.checkerframework:checker-qual:3.49.4`; лицензия в POM объявлена как **двойная: LGPL-3.0 и Apache-2.0**.

## A13. Что остаётся гипотезой (не подтверждается локально)

1. Содержимое скрытых эталонов S1–S7 — локально доступна только проверка формата.
2. Что политика «только явно объявленные методы» одинакова во всех скрытых эталонах (по S0 — да).
3. Что в скрытых эталонах `?HttpHeaders`-ID используются так же дословно (по S0 и по составу `ids` — да).
4. Существенность `message_delivery` (всего 4 ребра; `ts-food-service:mq.RabbitSend#send` → `ts-delivery-service`, `ts-preserve-other-service` → …). Для S1/S3/S4 это возможно, но не проверено.
5. Нужна ли обработка Lombok-аннотаций (`@Builder` конструкторы) на уровне AST для переноса значений; сейчас считаем, что нет (достаточно overlay объявленных методов + value-transfer для отсутствующих accessor).
6. Есть ли пригодный Rust-парсер Java для бонуса Rust. Зрелого публичного парсера Java на Rust я не подтвердил; это отдельный спайк, а не допущение.

---

# Часть B. Обоснованные исправления подготовленного плана

План в целом верен (роли, запрет `instance.json→solution.json`, границы ответа, отсутствие внутренней LLM, «не зашивать S0–S7»). Ниже — точечные правки, каждая с основанием.

| № | Что меняется | Основание (свидетельство) |
|---|---|---|
| **C1** | **Скелет-first как контракт.** `ProjectIndex = SkeletonIndex + SourceOverlay`. JavaParser переводится из «основы резолва» в «слой потока управления и значений». Не нужен symbol solver для маршрутов/ID/владельцев. | A3(1): `receiver_type` == FQN владельца для 1240/1240 `calls`; маршруты уже в аннотациях; gateway — в `config_entry`. |
| **C2** | **Новый обязательный компонент `DeclaredMethodOverlay`** («методы, объявленные в исходнике»): (а) добавляет недостающие `calls` между существующими ID, (б) отличает явно объявленный accessor от Lombok-сгенерированного при переносе значений. | A4: 5/24 gold `calls` S0 отсутствуют в скелете и все 5 — явно объявленный код (`Order#<init>()` → `getCode()`, `User#getPassword()`). A3(2). |
| **C3** | **Добавить модель Spring Security** (`AuthenticationManager.authenticate → UserDetailsService#loadUserByUsername (injected bean)`), это отдельный пункт §12, а не «часть DI». | A4/A5: 7 из 34 `executes` и 1 из 7 `data` S0 приходят только через эту цепочку. |
| **C4** | **Маппинг «ресурс ↔ БД» по имени таблицы + модуль**, а не по `schema`; `wait_list_order` без дампа — допустимо. Таблицы нет в дампе ⇏ «таблица пустая». | A6. |
| **C5** | **Конкретизировать сборку/зависимости**: т.к. Maven/Gradle нет — либо `lib/` с vendored JAR'ами фиксированных версий + SHA-256, либо `mvnw`. Символ-солвер подключать только если прототип докажет нужду (+guava/javassist). | A12, §18 плана (пока абстрактно). |
| **C6** | **UI-index: приоритет gateway-путей** `/api/v1/<service>/…`; per-service тестовые страницы (`/login`, `/contacts/create`) — вторичный источник. | A7. |
| **C7** | **Использовать warning'и `evaluate_golden.py` как обязательный инвариант-тест** в CI (missing executes, intra-service remote, «сдать всё»). | A10. |
| **C8** | **Таблица покрытия конструкций — по измеренным числам**; `switch` почти не нужен, `for`/`try-catch`/лямбды нужны. | A8. |
| **C9** | **Rust-бонус**: обязателен Rust и для анализа, и для построения ответа; тонкая обёртка не даёт надбавку. JavaParser — Java, значит для бонуса нужен Rust-парсер Java, наличие которого не подтверждено. Не тратить ресурс в первой версии. | A12 + README (Rust-бонус). |
| **C10** | **Ловушка маппинга ID из `unresolved`**: канонический ID всегда берётся из `nodes`; при 18 `?`-методах запрещено «дорисовывать» `org.springframework.http.HttpHeaders`. | A3(3), A9. |
| **C11** | **Уточнить Gate B**: `executes` обязан покрывать все источники `calls`/`remote`/`data` (это требование оценщика, не только наше). | A10. |

Отдельно отмечу, что пункт «`stmt:`-рёбра» в `baseline_closure.py` — мёртвый код: `contains`-рёбер к `stmt:` в скелете **нет** (0 из 1302), поэтому предупреждение плана про «исполняемые строки» практически не срабатывает. Оставляем как инвариант, но приоритет понижаем.

---

# Часть C. Проверенный план реализации

## C1. Вердикт по архитектуре

**Подтверждено:** собственное семантическое ядро + небольшая библиотека разбора — правильная граница для этого корпуса (532 файла / 38k LOC, 2.3 с у baseline на Python). Форк Tai-e/SootUp/Joern до прототипа не нужен. Скелет — не «подсказка», а **индекс идентификаторов и проводки**; основная семантическая работа — условия, значения, состояние.

**Меняется:** центр тяжести с «резолва вызовов» на «`DeclaredMethodOverlay` + поток управления + значения + состояние»; добавляется модель Spring Security; маппинг БД↔ресурс по таблице.

**Рабочий стек:** Java 21 (JDK есть) + JavaParser 3.27.0 (`javaparser-core`; `javaparser-symbol-solver-core` — опционально), сборка без Maven (vendored JAR + `javac`/`jar`) либо Maven Wrapper. Лицензия: LGPL-3.0/Apache-2.0 (выбрать Apache и зафиксировать уведомление).

**Незакрытые риски Gate A:** (i) хватит ли JavaParser без symbol solver на ветвления `SeatClass.FIRSTCLASS.getCode()`/`StringUtils.isEmpty`; (ii) не окажется ли `Order#<init>()`-класс рёбер шире, чем в S0; (iii) как переносить значения через отсутствующие (Lombok) accessor без ложных ветвлений.

## C2. Карта требований

| Требование | Источник | Компонент | Тест |
|---|---|---|---|
| 4 отношения строго, `relation` а не `type` | T1, T2 | `export.ContestExporter` | формат `--check skeleton` = 0 отказанных |
| ID копировать из `nodes` | T1, T2, T5 | `skeleton.IdRegistry` | `gold/S0.json → ids` == 1538/33 |
| `executes` = scenario→method | T2, T7 | `export` + `PredictionPolicy` | инвариант «источник calls/remote/data ⊆ executes» |
| `calls` = вызывающий метод → выбранная реализация | T2, T5 | `frontend.java` + `DeclaredMethodOverlay` | `Order#<init>()→OrderStatus#getCode()` |
| `remote` = метод-отправитель → обработчик другого сервиса, межсервисный | T2, T5 | `framework.http` + `skeleton` `remote_call` | S0: remote = 0 (verify-code выключен) |
| `data` = метод с вызовом репозитория → таблица (+отложенный ORM, +таблица коллекции) | T2, T5, README | `framework.repository` + `state` | 7/7 gold S0 |
| Фильтры в `executes`, без `filter→controller` в `calls` | T2, README | `framework.servlet` | `JWTFilter#doFilterInternal` в executes, не в calls |
| Библиотечные/сгенерированные методы не экспортировать | T2, README | скелет-whitelist (+A3(2)) | `User#getUserId()` отсутствует |
| Изоляция сценариев, один снимок T8 | T3 | `state.InitialState` | перестановка независимых сценариев |
| Язык стека и «нет внутренней LLM» | T1, §0 | весь продукт | нет вызовов сети на этапе анализа |
| Запрет запуска Train Ticket | T1 | `cli`, отсутствие рантайм-зависимостей | запуск без БД/Spring/Rabbit |
| ZIP + `submission.json` в корне + код | T1, T10 | упаковка | холодный прогон из ZIP |
| Правило `instance.json→solution.json` | другая задача | **исключено**, не реализуется | — |

## C3. Архитектура и контракты

Поток (правка: скелет идёт первым, исходники — overlay):

```
skeleton.json.gz ─┬─> SkeletonIndex (ids, kinds, routes, wiring: calls/runtime_dispatch/remote_call/message_delivery/data_access, gateway cfg)
                  │
sources (Java) ───┴─> SourceOverlay: DeclaredMethods + CFG(MethodSummary) + values
                                          │
JS/HTML + scenarios + context/SQL ──> ScenarioPlan (endpoint, params, refs)
                                          │
                              ScenarioEngine (условия, значения, состояние)
                                          │
                              EvidenceGraph (confirmed/possible/excluded/unresolved)
                                          │
                              PredictionPolicy ─> ContestExporter ─> submission.json
```

Пакеты плана сохраняются; добавляются:

| Пакет | Что добавляется |
|---|---|
| `skeleton` | `IdRegistry` (канонические ID, `?`-дескрипторы), `GatewayRoutes`, `WiringIndex`, `DataResourceIndex` (маппинг таблица↔модуль) |
| `semantic.extract` | `DeclaredMethodOverlay` (метод объявлен в исходнике?), `CfgBuilder`, `MethodSummary` |
| `framework.security` | `AuthenticationManagerModel` |
| `semantic.model` | `MethodId` (canonical skeleton ID + source key + module), `Value`, `Guard`, `Evidence` |
| `state` | `DumpReader`, `InitialState`, `TableMap` |

Минимальные контракты (уточнены):

```
SkeletonIndex      load(Path gz)
IdRegistry         canonical(sourceKey) -> MethodId | Ambiguous | Absent   // учитывает unresolved/? и owner FQN
SourceOverlay      declaredMethods(ModuleContext) -> Set<MethodId>
CfgBuilder         cfg(MethodId, CompilationUnit) -> MethodSummary
MethodSummary      seq: [Action(guards: [Guard], effects: [Effect], site: CallSiteRef)]
ScenarioGrounder   step -> {candidateEndpoints, chosen|ambiguous, params, negatives, refs}
ScenarioEngine     analyze(ScenarioPlan, ProjectModel, InitialState) -> ScenarioResult
PredictionPolicy   keep(Evidence, Mode{may|confirmed}) -> boolean
ContestExporter    write(List<ScenarioResult>, IdRegistry) -> submission.json
```

Инварианты:
- AST не покидает `frontend.*`; наружу только `MethodId`, `CallSiteRef`, диапазоны строк.
- Ни один экспортируемый ID не синтезируется: только значения из `nodes`.
- `remote` только межсервисный (иначе предупреждение оценщика).
- Источники `calls`/`remote`/`data` обязательно в `executes`.
- Дедуп — один раз за сценарий, детерминированная сортировка.

**Политика неизвестного.** Внутри — 4 метки: `confirmed` / `possible` / `excluded(basis)` / `unresolved(reason)`. Экспорт — отдельной `PredictionPolicy`: режим `may` для диагностики (сравнение с baseline), режим `confirmed` для сдачи. Числа по категориям — измеряем, пороги не подбираем по S0.

## C4. Реестр моделей фреймворков

| Модель | Где применяется (проверено) | Источник семантики | Влияние | Тест |
|---|---|---|---|---|
| Spring MVC маршруты/bindings | `UserController#getToken` `@PostMapping("/login")` + `@RequestBody`; аннотации в `nodes` | `nodes.method.annotations` + `config_entry` gateway | выбор входа шага | S0 шаг 1 → `UserController#getToken` |
| Spring Security auth | `TokenServiceImpl#getToken` → `authenticationManager.authenticate` | вызов на инжектированном бине → `UserDetailsService#loadUserByUsername`; далее `User#getX` | 7 executes + 1 data (S0) | S0: `loadUserByUsername` + `auth_user` |
| Servlet filter chain | `JWTFilter#doFilterInternal` (ts-common) | `executes` без входящего `calls` | 1 executes; запрет фиктивного `calls` | S0: фильтр в executes, не в calls |
| Spring DI | `@Autowired` поля; `PreserveServiceImpl` → `RestTemplate`, `RabbitSend` | тип поля → реализация в модуле (`runtime_dispatch`) | выбор реализации интерфейса | S0: `ContactsService` → `ContactsServiceImpl` |
| Lombok | `User`, `OrderInfo`, `Contacts`, `Order` | скелет уже исключает генерируемое; отсутствующий accessor = value-transfer | не экспортировать; значения полей DTO | `User#getUserId` отсутствует, `getPassword` есть |
| RestTemplate (+`@LoadBalanced`) | `TokenServiceImpl#getToken` exchange @67:55; `PreserveServiceImpl` exchange ×N | `remote_call` от места вызова; URL-литерал с именем сервиса | `remote` + возврат результата в ветку | S0 remote=0; S1 remote>0 |
| Entity/JPA | `@Entity/@Table(name="auth_user")`, `@ElementCollection/@CollectionTable` (`user_roles`), `@Column` | `data_resource` + аннотации | `data`-цели, включая таблицы коллекций | S0: `auth_user` + `user_roles` (две вершины) |
| Repository (Spring Data) | `OrderRepository`, `ConsignRepository.findByAccountId` | имя метода (derived query) → чтение/запись; имя `save` ≠ SQL само по себе, нужен реальный вызов | `data` + результат для следующего `if` | S0: `consign_record` |
| Enum-константы как значения | `SeatClass.FIRSTCLASS.getCode()`=2, `OrderStatus.PAID.getCode()`=1 | исходник enum | ветвления `seatType`, `state` | `order/OrderServiceImpl.java:126-187` |
| String/Collection utils | `StringUtils.isEmpty` (Spring) в `getToken`; `list.isEmpty()` | библиотечная модель-предикат | снятие remote-ребра | S0 шаг 1 |
| RabbitMQ | 4 `message_delivery`: `food-service:mq.RabbitSend#send` → `delivery-service:mq.RabbitReceive#process` | `message_delivery` + `RabbitListener` (2) | `remote` только при достижении отправки | S1/S3/S4 (гипотеза) |
| Spring `@Transactional` | 17 методов | границы: SQL-эффект остаётся, запись может откатиться | `data` есть, состояние — отдельно | S2 отмена, S7 |

## C5. Backlog (уточнённый, с критериями готовности)

Порядок и зависимости сохранены; критический путь выделен жирным, изменения отмечены ▲.

| ID | Задача | Зависит | Definition of Done (проверяемо) | Размер |
|---|---|---|---|---|
| P01 | Аудит T1–T10 + baseline | — | `INPUT_AUDIT.md`, `BASELINE_REPORT.md`; зафиксированы 0.431 и counts 34/24/0/7 | S |
| P02 | ADR по стеку/лицензиям/сборке ▲ | P01 | JAR-версии+checksums, LGPL/Apache-решение, план Gate A | M |
| **P03** | ▲ `SkeletonIndex` + `IdRegistry` (+`?`-дескрипторы) | P01 | 1538/33 совпадают с `gold.ids`; `findContactsByAccountId(...?HttpHeaders)` найден | M |
| **P04** | ▲ `DeclaredMethodOverlay` + `Mapping` AST↔skeleton | P02,P03 | перегрузки и `?`-методы разрешены; 0 коллизий `package/class` между модулями | M |
| P05 | Экспортёр + валидатор (обёртка над `evaluate_golden.py --check`) | P03 | 0 отказанных рёбер на S0–S7 | S |
| P06 | Call-site-preserving may-обход | P03,P05 | воспроизводит baseline S0 (25/22/1/5), но сохраняет call sites | M |
| P07 | Endpoint/UI index ▲ (приоритет gateway-путей) | P03,P04 | таблица «шаг→endpoint→параметры»; S0 шаг 6 → `ConsignController#findByAccountId` | M |
| **P08** | CFG + `MethodSummary` | P04 | ветви/early return/short-circuit/finally; тесты S0 `getToken` | L |
| **P09** | Значения, поля, call/return, enum-коды ▲ | P08 | ветвление `SeatClass.FIRSTCLASS`, `OrderStatus.PAID` | L |
| P10 | DI + библиотечные модели (+Spring Security ▲) | P04,P09 | `loadUserByUsername`, `User#getX` появляются из вызова `authenticate` | M |
| P11 | `DumpReader` + `InitialState` ▲ (маппинг по таблице) | P01,P03 | строки `auth_user`,`inside_money`,`orders` сверены; `wait_list_order` — «нет таблицы» | M |
| P12 | Репозитории + `data`-эффекты | P08,P09,P11 | 7/7 gold `data` S0; `user_roles` отдельной вершиной | L |
| P13 | HTTP + ответы + фильтры | P07,P09,P10 | S0: remote=0 (verify-code) с причиной `guard_proven_false`; нет фиктивного `calls` | L |
| P14 | `ScenarioPlan` + символ. ссылки | P07,P09 | 2 контакта/заказа; отрицания (`without food/assurance`) | M |
| P15 | Модель состояния | P11–P14 | оплата/выдача/отмена/перебронирование; изоляция сценариев | L |
| P16 | Сообщения/отложенные эффекты | P09,P13,P15 | только обоснованные доставки (4 `message_delivery`) | M |
| P17 | Поиск, обычные поезда, админ, смена роли | P10–P15 | S2–S6 покрыты без ID-hardcode | L |
| P18 | Политика unknown + отчёт доказательств ▲ | P06,P09 | категории unknown измеримы; экспорт без потери ID | M |
| P19 | Регрессии/абляции/обобщение | с P05 | прирост механизмов, не только S0 | M |
| P20 | Производительность + ZIP | P05,P15–P19 | холодный прогон из чистого ZIP | M |

Параллелизм: P07/P11/P04 — после P03; P08 → P09 → (P10,P12,P13) — критический путь.

## C6. Прототип и стоп-критерии (Gate A) — конкретизировано

Вход: 3 реальных файла (`TokenServiceImpl.java`, `OrderServiceImpl.java`, `order/entity/Order.java`) + 2 синтетических.

Ожидаемый результат прототипа (каждый пункт — бинарная проверка):
1. `getToken` сопоставлен с ID `...TokenServiceImpl#getToken(auth.dto.BasicAuthDto,org.springframework.http.HttpHeaders)`.
2. Найден call site `@67:55` и его единственная цель `VerifyCodeController#verifyCode(...)` из `remote_call`.
3. Guard `!StringUtils.isEmpty(verifyCode)`; при пустом коде из сценария ребро исключено с причиной `guard_proven_false`.
4. Восстановлено ребро `Order#<init>() → OrderStatus#getCode()` (отсутствует в скелете) через `DeclaredMethodOverlay`.
5. `ContactsController#findContactsByAccountId(java.lang.String,?HttpHeaders)` получен **из скелета**, а не из исходника.
6. Отсутствующая библиотека (jjwt/Jackson) → диагностика `dependency_unresolved`, без падения.

**Стоп-критерий:** если (2)–(5) не достигаются без написания собственного резолвера типов/инфраструктуры сверх плана, — пересматриваем границу: либо отказываемся от symbol solver в пользу overlay скелета, либо берём готовый dataflow-компонент, но **не** наращиваем компилятор своими силами.

## C7. Тесты, метрики, команды

- Инварианты формата: `evaluate_golden.py --check skeleton/... submission.json` → `exit=0`, 0 отказанных, 0 warning'ов.
- S0: IoU по 4 множествам + FP/FN с причинами. Хардкорных целей по S0–S7 не зашиваем; 0.431 — только baseline.
- Синтетика: вложенный `if`, вызов в условии, `&&`/`||`, `finally` после `return`, два call site к одному методу, перегрузка, интерфейс, отсутствующий JAR, пустой/непустой список, цикл 0/1/N, два одноимённых класса в разных модулях, SQL до отката.
- Обобщение: переименование сценария/локальной переменной; перестановка независимых сценариев; холодный vs кешированный прогон — тот же ответ.
- Абляции: baseline → call-site-preserving may → локальные условия → состояние → framework-модели.
- Наши (не организаторов) инженерные цели: холодный прогон < 60 с, peak JVM < 1 ГБ, детерминированный вывод (байтовое равенство), 0 сетевых вызовов на анализе.

## C8. Сдача и воспроизводимость

- `submission.json` в корне ZIP, блоки S0–S7, `relation`, только ID из `nodes`.
- `docs/`: `IMPLEMENTATION_PLAN.md`, `ARCHITECTURE.md`, `REQUIREMENTS_TRACEABILITY.md`, `TEST_PLAN.md`, `DEPENDENCY_DECISIONS.md`, `adr/0001-analysis-boundary.md`.
- Версии: JDK 21, JavaParser 3.27.0 (+guava/javassist/checker-qual **только** если включим symbol solver); `lib/*.jar` + `SHA256SUMS`; скрипт сборки/запуска без сети.
- Лицензии: JavaParser (выбираем Apache-2.0, уведомление в `THIRD_PARTY_NOTICES`), наши файлы без чужих заголовков удалёнными.
- Производственный путь не читает `gold/S0.json` и не берёт ответы из `examples/`.

## C9. Первые задачи после утверждения (не выполнять сейчас)

1. `docs/INPUT_AUDIT.md` + `BASELINE_REPORT.md` (P01): baseline 0.431, 34/24/0/7, 2.3 с, дефекты baseline (FP remote, dead `stmt`).
2. `adr/0001-analysis-boundary.md` (P02): скелет-first, vendored JAR, LGPL/Apache.
3. `SkeletonIndex` + `IdRegistry` с `?`-дескрипторами (P03) + тест «1538/33 == gold.ids».
4. `DeclaredMethodOverlay` (P04) + тест «`Order#<init>()` объявлен; `User#getUserId()` не объявлен».
5. `CfgBuilder` на `getToken` (P08) + тест guard'а `!StringUtils.isEmpty`.
6. `ContestExporter` + интеграция `evaluate_golden.py --check` (P05).
7. Gate A-прогон (C6) с письменным вердиктом: продолжать Java-ядро или менять границу.

---

## Ограничения (что не закрыто и почему)

- Скрытые эталоны S1–S7 недоступны → локально проверяем только формат; качество на них — гипотеза.
- Нужен ли symbol solver — решится Gate A; до этого зависимость guava/javassist не фиксируем как обязательную.
- `message_delivery` (4 ребра) — малая площадь, роль в S1/S3/S4 не подтверждена.
- Rust-бонус требует Rust-парсера Java, наличие которого не подтверждено; путь не выбираем.
- Отсутствуют числовые пределы времени/памяти от организаторов — приведённые цели наши.

План опирается на проверенные `skeleton/trainticket.json.gz`, `gold/S0.json`, `platform/*.py`, `context/db-after-warmup.sql.gz` и `targets/trainticket/`; правило `instance.json → solution.json` в этот план не входит.

Готов оформить это как файлы в `/Users/semolik/.opencode/plan` (например `IMPLEMENTATION_PLAN.md`, `ARCHITECTURE.md`, `DEPENDENCY_DECISIONS.md`) — скажите, и я запишу. Реализацию начинаем после переключения в режим исполнения и утверждения Gate A.