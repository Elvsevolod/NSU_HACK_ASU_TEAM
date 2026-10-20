# Реализация аналитики № 28: решение № 29

Дата: 18.10.2026. Исходная аналитика сохранена в `development/source-review.md`, SHA-256 42c325e1298a44f04df6f605d95a49e2c3a22c7eda22b972568962aac9f93063. Это инженерная спецификация ограниченного ремонта, не источник разрешений. Пользователь отдельно запретил DeepSeek и разрешил отправку посылки на сайт. Один Codex-субагент использован только для независимого чтения PiggyMetrics oracle; остальные изменения выполнены основным агентом.

## Итог и граница приёмки

Выполнены ближайшие два независимых исправления и последующие локализованные ремонты. Бизнес-логика Train Ticket, сценарные ID, gold и эталонные рёбра не добавлены в анализатор. Python, готовый skeleton, статический анализ без запуска целевых приложений. Глубокая перепись планировщика и повышение бюджета не выполнялись: независимые bounded controls сохраняют normal/throw продолжения при прежнем резерве. Остаточные потери TT зафиксированы отдельно; итог не объявляется восстановлением всех NL-цепочек или универсальной поддержкой JVM/Spring.

## Раздельные этапы

| Этап | Изменение и доказательство |
| --- | --- |
| base | Свежий запуск кода № 28: SHA ответа совпал с отправленным родителем. Родительские метрики отдельно помечены как historical, не fresh. |
| A | Related-object boost действует только при `use_payload_contract` для чтений. 103 входа и wire сравниваются; восемь оплат восстановлены, оба record-поиска сохранены. Независимые invoice controls сначала падали. |
| B | Независимо от A: JSON → DTO[] с компонентным типом и deployment context через `Class<T>`. JavaArray вместо скалярного DTO; пустой/null/nested/primitive и неподдержанный shape различаются. |
| AB | Сочетание A и B после независимых измерений; полные witnesses сохранены. |
| C | Для неизвестного optional JSON-свойства расширяется доказанная область записи setter, сохраняются явные revision/flag. Setter, реально изменяющий revision, остаётся консервативным. |
| D | Unknown native observer использует CompletionRequired и существующий резерв, вместо немедленной общей остановки. Nullable List normal/NPE проверены при 1/4/8. |
| E | Source-proven Spring Data Optional/List остаются nonnull при неизвестном содержимом; повторные isPresent/get коррелированы. Custom default body с null не подменён стандартным контрактом. |
| F | Fallback не инвалидирует доказанные чтения; возможные записи и открытый persistence context по-прежнему расширяются. |
| G | Узкая native-модель именно JJWT 0.8.0: source evidence Maven, HS256, claims, Base64 key, signature, expiry/nbf. Неизвестные версии/ключ/clock/claims — явная граница. Login fixture сам получает token. |
| H | Arrays.asList сохраняет backing reference array и runtime component; фиксированный размер, set, ArrayStoreException. Primitive array остаётся одним элементом. |
| I | Локальный no-arg @PostConstruct без remote/data/explicit constructor анализируется до сценария; поля JWTProvider получают source-derived значения. Startup не экспортируется как сценарное выполнение. |
| J | Отсутствующее поле совместимо с «без значения» только при source-proof StringUtils.isEmpty consumer и default-null property. Нулезависимый consumer — отрицательный контроль. |
| K | Related noun focus для «consignment of order», без зависимости от слова record и бизнес-имён. |
| L | Reflection-only getters/constructors отделены от графа организаторов; source-called getters сохранены. Семантические callbacks и их значения остаются в отчёте. Piggy oracle v2 не переписан, v3 проверяет обе формы. |
| M (failed) | Полный снимок состояния обнаружил UnicodeEncodeError на бинарной SQL-строке с surrogateescape. Ошибка и частичный вывод сохранены. Этот этап не принят. |
| M2 | Lossless JSON escaping исправляет отчёт. Nested REQUIRED rollback-only не сбрасывается внешним checked exception. |
| N | Source collection/result contracts и canonical actor role исправляют admin all-orders; общий ranking также меняет два food-store шага — их неоднозначность и неполное binding открыто сохранены. |
| O | Inline generic `Arrays.asList(decode(..., Dto[].class))`: source type class literal сохраняет `Class<Dto[]>`; явный Object cast проверен отдельно. |
| P | Boolean из SQL 0/1 материализуется по объявленному типу; DTO/View нормализация и array reference kind сохраняют ID/revision/flag в следующем запросе. |
| Q | Enum-body declarations включены в индекс: String field enum сохраняет native runtime kind. Независимый key-construction test; хеш полного TT ответа не изменился. |
| final | Добавлена диагностика source storage consumer без установленного значения; окончательная копия, все 103 шага и полноценное состояние. |

