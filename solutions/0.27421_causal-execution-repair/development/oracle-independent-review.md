# Независимая проверка oracle PiggyMetrics

Дата: 18 октября 2026 года. Проверяющий: `/root/oracle_reader`, отдельный агент Codex, прямо разрешённый пользователем для этой проверки. DeepSeek не использован. Анализатор, JVM, целевые сервисы, сборки и тесты не запускались. Runtime анализатора, его результаты и результаты oracle-derived тестов для составления этого заключения не читались.

**Решение по v1: `requires correction`.** Ожидаемый HTTP 500 на шаге 3 противоречит включённому Hystrix fallback. GET по имени не имеет нужного server scope в заданной входной identity. Кроме того, в v1 отсутствовали фактические Java arguments и JSON callbacks.

**Решение по v2: source oracle принят для явно ограниченного восьмишагового бизнес-профиля после перечисленных ниже исправлений; принятие анализатора остаётся открытым.** Смысловые изменения согласованы с основным агентом до записи v2. Основной агент должен проверить и принять конечный JSON, заморозить используемый файл в manifest проверки и затем измерить соответствие анализатора. Пять дополнительных случаев, перечисленных в v1, всё ещё требуют отдельных source-frozen oracle; их названия не означают выполненные проверки. V2 не подтверждает OAuth, все требования § 9.3 или переносимость в целом.

## Целостность и хронология

| Объект | SHA-256 / состояние |
|---|---|
| Pinned PiggyMetrics commit | `6bb2cf9ddbca980b664d3edbb6ff775d75369278`, проверен через Git |
| `oracle.json`, v1 | `dfe0a69beda626fe85791d9d221303793942e85d7e8ea2453e505f6b4151e37a`, оставлен без изменений |
| `oracle.reviewed-v2.json` | `499f635f5df70eafafc6ef0b424266949d62f5886a77b4af5c9e9f1cf82a9e8d` |
| `source_sha256` v2 | 53 закреплённых файла; все 53 текущих хеша проверены |
| Дайджест `source_sha256` | `e2dd06a3f569f547626ec04c689c09fb08861870dfdf6e9df64024b798d24506`, SHA-256 от UTF-8 `json.dumps(map, sort_keys=True, separators=(',', ':'))` |
| `method_symbols` v2 | 50 source-деклараций; строки и тексты деклараций проверены непосредственно в исходниках |

V1 был заморожен до runtime-ремонта. V2 подготовлен после начала A/C и исправляет ошибки чтения источников, выявленные независимым читателем. У v2 намеренно стоит `frozen_before_any_runtime_repairs=false`. Нельзя представлять его как oracle, целиком замороженный до любых исправлений. Независимость v2 обеспечивается источником ожидаемых значений и отсутствием чтения analyzer outputs, а не вымышленной хронологией.

Файлы v2 и его SHA расположены в `experiments/20261018-causal-execution-repair/real-journey/`. Исходники ниже указаны относительно `experiments/20261018-review-corpus/public/piggymetrics/`; полные хеши включены в JSON.

## Исправления исходных предположений

1. **Hystrix fallback действительно активен.** Корневой `pom.xml:11–21` закрепляет Boot `2.0.3.RELEASE` и Spring Cloud `Finchley.RELEASE`. `account-service/pom.xml:35–38,59–65` содержит OpenFeign и Hystrix; `AccountApplication.java:14–16` включает Feign, circuit breaker и method security. `config/src/main/resources/shared/account-service.yml:24–26` задаёт `feign.hystrix.enabled: true`. `StatisticsServiceClient.java:10` указывает `fallback = StatisticsServiceClientFallback.class`; fallback помечен `@Component` на строке 11 и в `updateStatistics:15–17` только логирует и нормально завершается. Исходный тест `StatisticsServiceClientFallbackTest.java:19–20,34–38` дополнительно подтверждает предполагаемый путь fallback; он не запускался.

   Поэтому downstream 400 преобразуется в нормальное завершение `statisticsClient.updateStatistics` через fallback. Внешний PUT возвращает **200 с пустым телом**, а не 500. В `executes` добавлен source fallback; событие `framework_callback` объясняет его происхождение. Искусственного прямого `calls` от caller к callback нет.

