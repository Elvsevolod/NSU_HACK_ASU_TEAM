# Разбор №30 и программа следующей реализации

**Дата проверки: 18 октября 2026 года.** Основание — `solution_30_collection_value_flow_analysis.zip` и приложенное задание `Вставленный текст(2).txt`. Этот документ содержит разбор, таблицу целей и полный промпт; отдельный `codex_overnight_implementation_prompt.txt` содержит тот же промпт для непосредственной передачи Codex.

## 1. Основной вывод и выбранное направление

**Продолжать от проверенного №30, сохранив его исправления, но сменить единицу работы: с «добавить очередную поддержку» на «устранить первую доказанную потерю и завершить конкретную цепочку значений, запросов и состояния».** Следующая версия должна сначала исправить неизвестный обход коллекций и типы аргументов массовых операций, безопасно пройти живой Map-цикл, затем закрыть независимую цепочку корзины через Stream, Optional, MVC и PATCH. Переписывать всё ядро сейчас оснований нет; организацию продолжений следует менять отдельным измеряемым экспериментом.

№30 не является пустой работой. Уникальность стандартного HashSet действительно исправлена, фильтр Basic219 с тремя доказанно ложными guards действительно пропущен с доказательством отсутствия эффектов, есть содержательные проверки сессий, двух пользователей, форматирования, inventory и сохранения полей. Но эти успехи пока не складываются в завершённое предсказание нужных пользовательских сценариев. В финальном сохранённом Train Ticket остаются **542 альтернативы с исчерпанным completion budget из 954 альтернатив**, а в корзине конкретный `orderId` уже приходит в repository, после чего теряется на неподдержанном terminal. Число альтернатив не является долей правильно решённых сценариев. [E02, E05, E08]

Почему возникает ощущение бесконечного ремонта: локальное исправление открывает следующий барьер, а приёмка слишком легко останавливается на исчезновении прежней ошибки. Есть и более опасный случай: анализ продолжает путь после потери точности и получает внешне правдоподобный пустой ответ. Поэтому теперь нужны одновременно **точные библиотечные контракты, явный статус незавершённости и проверка всей причинной цепочки**, включая отказы. Это инженерный вывод из найденных разрывов; он не устанавливает причины каждого изменения скрытой оценки.

Выбор №30 — выбор рабочей базы для переносимого Python-анализатора. №5 остаётся отдельно подтверждённым лучшим решением для зачёта. Возвращаться к его предметным правилам ради восстановления score не предлагаю. Сохранённое подтверждение сайта показывает, что после отправки №30 прежний №5 уже восстановили; в этой проверке я на сайт ничего не отправлял. [E01]

### Реалистичные направления

| Путь | Проверяемая польза | Цена и риск | Решение |
| --- | --- | --- | --- |
| Развивать №30 отдельными исправлениями native-контрактов и передачи значений | Сохраняет проверенные C1/C2, actor/frontend, formatter, типы и существующий корпус; исправляет найденные реальные разрывы | Нужно тщательно проверять границы и новые первые потери | **Основной путь** |
| Заменить организацию порядка и продолжений, сохранив семантические слои | Может убрать повторные эквивалентные обходы и широкое расширение состояния | Ошибка ключа эквивалентности теряет aliases, исключения, эффекты или рёбра; эффект ускорения пока не измерен отдельно | **Ограниченный эксперимент G06**, не обязательная полная переделка |
| Новое общее ядро, другой IR/движок | Возможно, даст более ясную семантику в перспективе | Снова потребуются Spring/HTTP/ORM/frontend-модели, история сценария и их проверки; текущие точечные дефекты этим автоматически не исчезнут | Отложить до результатов G03–G06 и G16 |
| Подгонять граф под старые рёбра или высокий сайт №5 | Может изменить конкурсную метрику | Не решает переносимость и причинное выполнение; противоречит ограничениям | Не использовать |

## 2. Что действительно проверено

Архив безопасно распакован в новый каталог. Исходные снимки не изменялись. Собственными скриптами на стандартной библиотеке Python пересчитаны хеши, множества рёбер и сводки сохранённых JSON. **Присланный анализатор, его тесты/checkers, JVM, сборки, сервисы Train Ticket и модели не запускались.** Новые контрпримеры ниже — программа проверок, а не уже выполненные тесты.

Установлено независимо от утверждений README:

- Все **4092** записи корневого MANIFEST совпали с файлами; пропусков, расхождений и непредусмотренных лишних файлов нет.
- В оценённом ZIP — 294 участника, из них 249 файлов code; его сохранённая серверная копия побайтно совпадает с отправленной. Code и submission соответствуют текущему финалу. README и IMPLEMENTATION_REVIEW обновлены после оценки: их нельзя считать содержимым исторической посылки.
- Code baseline внутри №30 — точно 236 файлов фактического №29; baseline submission совпадает с №29.
- Проверены **2916 хешей кода 12 стадий**. Прочитаны машинно 11 полных сохранённых отчётов; стадия E аварийная и submission не содержит.
- Пересчитаны все **11 сравнений по 103 шага**: сохранённые witness-хеши и дельты рёбер согласуются с пересчётом; расхождений не найдено.
- Имеющийся в предыдущем пакете Train Ticket пригоден для использованных source-ссылок: совпали все 10 записанных входных SHA — восемь сценариев, DB.gz, skeleton.gz. Совпали 1151 доступный защищённый файл TT, в том числе 1129 файлов target. Два отсутствующих вспомогательных файла перечислены в разделе ограничений.
- Для корзины совпали 99/99 файлов freeze-v2. У freeze-v1 отличается только форматирование SQL; сохранённая первоначальная ошибка возникает при чтении БД до выполнения сценария. Хронология «заморожено до первой инференции» согласуется с журналами, но не является независимой доверенной временной меткой. [E01–E03, E08]

Полная автоматическая обработка JSON означает проверку структуры, равенства и агрегатов. Она **не означает ручную верификацию каждой из 954 альтернатив против Java-семантики**. Содержательно исследованы прежде всего S6, поиск S1/явный TT-поиск, передача значений/сессии, реальные пути корзины, новые контракты и соответствующие проверки.

### Карта доказательств и соглашение о путях

Пути `code/...`, `checks/...`, `benchmark/...`, `development/...`, `validation_inputs/...` далее относятся к распакованному `solution_30`; `TT/...` — к `tt-challenge/targets/trainticket`. Номера строк относятся именно к этому снимку; для реализации надёжнее искать указанную функцию.

| Код | Доказательство |
| --- | --- |
| E01 | [site-score.json](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/benchmark/site-score.json), [независимая сверка архива](sandbox:/workspace/scratch/3c507d34b0c5/work_notes/review30_ev_integrity.json), [входные хеши TT](sandbox:/workspace/scratch/3c507d34b0c5/work_notes/review30_ev_inputs.json) |
| E02 | [пересчёт всех стадий, S0 и S6](sandbox:/workspace/scratch/3c507d34b0c5/work_notes/review30_ev_metrics.json), [final/analysis-report.json.gz](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/benchmark/final/analysis-report.json.gz), каталог benchmark/comparisons |
| E03 | [IMPLEMENTATION_REVIEW.md](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/IMPLEMENTATION_REVIEW.md), [requirements.json](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/development/requirements.json), [code-change-map.json](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/development/code-change-map.json) |
| E04 | [java_sets.py](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/code/analyzer/java_sets.py), [map_loop_proof.py](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/code/analyzer/map_loop_proof.py), [source_conversions.py](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/code/analyzer/source_conversions.py) |
| E05 | [tt-frontier.json](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/benchmark/tt-frontier.json), [адресуемые свидетельства TT/S6](sandbox:/workspace/scratch/3c507d34b0c5/work_notes/review30_exec_stage_witnesses.json), [BasicServiceImpl.java](sandbox:/workspace/scratch/3c507d34b0c5/analysis_input/tt-challenge/targets/trainticket/ts-basic-service/src/main/java/fdse/microservice/service/BasicServiceImpl.java) |
| E06 | [engine.py](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/code/analyzer/engine.py), [paths.py](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/code/analyzer/paths.py), [native_storage.py](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/code/analyzer/native_storage.py) |
| E07 | [S6: удалённые рёбра шага 8](sandbox:/workspace/scratch/3c507d34b0c5/work_notes/review30_ev_S6_step8_base_C1_C2.json), [S6: перенос 12 рёбер из шага 1 в покрытие шага 7](sandbox:/workspace/scratch/3c507d34b0c5/work_notes/review30_ev_S6_step1_retention.json) |
| E08 | [корзина: explicit.json](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/benchmark/cart-transfer-final/explicit.json), [nl.json](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/benchmark/cart-transfer-final/nl.json), [check_cart_profile.py](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/checks/check_cart_profile.py), validation_inputs/shopping-cart |
| E09 | [flow-witnesses-final/witnesses.json](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/benchmark/flow-witnesses-final/witnesses.json), [boundary-wires/checks.json](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/benchmark/boundary-wires/checks.json) |
| E10 | [legacy-final/checks.json](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/benchmark/legacy-final/checks.json), [document-journey/checks.json](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/benchmark/document-journey/checks.json), [17 мутационных контролей document](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/benchmark/document-journey/mutation-checks.json) |
| E11 | [phase timings](sandbox:/workspace/scratch/3c507d34b0c5/review30_input/solution_30/benchmark/final/analysis-report-timings.json), benchmark/stages/fair-base и checks/repeat_prepared.py |
| E12 | [подробная проверка исполнения](sandbox:/workspace/scratch/3c507d34b0c5/work_notes/review30_execution.md), [подробная проверка корзины](sandbox:/workspace/scratch/3c507d34b0c5/work_notes/review30_cart_stream.md); основные выводы этих рабочих записок полностью включены ниже |

Ссылки на вспомогательные JSON позволяют проверить точные tuples и JSON Pointer; для понимания выводов открывать их не обязательно.

## 3. История №30: что изменило ответ, а что изменило другие свойства

### Метрики и стадии

Сохранённый результат сайта: **0,36114 → 0,37269**, изменение **+0,01155**. S6: **0,44672740 → 0,43871457**, изменение **−0,00801283**. Открытый S0 остался **0,8008928571428572**; IoU executes/calls/remote/data: 0,828571428571 / 0,625 / 1 при двух пустых множествах / 0,75. В S0 remote по-прежнему пуст у prediction и gold; его IoU=1 ничего не добавляет к доказательству межсервисного анализа. [E01, E02]

| Стадия | E / C / R / D, сумма по сценариям | Всего | Что можно заключить |
| --- | --- | ---: | --- |
| base, точный №29 | 726 / 659 / 89 / 122 | 1596 | Воспроизводимая точка сравнения сохранённых ответов |
| C1-scalar-hashset | 723 / 656 / 89 / 122 | 1590 | Первые шесть удалений S6 |
| C2-noop-map-filter | 738 / 676 / 94 / 137 | 1645 | Проход Basic219; к C1 добавлено 55 рёбер |
| S1-angular-legacy, отдельная ветка от base | 726 / 659 / 89 / 122 | 1596 | Меняются свидетельства frontend/значений, не общий ответ |
| S2-actor-credentials, от S1 | 726 / 659 / 89 / 122 | 1596 | Меняются владельцы данных и часть шаговых рёбер; union тот же |
| C1-C2-S1-S2 | 738 / 676 / 94 / 137 | 1645 | Объединение веток сохраняет ответ C2 |
| F-formatter-effects | 738 / 676 / 94 / 137 | 1645 | Полезный ремонт formatter/состояния не меняет submission |
| E-effects-and-order-boundaries | Нет submission | — | Аварийная стадия, а не низкая оценка или частичный успешный прогон |
| E2-effects-and-order-boundaries | 720 / 654 / 89 / 132 | 1595 | После ремонта аварии более широкие границы эффекта меняют ответ |
| G-final | 720 / 654 / 89 / 132 | 1595 | Ответ E2 сохранён |
| H-source-proven-read-effects, текущий финал | 738 / 676 / 94 / 137 | 1645 | Уточнение доказанных read-effects возвращает ответ C2 |
| fair-base | 726 / 659 / 89 / 122 | 1596 | Отдельный контроль измерительных границ baseline |

E/C/R/D — executes/calls/remote/data. Это суммы отдельных сценарных графов, не число уникальных рёбер проекта и не оценка правильности. S1/S2 в названиях стадий здесь означают направления разработки, а не сценарии S1/S2.

**Финальный submission побайтно равен C2.** Следовательно, сайт оценил ровно этот сценарный граф; из website score нельзя получить отдельную оценку пользы поздних сессионных, formatter и state-исправлений. Это не обесценивает исправления — их нужно принимать по соответствующим value/state-контролям. [E02]

E завершилась ошибкой обработки nullable receiver metadata; E2 содержит её исправление. Наличие полного ответа E2 не доказывает верность слишком широких effects. В H есть более предметное доказательство чтения: стандартные/разрешённые derived reads и поддержанный простой SELECT сохраняются, `@Procedure`, `@Modifying`, default-метод с записью и неизвестные query effects не объявляются чистыми по префиксу. Проверены `resource_effects.proven_read`, `test_fallback_read_effects.py` и дельта G→H. Это допустимые общие Spring Data-правила, а не хардкод Train Ticket. [E03, E06]

### Что стоит сохранить

| Механизм | Что подтверждается | Граница подтверждения |
| --- | --- | --- |
| HashSet C1 | Уникальность известных скаляров; различение boxed kinds; null; неизвестный порядок; TT batch имеет 2 станции, 3 типа, 6 маршрутов | Не полный HashSet с пользовательскими equals/hashCode |
| Map no-op C2 | Три false guards Basic219 и пустой footprint; движение до следующего цикла | Не поддержка живого else Basic242; найдена отдельная ошибка проверки типа в proof |
| Angular/jQuery callbacks | Source-produced token проходит через storage в следующий header; отказы и соседние callback не смешиваются | В основном малые специально подготовленные Java/JS-профили; Angular-модель ограничена распознанной legacy API |
| Actor credentials | Разные actor scopes; admin без credentials не получает пассажирские значения; возврат к прежнему actor сохраняет его браузер | Это не понимание произвольной формулировки роли/аккаунта |
| Formatter | Source toString/getter и их effects/throws сохраняются; Petclinic снова сохраняет ID/поля/число строк | Ограниченная модель стандартного Spring formatter, не всех библиотек логирования |
| Inventory | В explicit и NL: три записи → выбранная запись → изменение quantity/revision → reread | All-present ветка не проверяет исполнение removeAll на отсутствующей категории |
| Document/Piggy/Petclinic | Сохранены более строгие проверки wire, DTO, state, errors и рёбер в заявленном профиле | Прочитанные сохранённые results; мои свежие прогоны отсутствуют; не универсальная точность |
| Singleton/aliases | Есть контроль: разные ветви меняют один bean, последующая запись revision=10 видна следующему запросу | Не доказательство корректности всех join/alias-графов |

Прочитаны соответствующие новые тесты, включая `test_actor_credentials_flow`, `test_angular_legacy_session`, `test_spring_formatter_effects`, `test_absence_escape`, `test_singleton_join_identity`. Число **1762** — сохранённый результат авторского набора, не количество независимо проверенных мной семантических утверждений. Document checker действительно сравнивает типы/arguments/state/status/graph; 17 сохранённых мутаций отклонены, в том числе ошибки, которые прежняя value-only проверка принимала. [E09, E10]

## 4. S6: полный разбор изменений

### 4.1. Итоговый сценарный граф

| Отношение | №29/base | №30 final | Добавлено | Удалено |
| --- | ---: | ---: | ---: | ---: |
| executes | 119 | 116 | 0 | 3 |
| calls | 101 | 98 | 0 | 3 |
| remote | 18 | 18 | 0 | 0 |
| data | 16 | 16 | 0 | 0 |
| Всего | 254 | 248 | 0 | 6 |

Ниже **все шесть удалений**, без выборки удобных случаев. Для краткости полные method IDs определены один раз:

- A = `method:ts-basic-service:fdse.microservice.service.BasicServiceImpl#queryTrainTypeByNames(java.util.List,org.springframework.http.HttpHeaders)`
- B = `method:ts-common:edu.fudan.common.util.JsonUtils#conveterObject(java.lang.Object,java.lang.Class)`
- C = `method:ts-common:edu.fudan.common.util.JsonUtils#object2Json(java.lang.Object)`
- D = `method:ts-common:edu.fudan.common.util.JsonUtils#json2Object(java.lang.String,java.lang.Class)`

| source | relation | target |
| --- | --- | --- |
| scenario:S6 | executes | B |
| scenario:S6 | executes | C |
| scenario:S6 | executes | D |
| A | calls | B |
| B | calls | C |
| B | calls | D |

Первое исчезновение — **base→C1-scalar-hashset**, до C2 и actor/frontend изменений. Все шесть происходили только из пользовательского шага 8: поиска высокоскоростных поездов Shanghai→Ning Bo на 1 октября 2026. В baseline они присутствуют в альтернативах с индексами **4, 5, 6, 7, 12, 13, 14, 15**, и все восемь завершаются budget outcome. В C1/C2 ни одна из 16 альтернатив их уже не содержит. Индексы разных версий нельзя считать парами одинаковых путей. JSON Pointer: `/scenarios/S6/steps/7/alternatives`; converter events baseline находятся, например, в alternative 4. [E02, E07]

### 4.2. Шаговые рёбра: ещё 12 удалений в admin-login

Фраза «в S6 изменился только шаг 8» была бы неверна для final относительно base. Она верна для edge-дельты **base→C1→C2**. Отдельно на S1-angular→S2-actor, а затем при включении actor-ветки в combined, из **шага 1** исчезают следующие 12 рёбер:

| Отношение | Все удалённые рёбра шага 1 |
| --- | --- |
| executes, 8 | `auth.entity.User#getAuthorities()`, `getPassword()`, `getUsername()`, `isAccountNonExpired()`, `isAccountNonLocked()`, `isCredentialsNonExpired()`, `isEnabled()`; `auth.security.jwt.JWTProvider#createToken(auth.entity.User)` |
| calls, 2 | `TokenServiceImpl#getToken(BasicAuthDto,HttpHeaders) → JWTProvider#createToken(User)`; `JWTProvider#createToken(User) → User#getUsername()` |
| remote | Нет |
| data, 2 | `UserDetailsServiceImpl#loadUserByUsername(String) → res:table:ts-auth-service.user_roles`; `TokenServiceImpl#getToken(BasicAuthDto,HttpHeaders) → res:table:ts-auth-service.auth_user` |

Все method IDs этой таблицы имеют prefix `method:ts-auth-service:`; полные пакеты service — `auth.service.impl.TokenServiceImpl`, security — `auth.security.UserDetailsServiceImpl`, JWT — `auth.security.jwt.JWTProvider`, DTO — `auth.dto.BasicAuthDto`; полные tuples сохранены в E07.

**Все 12 остаются в шаге 7 S6, passenger-login, в альтернативах 0 и 1.** Поэтому они не исчезают из union-графа и не меняют submission. Причина изменения шага 1 прослеживается в input: старый admin-login брал общие пассажирские credentials, новый выбирает actor=admin и сохраняет отсутствие установленных credentials как unknown; пассажирский шаг 7 использует свои actor-owned facts.

Особенность сериализации: `body={}` в этих свидетельствах не означает доказанное отсутствие username/password — `body_properties` отмечает их как present, а bound values неизвестны. Нельзя смешивать absent, null и unknown-present. Это улучшение принадлежности входных данных, а не доказательство успешной административной сессии. [E07, E09]

На уровне шагов final относительно base: **0 добавлений и 18 удалений — −11 executes, −5 calls, 0 remote, −2 data**. Двенадцать удалений шага 1 сохраняются в union через шаг 7.

В поздних стадиях есть дополнительные изменения witness/state без изменений сценарного union: F→E2 и G→H затрагивают шаги 8–14, E2→G — шаг 4. Они учтены в полном сравнении; их нельзя объяснять шестью удалениями C1.

### 4.3. Первая содержательная развилка и три причины, которые надо разделить

**1. Состояние неизвестно ещё до поиска.** В base, C1 и final таблица station впервые становится unknown на части исходов шага 2, train_type — шага 3. К завершению шага 7 обе returned-альтернативы несут шесть unknown tables: station, train_type, route, route_distances, route_stations, price_config. Это исходное состояние шага 8, а не результат HashSet в его поиске. Точная цепочка «первый effect/write → конкретный join → unknown table» пока не восстановлена; G02 требует её найти. [E05, E12]

**2. Унаследованная ложная определённость unknown foreach.** В `StationServiceImpl.queryForIdBatch` (строка 103) source сначала получает stations, создаёт stationMap, затем цикл 107 заполняет его, а цикл 111 читает по именам. `repository_values.unknown_result` возвращает opaque JavaList. В `Engine.execute`, строка 1332, unknown enhanced-for вызывает fallback и возвращает normal completion, не расширяя локальные записи пропущенного тела. StationMap остаётся известным пустым. Затем каждое имя получает известное null.

Это подтверждено кодом и сохранёнными условиями: C1/S6/step8/alternative1 содержит warning Station107, а в Basic191 дважды выбирается «значение станции равно null». **Неизвестное множество строк не доказывает отсутствие всех станций.** Дефект существует и в №29; его нельзя приписывать появлению C1. [E06; TT/ts-station-service/src/main/java/fdse/microservice/service/StationServiceImpl.java, `queryForIdBatch`]

**3. Тип аргумента теряется, а порядок расходует резерв продолжений.** В Basic194/197 `avaTrips.removeAll(startTrips.get(...))` получает unknown operand из-за отсутствующего consumer contract. После этого членство avaTrips неизвестно, Basic202/Train65/Basic382 создают дополнительные развилки. C1 добавляет корректную неопределённость порядка Station111. `java_sets.next_index`, строка 18, переводит неуместившийся порядок в CompletionRequired; `paths.run_paths` расходует тот же completion_splits, который нужен `Engine.fork_join` для разных normal/return/throw completion. В сохранённых budget-альтернативах C1 остановка наблюдается на mixed completion в queryTrainTypeByNames перед JsonUtils; остальные восемь альтернатив returned. [E04, E06]

**Установлено:** точный этап исчезновения, новые order choices, общий резерв, потеря consumer type, inherited unknown-foreach. **Гипотеза:** эквивалентные порядки вместе с избыточными развилками вытеснили нужное продолжение. **Не измерено:** отдельный вклад каждого фактора и семантическая правильность каждой из шести старых дуг.

### 4.4. Что можно и нельзя вывести из site score

При неизменных hidden gold, фильтрах и формуле IoU удаление только ложноположительных рёбер не может уменьшить оценку. Поэтому **условно**, при этих предпосылках, уменьшение S6 означает, что хотя бы одно из удалённых рёбер было нужным эталону. Однако хеша скрытого эталона нет; это не доказывает, какое ребро нужно, правильность всех шести или семантическую причину их потери. Практический вывод — исследовать source-путь и state, а не восстанавливать tuples вручную.

### 4.5. Изолирующие проверки

| Гипотеза/дефект | Минимальный независимый пример | Что отделяет эксперимент | Правильный результат |
| --- | --- | --- | --- |
| Unknown foreach становится пустым | Неизвестный repository List заполняет новый Map; затем проверка `map.get("A")==null` | Состояние БД и эффект пропущенного локального цикла отдельно от HashSet | Не выдавать известное true без доказательства отсутствия A |
| Недостающий bulk consumer type | `out.removeAll(groups.get("obsolete"))` и эквивалентный local-variable вариант | Тип потребителя отдельно от scheduler и домена | При out=[A,B,C], group=[B]: true и [A,C]; аналогично Set |
| Порядок отнимает completion reserve | Unordered set из нескольких элементов, коммутативное заполнение Map, затем unknown-ветка return/throw | Порядки/эквивалентные состояния отдельно от приложений | Сохранить все требуемые completion/effects или явную незавершённость |
| Нужная ветка зависит от порядка | В том же обходе callback меняет счётчик или бросает | Предотвращает ложное слияние порядков | Различия сохраняются; нельзя применять коммутативный proof |
| Upstream state преждевременно расширен | Изолировать конкретный source fragment шага 2/3 с теми же initial rows; paired known read / possible write | Начало unknown table до search | Proven read сохраняет rows; реальная/возможная запись меняет нужный ресурс с provenance |

Все эти новые проверки ещё предстоит выполнить. Повышение глобального бюджета может быть только диагностической абляцией с сохранённым baseline; само по себе оно не принимается как исправление.


## 5. Train Ticket: два разных места остановки

### 5.1. Поиск с известной исходной БД

В явном сохранённом probe запрос — POST `/api/v1/travelservice/trips/left`, body содержит startPlace, endPlace, departureTime. Для него уже получены известные batch-ключи: две станции, три типа, шесть маршрутов. C2 доказывает Basic219. Затем **перед первым элементом Basic242** выбор из шести route groups не помещается в сохранённый `path_limit=4`. `map_views.iterator_next → Engine.view_items → widen_map_iteration` расширяет все достижимые native roots локального окружения. Это значительно шире неизвестных записей тела цикла. [E04–E06]

В final S1, шаг 2, во всех восьми альтернативах нет ни одного условия строк 244–255. В alternative 0 есть `routes != null`, а следующая `avaTrips.size()==0` на Basic260 уже unknown. Возвращаемая ветка выбирает отсутствие поездок; TravelServiceImpl возвращает исходный пустой responses и другой source-метод заворачивает его в status=1. Поэтому внешний `{status:1,data:[]}` **имеет source-происхождение внутри расширенной альтернативы**, но не доказывает фактически пустой поиск. Другие альтернативы заканчиваются budget. [E05; TT/ts-travel-service/src/main/java/travel/service/TravelServiceImpl.java, `getTicketsByBatch` и `queryByBatch`]

В S6 поиск начинает с уже неизвестных таблиц и застревает раньше. Объединять два места остановки в одну причину «не хватает бюджета Basic242» нельзя.

### 5.2. Узкий ремонт generic/bulk вместо переписывания всех generics

У `Map<K,V>.get` тип V уже выводится в `Engine.source_type`, строка 2162. Ошибка появляется позже: `source_conversions.argument_type`, строка 90, знает `addAll(Collection)`, но не `removeAll/retainAll(Collection)`. `consumer_type` передаёт пустой expected type в `native_read_cast`; известный JavaList стирается до U.

Это подтверждено и на реальном S6 Basic194/197, и на независимом inventory. В сохранённом `inventory-negative-tests.txt` правильный результат удаления не получен; текущий `test_inventory_collection_journey.py`, строка 107, уже ожидает U/boundary. Такое ожидание полезно как честная фиксация ограничения, но не закрывает семантическую задачу. [E04, E12]

Минимальное исправление: общий descriptor **стандартного** метода Collection с проверенными receiver, overload и arity; argument `Collection<?>` сохраняет известный carrier. Source-defined override не должен перехватываться совпадением имени. Сначала парные tests direct-vs-local для List и Set, затем живой inventory case, затем S6. Null, unknown, несовместимый raw carrier, пользовательское equals/hashCode и read-only коллекции — отдельные отрицательные случаи.

### 5.3. Безопасность no-op proof

Найден отдельный дефект нового C2: `map_loop_proof.fits`, строка 31, принимает JavaArray за List/Collection, потому что JavaArray наследует Python-класс JavaList и получает flavor ArrayList. Обычная `Engine.reference_check`, строка 979, такой cast правильно отвергает.

Статический контрпример:

```java
Map raw = new HashMap();
raw.put("x", new String[]{"v"});
Map<String,List<String>> typed = raw;
for (Map.Entry<String,List<String>> e : typed.entrySet()) {
    List<String> xs = e.getValue();
    if (xs == null) { touch(); }
}
```

Source-присваивание xs требует ClassCastException. Proof может объявить normal-only no-op, пропустив эту проверку. **Контрпример не запускался**, связь с S6 не установлена. Нужен чистый общий predicate совместимости runtime reference с типом и paired proof-on/proof-off test. Одновременно нельзя отвергать стандартный Set как Collection только из-за внутреннего flavor: это другой, консервативный отказ proof. [E04, E06]

### 5.4. Как пройти живой Basic242

Тело цикла действительно может исполнять else: читать route и trips, вызывать source getters, проверять наличие и порядок станций и удалять часть avaTrips. Старый all-false proof правильно его отклоняет.

| Механизм | Когда применим | Что обязан сохранить | Решение |
| --- | --- | --- | --- |
| Ограниченное семантическое правило фильтра | Известные native containers; доказан footprint; решения по отдельным элементам не зависят от порядка; нет неподдержанного alias/equality/callback эффекта | Нужные удаления, source calls/executes, normal/throw, типы и неизменённые входы | Первый кандидат G05 |
| Слияние эквивалентных остаточных состояний | Одинаковые program point, remaining items, heap/aliases, DB/session, path constraints и completion | Различающиеся эффекты и исключения; union доказанных рёбер с provenance | Пилот G06 |
| Мемоизация summaries | Есть проверенная зависимость от input/read set и способ корректно применить effect/return/throw summary | Инвалидацию по версиям ресурсов, actor/session/clock/config и alias identities | После доказанного узкого summary |
| Worklist/continuations | Измерено, что повторный replay, а не библиотечная потеря, доминирует | Полноту раздельных completion и состояние каждой задачи | Отдельный эксперимент, не ночная перепись всего ядра |
| Сортировка Map или глобальное увеличение budget | Не даёт семантического основания | — | Не принимается как самостоятельный ремонт |

Не нужно сокращать footprint по названию getter. Если source callback меняет общий объект, сохраняет данные, вызывает remote или бросает, это должно быть исполнено/суммировано с доказательством либо оставаться границей. Ограниченная оптимизация может честно отказаться от такого случая.

### 5.5. Цепочка результата и следующий запрос

Полезная единица проверки:

**действие → выбранный frontend callsite → wire → фактический DTO/аргументы → ветви/remote/data → ответ root-request → изменения DB/beans/browser → запись history → поля следующего wire.**

Нужны ссылки producer→consumer на уровне конкретных полей, а не только совпадение числового ID. Для каждого результата отдельно фиксировать: доказанно завершённый непустой, доказанно пустой, неизвестный, частично исследованный/оборванный. Business HTTP status и завершённость анализа независимы: status=200/1 может соседствовать с analysis boundary. История не должна превращать отсутствие пригодного результата в конкретный ID из предыдущего несвязанного шага.

В сохранённом `tt-frontier.json` следующий NL body имеет travelDate, но выбранные tripId/from/to ещё не получены. Реальная последовательность search→select→booking пока не восстановлена. Изолированная успешная оплата её не доказывает.

**Оплата:** реальный UI body содержит **только orderId и tripId**. В source-верном отдельном probe это приводит к ветке внешней оплаты при userId=null; вариант с добавленным userId проходит другую ветку. Это две разные проверки, их нельзя смешивать. Дополнительный userId допускается только при его происхождении из actual UI/контекста исследуемого запроса; вставка его ради желаемой внутренней оплаты ошибочна. В NL orderId/tripId пока неизвестны, поэтому успех отдельного явного запроса не доказывает успех исходного сценария. [E05, E12; TT/ts-ui-dashboard/static/assets/js/client_order_list.js, `payMyOrder`, строка 112; body121–124; TT/ts-inside-payment-service, `pay`]

## 6. Корзина: полезный независимый профиль, который ещё не пройден

Пакет содержит source двух сервисов проекта shopping-cart, заявленный commit **64273c71575d61db8de6ba1a582b02f6a11103b3**, Java **21**, Spring Boot **4.0.6**. Commit установлен по frozen metadata и содержимому пакета; удалённый upstream commit отдельно не подтверждался. Начальный SQL и сценарий подготовлены для проверки, а не сняты с работающего приложения. Это допустимые явные входы. [E08]