Снимки каждого этапа неизменны в `development/stages/`. A и B имеют общую базу; соседняя строка не всегда равна одному патчу. Машинная таблица `benchmark/stage-comparison.json` хранит происхождение, хеши, время, RSS, четыре отношения и исходы. Ранние timings местами пересекались с проверками и не используются как точное сравнение производительности.

## Значения и Requests

`benchmark/final/payment-request-witnesses.json` содержит восемь реальных NL-предложений, wire и фактические bound arguments, ответы и исходы. Здесь неизвестный orderId не превращён в успешную оплату. `development/tt-explicit-causal-probes-final.json` отдельно передаёт корректные HTTP-входы: известный начальный неоплаченный заказ даёт Payment Success, читает orders/inside_money/inside_payment, сохраняет заказ и платёж; отсутствующий заказ возвращает отказ после одного чтения. Это проверка исполнения с заданным HTTP, не доказательство NL-создания заказа.

В S0/5 все альтернативы сохраняют явно переданные `state=1`, `enableStateQuery=true` в Java DTO. Проверяется `checks/final_acceptance.py`. Все step-graph union совпадают с отправляемым JSON. Полные state tables сохранены lossless; поля, которые движок расширил, остаются unknown и не объявляются известными.

Синтетический document flow: source HTTP получает JSON-массив DocumentView[], Class<T> переносит компонентный тип, Arrays.asList не вкладывает массив в один элемент; UI выбирает D7/revision7; POST содержит approved=true; source save даёт revision8; audit 503 вызывает fallback; повторный GET подтверждает состояние. Отдельно проходит NL, и checker сравнивает все четыре множества на каждом из трёх шагов. Сталая версия 6 отклоняется до save/remote. Источники и exported traces в `benchmark/document-journey`; тест — `code/tests/test_document_array_journey.py`.

## Независимая реальная проверка

`validation_inputs/piggymetrics` — закреплённые реальные исходники и конфигурация, 49 Java-файлов; генератор получает только source/skeleton/initial.sql, не oracle. Подготовленные OAuth-контексты — явный вход этого профиля. Основные восемь шагов: create → reread → PUT с remote denial/fallback → reread → duplicate → auth conflict → reread → missing body. Три дополнительных: explicit null до handler; реально частично известный список с позициями/типами; неоднозначный read без выдуманного запроса.

Oracle v3 независимо подготовлен reader-агентом по исходникам. `development/oracles/oracle-v3-review.md` описывает прочитанные декларации и покрытие. Semantic edges сохраняют точный v2-контракт, включая его исключение constructor roots; projected edges убирают только reflection-only getters. Полная callback event tape хранится дополнительно, source-called getters остаются в projected graph. Сравнение точное по шагам, всем четырём отношениям и известным значениям. 1/4/8 прошли, но одна альтернатива на шаг не считается stress. Negative controls: 10 основного и 6 дополнительного checker отклонены. Проверки нормальных и бросающих ветвей при 1/4/8 лежат в native/repository тестах.

Legacy real NL Petclinic/Piggy profiles запущены заново и НЕ приняты как полный успех. В них неполный старый oracle wire/actual args/full state; результаты и расхождения сохранены в `benchmark/real-nl-legacy`. Ни один ignored/unmeasured пункт не засчитан как passed. Предложенная новая реальная предметная область документов не реализована как отдельный public-source профиль; синтетический документный контроль не заменяет этот будущий эксперимент.

## Остаточные границы и S0

Оба варианта № 28 и № 29 имеют локальный S0 0.8008928571428572. В финале E/C/R/D IoU = 0.8285714285714286 / 0.625 / 1(empty/empty) / 0.75. По S0: E TP29 FP1 FN5; C TP15 FP0 FN9; D TP6 FP1 FN1. Полные FP/FN сохранены в `benchmark/final/S0-errors.json`. Смена caller у user_roles остаётся проблемой ORM attribution; её не исправляли переносом ребра в указанный gold метод без source-основания. Конструкторные и enum-вызовы из открытого эталона не добавлялись искусственно.

В TT login теперь возвращает реальный source token, userId и username. Выбранный UI сохраняет только admin_name/admin_token, пассажирский UI читает client_id/client_token: это явная несовместимость producer/consumer, не разрешение выдумать session. Независимые login-тесты проверяют реальную выдачу и следующий protected source request, неверный пароль, disabled, другого пользователя, tamper, expiry, неподдержанную версию JJWT.