2. **GET `/accounts/aurora` требует server scope.** `AccountController.java:19–22` проверяет `server` либо имя `demo`; `aurora` не удовлетворяет второму условию. Исходный request context v1 (`authenticated=true`, principal `aurora`, без OAuth scope) недостаточен для ожидаемого 200. Во v2 каждый GET имеет явно предоставленный server context и Bearer header. PUT `/current` получает отдельного principal `aurora` с `ui` scope. Создание остаётся анонимным: `account/config/ResourceServerConfig.java:54–58` разрешает `/` всем.

3. **OAuth-состояние — объявленный вход на границе профиля.** Source `ResourceServerConfig.java:33–42` создаёт client-credentials interceptor; `shared/account-service.yml:1–8` задаёт client ID, grant и scope. Auth `OAuth2AuthorizationConfig.java:44–57` различает browser/ui и account-service/server. Во v2 эти contexts разнесены; opaque token strings — только supplied values. Они не являются доказательством выпуска или криптографической проверки токенов. Client OAuth context считается уже заполненным, каждый HTTP-вход получает подтверждённый post-auth context. `CustomUserInfoTokenServices` и дополнительный HTTP introspection не замаскированы под часть проверенного пути.

4. **Incoming DTO account принимает `incomes=null`, statistics DTO его отвергает.** У `account/domain/Account.java:22–30` incomes/expenses имеют только `@Valid`, saving имеет `@NotNull`; все поля Saving из запроса не null (`account/domain/Saving.java:8–21`). У `statistics/domain/Account.java:14–24` incomes, expenses и saving обязательны. `StatisticsController.java:31–34` содержит `@Valid @RequestBody`. Это даёт `MethodArgumentNotValidException` / HTTP 400 после десериализации, до входа handler. Нулевой список не равен пустому списку: v2 сохраняет `incomes=null`, `expenses=[]`.

5. **DTO binding и JSON serialization вызывают source-методы.** Во v2 `executes` включает setter callbacks входного DTO, getter callbacks Feign encoder и ответа, а также setter callbacks statistics DTO до его validation reject. Эти события не означают входа отклонённого handler. `calls` описывает реальные source-to-source вызовы; roots framework callbacks описаны отдельно, без выдуманных caller edges. Порядок обхода bean properties не придуман: проверяется набор callbacks для конкретного trigger и их значения.

6. **Feign wire уточнён.** `AuthServiceClient.java:12` и `StatisticsServiceClient.java:13` задают `MediaType.APPLICATION_JSON_UTF8_VALUE`: существенный content type remote запроса — `application/json;charset=UTF-8`. Во v2 указаны `query={}`, body, header, remote identity и DTO FQN; добавлен отсутствовавший remote Request для шага 6. Source метод Feign с неаннотированным DTO-параметром использует тело запроса.

7. **Пустое тело и JSON null разделены.** Controller/fallback/remote handler с `void` не обещают JSON literal `null`. Во v2 есть `java_return={"$void":true}` и `response_body={"$empty":true}` для нормальных void ответов. Для framework-generated error bodies сохраняется явно непроверяемое поле с причиной; проверяются status, prefix и state.

8. **Args стали конкретными, а не текстовым обещанием.** Во v2 явно заданы `bound_arguments` с Java FQN, DTO полями, nested types и происхождением значения. У PUT отсутствующий на wire `lastSeen` становится null во входном DTO; source присваивает сохранённому account текущую Date. `body.name="body-mismatch"` не подменяет `principal.getName()="aurora"`. У отклонённого statistics запроса есть полный `binding_candidate_arguments`, но нет заявления о фактически выполненных handler arguments. У missing-body шага явно указан отказ без созданного DTO.

## Проверка каждого шага

