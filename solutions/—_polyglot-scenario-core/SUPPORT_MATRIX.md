# Срез требований исследования

Исходные 18 случаев были спецификацией, не готовыми тестами. «Проверено» ниже означает ограниченный случай; это не доказательство всей семантики языка/фреймворка. Тесты находятся в `code/tests/`.

| Требование | Состояние | Свидетельство / граница |
| --- | --- | --- |
| C01: Java/Python integers | Проверен срез | int/long overflow, division/remainder, SMT, переход через HTTP |
| C02: exception type/finally | Проверен срез | Catch по типу, finally, вложенный active exception |
| C03: return в switch | Проверено | Return сохраняется общим kernel |
| C04: null receiver | Проверено | Хвост после null-вызова не исполняется |
| C05: HTTP verb | Проверено | GET и POST по одному пути различаются |
| C06: HTTP error policy | Частично | RestTemplate/requests/httpx проверены на 404; JavaScript fetch не поддержан |
| C07: независимые состояния | Проверено | Изменения доступны внутри цепочки и не переходят в другой сценарий |
| C08: id разных сущностей | Частично | Типы/таблицы не объединяются по id; автоматическое связывание истории слабое |
| C09: MySQL columns/escaping | Проверено | Named columns, quotes, comments, semicolons, versioned comments |
| C10: rollback и факт обращения | Проверен срез | Совершённый flush сохраняет data, rollback убирает запись; add без flush не даёт data |
| C11: JSON Number JavaScript | Проверен конкретный срез | QuickJS-NG: IEEE754, -0, NaN/Infinity, UTF-16, coercion и JSON; символьная JS-арифметика и TS не реализованы |
| C12: profiles/middleware | Частично | Profiles выбираются; точный filter/security lifecycle неизвестен |
| C13: unknown mutation | Проверен срез | Havoc объектов, таблиц, оверлеев; normal/throw остаются альтернативами |
| C14: бюджет | Проверено | Необследованный хвост не доказывает отсутствие эффектов, must пуст |
| C15: cold/warm cache | Проверено | Тот же граф, 6 IR hits, новое состояние; полной инкрементальности нет |
| C16: units | Частично | 5 kg не становится 5 grams; неизвестная конверсия остаётся unknown |
| C17: неоднозначный запрос | Проверен срез | Близкие кандидаты остаются гипотезами; scorer не калиброван |
| C18: фоновые изменения | Не реализовано | Нет очередей, scheduler, background tasks и внешних конкурентных эффектов |

Дополнительно проверены LibCST aliases/shadowing/syntax, Z3 UNSAT/unknown и абляция, SQLGlot JOIN/GROUP/ORDER/COUNT/NULL, JDBC/native @Query/SQLAlchemy, Session binding/delayed write origin/flush/read/rollback и static Java fields. Результаты — `benchmark/tests.xml`, абляция — `benchmark/oss-components.json`.


Второй этап: проверены одинаковые app/main.py в двух deployment, относительные импорты и раздельные глобальные значения; точные границы поискового документа; цитаты контекста и конфликтующие credentials; сохранение строковых 0042/false; отказ от усечения 1/2, 1,000 и единиц; заголовки и тело Java → Python; Java static/implicit dispatch и отличие от Python; явные версии Maven по сервисам, invalidation кеша и неизвестная мутабельность заголовков. Поиск обработчиков отдельно измерен на 10 публичных действиях — 10/10 top-1 и 9/10 точных наборов. Полный UI/history/framework pipeline на независимом публичном приложении всё ещё не подтверждён.

Третий этап: отдельный браузерный кадр на путь, исходные jQuery-запросы и ограниченный AngularJS `$http`, URL/JSON/form, явные контролы, DOM/text, раздельные sessionStorage/localStorage, примитивные исключения до запроса и в callback, завершение callback через return. Цепочка UI → Java → Python → БД → JSON storage → второй запрос совпала по всем четырём отношениям. JSON/form и scalar Form/Annotated различаются; символические UUID в path/query сохраняют идентичность. Browser/app startup, составные действия с несколькими запросами, callback chains, fetch/axios, TS/JSX/Vue SFC, произвольный DOM и полная сериализация не покрыты. Они не выдаются за реализованную поддержку. Подробности — [UI.md](UI.md).

Четвёртый этап: 8 публичных HTTP-трасс через исходные FastAPI dependencies без готовых Session/User, form login, password verification, JWT/Bearer, CRUD, validation, response projection и отказ. Все повторяются offline CLI с двумя hash seed. Дополнительно проверены независимость schema cache и фабрик, Source/builtin/library name collisions, alias и nested JSON, provided-fields, порядок JWT exceptions и ресурсные пределы для keyword-вызовов. Нативные версии закреплены; конфликт явно переданной версии останавливает неподдержанный хвост. Подробные границы, включая внутренние Source-конструкторы, генераторы и настройки валидации, — [FASTAPI.md](FASTAPI.md). Полного публичного Java/Python/UI-эталона и общей универсальности это ещё не доказывает.

Пятый этап: deployment-scoped Spring configuration, resolved Environment snapshots, servlet context и отдельный status 405, исходные exception handlers, ограниченные field Bean Validation и Java time. Проверены escapes/continuations/повторы properties, YAML merge и позиции, приоритет профилей, конфликт snapshots, сохранение Feign proxy, enum methods, UTF-16 длина, nullable constraints, каскады, advice priority и source-name shadowing. Даты используют явные clock/timezone и закреплённую IANA; DST gaps/overlaps и отрицательные epoch milliseconds проверены. Региональная tzdb без версии, nanoseconds, расширенные годы и неизвестная сериализация диагностируются.

В PiggyMetrics проходят 6/7 условных проверок обработчиков, но полная цепочка чтение → изменение → Feign → статистика остаётся неуспешной. Все 7 результатов воспроизводятся offline CLI, включая провал. Проверки предполагают успешный проход предшествующей framework/security-фазы; Jackson accessors, persistence converters, Streams/method references и полноценная авторизация ещё не подтверждены. Этот корпус не устанавливает полную поддержку Spring HTTP.