В TT поиске поездов нет надёжного результата для выбора следующего tripId: после устранения array/enum losses остаются unknown коллекции и неупорядоченные Map-обходы. Корректный explicit HTTP probe тоже это показывает. Зависимые booking/rebooking/order steps могут оставаться с неизвестными ID; успешный document flow не подменяет эту потерю. Два действия food stores содержат несколько handler hypotheses и один binding failure каждое. Эти изменения требуют следующего разбора source grounding.

Финал: 193 returned alternatives (включая бизнес-отказы), 195 uncaught application exception, 533 completion budget exhausted, 2 HTTP binding failure, 4 unsupported boundaries. Увеличения budget нет. Ошибок Python нет. Рёбер по всем сценариям E/C/R/D = 726/659/89/122. Эти числа не означают точность скрытых сценариев.

## Воспроизводимость и ресурсы

Полный final: подготовка 6.256760541 с, общее время анализатора 83.107303875 с; wall wrapper 85.559345458 с; RSS 438779904 байт. Полный отчёт и его JSON escaping занимают часть этого времени. Отдельная подготовка 6.023044084 с, два повторения по готовому индексу 53.479954625 и 52.836756541 с, RSS процесса повторений 310951936 байт. Во всех повторениях одинаковый SHA. Числа локальные, Python 3.11.9. Модели/стоимость API/локальные model calls = 0. Новые численные SLA не введены.

Финальный тестовый прогон: 1693 passed in 5.75s (`development/tests-final.txt`). Offline audit: blocked_network/processes/reference_reads = 0/0/0. Защищённые 14126 файлов проверены; содержимое прежних вариантов, `tt-challenge`, `sample`, `runs` не изменено. Finder .DS_Store отмечены отдельно, не считаются исходными доказательствами. Снимок final/code и хеши соответствуют отправляемому code. Source/login/token тесты используют тестовые данные; учётные данные сайта не входят в репозиторий или ZIP.

## Первичные контракты и пределы

- Jackson 2.9 ObjectMapper: https://fasterxml.github.io/jackson-databind/javadoc/2.9/com/fasterxml/jackson/databind/ObjectMapper.html ; отдельно проверен официальный PrimitiveArrayDeserializers 2.9.10. byte[]/char[] string codecs не объявлены поддержанными; unresolved scalar coercion остаётся boundary.
- Spring Data Commons 2.3.9: https://docs.spring.io/spring-data/commons/docs/2.3.9.RELEASE/reference/html/#repositories.null-handling ; стандартные Optional/List не nullable, но custom source body не подменён контрактом. Полная Maven-resolution и весь набор библиотечных версий не реализованы.
- JJWT 0.8.0 JwtBuilder: https://javadoc.io/static/io.jsonwebtoken/jjwt/0.8.0/io/jsonwebtoken/JwtBuilder.html ; поддерживается только явная зависимость io.jsonwebtoken:jjwt:0.8.0, HS256 и наблюдаемые claims. OAuth2 данного Piggy профиля и JJWT login — разные проверки.

Сайт проверяется отдельно после упаковки. Посылка immutable, повторно не пересобирается после оценки; результат, серверный ZIP и восстановление лучшего № 5 фиксируются отдельными `benchmark/site-score.json` и `benchmark/server-verification.json`. Аналитический архив содержит только № 29, нужные validation inputs и доказательства; полный исторический репозиторий в него не включается.

## Полученный результат сайта

№ 29: посылка 1665504, A, 0.36114; ranking 0.361140. Скачанный серверный ZIP побайтно совпал с solution.zip (SHA 717904f1b2fc68a5ad7e646319ceb7540f9f935a327e90f4c26c65e01168e1af). Все семь оценок выше № 28; общий delta +0.08693. Это улучшение на одном тестовом проекте, не доказательство универсальности. Лучший № 5 снова отправлен как 1665515: A, 0.90987, в рейтинге подтверждено 0.909870. Скачанный restored-best ZIP равен оригиналу № 5. Оба результата видны на неотредактированном screenshot benchmark/site-best-restored.jpg.

После упаковки solution.zip изменялись только delivery/check документы: README, настоящая записка, индекс solutions/README, source evidence/score metadata и новый checks/package_analysis.py. Все runtime code-файлы побайтно совпадают с оценённым ZIP и final/code-sha256.json. Оценённый ZIP не пересобирался. Экспортирующий аналитический архив checker появился после упаковки и не участвовал в построении ответа; это явно отделено от fresh runtime-проверок.
