# Независимое чтение дополнительных oracle PiggyMetrics

Дата: 18 октября 2026 года. Проверяющий: `/root/oracle_reader`, тот же отдельно разрешённый пользовательский агент Codex. Проверены только oracle, закреплённые Java/config источники и ранее проверенный source oracle v2. Runtime, outputs и тесты анализатора не читались. Целевые приложения, JVM и сборки не запускались; DeepSeek не использован. Исходный дополнительный v1 не изменён.

**Решение: source-предположения трёх случаев в основном верны; как строгий acceptance oracle файл требует дополнений.** В нём пока нет полностью заданных initial state, rejected binding candidate, formal unknown-slot semantics и per-case events. Это недостаток полноты ожидаемых данных, а не обнаруженная ошибка enum или бизнес-статуса. Основному агенту сообщены необходимые поправки до любой коррекции v1.

## Проверенные объекты

| Объект | SHA-256 |
|---|---|
| `additional-source-cases.oracle-v1.json` | `51fcbbb73623d8cd169138f529b5aae5c2af05446d67f5fde10a20ccf96fe000` |
| Родительский `oracle.reviewed-v2.json` | `499f635f5df70eafafc6ef0b424266949d62f5886a77b4af5c9e9f1cf82a9e8d` — совпадает с parent reference |
| `account/domain/Item.java` | `4c4e72209093b482cd637c17c1e6d1261d6c9e7eced12f8447a4b8382c3d94dd` |
| `account/domain/TimePeriod.java` | `414bb8f973f971a4ef5acdf92da30d85bacf3875f0bca9a5a2ce3a062bb31e73` |
| `account/domain/Account.java` | `0459c909851d021c05a1fe157e977f5e33fabd92ef4c34042bcbb61f3306b0a1` |
| `account/controller/AccountController.java` | `703a1e218d8173f9d47dc85f3de5d8fd333dc8531130f6371887b4f21d2144a5` |
| `account/service/AccountServiceImpl.java` | `60c25f01e6553c642f2536177f96bc8a6500be0b8a881a812b227068461ee27d` |
| `account/config/ResourceServerConfig.java` | `76aacb7bd3d884a7aa8b58c11dabb86120bcfd38cb6f89b2595a29189e0d7955` |

Все Java paths в таблице отсчитываются от `experiments/20261018-review-corpus/public/piggymetrics/account-service/src/main/java/com/piggymetrics/`. Git commit профиля остаётся `6bb2cf9ddbca980b664d3edbb6ff775d75369278`. Список перечисленных файлов, их хешей и точных строк пригоден для отдельного manifest дополнительных случаев; одного parent oracle hash недостаточно, если checker не разрешает его ссылки и не проверяет входные source hashes.

## 1. `invalid-saving-null`

Source вывод верен при заданном authenticated post-auth context. `AccountController.java:30–32` принимает `Principal` и `@Valid @RequestBody Account`. В `Account.java:28–30` saving имеет `@NotNull`. Явное JSON `{"saving":null}` десериализуется с вызовом `Account.setSaving(null)` (`Account.java:71–72`), затем validation отказывает **до** handler/service. Bean поля name, lastSeen, incomes, expenses, note, отсутствующие на wire, остаются null по Java reference default. Их setters не вызываются лишь потому, что поле отсутствует. Объект Saving не создаётся, его setters/getters не исполняются.

Ожидаемые `executes=[account.Account.setSaving]`, `calls=[]`, `remote=[]`, `data=[]`, status 400 и `handler_entered=false` корректны. Причина — `org.springframework.web.bind.MethodArgumentNotValidException`, `javax.validation.constraints.NotNull` на `saving` со значением null. Это не source `IllegalArgumentException` и не вызов account `ErrorHandler.processValidationError`. `saveChanges` не успевает выполнить даже lookup (`AccountServiceImpl.java:76–79`).

Для строгой проверки необходимо:

