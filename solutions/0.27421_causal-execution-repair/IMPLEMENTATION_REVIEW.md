# Приёмка ремонта № 28

Основание: `solution_27_regression_review.md`, SHA-256 `cd2bba99ad21944b841f712c2fbf8d0757842988ce40f326087cb66ae743c9e0`. Родитель № 27; № 23 и № 5 сохранены неизменными. DeepSeek запрещён пользователем и не использован. Исправления относятся к ограниченному Python-анализатору исходников, а не к полной реализации JVM/Spring.

## Результат и ограничения

Обязательный полный source-профиль PiggyMetrics проходит: восемь последовательных HTTP-шагов с непустыми remote и data, плюс invalid input, частично неизвестный список и неоднозначное действие. Выполнено 1625 тестов. Проверка отвергает 10 повреждений основной трассы и шесть дополнительных. Все восемь ответов Train Ticket повторены с готовым индексом. Целевые приложения не запускались.

Общая точность пока не улучшена доказательно. S0: 0,8627976190 → 0,8008928571. Число рёбер: 1026 → 1332. Полный прогон: 84,150 с против 28,441 с повторённой базы; RSS 390709248 против 345817088 байт. Два повторных анализа с готовым индексом заняли 51,105 и 49,660 с; это другая измеряемая фаза. Ускорение равноценного анализа не заявляется. Сайт: A, 0,27421, посылка 1665291; +0,08019 к № 27, −0,38764 к № 23, −0,63566 к № 5. Это ограниченный прирост относительно провального родителя, без восстановления лучшего качества.

В Train Ticket остаются 587 остановок по completion budget, четыре unsupported-semantic boundary, 304 альтернативы с исключением и три остановки фильтра; 109 альтернатив вернули результат. У 53 шагов все сохранённые результаты неизвестны. Не каждое исключение является допустимым бизнес-отказом. Эти случаи не заменены статическим замыканием и не названы исправленными полными путями. Неизвестный JJWT/provider, некоторые даты, discovery и другие внешние API остаются вне поддержанного контракта. Численные SLA и обещания скрытой точности не назначались.

## Карта реализации

| Этап | Изменение | Проверка и граница |
|---|---|---|
| A | Разрешение static/import/FQN поля Logger; общий native descriptor; SLF4J formatting callbacks | Bare/Class/FQN/static import, shadowing, custom info, аргументы с эффектами, null Logger и caught toString failure. Provider transport failure явно вне модели |
| B | Общий return/value контракт String; replace/locale/UTF-16/trim и сохранение типа через return | Значение проходит helper/DTO/length/branch; неподдержанные locale/Unicode остаются типизированной неизвестностью |
| C | Singleton adopt/rebase, совместный перенос state/frame/result и aliases | 7/9 и throw/catch при limit 1/2/4/8; прежние locals, receiver, аргументы, browser и таблица остаются связаны |
| D | Remote фиксируется при входе серверного обработчика | Prefix сохраняется при analysis stop; binding/filter reject до входа не создаёт remote |
| E1 | Загруженный UserDetails становится receiver status/password/authority callbacks | Один principal, invalid password/disabled остаются отказами; исходная Dao-проводка проверяется, неоднозначность не угадывается |
| E2 | UI response → storage → headers → immutable Request; clear/error/actors | Полная цепочка с настоящим AuthenticationManager adapter; explicit/UI wire и binding совпадают; другой actor не получает token |
| E3 | Выбранные поля согласованы с wire и фактическими Java args | Missing/null/DTO defaults различаются. Если UI не умеет передать выбранное поле, direct HTTP hypothesis явно диагностируется |
| F1 | Input journal отделён от результатов | Новые credentials сохраняются при неизвестном ответе регистрации; старый аккаунт/литерал UI не подставляется |
| F2 | From/to после сравнительного with; фактический UI early return | Языковые пары и source guard проверены отдельно; желаемое действие не переписывает ошибочный UI |
| F3 | Вывод payload schema и source reference parameters; неоднозначность identity | Record отличается от record type; related order/shipment ID — от ID самой записи. Неуточнённый principal/named lookup не превращается в выбранный Request |
| F4 | Ordinal по исходным слотам без сжатия unknown/duplicates; producer scopes | [U,C] first остаётся неизвестным; [A,A,B] second=A; unrelated known producer не стирает историю; одинаковые ID разных deployment/FQN разделены |
| G | Раздельные unknown-value/receiver/target/semantics/budget; узкие readonly native summaries | Optional/HTTP entity/collection observers не получают произвольный global write. Throwing completions остаются отдельными; общий бюджет не повышен |
| H | Source-only адаптер полного трёхсервисного профиля; Feign/контекстный путь/validation/Principal/JSON defaults | Строгая реальная цепочка и три дополнительных случая. OAuth post-auth identity предоставлена входом, выпуск/верификация токена исключены |
| I | Source-compatible witness и отдельный semantic checker | Wire/headers/body/absence, DTO/FQN/вложенные типы, remote identity, fallback args, status, записи, операции сохранения и per-step edges. Пустые args и ignored body не засчитаны |
| J | Семь воспроизведённых дополнительных рисков | Unknown loop completion; nested REQUIRED rollback-only; uncertain save без Python crash; lazy hydration helpers; column aliases при dirty checking; mutable table identity; multiple-route shared binder |
| K | Снимки, измерения, отрицательные controls, офлайн-повтор и отдельная упаковка | 21 immutable stage; исходные отчёты и неудачные промежуточные результаты сохранены; сайт и архив привязаны к SHA |