### 6.1. Что сохранено по восьми шагам

| Шаг | Намерение профиля | Сохранённый результат №30 |
| --- | --- | --- |
| 1 | GET payments?orderId=11 | Repository получает [11]; четыре альтернативы, все result=U после toList |
| 2 | Выбрать APPROVED payment и refund | Explicit не выполняется: producer не дал ID; NL строит запрос с ID=U |
| 3 | Перечитать этот payment | Explicit не выполняется; NL не подтверждает нужную identity |
| 4 | Перечитать связанный order | Explicit не выполняется; конкретная межсервисная цепочка не подтверждена |
| 5 | Повтор refund, ожидаемый отказ | Explicit не выполняется; NL с U не доказывает repeat refusal |
| 6 | GET payment 999, отсутствующий ID | В explicit две альтернативы 200 с DTO из null-полей и две exception/status U; нужного 404 нет |
| 7 | Неоднозначное «Read the record» | В NL нет произвольно выбранного entry; это полезный отрицательный результат |
| 8 | Перечитать payments данного order | First loss повторяется; итог REFUNDED не доказан |

В NL на шаге 2 сохранены возможные save и последующее unknown состояние payment table. Это последствия анализа с неизвестным ID, а не выполненный возврат конкретного платежа. Explicit probe missing-ID остаётся важным независимым входом: его БД ещё конкретна. [E08]

Первая потеря установлена точно: `PaymentPersistenceAdapter.findByOrderId`, строка 62, читает по известному аргументу 11; строка 65 вызывает `map(PaymentPersistenceMapper::toDomain).toList()`. `Engine.stream_call`, строка 3340, отказывает terminal до выполнения mapper. Затем PaymentController, строка 114, получает неизвестную коллекцию. Это **не проблема выбора handler или извлечения первого orderId**.

### 6.2. Checker сначала нужно сделать пригодным для успеха

Текущий `check_cart_profile.py` намеренно записывает failed-transfer: `passed=False`, first_loss=Stream.toList, затем требует наличия этого warning. После исправления terminal старый checker не станет положительным; его assertion должен перестать выполняться. Старую запись сохраняем, новый evaluator версионируем.

Есть и содержательные пробелы: edges объединены между шагами; отсутствие exact step count; status выбирается без обязательной связи с root request; не проверены все changes/writes/error_code/provenance/NL contracts. При неоднозначности hypothetical trace с **двумя выполненными mutating handlers** прошёл бы критерий «не ровно один entry». Произвольный выбор read-only GET также нарушает must_not_choose, даже без изменения состояния. Текущие реальные нулевые alternatives этому плохому примеру не соответствуют, но новый negative нужен. [E08, `check_cart_profile.main`]

Oracle содержит **18 необходимых рёбер: calls 13, data 4, remote 1, executes 0**. В сохранённом результате найдены соответственно 3/13, 2/4, 0/1; executes вообще не размечен этим subset. Это покрытие объявленного обязательного subset, не recall полного графа, не full precision/IoU и не доказательство всех четырёх отношений. Новый gate должен проверять рёбра по шагам, нужные/запрещённые эффекты, typed values и состояние; полную точность графа можно объявлять только после отдельной полной разметки.

### 6.3. Точный Stream.toList для Java 21

Свежая проверка выполнена по первичным Java 21 API, см. раздел источников. `Stream.toList()` — terminal с сохранением encounter order, если он задан, и неизменяемым контейнером результата; API не обещает конкретную реализацию списка или пригодность identity-sensitive операций. В default implementation нет отбрасывания null. `Collectors.toList()` не гарантирует mutability, а `Collectors.toUnmodifiableList()` отвергает null. Поэтому простое переименование в существующий collect или List.of семантически недостаточно. [W1, W2]

**Минимальная предлагаемая поддержка** использует текущий lazy pipeline и source callback engine:

| Свойство | Требование к реализации и проверке |
| --- | --- |
| Materialization | Новое хранилище результата. Уже имеющийся ReadOnlyList можно обернуть вокруг нового backing; view над исходным source использовать нельзя. Новое внутреннее хранилище не доказывает новую Java identity; два результата не должны автоматически считаться разными объектами |
| Элементы | Сохранить null, повторы, declared/observed types и связь с исходными объектами; mapper создаёт новые объекты только через своё source-выполнение |
| Порядок | Передавать доказательство порядка от источника. Не превращать SQL без ORDER BY или HashSet в известный порядок INSERT/обхода Python |
| Кардинальность | Знать размер при полностью определённой materialization; unknown predicate/membership не превращать в точный размер |
| Callbacks | Исполнять необходимые mapper/filter callbacks через существующий механизм, сохранять calls/executes/effects/throws; не объявлять удалённый callback «чистым» по имени |
| Exceptions | На throw не выдавать нормальный список; сохранять предшествующие эффекты и отсутствие последующих callbacks для принятой последовательной модели |
| Mutators | Проверить add/set/remove/clear/bulk/iterator/view; read-only контейнер не означает неизменяемость объектов внутри |
| Lifecycle | Сохранять linked/consumed между aliases; повторное использование не должно давать второй нормальный результат |
| Неизвестные случаи | Явная boundary с сохранённой областью неопределённости; без ложного пустого списка и без выдуманного порядка |

В №30 существующий collect умеет lazy filter/map над ограниченной последовательной коллекцией и уже выполняет callbacks. Но reused stream возвращает U+warning; unordered source более одного элемента останавливается; general interference поддержана частично. Это границы имеющейся модели, которые новый terminal не должен скрыть. В версии №30 нет самостоятельного полного unmodifiable-toList контракта. [E06, `stream_call`; `test_java_streams`, `test_stream_parameter_types`]

Java Stream допускает оптимизации некоторых pipeline и не даёт общей гарантии исполнения всех side effects произвольных callbacks. Поэтому proposed interpreter contract надо ограничить поддержанным последовательным materializing pipeline; нельзя перенести его на count/short-circuit/parallel. Источник, изменённый до terminal, и interference во время terminal — также разные случаи. [W3]

**Два обязательных отрицательных контроля:**

1. `Stream s=xs.stream(); Extension.touch(xs); s.collect(Collectors.toList())` при первоначально пустом xs. Если opaque effect меняет source на неизвестный, physical len=0 не доказывает пустоту. В текущем collect terminal нет начального opaque guard для уже созданного pipeline; проверка после callback при нулевых итерациях не сработает. Прямой `alreadyOpaqueList.stream()` раньше перехватывается другим guard — нельзя приписывать ему тот же обход. Новый контрпример ещё не запускался; для будущего toList нужен тот же отрицательный контроль. Сам toList в №30 пока unsupported и не выдаёт этот конкретный пустой результат.
2. Repository возвращает две строки без ORDER BY; последующий `toList().get(0)` не должен выбирать первую INSERT-строку как гарантированную. Сейчас materialization создаёт JavaList с default order_known=True, а association loading лишь предупреждает о недоказанном порядке. Для cart выбор единственного APPROVED от перестановки не зависит; именно такой вывод допустимо доказать отдельно. [E06, `stream_call`, `repository`; `persistence.py`]

### 6.4. После Stream уже видны следующие препятствия

| Препятствие | Достигнуто или предстоящее | Минимальный ремонт |
| --- | --- | --- |
| Optional.map теряет absence | **Достигнуто** на explicit GET999: adapter строка 48 | Preserve present/empty/unknown и result type; mapper только при present, но null-функция отвергается и при empty; затем корректный orElseThrow |
| MVC specific handler против catch-all | Подтверждено статически; корректный domain throw пока теряется раньше | Выбирать доказуемо более специфичный handler в ограниченном advice-профиле |
| Параметр HttpServletRequest в advice | Подтверждено статически: engine строка 465 передаёт failure.value всем параметрам | Раздельный binder исключения/request/response; проверка request URI |
| patchForObject | Подтверждено статически; конкретный refund ещё не дошёл | Descriptor метода, body/class token/URI args, статус и exceptions через общий HTTP pipeline |
| localhost:8083 → order-service | Подтверждено статически: hostname теряет port, host/module substring не связывает endpoint | Source/config facts host+port+deployment/profile; не игнорировать host глобально |
| reduce в Order.total | Подтверждено source; ещё не достигнуто конкретным refund | Ограниченный последовательный fold с typed BigDecimal/callbacks |
| ORM/JSON/record и дальнейшая история | Возможные следующие границы, не объявлены уже причинами | Исправлять только после следующего конкретного first-loss witness |

У cart PATCH не упирается в предположение «Java-клиент вообще не умеет PATCH»: `ApplicationConfig`, строка 34, явно создаёт **HttpComponentsClientHttpRequestFactory**, и pom содержит httpclient5. Это положительное source-доказательство. У произвольного RestTemplate конфигурация может быть иной; API-поддержка метода и способность конкретной request factory отправить его — отдельные факты. [E08; W5]

Remote-сервер всё равно строит OrderResponse, даже если клиент запросил Void.class. Его `OrderHttpMapper.toResponse` вызывает `Order.total`, который использует `reduce(BigDecimal.ZERO, BigDecimal::add)`. Игнорирование client payload не разрешает пропустить server executes/data/errors. Значение total=12.5 из oracle нельзя переносить в модель вместо source-вычисления.

### 6.5. Состояние и граница профиля

Source refund сначала сохраняет payment.refund(), затем вызывает remote revert order. Повторный REFUNDED не проходит guard APPROVED и должен остановиться **до save и remote**. После успешной цепочки ожидаются REFUNDED для выбранного payment и PENDING для связанного order; другие записи и их число сохраняются. Источник не задаёт автоматический распределённый rollback всех предшествующих запросов при remote error. [E08; `RefundPaymentUseCase.execute`, `Payment.refund`, `RevertOrderToPendingUseCase.execute`]

В исходном oracle есть слишком сильное требование обязательного write в order_details. Cascade и сохранение aggregate не доказывают физический UPDATE неизменённых детей. Новый evaluator должен отдельно проверить итоговые children/IDs/поля/кардинальность и доказанные datastore effects; не добавлять data/write ради старого ожидания.

Профиль явно ограничен **прикладным выполнением после аутентификации**. При этом нынешний runner создаёт обычный HTTP Request без headers, а часть JWT filter видна в trace; полная authenticated security chain не доказана. Нужно сделать post-auth starting boundary явной в runner/witness. Нельзя объявлять это успешной моделью всей Spring Boot 4/JJWT 0.11.5 безопасности, отключать общую security или вставлять токен. Дальнейшая поддержка security — отдельная задача, сейчас не prerequisite прикладного профиля.

После настройки на cart этот набор станет регрессионным контролем. Для следующего заявления о переносимости нужен **другой заранее замороженный прикладной профиль**, с исходниками, контекстом, сценарием и independent oracle, подготовленными до просмотра его нового результата. При отсутствии подходящих входов честный итог — ограничение, а не переименование train/inventory примера в новый holdout.

## 7. Измерения и критерии прогресса

| Измерение, сохранённая сопоставимая пара | fair-base №29 | №30 final |
| --- | ---: | ---: |
| Подготовка, с | 6,1986 | 6,4037 |
| Расчёт сценариев, с | 68,2015 | 67,2997 |
| Полный интервал до завершения final report write, с | 85,5526 | 85,1478 |
| Peak RSS, bytes | 447 152 128 | 451 428 352 |

Для final запись отчётов отдельно занимает 11,4095 с. Prepared repeats — 55,9441 и 54,9567 с; это повторный анализ подготовленного проекта без того же полного CLI/report-write пути. Их нельзя выдавать за ускорение всего CLI до 55 секунд. Одной пары замеров недостаточно для устойчивого заявления о выигрыше; моих новых прогонов нет. [E11]

Найдена небольшая переносимая ошибка измерительного кода: `checks/repeat_prepared.py`, строка 43, записывает raw ru_maxrss как bytes, тогда как `portable.py`, строка 80, нормализует платформенные единицы. Сохранённые Darwin-значения корректны; Linux-ветка требует нормализации. Это задача измерительного harness, не объяснение слабой точности.

Приёмка следующей версии должна видеть одновременно:

- достигнутые source program points и законченные/незаконченные completion;
- typed values, root responses, producer→consumer ID и state changes;
- per-step E/C/R/D, required/forbidden edges и причины новых/удалённых рёбер;
- negative controls, где неверный ответ обязан быть отклонён;
- стоимость подготовки/расчёта/report/RSS/repeated analysis;
- отдельный website score на точном неизменном ZIP.

Порогов score, памяти и времени я не назначаю. Любой будущий численный норматив должен быть предложением для согласования. Небольшие fixture sizes и число повторов ниже — условия эксперимента, не обещание эффективности и не SLA.

## 8. Приоритетная очередь

**18 целей.** «Обязательная» означает: выполнить и проверить либо зафиксировать конкретную блокировку; «эксперимент» допускает обоснованный отрицательный результат. Необязательны расширения за пределами этих контрактов — parallel streams, произвольные collectors, глобальная новая IR, общий кеш всех методов, новые языки, модели и UI. Они не должны вытеснить закрытие найденных причин.

Полные карточки с файлами, MRE, положительными/отрицательными проверками, evidence, rollback и независимым продолжением находятся в готовом промпте ниже. Это уже заполненная очередь, а не предложение Codex составить её самостоятельно.

| Цель | Тип / приоритет | Зависимости | Проверяемый результат и основной критерий |
| --- | --- | --- | --- |
| G01 — новая версия, baseline, входы | Обязательная / P0 | — | Проектный skill применён; старые файлы защищены; точный №30 и команды/inputs зафиксированы; scope нового holdout заморожен до настройки |
| G02 — причинный разбор S6 | Обязательная / P0 | G01 | Union и step deltas воспроизведены; первый unknown-table effect/merge локализован или точно отмечен как unresolved; абляции разделяют типы, порядок, completion |
| G03 — неизвестный foreach | Обязательная / P0 | G01, материал G02 | Unknown rows больше не превращаются в доказанно пустой локальный агрегат; известный пустой List остаётся точным |
| G04 — Collection consumer contracts | Обязательная / P0 | G01 | Direct и local Map.get дают одинаковый результат removeAll/retainAll у List/Set; живой inventory removal проходит |
| G05 — безопасный Map proof и живой фильтр | Cast soundness / P0; bounded pilot / P1 | G03, G04 | Array→List не проходит proof; Basic242 действительно исполняется/суммируется с доказанными effects либо точно отказывается |
| G06 — порядок и продолжения | Измеряемый эксперимент / P1 | G02–G05 | Эквивалентные состояния сокращаются без потери return/throw/alias/effects; принятие только по парному результату и стоимости |
| G07 — cart positive gate | Обязательная / P0 в cart-ветке | G01 | Versioned typed per-step oracle/checker; старый failed trace остаётся failure; испорченные witnesses отклоняются |
| G08 — Stream.toList | Обязательная / P1 | G07; G03/G05-контроли | Корректная materialization, null/types/order/aliases/unmodifiable/lifecycle/effects; первый cart producer содержательно восстановлен либо следующая граница установлена |
| G09 — Optional и MVC отказы | Обязательная / P1 | G07; G08 не нужен для GET999 | Exact empty/present; 404 из source handler; request binder верен; repeat refusal проверяется после G12 |
| G10 — PATCH, transport, endpoint | Обязательная / P1 | G07, базовые HTTP-контроли | Source/config определяет factory и host+port; правильный PATCH/remote/state; no-send negatives |
| G11 — reduce и server response | Обязательная / P1 | G08 | Typed sequential fold, source subtotal и server mapper; Void клиента не скрывает серверное исполнение |
| G12 — вся корзина | Обязательная / P1 | G07–G11 | Explicit и NL связывают actual producer→refund→remote→reread; repeat/missing не меняют лишнее состояние; ambiguity не выбирает handler произвольно |
| G13 — вся цепочка TT | Обязательная / P1 | G02–G05; G06 выполнен или отклонён; актуальные value-контракты | Search→selection→booking/order→реальный UI payment без добавленного userId; незавершённость не выдаётся за empty/success |
| G14 — общие регрессии | Обязательная / P1 | Все принятые code stages | Piggy/Petclinic/inventory/document/actors/frontend/formatter/order и четыре отношения проверены с правильной областью oracle |
| G15 — новый замороженный transfer | Обязательная проверка границы / P2 | Freeze G01, G14 | Независимый исходный профиль до настройки; результат и первый loss честно сохранены; нет заявления о новом holdout после его подгонки |
| G16 — стоимость и переносимые units | Обязательная / P2 | Финальный кандидат | Сопоставимые phase timings/RSS/repeated analysis; исправлена единица ru_maxrss; optional optimization только при измеренной причине |
| G17 — сайт и восстановление лучшего | Обязательная при доступном сайте / P2 | G14, G16, готовый неизменный ZIP | Реальный verdict отдельно от S0; assessed bytes сохранены; восстановлен проверенный лучший №5 по действующим инструкциям |
| G18 — воспроизводимый результат | Обязательная / P0 как завершение | Все цели обработаны | Архив нового варианта, delta, inputs, witnesses, команды, ограничения и точный статус каждой цели; без дублирования всей истории |