- Дополнить Request `query={}` и `authorization=["Bearer supplied-user-token"]`, используя `aurora-user` из parent v2. Иначе существенный wire не согласован с его Bearer identity contract. Сам supplied post-auth context остаётся входом; ни токен, ни успешная OAuth проверка здесь не выводятся анализатором.
- Задать initial state целиком либо формальную разрешаемую ссылку на `/preconditions/initial_state` parent v2. `state="unchanged complete initial tables"` — текстовое пожелание; checker должен сравнивать фактические значения всех исходных таблиц после отказа, а не только count или отсутствие write events. Отдельно указать, что case начинается с этой initial state, а не с конца восьмишаговой цепочки.
- Оставить handler `bound_arguments` **непроверенными из-за отсутствия invocation**, но задать `binding_candidate_arguments`: principal с name aurora и source Account DTO с шестью полями, все null; provenance различает explicit-null saving и пять missing fields. На уровне complete argument list handler не был вызван. DTO candidate, его FQN и результат validation всё равно проверяемы.
- Задать события: request binding → framework callback `Account.setSaving(null)` → validation reject → HTTP 400. Не добавлять handler entry, service call, saving construction или data/remote. Body framework error явно не проверяется с причиной, как в parent v2.

Нельзя засчитывать строковое `bound_arguments="unmeasured..."` как проверенные значения параметров. Причина неприменимости handler arguments законна; отсутствующий rejected candidate этой причиной не покрывается.

## 2. `partly-known-real-list`

Закреплённый `TimePeriod.java:5` содержит **MONTH**. У Item поля и типы определены в `Item.java:10–24`: title/String, amount/BigDecimal, currency/Currency, period/TimePeriod, icon/String. Известный элемент Rent/7/USD/MONTH/home согласован с source types и field constraints. AccountSaving 20/USD/0/false/false также согласован с полями Saving. `amount=7` и Date `$instant` — семантические входные значения с нужными native Java types; это не факты о запуске JVM и не разрешение подменять BigDecimal строкой либо Date произвольным текстом.

GET source делает `accountService.findByName(name)` (`AccountController.java:19–22`). Service только проверяет непустое имя и возвращает найденную запись (`AccountServiceImpl.java:37–39`). Он **не сортирует и не фильтрует incomes**, не обращается к statistics и не выполняет `@Valid` над возвращаемой коллекцией. Поэтому неизвестность полей первого Item сама по себе не вызывает validation reject. `@Valid` на Account.incomes — field metadata; оно не является автоматически вызываемым getter guard при GET serialization.

При обычной успешной JSON serialization ожидаются source getter callbacks Account и Saving, а также **все пять Item getters для известного второго элемента**. Они входят в `executes`; прямых source `calls` из Account getter в Item getter нет. Вложенные getter callbacks вызывает сериализатор. Known Item не создаётся обработчиком; его setters не должны добавляться в граф лишь из-за того, что fixture задаёт начальную запись.

Wire GET с `server-reader` и его Authorization корректен: `AccountController.java:19` требует server scope для имени aurora. `ResourceServerConfig.java:54–58` также требует authenticated context на этом маршруте. Для полного wire стоит явно задать `query={}` и `body={"$missing":true}`, чтобы отсутствие не превратилось в null/пустой объект при переносе между fixture и Request.

Нужны следующие уточнения oracle:

- Задать полное отдельное `initial_state`: показанный initial_account как единственная или явно определённая строка accounts и точные строки/пустые списки остальных таблиц. Указать это формально, а не неявно наследовать конечное состояние восьмишагового сценария. `state after` должен сравниваться с полным initial state.
- Определить `{$unknown:true}` как **семантическую неизвестную позицию списка**, а не literal JSON объект, runtime Map или пропущенную запись. Указать declared element type `com.piggymetrics.account.domain.Item`, nullable/non-null alternatives и отсутствие произвольного неизвестного subtype/callback behavior. Например, допускается source Item с неизвестными значениями типизированных полей и/или null slot; для non-null случая runtime тип — source Item из профиля. Нельзя одновременно обещать нормальный 200 для произвольного неизвестного receiver с неизвестными сериализационными эффектами.
- Формально сохранить длину списка 2 и позиции: response incomes[0] остаётся той же неизвестной позицией, incomes[1] равен полному известному Item. Нельзя сжать результат до одного известного элемента, заполнить slot0 его значениями или использовать known second как first. Если slot0 допускает null, ожидаемый semantic unknown должен корректно включать эту альтернативу. Это не требование выводить literal `{"$unknown":true}` пользователю по HTTP.
- Указать типы Date (`java.util.Date` с точным instant), amount/interest (`java.math.BigDecimal`), Currency и TimePeriod в seeded и returned DTO. Сравнивать точные числовые значения и instant, не форму произвольного string representation. Object/collection provenance должно ссылаться на Account.incomes и исходный index, а не на compressed known-objects list.
- Добавить phase events: server-scope decision → handler entry с name aurora → repository findByName с точной возвращённой записью → response serialization callbacks → 200. У Item callbacks известного элемента зафиксировать receiver provenance `initial_account.incomes[1]` и все пять returned values. Нельзя требовать два вызова каждого getter без non-null/exact-type предусловия slot0; хотя уникальное `executes` для Item гарантировано известным slot1.