Дополнительный реальный случай обнаружил потерю null/типизированного unknown enum при materialization. Исправлена общая enum-гидратация, не бизнес-правило PiggyMetrics. Это закреплено отдельным тестом и исходной трассой неудачного прогона.

Фактические JSON getters теперь экспортируют executes как framework callbacks; синтетический source calls не создаётся. Конструкторы reflection root сохраняют прежнюю отдельную проекцию. Усиленные унаследованные тесты сохраняют прежние значения и проверяют новую явную политику getter events. Структурный witness допускает лишь явно условный setter при неизвестной JSON property presence и не объявляет его подтверждённым фактом исполнения. `semantic_accuracy_proven=false` сохранён намеренно.

## Причинные этапы и регрессии

`benchmark/stage-comparison.json` содержит кодовые манифесты, хеши ответов, время/RSS, исходы, четыре отношения и S0 для каждого снимка. A и B проверены отдельно на базе № 27, C и D также отдельно; затем ABCD и последовательные E/F/G/H/J. Это не позволяет назначать каждому последующему патчу долю скрытого score.

Промежуточный F3 чрезмерно усиливал payload schema для refresh/list и ошибочно переключал запросы. Его S0 0,2786889076 сохранён, а не заменён финальными числами. Применимость правила ограничена обычным чтением; list-of сохраняет объект действия. Related-key проверяется только по непустому source entity, чтобы пустое имя из ById не совпадало со всем. Итог снова выбирает обычные и высокоскоростные order handlers отдельно и find-by-order для consignment/assurance. Это исправление общих правил, без условий по scenario ID или именам Train Ticket.

В `benchmark/uncertainty-and-budget.json` перечислены причины и примеры реальных остановок, тип receiver, footprint, completions, source site и положение в трассе. Source-профиль с independently supplied правильными Request проходит при 1/4/8 за 0,066–0,081 с анализа, RSS примерно 54–55 MB. Он проверяет сохранённые значения, отказы и рёбра. Совместимые continuations и readonly native summaries проверены; повышение общего бюджета признано необоснованным способом лечить неподдержанную библиотеку. Неизвестный внешний вызов по-прежнему не обещает точное состояние или полный будущий граф.

## Полный независимый профиль

Закреплён commit PiggyMetrics `6bb2cf9ddbca980b664d3edbb6ff775d75369278`. Адаптер собирает 49 Java-файлов трёх сервисов, декларации enum-методов и source configuration в готовый входной скелет. Он не читает ожидаемый граф. `run_real_journey.py` и `run_additional_journey.py` также не загружают oracle; ожидаемые значения читает только последующая проверка.