Если TT-ветка блокируется на семантическом proof, следующий независимый переход — G07–G11. Если cart блокируется на ORM/типах после terminal, доступны G02–G06, контрольные наборы и измерительная часть. Не следует завершать всю работу после первого зелёного исправления.

## 9. Первичные внешние источники

Проверены **18.10.2026**, только публичные документация/API; приватные фрагменты проекта в поиск не отправлялись. Для этого follow-up не нужен новый каталог движков: установленные причины находятся в собственных контрактах выполнения.

| Код | Источник и роль |
| --- | --- |
| W1 | [Java SE 21 Stream.toList](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html#toList()) — terminal, order, unmodifiable result, implementation requirements |
| W2 | [Java SE 21 Collectors](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Collectors.html) — различия toList/toUnmodifiableList |
| W3 | [Java SE 21 stream package](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/package-summary.html) — laziness, ordering, interference, ограничения обещаний о callback effects |
| W4 | [Java SE 21 Optional](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html) — map, null-result→empty, orElseThrow |
| W5 | [Spring RestTemplate API](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/client/RestTemplate.html) — PATCH и зависимость от request factory; просмотренная current-страница обозначена 7.0.9, это не утверждение о resolved transitive version cart |
| W6 | [Spring MVC exception handling](https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-exceptionhandler.html) — specificity и различные виды advice arguments |
| W7 | [Java SE 21 List](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html) — read-only контейнер и изменяемость элементов |

Попытки получить ReferencePipeline из конкретного upstream JDK21u через веб-инструмент завершились ошибкой доступа. Точный контракт выше опирается на доступную Java 21 API, а не на непрочитанный файл или текущую ветку JDK master. При реализации нужно зафиксировать поддержанный JDK/Spring profile и не расширять его обещания на все версии.

## 10. Ограничения этого разбора

Подробные карты чтения: [evidence coverage](sandbox:/workspace/scratch/3c507d34b0c5/work_notes/review30_ev_coverage.json), [execution coverage](sandbox:/workspace/scratch/3c507d34b0c5/work_notes/review30_exec_coverage.json), [cart coverage](sandbox:/workspace/scratch/3c507d34b0c5/work_notes/review30_cart_coverage.json). Они различают полное чтение, выбранные функции/дельты, машинную обработку JSON и hash-only сверку; числа записей пересекаются и не должны суммироваться как уникальные файлы.

Не проверены заново все 19654 historical protected files, весь старый корпус тестов построчно, все startup/security/unused use cases корзины, все внешние зависимости и весь general NL grounder. Прочитаны relevant 19 production-file deltas №29→№30, новые тесты, ключевые пути и сохранённые witnesses; это scoped инженерная проверка, не формальная верификация ядра.

В доступном предыдущем TT-пакете нет двух файлов из recorded protected list: корневого файла переменных окружения target и `old-docs/Lib/myproject.zip`; точные пути и expected SHA указаны в E01/input report. Использованные Java/JS/сценарии/DB/skeleton совпадают. Если новая реализация требует отсутствующих конфигурационных значений, их нельзя домыслить; G01/G02 должны сохранить конкретный missing-input blocker.

Скрытых gold S1–S7 нет. Полного edge oracle корзины нет. Чтение чужого «passed» не объявляется новым прогоном. Новые MRE, абляции, full cart success, полная TT цепочка, устойчивое ускорение и новая независимая переносимость пока **не доказаны**. Готовая очередь ниже предназначена именно для получения этих доказательств.

## 11. Готовый промпт для автономной реализации

Следующий текст полностью совпадает с отдельным TXT-файлом. Он не требует доступа к внутренним рабочим запискам рецензентов: все существенные исходные факты, очередь, критерии и ограничения включены. Реальное выполнение зависит от доступных в Codex инструментов, среды и лимитов; текст не создаёт механизм фонового исполнения сам по себе.

```text
ЗАДАНИЕ CODEX: следующая версия после №30, вся очередь G01–G18

Дата программы: 18.10.2026.
Исходный пакет: solution_30_collection_value_flow_analysis.zip.
Сопроводительный разбор: solution_30_followup_review.md. Этот промпт самодостаточен; отсутствие внутренних рабочих записок рецензентов не блокирует выполнение.

ОБЩАЯ ЦЕЛЬ

Развить проверенный №30 до следующего варианта переносимого Python-анализатора. Исправить доказанные потери типов/коллекций/состояния, исследовать регрессию S6, пройти живой Map-фильтр, поддержать ограниченный Stream.toList и следующие реальные препятствия корзины, проверить полные многошаговые цепочки и регрессии, измерить стоимость, получить разрешённую оценку сайта и подготовить воспроизводимый аналитический архив.

Единица успеха — проверенная связь source/request/values/branches/effects/state/next request. Исчезновение warning, число тестов, корректный формат и отдельный успешный HTTP-пример сами по себе цель не закрывают.

РАЗРЕШЕНИЕ ПОЛЬЗОВАТЕЛЯ И НЕПРЕРЫВНОСТЬ РАБОТЫ

«Я разрешаю выполнять всю описанную очередь реализации последовательно и автономно. Планирую оставить тебя работать всю ночь. После завершения и проверки одной подцели сразу переходи к следующей, без ожидания сообщения “продолжай”.

Используй доступный механизм постоянной цели. Если одновременно поддерживается только одна активная Goal, создай общую цель, охватывающую всю очередь, а отдельные цели веди как подцели в сохраняемом плане. Не завершай общую цель после первого исправления.

После каждого этапа обновляй журнал: что изменено, чем проверено, где лежат результаты, что осталось и какая цель выполняется следующей. Сохраняй состояние работы так, чтобы после сокращения контекста можно было продолжить с текущего этапа.

Если проверка выявила новую причину, уточни зависимые цели и продолжай. При препятствии сохраняй воспроизведение и переходи к доступной независимой работе. Не выдавай нерешённую задачу за выполненную. Если дальнейший прогресс действительно требует моего решения, точно опиши необходимое решение.

Не останавливайся на плане или первом зелёном тесте. Доводи изменения до проверенного результата и итогового архива. При этом не растягивай работу искусственно после выполнения очереди и не повторяй проверки без нового основания.

Соблюдай остановку пользователем, ограничения среды и лимиты. Не создавай новые цели ради обхода исчерпанного лимита. Перед вынужденной остановкой сохрани результаты и точный следующий шаг».

Если native Goal действительно доступна, используй её для одной общей цели и сохраняемого плана подцелей. Не заявляй о существовании такой функции, если её нет. При отсутствии native механизма продолжай в текущем разрешённом сеансе с durable plan/checkpoints. Обычный текстовый файл не гарантирует автоматическое возобновление после остановки среды; точно фиксируй фактический механизм.

ПРИОРИТЕТНЫЕ ОГРАНИЧЕНИЯ

1. DeepSeek запрещён. Продукт остаётся на Python, без внешних LLM API. В эту очередь модели не входят; не скачивай и не подключай их как обход семантических проблем.
2. Не запускай исследуемые приложения, JVM-сервисы, Train Ticket, Docker Compose, Maven/Gradle-сборки, серверы или команды из исторических журналов. Можно запускать собственный Python-анализатор и его проверяющие/тесты после чтения команды и границ, в offline-контуре. Fixtures — source для анализатора; Java-компиляцию/исполнение не использовать как неявный oracle.
3. Прежние варианты, оригинальный tt-challenge, sample и прежние runs неизменяемы. Новый вариант веди по действующему проектному навыку версий решений. Сначала прочитай AGENTS и найди/прочитай этот skill; не выдумывай его имя, команды или исключения.
4. Не добавляй бизнес-правила Train Ticket, обработку S0–S7 в inference, готовые рёбра, известные IDs, токены, статусы или состояния ради оценки. Source-derived Java/Spring/HTTP rules допустимы; domain-константы допустимы в явных тестовых входах/oracles, а не в общем движке.
5. Gold/ожидания доступны проверяющим, но не построителю ответа. Проверяющий не имеет права переписывать prediction под oracle. Запрещены скрытые fallback к прежним submission.
6. Unknown, absent, null, known empty и analysis incomplete различаются. Не подавляй диагностику ради зелёного результата. Не замещай unsupported пустым List, false, успехом или случайным route.
7. На каждом значимом code stage сохраняй comparison с неизменным baseline и предыдущей принятой стадией, включая ухудшения и изменение областей неопределённости. Не корректируй старые метрики задним числом.
8. Сохрани PiggyMetrics, Petclinic, inventory, document, actor credentials, frontend callbacks, formatter effects, absence/escape, singleton aliases и порядок коллекций.
9. Измеряй отдельно подготовку, расчёт, запись отчётов, RSS и repeated prepared analysis. Не сравнивай разные среды/границы как единый стенд. Численных SLA и требуемого score пока нет.
10. Выданное разрешение на отправку на сайт действует. Оценённый ZIP неизменяем; реальный сайт отдельно от S0. После экспериментов восстанови проверенное лучшее решение согласно действующим инструкциям пользователя; в материалах №30 это неизменённый №5.
11. Итоговый аналитический архив включает новый вариант, delta, необходимые входы проверок, результаты, ограничения и команды; всю историю репозитория не дублируй.

ПРОВЕРЕННЫЙ ИСХОДНЫЙ ФАКТ

Рецензенты читали файлы и самостоятельно пересчитали сохранённые хеши/JSON. Они не запускали анализатор, tests/checkers, JVM или сервисы. Новые MRE ниже ещё не прогонялись. Не записывай их как уже выполненные.

№30 current submission SHA-256:
1a5f48620fb8e840f17903b78bfff037cf88191f888a452dc609f6970789731a
Оценённый solution.zip:
1490f076524239980ad0a5211cce97c86135b20efe65fc895dc523afa0d5e8be
Parent №29 submission:
1f634b961b983d1ef5bfb63d06d8f5b2fb6542c2ef321d36146f920554dd5353

Сохранённый сайт №30: 1665671, A, 0.37269; parent0.36114.
S6: 0.44672740→0.43871457, delta−0.00801283.
S0 неизменен 0.8008928571428572, remote пуст с обеих сторон.

12 стадий: base; C1-scalar-hashset; C2-noop-map-filter; отдельная ветка base→S1-angular-legacy→S2-actor-credentials; C1-C2-S1-S2; F-formatter-effects; failed E-effects-and-order-boundaries; E2-effects-and-order-boundaries; G-final; H-source-proven-read-effects; fair-base.
E аварийная, без submission. Финальный H побайтно равен C2. S1/S2 меняют важные witnesses и сохраняют union своей base-ветки 1596; включение этих изменений в C2 и последующий F сохраняют ответ C2 с 1645 рёбрами. F→E2 теряет 50 рёбер; G→H возвращает их.

S6 union: E119/C101/R18/D16→E116/C98/R18/D16, добавлений 0.
Удалены ровно 6:
- executes JsonUtils.conveterObject(Object,Class);
- executes JsonUtils.object2Json(Object);
- executes JsonUtils.json2Object(String,Class);
- BasicServiceImpl.queryTrainTypeByNames(List,HttpHeaders) calls JsonUtils.conveterObject;
- conveterObject calls object2Json;
- conveterObject calls json2Object.
Первое исчезновение base→C1, только из шага 8. В baseline они есть в alternatives4,5,6,7,12,13,14,15, все budget.
На уровне шагов final также теряет 12 рёбер admin-login шага 1 (8E/2C/2D), но все 12 остаются в passenger-login шага 7, alternatives0,1. Итог per-step0 добавлений/18 удалений, union0/6. Не путай эти два уровня и не сопоставляй пути по их порядковым индексам.

Перед S6 search таблицы уже неизвестны: station впервые на части исходов шага 2, train_type на шаге 3; после шага 7 обе returned-альтернативы имеют unknown station/train_type/route/route_distances/route_stations/price_config. Точный первичный effect→join ещё не установлен.

Подтверждён inherited дефект: opaque repository List в StationServiceImpl.queryForIdBatch/цикл 107 пропускается Engine.execute1332 с normal completion и без расширения локального stationMap; далее для всех имён получается известный null. Unknown rows не доказывают no rows.

Подтверждён узкий contract gap: Map<K,V>.get сам выводит V (engine.source_type2162), но source_conversions.argument_type90–105 знает addAll(Collection) и не знает removeAll/retainAll. Известный Map.get operand стирается native_read_cast1027 из-за unresolved consumer. На S6 это Basic194/197 и Set; на inventory — List. All-present inventory обходит вызов посредством no-op proof, а текущий missing-category test107–114 ожидает U.

C1 добавляет unspecified order и при переполнении обычного выбора использует CompletionRequired; java_sets.next_index18 и paths.run_paths расходуют общий completion reserve с return/throw. Отдельная причинная абляция пока не выполнена. Не возвращай 6 рёбер вручную.

У известного отдельного search/S1 другая первая граница: C2 действительно доказывает Basic219 по 3 false guards; Basic242 имеет 6groups, path_limit4. Во всех 8 final S1/step2 alternatives нет условия тела 244–255: widening начинается до первого элемента. Затем avaTrips.size unknown и source-ветка может вернуть внешний status1/data[]. Это возможный результат после абстрактного расширения, не доказанный пустой поиск.

Новый cart:
validation_inputs/shopping-cart; Java21, Boot4.0.6; заявленный source commit64273c71575d61db8de6ba1a582b02f6a11103b3.
Первый GET payments?orderId=11 читает repository с[11], затем PaymentPersistenceAdapter65 toList возвращаетU без mapper. Explicit шаги 2–5 пропущены из-за producer ID; NL продолжает сU.
Независимый GET999 теряет absence на Optional.map(adapter48), даёт два 200/nullDTO и дваexception/U.
Далее source требует MVC specificity/servlet arguments, patchForObject, host+port mapping и reduce; это статически предстоящие границы.
Apache factory в ApplicationConfig34 доказана; не приписывай этому cart SimpleClient/URLConnection.
OrderClient URL default localhost:8083; order server.port8083; current request_address теряетport, host/module substring не разрешает deployment.
Order.total141 использует map(subtotal).reduce(BigDecimal.ZERO,BigDecimal::add); сервер строит response даже при client Void.class.
Cart checker main13–47 намеренно hardcodes failure/firstloss; его нужно версионировать до заявления успеха. Required edges subset:13calls/4data/1remote/0executes, неfullIoU.
Scope cart — прикладное выполнение после аутентификации. Нынешний runner не доказывает полный security HTTP path. Не выдумывай токен и не отключай security всего продукта.
Oracle обязательного физического UPDATE неизменённых order_details слишком силён; source подтверждает cascade/aggregate, а не конкретный dirty-check SQL.

ОРГАНИЗАЦИЯ РАБОТЫ

В новой версии заведи:
- development/overnight-plan.md — вся очередь и текущие зависимости;
- development/overnight-state.json — durable machine-readable checkpoint;
- development/overnight-log.md — изменения, проверки, выводы и следующие действия;
- development/checkpoints/ — immutable code manifests/diffs после meaningful stages;
- benchmark/overnight/Gxx/<stage>/ — уникальные неперезаписываемые результаты;
- checks/ — новые проверяющие, сравнения и минимальные inputs;
- FINAL_REVIEW.md, REPRODUCE.md, LIMITATIONS.md — итог.

Это предлагаемые новые пути внутри NEXT_SOLUTION, не предписание менять старые имена/файлы. Соблюдай проектный skill, если он задаёт другой корректный layout; запиши отображение путей.

Каждая запись checkpoint содержит goal_id, status, evidence_paths, code/input hashes, commands, actual exit status, what_changed, tests_run, tests_not_run, findings, unresolved, rollback, next_goal. Для времён фиксируй среду и границы. Не записывай declared passed без результатов.

Статусы: pending, in_progress, verified, experiment_rejected, blocked_with_reproducer, not_run. Для обязательного исправления blocked не равно verified. После изменения его зависимости пересмотри только затронутые результаты. При compaction сначала прочитай checkpoint/plan, сверяй рабочие файлы и продолжай, не начинай baseline заново.

Выбирай следующую доступную цель в указанной очереди. G06 допускает отрицательный эксперимент; не увлекайся полной переписью scheduler. При TT-blocker продолжай G07–G11; при cart-blocker продолжай TT, независимые controls, measurements. Не запускай несовместимые mutation/measurement этапы параллельно в одной копии. Делегирование независимых read/review допустимо.

ОЧЕРЕДЬ: 18 КОНКРЕТНЫХ ЦЕЛЕЙ

G01. Новая версия, неизменный baseline, входы и правила измерения
Тип: обязательная/P0. Зависимости: нет. Стоимость: малая–средняя, инфраструктура и сверка.
Результат: правильно созданная по project skill следующая версия, известные входы и воспроизводимый parent30 без изменения originals.
Файлы: START_HERE.md, MANIFEST.json, solution_30/IMPLEMENTATION_REVIEW.md, development/requirements.json, benchmark/final, benchmark/site-score.json; code/offline_run.py; checks/stage_benchmark.py, check_integrity.py, repeat_prepared.py, replay_archive.py; проектные AGENTS/skill.
Порядок:
1) Найди фактический ROOT/tt-challenge/solution30 и skill, прочитай команды и imports перед запуском. Не используй исторический /Users/... path.
2) Создай NEXT_SOLUTION по skill, сохрани baseline manifest защищённых файлов и pre-existing work. Не переключай/не очищай чужие изменения.
3) Сверь code/submission30 и historical ZIP; docs после оценки учитывай отдельно. Проверь TT inputs against recorded SHA, в том числе skeleton = 765f38d8b528268d38be5154fd2f512cf383809df814bc3c5bdb5d9bf1a1faba, DB = a93888a0143b86f9322f60e9201a1a47fa396ba86e3de5a1d914842d51bb5423, S6 737b33185f7f9c46109c9bce1fc8c143b4adbd27cea78519cc13e651d44d054d.
4) Выполни один разрешённый offline baseline30 в новом output, сравни exactsubmission и semantic witnesses, зафиксируй environment. Если различается, сначала сохрани repro и устрани причину сравнимости.
5) До настройки под новый transfer сохрани scope/inputs/oracle выбранного независимого приложения: реальные Java/Spring исходники, готовый skeleton, DB, multi-step HTTP journey, непустые remote/data, отказы и ambiguity. Если такого неиспользованного пакета нет, запиши точный missing-input для G15 и продолжай; не выдавай новый synthetic пример за независимое приложение.
MRE/checks: изменение одного байта копии input должно отвергаться manifest gate; baseline30 в двух разных новых output не должен читать старый submission. Negative offline guard — разрешённый тест запрета reference/network/process.
Приёмка: inputs/code hashes совпали либо каждое отличие объяснено и сравнение переосновано; старые paths неизменны; baseline commands и значения доступны; один общий Goal/plan содержит все 18 целей.
Evidence: G01 manifest, environment, commands/stdout/stderr/exit, exactdiff/semanticdiff, protected-before, scope/freeze G15.
Откат: ошибка layout или защищённых paths — не продолжай mutations; исправь только новую копию. Отсутствующий обязательный skill/TTinput — конкретный blocker, без подделки.
Далее: G02. Независимо при blocker: read-only разбор S6 и спецификация G07/контрпримеров в разрешённых рабочих заметках; не выдавать это за новую реализованную версию.

G02. Причинный ledger S6 и разделение трёх факторов
Тип: обязательная/P0, исследование с проверяемым результатом. Зависимости: G01. Стоимость: средняя.
Результат: точное происхождение S6 regression и воспроизводимые независимые cases; отсутствие скрытого gold остаётся явным.
Файлы: benchmark/stages/{base,C1-scalar-hashset,C2-noop-map-filter,S1-angular-legacy,S2-actor-credentials,H-source-proven-read-effects}; benchmark/comparisons; checks/run_tt_causal_probes.py; analyzer/paths.py::run_paths, engine.py::choose/fork_join/execute/fallback, java_sets.py::next_index, state/resource_effects/repository_values; TT Station.queryForIdBatch, Basic.queryForTravels/queryTrainTypeByNames.
Порядок:
1) Пересчитай E/C/R/D final-vsbase на union и каждом из 14 шагов; сохрани все 6 и 12tuples, retention step7, exact request/actual args/state/event pointers.
2) Сопоставляй paths по смыслу input/constraints/trace, не по alternative index; warnings сортируются и не являются хронологией.
3) Найди самый ранний effect/операцию/merge, сделавший station unknown на step2, train_type на step3; проследи до input search. Раздели законную неизвестность пользовательских данных и необоснованное расширение read-only состояния.
4) Подготовь маленькие paired copies без изменения originals: known DB vs opaque DB; correct C1 membership с имеющимся vs исправленным consumer contract; коммутативный unordered loop vs order-dependent callback. В G02 подготовь pair/harness; вторую половину с исправленным consumer выполни после G04 и обнови ledger. Для диагностической проверки разрешается локально разнести счётчики order-choice и completion, не принимать одно увеличение лимита как fix.
5) Сохрани прежний parent с ошибочным HashSet только как исторический comparator. Не возвращай его семантику в продукт.
MRE+: native unordered коллекция→коммутативный Map→неизвестное условие return/throw; конкретный read сохраняет таблицу. MRE−: callback пишет общий counter/DB или бросает; unknown input остаётся unknown.
Приёмка: первый divergence адресуем; вклад каждого выполненного сравнения отделён; если первичная причина не установлена, есть точный input/reproducer и ещё не выполненный эксперимент. Ни одна из 6 дуг не добавлена по S6/ID. Скрытая правильность каждой дуги не объявлена.
Evidence: G02/causal-ledger.json+md, full deltas, source snippets+locations, input hashes, completed/boundary/throw outcomes, budget categories, measured/unmeasured hypotheses.
Откат: instrumentation меняет baseline semantics без объяснения — убрать из продуктовой ветки, сохранить эксперимент. Не откатывать правильную уникальность HashSet ради score.
Далее: G03/G04. Независимо при blocker: G07–G11; ledger остаётся blocked_with_reproducer, общая цель продолжается.

G03. Unknown foreach не должен порождать известную пустоту
Тип: обязательная/P0. Зависимости: G01; используй факты G02. Стоимость: средняя, execution/effects.
Результат: opaque nonnull collection сохраняет неизвестный эффект локального обхода или явно останавливает анализ; известный empty остаётся точным.
Файлы/функции: analyzer/repository_values.py::unknown_result; engine.py::execute enhanced_for (около 1332), fallback (около 796), view_items/widen_map_iteration; heap_join.py; новые tests/test_unknown_collection_iteration.py и source fixtures.
Порядок: сначала воспроизведи unknown List→local Map; затем введи корректную boundary либо bounded footprint локальных writes. Поддержку точного эффекта добавляй только по AST/alias/normal-throw proof. Не делай все DB таблицы unknown и не исполняй неизвестное число итераций один раз сU как будто это полный результат.
MRE: Map names=new HashMap(); for(Row r:repository.findAll()) names.put(r.id,r.name); return names.get("A")==null. Для abstract unknown rows нельзя известноеtrue. Positive counterparts: известный[], известный[A], known list с двумя элементами.
Отрицательные: запись в alias Map/bean/DB, return/break/continue/throw из тела, пустой физический carrier с opaque=True, неизвестная membership при известной кардинальности, shared alias в следующем запросе.
Приёмка: отсутствует ложный concrete result после пропущенного эффекта; известные случаи сохраняют значения и source edges; неполнота и возможные effects объяснены, abnormal completion не теряется. В S6 цикл 107 функции StationServiceImpl.queryForIdBatch больше не создаёт доказанное отсутствие станций из unknown rows.
Evidence: before/after MRE traces, affected roots, source-proven effect or boundary, TT step2/3/8 comparison, existing singleton/order controls.
Откат: если footprint забывает alias/effect или выдаёт normal result без основания, оставь честную boundary и убери неподтверждённую точность. Более ранняя остановка фиксируется как precision cost, а не скрывается.
Далее: G04. Независимый fallback: G07/G09, подготовка G08; G06 не маскирует этот semantic bug увеличением budget.

G04. Standard Collection arguments для removeAll/retainAll
Тип: обязательная/P0. Зависимости: G01. Стоимость: малая–средняя.
Результат: известный Map.get сохраняется в bulk consumer; direct call эквивалентен варианту с typed local variable для List и Set.
Файлы: source_conversions.py::argument_type/consumer_type; engine.py::source_type/native_read_cast/reference_check; java_lists.py::call; java_sets.py::call; test_inventory_collection_journey.py, test_hashset_membership.py; новый consumer regression.
Порядок: разрешить source overload прежде standard model; добавить точный erased Collection<?> argument contract по доказанному receiver/методу/arity. Не выводить тип из Python payload и не добавлять правило только по имени. Проверить Map.get alias/kinds до и после native_read_cast, затем сделать missing-category inventory положительным live-removal тестом.
MRE+: groups["obsolete"]=[B], out=[A,B,C]; out.removeAll(groups.get("obsolete")) →true,[A,C]; local List g=groups.get(...) должен дать то же. retainAll→true,[B]. Для Set проверяй membership/changed, а не произвольный order. out.removeAll(out)→empty; out.retainAll(out)→false/unchanged.
MRE−: null operand→нужное исключение; unknown operand→явная граница; String[] вместо Collection, polluted raw Map, custom override/equals/hash, unmodifiable/fixed-size collection, wrong arity.
Приёмка: direct/local совпадают по result/types/aliases/effects/throws; inventory missing office возвращает нужные оставшиеся продукты по исходникам, а истинно unknown case остаётся negative; S6 Basic194/197 не теряет operand по причине отсутствия consumer type.
Evidence: paired traces, kind/declared-type witness, новая версия правильного inventory expectation и отдельные negatives, S6/full103 delta относительно 30.
Откат: общее name-only dispatch, незаконный array cast, пропущенный callback или ложная known membership — откатить descriptor/dispatch patch, сохранив tests и диагностику.
Далее: G05. Независимо при blocker: G07–G11.

G05. Надёжность no-op proof и ограниченный живой Map-фильтр
Тип: обязательная проверка soundness/P0; bounded live-effect pilot/P1. Зависимости: G03,G04. Стоимость: средняя–высокая; два последовательных checkpoints.
Результат: no-op proof не обходит Java cast/throw; затем source-generic живой фильтр действительно исполняется/суммируется, либо даёт точную границу.
Файлы: map_loop_proof.py::prove/fits31; engine.py::reference_check979, execute enhanced_for, view_items, collection membership/callbacks; native_arrays.py::JavaArray; native_storage/heap_join/map_views; test_map_noop_filter.py.
Порядок A: выдели/используй чистый predicate reference compatibility, согласованный с ordinary reference_check. Unknown compatibility отклоняет proof; JavaArray не List; Set является Collection, но не List. Guard evaluator не должен побочно изменять heap.
MRE A−: raw Map содержит String[], присвоен Map<String,List<String>>, loop local List xs=e.getValue(); if(xs==null)touch(). Обычное исполнение требует ClassCastException; proof-on не может дать normal-only. A+: настоящий List, null reference, допустимая Collection, пустой Map; proof-on/off совпадают по семантическим outcomes, heap/aliases, source E/C/R/D и наблюдаемым effects. Служебный trace/число эквивалентных alternatives могут отличаться; новый proof event не является source edge.
Порядок B: новый общий эффект для per-entry фильтра по известным native данным. Read set, written roots, aliases, null/type checks, callbacks и completions должны быть доказаны. Можно исполнить source getters/тело и суммировать коммутативные удаления; нельзя выбросить source executes/calls или назвать getter чистым по префиксу.
MRE B+: независимая выдача оборудования: Map групп содержит разрешённые позиции; subset удаляется из отдельного Set на основе известного списка допустимых переходов. Все-present/no-removal и live-removal cases; перестановка entry order не меняет конечную membership. B−: тело меняет shared counter/Map traversal source, order-dependent callback, read/write DB, custom equality, throw после части removals, aliases пересекаются.
Приёмка: A soundness gate обязателен; B принимается только с proof obligations и paired slow reference interpreter на малом поддержанном source. На TT фиксируй вход в тело Basic242/условия 244–255, avaTrips и следующий frontier. Нельзя закрыть B лишь потому, что исчез warning или тело объявлено no-op.
Evidence: proof certificate с исходными AST locations/reads/writes/aliases/normal-throw, proof-on/off traces; Basic219 остаётся корректным; Basic242 before/after source events.
Откат: любое несовпадение семантики — отвергни только соответствующую оптимизацию; оставь обычное исполнение/явную boundary и исправление cast. Честный отказ B не отменяет A.
Далее: G06. Независимый fallback: G07–G11; failure B сохраняется как bounded pilot rejection.

G06. Пилот эквивалентных состояний и стоимости продолжений
Тип: исследовательский эксперимент/P1, отрицательный результат допустим. Зависимости: G02–G05. Стоимость: высокая относительно локальных patches; не превращать в обязательную полную перепись.
Результат: измерить, можно ли убрать повторение семантически эквивалентных порядков без потери путей и alias/effect semantics.
Файлы: paths.py::run_paths/join_states; engine.py::choose/fork_join; java_sets.py::next_index; map_views.py::iterator_next; heap_join.py; state.py; новый isolated comparison harness.
Порядок: сперва instrumentation unique/repeated states, order choices, completion kinds, time spent replay. Затем один opt-in prototype слияния остаточных состояний в одном program point. В ключ входят remaining elements, relevant env/heap identity+aliases, typed values, read resource versions, browser/actor/session, clock/config assumptions, path constraints и pending completion. Учитывай также релевантные bean roots, active transaction, pending writes/managed entities и request/event/provenance context; вместо полного state допустима доказанная релевантная проекция. Не включай все методы в общий кеш без доказанной summary/invalidation.
MRE+: коммутативный фильтр из G05 при нескольких порядках; одинаковые состояния сходятся. MRE−: те же values при разных aliases/receiver identity, другой actor/DB revision, возвращаемое значение одинаково, но effects/throw отличаются; callback увеличивает counter.
Приёмка: для полностью перебираемого малого случая result/state/effects/normal-throw и полный E/C/R/D, включая отсутствие лишних рёбер, эквивалентны reference без оптимизации; сохранены provenance каждого существенного исхода. Затем paired TT/S6 frontier и phase cost. Если сокращения повторного replay или содержательного продвижения нет, эксперимент отклоняется.
Мемоизацию добавляй лишь после корректного узкого summary; worklist оправдан только если данные показывают существенную стоимость restart. Простое разнесение/увеличение бюджетов — диагностическая абляция, не самостоятельный semantic fix.
Evidence: prototype flags/defaults, before/after unique/repeat counts, residual-state signatures, semanticdiff, time/RSS и regression results.
Откат: потеря эффектов/исключения/alias либо необъяснённое ухудшение — удалить/отключить prototype в final; baseline engine остаётся рабочим. Не упрощай ключ ради прохождения speed test.
Далее: G07. Независимо при blocker: G07–G11 немедленно; не задерживай всю очередь бесконечной оптимизацией.

G07. Положительный cart checker и явная граница после аутентификации
Тип: обязательная/P0 в cart-ветке. Зависимости: G01. Стоимость: средняя, проверяющий и runner.
Результат: новая версия evaluator может принять правильную цепочку и отвергнуть содержательно неправильную; старый failed-transfer остаётся неизменным отрицательным примером.
Файлы: checks/check_cart_profile.py::main/subset, checks/run_cart_profile.py::main; validation_inputs/shopping-cart/oracle-v1.json, source-scope/freeze и profile context; checks/evidence.py; analyzer/engine.py::http_invoke401–476 и HTTP response witness. Меняй только новую версию этих файлов.
Порядок:
1) Сохрани oracle-v1 и исходную failed-запись; создай versioned oracle/checker с объяснённой delta. Старые passed=False и assert unsupported-toList нельзя оставить положительным gate.
2) Проверь ровно восемь шагов, уникальные номера, соответствие actual request/root response, typed values и обязательные/запрещённые effects по каждому шагу. Для строк нужен взаимно однозначный matching по ключам, а не многократное совпадение одного actual объекта с несколькими expected.
3) Проверь explicit и NL отдельно: actual producer IDs, state before/after, error code+status, отсутствие произвольного выбора handler и мутаций при ambiguity. Не складывай remote разных шагов для удовлетворения требования refund.
4) В runner и свидетельстве явно обозначь прикладной entry boundary после аутентификации. Это объявленное ограничение профиля, а не успешное прохождение JWT/security. Не вставляй токен, не отключай security всех проектов и не моделируй вход без headers как authenticated HTTP.
5) Раздели финальные rows/children и доказанные datastore effects. Не требуй физического UPDATE неизменённых order_details лишь из cascade/save; уточни это требование oracle по исходникам и заранее объявленному ORM/provider-контракту, независимо от prediction и возможностей текущего анализатора.
MRE+: отдельно написанный checker fixture с правильными восемью шагами, связанными IDs, refund/revert/reread/409/404 и неизменными посторонними строками. Это тест checker, не результат анализатора и не вход построителя ответа.
MRE−: исходный failed trace30; пропущенный/дублированный шаг; remote на другом шаге; другой payment ID; 200 вместо 409; потерянный error_code; true вместо 1; перестановка root/remote responses; изменение чужой строки; save после отказа; два реально выполненных mutating handlers при ambiguity; один произвольно выбранный read-only handler без изменения state; потеря producer provenance.
Приёмка: положительный fixture принят, каждый существенный negative отвергнут с понятной причиной; реальный trace пока получает честный статус. Измеряется только покрытие объявленного required subset, не recall полного графа; full precision/IoU не выводятся. Для executes, которого нет в v1, добавь проверяемые source-derived обязанности нужных шагов, не называя это полным gold.
Evidence: oracle/checker version+SHA, reviewed scope, mutation results, failed30 replay, явная post-auth boundary, схема typed state/effects/provenance.
Откат: evaluator подгоняется к неизвестному/неполному ответу или снимает обязательную проверку ради pass — откатить такое ослабление; сохранить уточнение недоказанного ORM write отдельно и с обоснованием.
Далее: G08. Независимо при blocker: G09 GET999, G10 transport MRE или G02–G06; не ждать готовности всей цепочки для исправления независимого слоя.

G08. Stream.toList с реальным контрактом materialization
Тип: обязательная/P1. Зависимости: G07 для cart gate; используй G03/G05 soundness-контроли. Стоимость: средняя–высокая, ограниченная стандартная библиотека.
Результат: поддержанный последовательный materializing pipeline сохраняет значения, типы, null, aliases, порядок/неизвестность порядка, callbacks и неизменяемость результата. Первый cart producer восстановлен либо следующий конкретный frontier сохранён.
Файлы: analyzer/engine.py::stream_call (около 3318–3383), source_type, repository; models.py::wire/library; native_storage.py::JavaList/ReadOnlyList; java_lists.py; call_effects.py; state.py/heap_join.py; persistence.py; tests/test_java_streams.py и test_stream_parameter_types.py. Source: PaymentPersistenceAdapter.findByOrderId61–65, PaymentPersistenceMapper.toDomain, Payment.reconstitute, PaymentController.
Основание: Java21 Stream.toList API — encounter order, если определён, unmodifiable container, null не исключён default implementation, value-based identity возможна. Collectors.toList не гарантирует mutability; toUnmodifiableList отвергает null. Первичные ссылки приведены в конце промпта; не подменяй один контракт другим.
Порядок:
1) Верифицируй receiver/namespace/arity, текущий lazy pipeline и типы каждого map/filter. Общий terminal helper допустим лишь с отдельными result contracts.
2) Проверь opaque/source state ДО обхода, включая уже созданный stream над carrier, который позднее стал unknown. Known empty и физический len0 при opaque различаются.
3) Материализуй новое хранилище с element aliases и type metadata. ReadOnlyList над новым backing пригоден после проверки; view над source не подходит. Не делай вывод о неравенстве двух Java objects только по новой внутренней аллокации: toList API не гарантирует такую identity. Alias одного результата остаётся тем же объектом.
4) Пропагируй order provenance от List/Set/repository. SQL без ORDER BY не получает INSERT order. Для unordered pure per-element mapping допустим только доказанный order-invariant результат либо явные alternatives/boundary; side-effecting/order-dependent callbacks требуют отдельного анализа.
5) Проверь callbacks, normal/throw, linked/consumed aliases и mutations результата, включая пустой clear, iterator и views. На wire boundary новый JSON container не обязан наследовать Java unmodifiable marker; в HTTP JSON передаются значения и структура по wire contract. Unmodifiable/type/alias metadata остаются в semantic witness, не добавляются в payload; remote DTO не наследует Java heap identity исходных объектов.
MRE+: [a,null,a]→toList с сохранением multiplicity/alias/null; типы Boolean/Integer/Long не сливаются по Python equality; mapper конструирует DTO по source; filter известен; known empty; source меняется после materialization — результат не становится view. Cart GET orderId11: source mapper действительно проходит, видны обе платежные записи с правильными полями.
MRE−: add/set/remove/clear/bulk/iterator mutations; callback throws после одного эффекта; reused stream; custom Stream/toList с тем же именем; null/unknown callback; HashSet→get(0); repository без ORDER BY→first; source interference; opaque empty carrier. Для последнего сначала воспроизведи существующий collect: Stream s=xs.stream(); Extension.touch(xs); s.collect(Collectors.toList()); затем такой же negative для нового toList.
Приёмка: normal results полностью обоснованы; throws не превращаются в list; эффекты и source calls/executes не исчезают; state copy/join сохраняет ограничения. Кардинальность известна только при доказанной membership. Не обещай все Stream/parallel/count/short-circuit и произвольную callback execution policy.
Evidence: contract matrix и versioned tests, source/terminal type+alias+order traces, opaque reproduction, cart step1 before/after, следующий first-loss с input hash. Исчезновение toList warning без пригодного producer не закрывает весь профиль.
Откат: ложная пустота/порядок/mutability/type, пропущенные effects или illegal source cast — откатить точную ветвь модели к явной boundary; не возвращать mutable collect как универсальный alias toList.
Далее: G09, затем G10/G11. Независимо при blocker: GET999 Optional/MVC, PATCH MRE, измерительная нормализация G16.

G09. Optional и правильные HTTP-отказы MVC
Тип: обязательная/P1, два последовательных checkpoints. Зависимости: G07; GET999 не зависит от успешного G08. Стоимость: средняя.
Результат: empty/present/unknown Optional сохраняются через map; конкретный domain throw связывается с правильным source handler и HTTP request. Внешний 404/409 не возникает из guessed status.
Файлы: models.py::optional_value/library (около 374); engine.py::source_type, library dispatch Optional3036–3083 и request/advice binding около 465; http_contracts.py::exception_handler; cart PaymentPersistenceAdapter.findById46–49, GlobalExceptionHandler53–58/113–118/209–215; Payment.refund; OrderPersistenceAdapter.findById.
Порядок A: реализуй ограниченный Optional.map с source callback invocation и типом результата: empty не вызывает mapper, present вызывает, mapper returning null даёт empty, exception сохраняется. Ссылка на mapping function проверяется независимо от presence: Optional.empty().map(null) тоже требует NullPointerException; unknown не превращается в empty/present. Проверить of/ofNullable/orElseThrow совместно с существующими операциями.
Порядок B: разрешай наиболее специфичный доказанный handler по type hierarchy в поддержанной области controller/advice. Root/cause, несколько advice и их ordering не своди к первому по порядку файла; поддержи явно или оставь boundary. Bind исключение, HttpServletRequest/Response и прочие поддержанные параметры отдельно. Не передавай failure.value каждому параметру.
MRE+: empty.map(callbackWithWrite) не пишет; present.map идёт в source, null-mapper-result→empty; GET payment999→исходный PaymentNotFoundException→404/PAYMENT_NOT_FOUND и корректный request URI; наличие специфичного и общего Exception handler выбирает специфичный. Повтор refund после G12→409/PAYMENT_ALREADY_PROCESSED до save/remote.
MRE−: unknown Optional; mapper null reference; mapper throws после эффекта; unrelated exception; две неразрешимые advice; handler сам throws; request-параметр ошибочно заполнен exception; отсутствие ID не выдаёт 200 с DTO(null).
Приёмка: на самостоятельном GET999 при чистом контексте больше нет normal 200/nullDTO; реально сохранены source throw→handler→root status/error body. Поддержанный present путь сохраняет values/types/aliases; unsupported advice cases диагностируются. Повторный отказ окончательно принимается только на перенесённом состоянии G12.
Evidence: A/B отдельные stages, exception type hierarchy/binding traces, status/error/URI и absence of writes, cart explicit/NL step6, старые Spring error controls.
Откат: выбирается handler по name/order без proof, exception поглощается или unknown превращается в absence — убрать спорное правило, сохранив точную поддержанную часть и негативные tests.
Далее: G10/G11. Независимо при blocker: G08, endpoint binding и TT value-flow; блокировка одного advice не отменяет Optional checkpoint.

G10. PATCH по source/config с правильной стороной сервера
Тип: обязательная/P1. Зависимости: G07 и базовые HTTP-контроли; G09 нужен для части ошибок полной цепочки. Стоимость: средняя–высокая.
Результат: доказанный PATCH RestTemplate связывается с нужным сервером и выполняет его source; неизвестный transport/endpoint не превращается в успешный remote.
Файлы: engine.py::library dispatch RestTemplate2697–2704/2729–2731/2788 и HTTP method handling3469–3471; request_url.py::request_address; baseline_closure.py::Index.handlers_for; http_contracts.py; source/config extraction. Cart: payment ApplicationConfig34–36/47–49, application.properties23, pom.xml httpclient5; OrderClientAdapter70–71; order application.properties2, OrderController.revertPayment121–123, RevertOrderToPendingUseCase.execute35–40.
Порядок:
1) Добавь точный descriptor patchForObject: URL, body, response class token, URI variables, return/error semantics. Используй общий HTTP pipeline, не прямой вызов cart handler. Сохраняй request method/body/headers/response в witness.
2) Из constructor/bean wiring установи HttpComponentsClientHttpRequestFactory и применимый контракт PATCH. У cart source это доказано; для произвольного клиента factory может быть иной. Не считай метод API достаточным доказательством фактической отправки.
3) Сохраняй scheme/host/port/path и provenance разрешённых placeholders/profile/env. Исправь потерю port в request_address и host-module substring heuristic. Сопоставление localhost:8083 с source server.port допустимо при известных deployment assumptions; одних совпавших путей недостаточно.
4) Выполни серверный handler/application/persistence и формирование response; Void.class означает отсутствие client payload, но не разрешает пропустить server mapper, side effects или exception. Обработай source HTTP error path отдельно.
MRE+: два небольших сервиса с одинаковым path и разными ports; клиент с доказанной Apache factory PATCH-ит только нужный. Body=null, responseType=Void, server меняет одну запись и формирует ответ; наблюдаются remote и source executes/calls/data.
MRE−: неизвестный/конфликтующий env endpoint; неоднозначное deployment mapping; другой port; неподходящий либо неизвестный request factory; custom patchForObject; URI variable не разрешена; server404/500; отказ до send. Не добавляй remote/server effects для доказанно неотправленного запроса; при неизвестности сохраняй возможные исходы/границу.
Приёмка: конкретный cart URL выводится из source/config, не из имени приложения; выбран правильный сервер/метод; пустой client payload не скрывает сервер. Port collision и transport negatives проходят. Расширение endpoint binding не ломает существующий Train Ticket remote resolution.
Evidence: bean/factory/config chain с locations, normalized address и assumptions, client/server response pairing, state before/after, full E/C/R/D малого MRE, cart frontier.
Откат: hostname игнорируется глобально, binding основан на доменном remap, server исполняется при no-send или HTTP error объявляется normal success — убрать спорный mapping/dispatch, сохранив доказанную узкую часть.
Далее: G11, затем G12. Независимо при blocker: G08/G09, TT G13 и подготовка G14; не маскировать endpoint проблему ручным server ID.

G11. Последовательный typed reduce и source-ответ order-service
Тип: обязательная/P1 для cart-цепочки. Зависимости: G08; G10 для интеграции remote. Стоимость: средняя, может выявить отдельный numeric/record frontier.
Результат: поддержанный sequential reduce(identity, accumulator) исполняет source callback с правильными типами и исключениями; Order.total и server response вычисляются по коду.
Файлы: engine.py::stream_call, callback invocation, source_type и typed numeric dispatch; models.py::library/wire; cart Order.total141–144, OrderDetail.subtotal86–87, Quantity constructor19–21, OrderHttpMapper.toResponse46–63, OrderPersistenceMapper mapping, OrderPersistenceAdapter.
Порядок: сначала изолируй binary reduce overload от трёхаргументного/Optional/parallel; выполни identity и каждый accumulator call с propagated types, element aliases и normal/throw. Затем source map(OrderDetail::subtotal)→reduce(BigDecimal.ZERO,BigDecimal::add). Проверь реально достигнутые BigDecimal/record/mapper операции; не добавляй их по предположению и не меняй source quantity/total на oracle.
MRE+: известный empty→identity; два элемента с decimal amount и quantity→точная сумма по source; accumulator принимает корректный тип; source method reference виден в calls/executes. Для cart финальное значение 12.5 является expected проверяющего, не константой движка.
MRE−: неверный overload, parallel stream, unknown membership, порядок важен для accumulator, incompatible accumulator type, callback throws после эффекта, null element с source guard, scale-sensitive BigDecimal.equals против compareTo, мутация source во время terminal. Не используй float equality для доказательства всех BigDecimal контрактов.
Приёмка: результаты/types/state/throws маленьких cases соответствуют разобранному source; server mapper пройден до HTTP response, его ошибка не скрыта Void клиента. Поддержка ограничена проверенными операциями; очередной unsupported record/JSON/numeric случай имеет точный witness, а не фиксированный total.
Evidence: reduce contract/overload table, typed accumulator traces, source subtotal/Quantity events, server response witness, negative outcomes и cart next frontier.
Откат: source callback заменён guessed arithmetic, decimal типы теряются, неверное normal completion при throw или unsupported parallel объявлен точным — откатить соответствующий вариант модели к boundary.
Далее: G12. Независимо при blocker: G09, TT G13, общие controls; зафиксировать минимальный record/numeric case и продолжить независимую часть.

G12. Полная корзина: producer, refund, remote, состояние и отказы
Тип: обязательная/P1, интеграционная проверка. Зависимости: G07–G11 либо явно зарегистрированные оставшиеся boundaries. Стоимость: средняя–высокая; исправления только по новым наблюдаемым причинам.
Результат: исходные explicit и NL цепочки проверены целиком; нет объявления успеха по одному GET/terminal/PATCH.
Файлы: checks/run_cart_profile.py::main и новый versioned evaluator; analyzer/contracts.py::ContractGrounder, сценарный history/session binder, paths.py::run_paths, state.py, repository/persistence effects; cart RefundPaymentUseCase.execute36–40, Payment.refund111–115, OrderClientAdapter, RevertOrderToPendingUseCase.execute35–40, Order.revertToPending128–132. Фактические имена новых runner helpers фиксируй в журнале.
Порядок:
1) Начинай explicit и NL из двух независимых копий одного frozen DB; внутри каждой цепочки состояние последовательно переносится. Не загрязняй NL запуском explicit и не сбрасывай DB перед каждым шагом.
2) Первый запрос orderId11 берётся из явного входа. Selected payment/order ID получай из actual producer и формулировки сценария: единственный APPROVED among returned records. ID21 — expected oracle, не fallback. Несколько alternatives с одним доказанным выбором можно согласовать по семантике/provenance; нельзя взять первую произвольную alternative.
3) Проведи refund→remote order revert→reread payment/order→повтор refund→GET999→ambiguity→final reread. Для каждого шага сохрани request/args/constraints/root+remote responses/normal-throw/state/effects и источник ссылок на предыдущий результат.
4) По новому first-loss добавляй минимальный общий fix и MRE. Корректный source save перед remote error не откатывай автоматически: отсутствие доказанной transaction semantics не позволяет выдумать распределённый rollback.
MRE+: выбранный payment APPROVED→REFUNDED, связанный order PAID→PENDING; reread подтверждает изменения; остальные payments/orders/details и cardinalities сохранены. Повтор даёт 409/PAYMENT_ALREADY_PROCESSED до save/remote; отсутствующий ID даёт 404/PAYMENT_NOT_FOUND без writes; неоднозначная фраза сохраняет candidates/diagnostic и не выбирает произвольно handler, включая read-only GET; mutating request тем более не выполняется.
MRE−: producer empty/unknown/incomplete; два подходящих payment; два разных IDs на alternatives; перепутанные response поля; чужая строка изменилась; state reset между шагами; save/remote после повторного отказа; server exception после предыдущего save; подставленный orderId из oracle; отсутствие root HTTP ответа при наличии remote200.
Приёмка: typed per-step G07 gate проходит на реальном анализаторе для объявленного post-auth профиля; required/forbidden effects проверены отдельно от полного graph precision. Если остаётся boundary, фиксируй конкретный провал и неподдержанную область; cart не получает pass. После первого исправления этот профиль называется regression control, не новым holdout.
Evidence: complete explicit.json/nl.json, per-step causal ledger, snapshots+diff всех таблиц, producer lineage, negative/mutation results, remaining unsupported list, exact runner/inputs SHA.
Откат: успешная цепочка требует domain/ID/token/state insertion, silent unknown→empty или ослабления error/state gate — отвергни такой patch; сохраняй рабочие независимые библиотечные улучшения.
Далее: G13. Независимо при blocker: G14 и G16 для принятого кандидата; G15 только с настоящими замороженными входами. Общая цель не считается успешной только из-за частично восстановленной корзины.

G13. Train Ticket от поиска до реального UI-запроса оплаты
Тип: обязательная/P1, интеграционная проверка. Зависимости: G02–G05; G06 должен быть выполнен либо обоснованно отклонён, не является обязательным новым scheduler. Стоимость: средняя–высокая.
Результат: восстановлена либо точно локализована вся последовательность action→frontend request→handler→args→branches/remote→result→state→next request; S6 и отдельный known-input search не смешиваются.
Файлы: checks/run_tt_causal_probes.py; analyzer/contracts.py::ContractGrounder, frontend request/callback/session modules, paths.py, actors.py, engine.py; TT StationServiceImpl.queryForIdBatch, BasicServiceImpl.queryForTravels/queryTrainTypeByNames, TravelServiceImpl.queryByBatch/getTicketsByBatch; ts-ui-dashboard/static/assets/js/client_order_list.js::payMyOrder112–131; ts-inside-payment-service source pay.
Порядок:
1) После G03/G04 обнови G02 ledger. Сравни source-derived состояние, known/null/unknown значения и completion у S6 search, а не только итоговые 6 рёбер.
2) Для отдельного известного запроса search с исходной БД проверь no-op219 и фактическое прохождение живого 242: conditions244–255, source callbacks, avaTrips, response IDs. Явные startPlace/endPlace/departureTime допустимы как вход probe, не как fallback NL.
3) В полной исходной NL цепочке проследи выбор строки, перенос tripId/from/to/date, booking/order response и его orderId/tripId до payMyOrder. Для каждого поля сохрани producer и допущения; отсутствие результата объясни точным первым loss.
4) В UI payment body сохраняй только orderId/tripId из source. Authorization берётся из доказанного actor/session callback; userId не добавляй ради внутренней ветки оплаты. Body с дополнительным userId допускается отдельным явно заданным probe, результаты не смешиваются.
5) Разделяй business response и analysis status: исходный status1/data[] после widened ветки не доказывает concrete empty поиск. Budget/unsupported/binding/uncaught outcomes видны отдельно; не восстанавливай продолжение из guessed ID.
MRE+: независимый source UI получает список, выбирает единственный объект по заданному условию, отправляет его ID, затем использует ID ответа следующего запроса; две роли имеют независимые credentials/session. Полная TT-цепочка проверяет те же общие механизмы.
MRE−: пустой producer, неизвестный producer, interrupted producer, несколько подходящих строк, stale ID после изменения состояния, actor switch без нужного credential, неисполненный frontend success callback, неизвестный token, extra userId не из UI. Неподтверждённая связь должна остаться boundary/candidates, а не конкретным запросом.
Приёмка: полная цепочка с пригодными source-derived values/state достигает следующего шага и имеет подтверждённые E/C/R/D, либо точный оставшийся frontier и невыполненная часть. Сценарий не закрывается isolated payment200. Все изменения S6/103 шагов объяснены; скрытые gold edges не объявлены известными.
Evidence: per-field provenance, UI wire diff, chain of root/remote responses, DB/actor state transitions, source conditions, completion matrix, parent30 vs accepted stages; отдельные explicit/NL results.
Откат: связь сценария улучшается лишь через action/domain mapping, ID/token/state insertion, отказ от source UI body или скрытие incomplete — отвергни patch. Сохрани полезный общий value-flow fix с независимым MRE.
Далее: G14. Независимо при blocker: G12 cart, G14 controls, G16 cost; не трать оставшийся сеанс на подгонку S6 без нового различающего эксперимента.

G14. Содержательные общие регрессии и четыре отношения
Тип: обязательная/P1. Зависимости: все принятые code stages; часть выполняется сразу после соответствующего изменения. Стоимость: средняя, итоговый прогон и анализ дельт.
Результат: улучшения проверены против существующих контрактов и не маскируются ростом числа tests или неизменным union.
Файлы: code/tests; checks/run_real_journey.py/check_real_journey.py/check_journey_mutations.py; run_additional_journey.py/check_additional_journey.py/check_additional_mutations.py; run_document_journey.py/check_document_journey.py/check_document_mutations.py; check_legacy_state.py, check_boundary_wires.py, check_semantic_projection.py, compare_public_corpus.py, compare_stages.py, final_acceptance.py; protected manifests и corpus inputs.
Порядок:
1) Сохрани и выполни релевантные PiggyMetrics/Petclinic/inventory/document/actor/frontend/formatter/absence/singleton/order controls, после изменения — их конкретные downstream проверки. Финальный полный набор не повторяй без причины после неизменённого кода.
2) Проверь не только графы, но values/types/provenance/effects/state/completions. В inventory missing-category теперь должен быть правильный live-removal positive, а старый ожидаемыйU переносится в отдельный действительно unknown negative.
3) Сравни все четыре отношения по сценарию и шагу. На маленьких полностью размеченных MRE нужны FP/FN и full exact semantics; на required-edge oracle — только покрытие объявленного required subset, не recall полного графа. Пустые remote в старых corpus/S0 не подтверждают межсервисную точность.
4) Обнови versioned final_acceptance: cart-failure requirement — запись результата 30, не положительный gate новой версии. Зафиксированные в тестовых логах 1762 также являются историческим результатом, не требуемым числом tests; сам final_acceptance не содержит такого численного assertion. Сохранение старой failed записи можно проверить отдельно; это не заменяет новый cart acceptance.
5) В final кандидат включай только принятые patches; opt-in отвергнутый G06 не должен случайно стать default. Проверь offline guard и отсутствие reference/business dependencies по фактическим reads/code delta.
MRE+: сохранённые real journeys продолжают давать нужные ответы/ошибки/состояние; actor Bob refusal и возврат Alice не смешивают credentials; formatter source callback effect/throw сохранён; same bean alias переживает join и следующий request.
MRE−: mutation witnesses с wrong type/value/ID/status/effect/ordering; global unknown reduction без основания; extra source edge; пропущенный callback; reordered HashSet принят как known; reference file read разрешён inference; старый submission используется fallback.
Приёмка: все объявленные пройденными gates имеют свежий результат на exact candidate. Каждая регрессия имеет semantic explanation, исправление либо отвод patch; graph delta сама по себе не обязана быть нулевой. Неизменный submission при изменившихся witnesses отмечается явно.
Evidence: command/exit/inputs/code SHA, test results и список not_run, typed witness/mutation results, all-stage delta, protected-after, final acceptance schema. Не заменяй результаты одной строкой «все tests зелёные».
Откат: доказанная семантическая регрессия в поддержанном профиле — откатить вызывающий patch или исправить его с новым MRE; не снижать проверку ради pass.
Далее: G15/G16. Независимо при blocker: isolate offending patch, проверь остальные принятые изменения и подготовь provenance/архив G18, сохранив статус blocker.

G15. Новый заранее замороженный независимый профиль
Тип: обязательная проверка границ/P2; наличие полного входного пакета — prerequisite. Зависимости: freeze G01, G14. Стоимость: средняя при готовых входах; неподготовленный dataset — отдельная работа.
Результат: честное новое свидетельство переносимости либо точный список отсутствующих входов. Cart после настройки не называется свежим holdout.
Файлы: выбранный в G01 source/config/ready skeleton/context/scenario/oracle/profile manifest; новый isolated runner/checker в NEXT_SOLUTION; existing evidence schemas. Конкретный пакет не выдуман: его имя/SHA должны быть внесены после обнаружения реальных входов.
Порядок: используй другой реальный Java/Spring проект и предметную область, не переименование Train Ticket/inventory. До первого candidate result зафиксируй source revision, разрешённую framework boundary, explicit+NL chain, complete state expectations, required/forbidden edges, проверяющего и negative mutations. Разметка основывается на source, не на prediction. Готовый skeleton требуется как вход; построение общего skeleton generator не добавляй в эту очередь.
MRE/профиль+: минимум содержательная цепочка выбора объекта→изменение→remote действие→reread с непустыми remote/data, связыванием actual response и состоянием; другой отказ и missing/ambiguous input. Небольшие source counterexamples из G03–G11 дополняют, но не заменяют эту проверку.
MRE−: два подходящих объекта, отсутствующий ID, отказ после предшествующего изменения, неопределённый endpoint/config, изменённая чужая строка, remote от другого шага, ошибочный callback/order/type. Проверяющий должен отвергать такие witnesses до вывода о candidate.
Приёмка: зафиксирован первый результат без настройки на него, границы и метрики по области oracle. Если после результата нужен общий fix, сохрани первоначальный holdout outcome; последующие запуски называются regression. Никаких full precision/IoU без полного oracle. Если нет source/skeleton/context/scenario/oracle, статус blocked_with_reproducer или not_run с точным missing-input, не «transfer пройден».
Evidence: freeze timestamp+SHA до prediction, source scope/independence rationale, checker validation, first result, first-loss и последующие изменения отдельно.
Откат: утечка oracle в inference, profile-константы в engine или posterior rewrite freeze — отклонить такое доказательство; исправить процесс, не переименовывать результат в независимый.
Далее: G16 даже при отсутствии пакета. Независимый fallback: G16–G18 и спецификация недостающего профиля; не прекращать всю ночь ради пользовательского уточнения, пока есть разрешённая работа.

G16. Сопоставимая стоимость и правильные единицы памяти
Тип: обязательные измерения/P2; performance optimization необязательна и только по фактической причине. Зависимости: G01 и финальный принятый кандидат. Стоимость: малая–средняя без нового scheduler.
Результат: воспроизводимые phase timings/RSS и repeated prepared analysis; скорость не покупается потерей branches/effects/edges.
Файлы: checks/repeat_prepared.py43, checks/stage_benchmark.py, analyzer/portable.py (нормализация ru_maxrss около 80, phase accounting); offline_run.py, benchmark/final/analysis-report-timings.json и новые isolated results. Старые результаты не переписывай.
Порядок:
1) Исправь ошибку единиц: repeat_prepared пишет raw ru_maxrss как peak_rss_bytes; на Linux raw имеет единицы KiB, на Darwin bytes. Согласуй общую platform-aware conversion с portable и запиши raw/unit/normalized bytes. Для иной платформы не объявляй неподтверждённые units.
2) Запусти parent30 и candidate в одной среде с одинаковыми inputs/flags/path policy, отдельно сохрани preparation/index, analysis, validation/serialization, report writing, end-to-end и peak RSS. Укажи версии Python/parser/пакетов/OS/CPU и смысл cold/prepared; не обещай очищенный OS cache без реально выполненной процедуры.
3) Выполни повтор на подготовленном индексе и том же declared initial context, а не на мутировавшей DB предыдущего scenario run. Сравни exact prediction и важные witnesses; зафиксируй, какие файлы/фазы repeat не включает.
4) Если наблюдается конкретная регрессия стоимости, профилируй эту фазу и один локальный candidate. G06 worklist/cache принимается по semantic equivalence и измеренному устранению причины, не по красивой архитектуре.
MRE+: platform conversion на документированных Linux/Darwin единицах; prepared reuse сохраняет output и не протекает состоянием; report mode/без report сравниваются как разные границы. MRE−: raw KiB подписан bytes; summary.elapsed выдан за end-to-end; разные inputs/лимиты; меньше рёбер при «ускорении»; повтор использует уже изменённые rows.
Приёмка: единицы и границы однозначны, все actual runs с exit и hashes; нет рейтинга разных окружений. Сравнение включает разброс доступных повторов и его ограниченность. Новых SLA/обязательного процента ускорения не назначать; предложенный порог для будущего согласования явно обозначить предложением.
Evidence: environment manifest, phase records и raw measurements, count индексов/model calls, prepared-output diff, paired cost/semantic table. Для ориентира сохранённая сопоставимая пара 30: analysis68.2015→67.2997 сек, RSS447152128→451428352 байт; это один historical pair, не доказанный тренд.
Откат: performance patch ухудшает доказанную семантику или эффект не воспроизводится — убрать patch, оставить корректную нормализацию измерений и отчёт. Не повышай global budget как результат performance работы.
Далее: G17. Независимо при blocker среды: сохрани доступные measurements/ограничения, переходи к packaging G18; отсутствующую память/время не заполняй оценкой по числу tests.

G17. Реальная оценка неизменного ZIP и восстановление лучшего
Тип: обязательная при доступном сайте/P2. Зависимости: G14/G16, корректный package по skill и доступная авторизованная сессия. Стоимость: малая по коду, зависит от внешней очереди.
Результат: оценка exact candidate получена и сохранена отдельно от S0; после эксперимента восстановлено подтверждённое лучшее решение по действующим инструкциям пользователя.
Файлы: checks/package_final.py, replay_archive.py, check_integrity.py; solution.zip/submission.json/package manifest нового варианта; benchmark/site-score.json и новые записи assessed/restore с фактическими именами. Используй действующий механизм сайта, а не скопированные shell-команды из логов.
Порядок:
1) До отправки заверши code gates, offline replay именно содержимого ZIP и сверку submission. Зафиксируй SHA exact archive и assessed prediction. Документы, изменяемые после score, должны лежать отдельно или иметь явно другую post-score версию; assessed ZIP больше не пересобирай.
Перед проверкой timeout добавь в новой копии replay wrapper/finally: текущий replay_archive при TimeoutExpired на subprocess не создаёт replay.json. Сохраняй failure/timeout/exit/partial outputs, не fabricated completion.
2) По уже выданному разрешению отправь кандидат доступным штатным способом, дождись доступного verdict с ID/time/score; сохрани actual per-scenario values, если сайт их предоставляет. Не подставляй S0 или предыдущий score при ожидании/ошибке.
3) Сравни общий/S1–S7 с parent30, одновременно сохрани local semantics. Ухудшение не скрывается; его причина без hidden gold остаётся гипотезой, пока нет отдельного source/MRE доказательства. Не запускай цикл подгонки по ID сценария.
4) Восстанови проверенное лучшее решение согласно уже действующему распоряжению. В пакете 30 подтверждён №5, ZIP SHA f574de87739df8a679fff57d632b792c3a4742de7cb1d146d9b92fd2d7db0e46 и сохранённый restore1665676/0.909870. Проверь действующие инструкции и фактический лучший artifact; не пересобирай №5 из текущих других файлов.
MRE/проверка+: ZIP replay даёт его submission, site ID/score относятся к этому SHA, restore относится к правильным bytes. Negative: повреждённый/другой ZIP, verdict другого submission, формат accepted без score, timeout, restore не подтверждён. Каждый negative получает фактический статус, не fabricated success.
Приёмка: assessed artifact immutable, реальные внешние evidence сохранены, local S0 отдельно, best restoration подтверждено. Если сайт/сессия недоступны, не запрашивай повторного разрешения на уже разрешённую отправку: зафиксируй конкретный технический blocker и подготовь точный следующий шаг. Доступ/сессию нельзя обходить.
Evidence: SHA/size/manifest, replay outputs, site receipt/verdict/score table, submitted-at, restore receipt/hash, неизменные копии архивов. Секреты сессии не включай в аналитический пакет.
Откат: неудачный candidate не становится новым default; восстанови авторизованный лучший. Если восстановление блокировано, не заявляй, что оно выполнено; вынеси этот факт в начало итогового статуса.
Далее: G18. Независимо при blocker: G18 с готовым проверенным ZIP, commands и pending site/restore записью; не останавливать сбор доказательств из-за недоступного внешнего verdict.

G18. Итоговый аналитический архив и честное завершение общей цели
Тип: обязательная/P0 как завершение. Зависимости: все 18 целей получили фактический статус; обязательные нерешённые цели не становятся verified. Стоимость: малая–средняя.
Результат: пользователь получает новый вариант, что именно улучшено/не улучшено, фактические проверки, оценку при наличии и воспроизводимый следующий шаг. Не только список обещаний.
Файлы: checks/package_analysis.py, package_final.py, replay_archive.py, check_integrity.py; FINAL_REVIEW.md, REPRODUCE.md, LIMITATIONS.md, development/overnight-plan.md, development/overnight-state.json, development/overnight-log.md, checkpoint manifests и benchmark/overnight. Соблюдай project skill для итоговых имён и layout.
Порядок:
1) Сверь final working code с выбранным accepted checkpoint и ZIP; rejected prototype отключён/отделён. Приложи source diff от 30 и manifests protected before/after. Не редактируй старые snapshots ради красивой истории.
2) Собери только новый вариант, необходимые delta/input profiles/checkers/results/commands/ограничения. Полный новый независимый source профиль при правомерном включении и frozen revision; общий неизменный TT можно дать точным manifest+инструкцией расположения, если он уже есть в рабочем пакете. Не дублируй всю историю repository. Для отсутствующих необходимых входов перечисли exact path/hash и влияние на воспроизведение.
Адаптируй новый checks/package_analysis.py: текущие строки 13–14 безусловно требуют server-verification passed, а 25–43/65–66 фиксируют solution_30 и старый failed cart outcome в START_HERE. Упаковщик должен брать текущие verified outcomes и явно поддерживать site pending, не копировать прежний passed; это не разрешение отправить не прошедший code gates candidate.
3) В REPRODUCE укажи прочитанные и действительно выполненные команды, зависимости, CWD, flags, exits и output paths. В отдельном разделе — команды следующих ещё не выполненных проверок. Проверяй извлечённый финальный ZIP в новом temp/output, не на старом рабочем submission.
4) FINAL_REVIEW начинает с outcomes: S6/TT/cart/transfer/регрессии/стоимость/сайт+restore; затем таблица G01–G18 с evidence и blockers. Различай mechanism implemented, test-on-small-case, regression profile, new independent application. Пиши tests_run/not_run, не только count.
MRE/проверка+: manifest перечисляет все включённые файлы и совпадает с extracted archive; replay exact; ссылки/команды указывают на существующие package paths. Negative: missing input, лишний historical secret/session dump, изменённый protected file, docs приписали старые метрики новому коду, обязательная blocked цель отмечена done.
Приёмка: результат самодостаточен для разрешённого offline воспроизведения в заявленной среде; все claims привязаны к actual evidence. Если цель не решена, в отчёте точный first-loss, минимальный воспроизводитель и следующий эксперимент, а не глобальное «всё работает». Сохрани архив и выдай фактический путь/ссылку.
Evidence: final archive SHA/size/content manifest, replay/integrity output, итоговая таблица и durable checkpoint; все assessed artifacts остаются неизменными.
Откат: проблема integrity/упаковки — пересобери только новый неоценённый analytical archive. Нельзя переписывать оценённый ZIP; создай новый явно отличающийся artifact при необходимости.
Далее: завершай общую Goal лишь когда все разрешённые доступные работы выполнены и результат сохранён. Если среда/лимит/пользователь останавливают раньше — сохрани exact current goal, accepted code hash, последний output и следующую команду; не создавай новую Goal для обхода ограничения. Независимая альтернатива при blocker упаковки — сохранить review/manifests/checkpoint и готовые отдельные artifacts, явно указав, что архив ещё не получен.

КОМАНДЫ И ГРАНИЦЫ ВОСПРОИЗВЕДЕНИЯ

Следующие интерфейсы проверены чтением кода №30. Рецензент их не запускал. Перед запуском в новой версии прочитай сами scripts/imports и актуальные project instructions; после изменения CLI обнови команды. Не исполняй исторические команды установки/сборок/серверов. Все outputs должны быть новыми, внутри нового варианта или разрешённого нового runs каталога по skill.

В G01 заполни абсолютные значения task-specific variables:
NEXT_SOLUTION — новая версия, созданная по project skill;
BASELINE_SOLUTION — неизменная установленная №30;
TT_CHALLENGE — фактический полный tt-challenge из рабочего репозитория;
OVERNIGHT_RUN — новый output для конкретного запуска, не существующий старый runs;
CART_RUN, REPEAT_RUN, ARCHIVE_REPLAY_RUN — отдельные новые output paths.
Эти имена не являются готовыми путями; не подставляй /Users/... из логов или каталог обзора вместо рабочего repo. Для baseline используй отдельный run path и BASELINE_SOLUTION, для candidate — NEXT_SOLUTION. Исходный ZIP30 не содержит весь tt-challenge; отсутствие входа нельзя заменить gold/submission.

Основной offline CLI:

python -B "$NEXT_SOLUTION/code/offline_run.py" \
  --source "$TT_CHALLENGE/targets/trainticket" \
  --skeleton "$TT_CHALLENGE/skeleton/trainticket.json.gz" \
  --context "$TT_CHALLENGE/context" \
  --scenarios "$TT_CHALLENGE/scenarios" \
  --output "$OVERNIGHT_RUN/submission.json" \
  --report "$OVERNIGHT_RUN/analysis-report.json"

Читанный offline_run устанавливает audit guard для network/process/reference reads и затем вызывает analyzer.portable; разрешённые input/output явно указаны. Проверяй фактический audit sidecar и exit, а не только наличие JSON. В текущем CLI path-limit по умолчанию 4, graph-policy observed-union; доступен --no-constraints. Для сопоставимого baseline не меняй эти условия молча. Опции --completion-limit у прочитанного CLI нет; не выдумывай готовый flag. Любая экспериментальная опция должна быть реализована, opt-in и записана.

Проверяющие формата и открытого S0 запускаются отдельно от inference:

python -B "$TT_CHALLENGE/platform/evaluate_golden.py" \
  --check "$TT_CHALLENGE/skeleton/trainticket.json.gz" \
  "$OVERNIGHT_RUN/submission.json" --json

python -B "$TT_CHALLENGE/platform/evaluate_golden.py" \
  "$TT_CHALLENGE/gold/S0.json" \
  "$OVERNIGHT_RUN/submission.json" --json

Сохрани stdout/stderr/exit в новые файлы с недвусмысленными именами. Format check не доказывает correct edges, S0 не является site score; пустой remote IoU1 не является remote validation. Эти gold reads разрешены только checker-процессу и не должны попадать в построитель ответа.

Существующий отдельный TT probe runner:

python -B "$NEXT_SOLUTION/checks/run_tt_causal_probes.py" \
  --challenge "$TT_CHALLENGE" --output "$OVERNIGHT_RUN/tt-causal-probes"

В G02/G13 расширь runner source-derived witnesses для необходимых сравнений, не добавляя behavior по ID сценария в analyzer. Сохранённый одиночный payment probe и исходная полная NL цепочка должны оставаться разными результатами.

Интерфейсы cart runner/checker после versioning G07:

python -B "$NEXT_SOLUTION/checks/run_cart_profile.py" --output "$CART_RUN"

python -B "$NEXT_SOLUTION/checks/check_cart_profile.py" \
  --trace "$CART_RUN" --output "$OVERNIGHT_RUN/cart-checks.json"

Эти команды предполагают сохранение интерфейса в новой версии; если versioned checker имеет новое имя, запиши реальное имя. Нельзя просто запустить старый checker30 и назвать его hardcoded failed-transfer результат подтверждением исправленного cart. Runner/checker читают новый frozen scope, не переписывают oracle по prediction.

Повтор подготовленного анализа после исправления units G16:

python -B "$NEXT_SOLUTION/checks/repeat_prepared.py" \
  --source "$TT_CHALLENGE/targets/trainticket" \
  --skeleton "$TT_CHALLENGE/skeleton/trainticket.json.gz" \
  --context "$TT_CHALLENGE/context" \
  --scenarios "$TT_CHALLENGE/scenarios" \
  --expected "$OVERNIGHT_RUN/submission.json" \
  --output "$REPEAT_RUN" --repetitions 2

Здесь 2 — существующий default runner для первоначальной пары, не согласованный статистический норматив. expected читает comparator, а не источник рёбер; отдельный analysis результат должен строиться заново. Не сравнивай этот режим с end-to-end как одинаковую работу: повторный prepared run не включает весь цикл записи отчётов.

Проверка exact packaged analyzer:

python -B "$NEXT_SOLUTION/checks/replay_archive.py" \
  --archive "$NEXT_SOLUTION/solution.zip" \
  --source "$TT_CHALLENGE/targets/trainticket" \
  --skeleton "$TT_CHALLENGE/skeleton/trainticket.json.gz" \
  --context "$TT_CHALLENGE/context" \
  --scenarios "$TT_CHALLENGE/scenarios" \
  --output "$ARCHIVE_REPLAY_RUN"

Прочитанный replay_archive извлекает ZIP во временный каталог, проверяет manifest, запускает содержащийся offline Python-analyzer и pytest code/tests, сравнивает с содержащимся submission и читает audit. Это запуск проверяемого Python-кода, поэтому сначала прочитай изменения runner/tests и проверь их границы. В новой версии не полагайся на старое имя temp prefix/номер tests. Timeout — ограничение процесса, не свидетельство успешного завершения. Проверь безопасность путей и отсутствие symlink/дубликатов при упаковке/извлечении нового архива.

checks/stage_benchmark.py принимает stage, --existing-snapshot, --timeout. Он создаёт development/stages/<stage> и benchmark/stages/<stage>, копирует code, запускает свой offline CLI, затем отдельно evaluator и сжимает собственный новый report. ROOT=VARIANT.parents[1] предполагает конкретный repository layout; чтение архива в произвольной папке не удовлетворяет этому контракту. До запуска адаптируй path discovery в новой копии или используй явные команды выше. Не запускай stage_benchmark внутри исходной №30 и не перезаписывай существующий stage.

checks/final_acceptance.py в №30 содержит обязательный failed cart scope. Новый final gate должен проверять результаты новых G07/G12 и остальные актуальные обязанности, а исторический failure — отдельно. Не принимай exit0 старого final_acceptance за выполненные новые цели.

ПЕРВИЧНЫЕ КОНТРАКТЫ ДЛЯ РЕАЛИЗАЦИИ

Проверено рецензентом 18.10.2026 чтением первичных страниц; target services не запускались.
- Java21 Stream.toList, lifecycle/reduce contracts: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html
- Java21 Collectors.toList/toUnmodifiableList: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Collectors.html
- Java21 Stream ordering, laziness, non-interference и границы side effects: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/package-summary.html
- Java21 List/unmodifiable contracts: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html
- Java21 Optional.map/orElseThrow: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html
- Spring MVC exception handler specificity и аргументы: https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-exceptionhandler.html
- Spring RestTemplate patchForObject/request factory: https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/client/RestTemplate.html

Последняя ссылка при проверке показывала текущую документацию Spring7.0.9; это не доказательство exact resolved dependency cart. Используй исходные pom/config и доступные version-pinned primary contracts. Poms cart указывают Java21 и Boot4.0.6; полную транзитивную сборку рецензент не выполнял. Код JDK21u ReferencePipeline по version-pinned URL получить не удалось; выводы о toList основаны на Java21 API, не на случайном OpenJDK master. Если для узкого поведения нужен implementation-specific контракт, установи версию и проверь первичный источник, не обещай full JDK/Boot support.

КАК ДЕЙСТВОВАТЬ ПРИ НОВОМ ПРЕПЯТСТВИИ

Для нового first-loss сохраняй: actual request и аргументы, предыдущий producer, source location, последнюю известную typed value и первую unknown/boundary, path constraints, completion, affected state, diagnostic/event pointer. Выведи минимальный source-generic MRE. Сначала проверь, не является ли потеря следствием более раннего незавершённого producer; не лечи последствия догадкой о значении.

Если fix небольшой и относится к целям очереди, добавь его как подэтап текущей цели, укажи новые зависимости и продолжай. Если он требует необоснованной полной модели JVM/ORM/языка, сохрани границу и перейди к независимой цели. G06 отрицательный эксперимент допустим; G15 отсутствие входов допускает not_run; обязательные semantic fixes при этом не получают verified автоматически.

После каждой принятой стадии обновляй durable plan/log/state. Перед сокращением контекста сохрани текущую команду, незавершённый процесс/output, accepted hash и next goal; после восстановления прочитай их и продолжай. Не запускай повторно уже выполненный expensive baseline без различия кода/входов или неразрешённого риска. Если закончилась доступная среда/лимит или пользователь остановил, подчиняйся остановке; не создавай фиктивную постоянную цель для обхода.

ФОРМА ИТОГОВОГО ОТВЕТА CODEX

Начни с конкретного результата и ссылок на новый вариант/аналитический архив. Укажи, что изменено и почему это обосновано, что реально запускалось, основные значения/состояния/edge deltas, результаты S6/TT/cart/independent transfer, регрессии, стоимость, фактический сайт и restoration. Приложи таблицу G01–G18: status, evidence path, remaining issue, next action.

Не заканчивай сообщением «план готов» или «первый тест прошёл». Пользователь уже разрешил всю очередь. Выполни и проверь доступные этапы последовательно, переходи к независимой работе при препятствии, подготовь результат и точный checkpoint. При полном завершении не растягивай работу искусственно; при вынужденном неполном завершении прямо назови нерешённое и необходимое дальнейшее действие.
```