Указанные в v1 графовые множества соответствуют этому ограниченному semantic input. Дополнительные условия выше делают это проверяемым oracle, а не обещанием для произвольной непрозрачной коллекции.

### Новые source symbols

Все ниже относятся к module `account-service`, owner FQN `com.piggymetrics.account.domain.Item`, source `account-service/src/main/java/com/piggymetrics/account/domain/Item.java` с SHA-256 `4c4e72209093b482cd637c17c1e6d1261d6c9e7eced12f8447a4b8382c3d94dd`.

| Semantic ID | Declaration line | Source declaration | Известное возвращаемое значение |
|---|---:|---|---|
| `account.Item.getTitle` | 26 | `public String getTitle()` | `Rent` |
| `account.Item.getAmount` | 34 | `public BigDecimal getAmount()` | BigDecimal 7 |
| `account.Item.getCurrency` | 42 | `public Currency getCurrency()` | account Currency.USD |
| `account.Item.getPeriod` | 50 | `public TimePeriod getPeriod()` | account TimePeriod.MONTH |
| `account.Item.getIcon` | 58 | `public String getIcon()` | `home` |

Каждый getter на следующей строке только возвращает собственное поле. Все пять необходимо добавить в frozen method map для проверки `executes` и callback events. Setter declarations 30/38/46/54/62 существуют, но этот GET их не вызывает. Инициализация fixture вне пути запроса не считается выполнением source setters.

## 3. `ambiguous-account-read`

Оба source-контракта существуют и возвращают Account:

- `getAccountByName(@PathVariable String name)`, `AccountController.java:19–22`, GET `/{name}`; требуется server scope, кроме demo. Он нуждается в значении name.
- `getCurrentAccount(Principal principal)`, `AccountController.java:25–27`, GET `/current`; имя берётся из `principal.getName()` и может отличаться от искомого имени.

Второй метод отсутствовал среди 50 symbols исходной восьмишаговой цепочки. Для нового oracle добавить semantic ID `account.AccountController.getCurrentAccount`, module `account-service`, owner FQN `com.piggymetrics.account.controller.AccountController`, declaration line 26, declaration `public Account getCurrentAccount(Principal principal)`, source `account-service/src/main/java/com/piggymetrics/account/controller/AccountController.java` с SHA-256 `703a1e218d8173f9d47dc85f3de5d8fd333dc8531130f6371887b4f21d2144a5`.

Принятое поведение — запросить уточнение или вернуть явную unresolved ambiguity с обеими source hypotheses — разумно для намеренно недоопределённого действия `Read account`. Это **контракт обработки неопределённого NL-намерения**, а не факт о выполнении обоих HTTP handlers. Source доказывает наличие разных lookup contracts; сам Java-код не определяет смысл произвольной английской фразы.

Для строгого oracle явно задать:

- Identity context и его eligibility. Подойдёт parent `server-reader` с principal `account-service` и server scope: оба route contracts разрешены, имя для name-based hypothesis всё ещё отсутствует. При `aurora-user/ui` нельзя без объяснения назвать GET по произвольному имени одновременно разрешённым. Для anonymous закрыты оба защищённых GET, и security rejection — отдельная причина.
- Никаких введённых пользователем name/current/by-identity qualifiers, предыдущих Account refs или UI context, выбирающих один маршрут. Для name-based hypothesis missing name — незаполненный обязательный слот, а не доказательство готового Request. Две гипотезы ещё не означают два runnable запроса.
- Структурированный expected ambiguity: оба semantic IDs с недостающими аргументами/основаниями, selected handler/request отсутствует. Не назначать status/result успешного HTTP запроса; они не измерялись, потому что запрос не выбран. Не засчитывать это как проверенные Java arguments.
- Полное initial state и его неизменность, отсутствие source handler entry/data/remote. Не строить граф исполнения объединением кандидатов, не выдумывать name из principal и не выдавать молчаливый lexical top-1 за успешное разрешение неоднозначности.

## Граница принятия