Первый oracle, SHA `dfe0a69beda626fe85791d9d221303793942e85d7e8ea2453e505f6b4151e37a`, заморожен до runtime-ремонта. Независимый разрешённый пользователем Codex-читатель выявил source-ошибки в статусе Hystrix fallback и security context. Исправленный source-only v2: `499f635f5df70eafafc6ef0b424266949d62f5886a77b4af5c9e9f1cf82a9e8d`. Он создан после начала A/C; нельзя считать его целиком замороженным до любых исправлений. Читатель не видел runtime или outputs. Проверены 53 хеша исходников и 50 деклараций.

Дополнительный v1 также сохранён. Source-reviewed v2 дополнительных случаев: `5417ee09198c59c672589cbd1a448544259bb1c4c87f6dfea1dcb94519ebc63b`; 56 деклараций. Неполный список означает два точно nonnull source Item: первый с пятью независимыми типизированными unknown полями, второй Rent/7/USD/MONTH/home. Не обещается сериализация произвольного неизвестного receiver. Проверены 21 getter callback, их значения и receiver, исходные позиции, отсутствие writes/remote. Ambiguity — заданная политика обработки недостаточного NL-контекста, а не свойство Java-кода.

Шаги основной цепочки: создание с remote Auth save; GET по имени из результата; PUT по principal с отличающимся body.name; локальное сохранение до удалённого validation reject и fallback; чтение; duplicate local refusal; занятый Auth username с удалённым отказом; последующее чтение; missing body reject. Фактическая восьмишаговая последовательность и точные значения находятся в oracle и trace. В Mongo-профиле сохраняются немедленные datastore writes, а не фиктивный JDBC commit; rollback проверен отдельно на nested REQUIRED.

Файлы ошибок Spring, не заданные source-контрактом, явно unmeasured. Не вызванные Java args при validation reject и полностью неоднозначном действии — not applicable; кандидат DTO проверен отдельно. Они не увеличивают число измеренных полей. Передача source witnesses не равна semantic oracle. Исторические короткие real-NL controls #5/#23/#27/#28 повторены на одинаковых входах, но пустые arguments, ignored results и подсчёт строк больше не названы полной приёмкой. Parent #27 на новом explicit HTTP-профиле не проходит source routing/chain gate; это сохранённый результат, не замена контролю качества.

## Воспроизведение и архивы

Команда продукта — в README. Полные результаты и кодовые снимки находятся в `benchmark/stages` и `development/stages`; эталон S0 используется только последующей оценкой. В production нет внешней LLM, JVM, запуска target services или обязательной модели. Зависимости закреплены, включая bcrypt 5.0.0 для поддержанного PasswordEncoder contract.

`benchmark/final` содержит исходный ответ, полный сжатый report, формат, S0, source-compatible witnesses, ресурсы, входные/кодовые хеши и offline audit. После финального построения изменён только независимый `verify_run.py`: уточнено допустимое условное JSON setter witness. Изменение отражено в `metadata.post_run_manifest_delta`; код построения графа и восемь ответов не менялись.

`solution.zip` — компактная самостоятельная посылка. Перед отправкой она распаковывается в отдельный временный каталог, повторяет восемь JSON и весь набор тестов с блокировкой сети/запуска процессов/чтения эталонов. Оценённый ZIP затем неизменяем. Аналитический архив включает только вариант № 28, его измерения, отрицательные эксперименты, исходный review и необходимый source/oracle-профиль. Предыдущие аналитические пакеты и полные старые варианты в него не включаются.

Все 8787 защищённых файлов проверены по хешам. Новые `.DS_Store` от Finder перечислены отдельно; содержимое прежних вариантов, `tt-challenge`, `sample` и `runs` не изменено. Изменение сводного `solutions/README.md` разрешено правилами ведения вариантов.

Серверный архив № 1665291 скачан и байт-в-байт совпал с `solution.zip` (SHA-256 `00e09cb5744cac0f1305fb75d5492d7b3d1b2998cff69c376157c4a09bb1ea08`). После этого исходный № 5 восстановлен: 1665292, A, 0,90987; рейтинг0,909870. Оценённый ZIP № 28 не пересобирался.