| Шаг | Handler / вход | Подтверждённый результат и состояние | Источник |
|---|---|---|---|
| 1 | POST `/accounts/`; account `User(username=aurora,password=alpha-safe-pass)` | Оба обязательных поля проходят account validation. Account отсутствует. Remote auth handler вошёл, проверил отсутствие пользователя, вызвал BCrypt encode исходного пароля и сохранил auth User. Account получает `name=aurora`, текущую Date, Saving `0 USD / 0 / false / false`; incomes/expenses/note остаются null. Ответ 200 содержит Account; name — его `@Id`. | `account/domain/User.java:9–15`; `AccountServiceImpl.java:46–69`; `auth/UserController.java:27–30`; `auth/UserServiceImpl.java:25–35`; `account/Account.java:17–33`; `Currency.java:7–8` |
| 2 | GET `/accounts/{step1.response.name}`; server identity | 200, точная сохранённая запись. Значение route ID связано с полученным ответом; запрос не получает `body`. Есть `data(findByName,accounts)` и response getter callbacks. | `AccountController.java:19–22`; `AccountServiceImpl.java:37–39`; `AccountRepository.java:8–10` |
| 3 | PUT `/accounts/current`; principal aurora, входной DTO с несовпадающим name, incomes null, expenses [], saving 20 EUR, note | `saveChanges` выбирает строку по principal, копирует четыре редактируемых поля, присваивает Date и завершает локальный save **до** remote. Statistics body содержит сохранённое имя aurora, не body-mismatch. Stats DTO десериализуется, затем validation rejects incomes null: 400, handler/service/data не вошли. Hystrix вызывает fallback; внешний ответ **200 / empty body**, сохранённая Account запись остаётся изменённой. | `AccountController.java:30–32`; `AccountServiceImpl.java:76–90`; `StatisticsServiceClient.java:10–14`; `StatisticsServiceClientFallback.java:11–17`; `statistics/Account.java:14–24`; `StatisticsController.java:31–34` |
| 4 | GET того же ID с server context | 200, возвращает сохранённые на шаге 3 расходы, saving, note и null incomes. Это обязательная проверка полей, а не числа строк. | `AccountServiceImpl.java:37–39,78–90` |
| 5 | Повторный POST aurora | `findByName` находит существующий Account, `Assert.isNull` выбрасывает `IllegalArgumentException` **до** authClient. Account advice даёт 400 / empty body. В remote нет запроса; состояние обеих БД не меняется. | `AccountServiceImpl.java:48–51`; `ErrorHandler.java:17–20` |
| 6 | POST occupied; Account отсутствует, auth User occupied есть во входном состоянии | Account lookup пройден, auth handler действительно входит. Auth `Optional.ifPresent` читает username существующего User и выбрасывает IllegalArgumentException до encode/save. В auth нет source advice, меняющего это в 400; remote отвечает 500. У AuthServiceClient нет fallback; account получает Feign/Hystrix failure, а не прямой экземпляр remote IllegalArgumentException. Account advice по IllegalArgumentException его не перехватывает. Внешний ответ 500, новых записей нет, исходный пароль occupied не изменён. Remote edge достигнутого префикса сохраняется. | `AuthServiceClient.java:9–13`; `auth/UserServiceImpl.java:27–33`; `account/AccountServiceImpl.java:48–65`; `account/ErrorHandler.java:17–19`; поиск source advice в auth/statistics не обнаружил обработчика |
| 7 | GET aurora с server context | 200 с теми же полями, что после шага 3; отказ шага 6 не портит другую Account строку. | `AccountServiceImpl.java:37–39` |
| 8 | POST `/accounts/`, body отсутствует | Required RequestBody отвергнут: 400, никакого User DTO/handler/source-события DB/remote, состояние не меняется. Missing не заменяется JSON null или пустым объектом. | `AccountController.java:35–37`; Spring `RequestResponseBodyMethodProcessor.resolveArgument/readWithMessageConverters` |

На каждом шаге v2 задаёт полные значения всех логических persistent fields, включая пустую `statistics-service.datapoints`. Сравнение записей должно идти по указанному первичному ключу; порядок документов MongoDB не объявлен пользовательской семантикой. Mongo `_id` связан с Account.name/User.username. Внутренний `_class` и BSON bytes не названы проверенными бизнес-полями.