В дополнительном v1 не найдены неверные MONTH, Rent/7/USD значения, source getters или ожидаемый validation status **при надлежащих предусловиях**. Его нельзя пока отмечать полностью принятым по § 9.3: важные поля остаются строковыми обещаниями. Необходимо выпустить отдельный дополненный oracle с новым SHA, сохранить v1 и явно привязать evaluator к новому файлу. Такой файл можно до реализации соответствующих механизмов проверить по этому заключению и источникам, не используя actual analyzer outputs для выбора ожиданий.

Эти три случая не доказывают отдельно duplicates `[A,A,B]`, одинаковый actual ID в разных deployments или login/token/header/failed clear. Их покрытие должно подтверждаться своими проверками; перечисление названия или успех частично известного GET не заменяет их.

## Дополнение: отдельный проверенный v2

После согласования замечаний с основным агентом подготовлен **`additional-source-cases.oracle-reviewed-v2.json`**. V1 сохранён без изменений. Новый SHA-256: **`5417ee09198c59c672589cbd1a448544259bb1c4c87f6dfea1dcb94519ebc63b`**. Рядом записан `ADDITIONAL-SOURCE-CASES.reviewed-v2.sha256`.

**Решение по этому v2: source-only oracle принят для трёх явно заданных случаев.** Это готовность ожидаемых данных к использованию, а не результат выполнения анализатора. Основной агент отдельно принимает конечный JSON и фиксирует его SHA в manifest evaluator. Независимость здесь не означает, что этот дополнительный v2 предшествовал всем runtime-изменениям: выводы получены без чтения runtime/outputs/tests, а не подгонкой под них.

V2 устраняет перечисленные выше пробелы:

- Каждый case независимо начинает с полного `initial_state` и требует точно равный `expected_state`. Account seed: name aurora, фиксированная Date, saving 20 USD / 0 / false / false, note partially-known-seed; в invalid/ambiguity incomes=null и expenses=[], в partial incomes содержит два явно заданных source Item. Все таблицы auth users и statistics datapoints перечислены. Это отдельный входной snapshot с seed из additional v1, **не** конечное состояние основной восьмишаговой цепочки с saving 20 EUR. Non-account таблицы взяты из main v2 initial preconditions. Provided post-auth identity является отдельным заданным входом; fixture не выдаётся за выполненный login.
- Invalid PUT имеет Authorization supplied-user-token, query={}, полный rejected Account DTO candidate с шестью null полями, раздельное происхождение explicit-null saving и missing остальных полей, supplied Principal aurora. Проверяется source setter event и validation 400 до handler. Неприменимость фактически invoked handler args явно сохранена и не засчитывается как проверенные параметры.
- Первый Item partial list теперь **точно non-null source Item**, второй — также non-null source Item. Неизвестны только пять типизированных полей первого. Для каждого поля указан отдельный symbol_id, declared Java type, допустимые native значения/null и input provenance. Источник не проверяет их constraints при GET. Marker означает semantic unknown value, а не literal HTTP JSON объект и не произвольный receiver с неизвестными callbacks. Результат обязан иметь объект с пятью неизвестными полями в index0 и полный известный Rent/7/USD/MONTH/home в index1.
- Partial GET содержит body missing/query={}, server-reader identity, полный bound String name и этапы read/serialization/response. Предписан 21 serialization callback: шесть Account, пять Saving и по пять для каждого из двух non-null Item. Каждый Item callback связан с конкретной исходной позицией и returned field value. Graph executes дедуплицирует их. Порядок обхода properties не выдумывается; source-to-source calls не дополнены фиктивными projection edges.
- Ambiguity использует явный server-reader principal account-service со scope server. History, refs, UI и supplied name/route qualifiers отсутствуют. Сохранённая строка aurora не становится недостающим аргументом намерения. Named hypothesis содержит missing name, current hypothesis — provided principal; оба допустимы как разные смыслы действия. Expected decision требует ровно unresolved candidate set, отсутствующий selected Request/handler, пустой execution graph, отсутствие handler/data/remote и неизменное полное состояние. HTTP status/result/actual args неприменимы, потому что HTTP выполнение не выбрано.

Сохранены 53 хеша pinned источников и расширенный map из **56 source-деклараций**: прежние 50 плюс пять Item getters и getCurrentAccount. При подготовке все 53 хеша повторно сверены с файлами, а все 56 declaration lines — с точным source text. Проверена JSON-структура трёх cases, неизменность initial/expected state, все referenced executes symbols, число и позиции Item callbacks. Эти проверки обрабатывали только oracle и исходники; анализатор не импортировался и не запускался.
