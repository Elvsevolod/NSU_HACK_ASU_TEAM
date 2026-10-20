# Ночная реализация №31 после №30

Основной договор: development/inputs/codex_overnight_implementation_prompt.txt, прочитан полностью. Общее постоянное Goal создано. Переход между подцелями без ожидания пользователя. DeepSeek запрещён.

Стадии: development/stages/<stage> и benchmark/stages/<stage> для совместимости с существующим измерителем; дополнительные данные — benchmark/overnight/Gxx/<stage>.

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


## Фактическое закрытие очереди

| Цель | Статус |
| --- | --- |
| G01 | verified |
| G02 | verified |
| G03 | verified |
| G04 | verified |
| G05 | verified |
| G06 | experiment_rejected |
| G07 | verified |
| G08 | verified |
| G09 | verified |
| G10 | verified |
| G11 | verified |
| G12 | verified |
| G13 | verified |
| G14 | verified |
| G15 | not_run |
| G16 | verified |
| G17 | verified |
| G18 | verified |

Принятая стадия: G16-report-fastpath. Сайт1665875/A/0.39232, восстановление1665877/A/0.90987. G13 — точный remaining frontier, G06 experiment_rejected, G15 not_run. Новая работа по ним не объявлена выполненной.