Не следует называть Mongo write здесь распределённым transaction commit. В выбранных source-методах нет транзакции, объединяющей local save и HTTP вызов. Oracle предполагает обычные успешные storage операции; завершённый save выполняется до remote reject. Его сохранность проверяется последующим чтением. Нет основания откатывать обе базы по одному HTTP status.

## ID, пароль и независимость проверки

`Account.name` и `auth.User.username` помечены `@Id` (`account/Account.java:17–18`, `auth/User.java:13–16`). Это source-defined идентификаторы, а не произвольно угаданные UUID. Ответ шага 1 обязан нести `name=aurora`; следующие чтения используют именно этот response-derived ID. Контрольный explicit Request и продуктовый NL-grounder должны оцениваться раздельно: нельзя давать продукту oracle для подстановки ID или выбора handler.

Auth пароль в БД — результат `encoder.encode(user.getPassword())`, `setPassword(hash)`, `repository.save(user)` (`auth/UserServiceImpl.java:19,30–33`). JSON boundary создаёт отдельный auth User объект: хеширование remote DTO не превращает caller account User пароль в хеш. Literal `alpha-safe-pass` не должен оказаться сохранённым как password auth User. Нельзя засчитать абстрактный произвольный non-null String без связи с encode input. `$encoded_from` — проверяемое требование к provenance семантического результата BCrypt; точные соль и байты хеша не зафиксированы.

V2 по-прежнему не содержит проверок пяти дополнительных случаев: unknown-list positions/duplicates, unrelated unknown producer, ambiguous source action, same actual ID across deployments и login/token/header/failed clear. Эти пункты сохраняются как pending; их нельзя закрывать успешными восемью шагами, пустыми expected.arguments или словом bounded.

## Первичные документы для границ библиотек

Документация проверена через Context7; для исторической версии основой служат официальные pinned источники, а не API нового Spring Cloud:

- [Spring Boot 2.0.3, § 76.3](https://docs.spring.io/spring-boot/docs/2.0.3.RELEASE/reference/htmlsingle/#howto-customize-the-jackson-objectmapper): default Jackson2 настройки отключают unknown-property failure и timestamp dates; поэтому лишние name/lastSeen/note в statistics JSON не обязаны обрывать binding раньше `@NotNull`.
- [OpenFeign 2.0.0, Hystrix support/fallbacks](https://raw.githubusercontent.com/spring-cloud/spring-cloud-openfeign/v2.0.0.RELEASE/docs/src/main/asciidoc/spring-cloud-openfeign.adoc): classpath + enabled property активируют wrapper; объявленный bean fallback используется при error. Эти условия прямо выполнены pinned конфигурацией проекта.
- [Finchley dependency BOM](https://raw.githubusercontent.com/spring-cloud/spring-cloud-release/vFinchley.RELEASE/spring-cloud-dependencies/pom.xml): историческая release train dependency, не предположение о современной версии.
- [Feign SynchronousMethodHandler](https://raw.githubusercontent.com/OpenFeign/feign/9.5.1/core/src/main/java/feign/SynchronousMethodHandler.java) и [HystrixInvocationHandler](https://raw.githubusercontent.com/OpenFeign/feign/9.5.1/hystrix/src/main/java/feign/hystrix/HystrixInvocationHandler.java): non-2xx проходит ErrorDecoder, normal void возвращает null на Java boundary, fallback вызывается через wrapper. Полное Maven dependency resolution не запускалось; для основного вывода о fallback дополнительно есть pinned OpenFeign contract и source fallback test проекта.
- [Spring 5.0.7 RequestResponseBodyMethodProcessor](https://raw.githubusercontent.com/spring-projects/spring-framework/v5.0.7.RELEASE/spring-webmvc/src/main/java/org/springframework/web/servlet/mvc/method/annotation/RequestResponseBodyMethodProcessor.java): body reading предшествует @Valid; missing body и invalid DTO различаются и отказывают до handler.

Этот отчёт и v2 созданы только из исходников, конфигурации, первичной документации и исходного ручного v1. Совпадение с будущим фактическим выводом анализатора не использовалось для выбора ожидаемых значений.
