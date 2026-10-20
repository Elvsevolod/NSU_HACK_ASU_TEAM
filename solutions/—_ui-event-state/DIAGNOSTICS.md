# Диагностика варианта № 11

Цель устранить все неизвестные входы не достигнута. По единому аудиту всех альтернатив: **18 шагов / 49 пар шаг–поле** против **17 / 48** у № 10. Проверка только первой альтернативы даёт 18 против 16; сравнивать эти определения нельзя. В аудите отдельно перечислены свободные символические значения нового аккаунта. Сгенерированные идентификаторы определяются по происхождению и идентичности, а их случайные байты не предсказываются.

## Замечания ревью № 10

| Замечание | Исправление и проверка |
| --- | --- |
| HTTP-метод getForObject/postForObject | Методы определяются по сигнатуре; строковое тело POST не становится глаголом. test_review10_execution, test_http_uri_templates |
| Выполнение после отказа | Optional, null, 404/5xx, FilterChain и shouldNotFilter; дополнительно границы массивов/списков/строк и итератора. test_guaranteed_access_failures |
| switch и catch | Abrupt completion, fallthrough/default/arrow, типы catch/multicatch и finally. test_review10_execution |
| UUID как выдуманная строка | Типизированный символ, length36, правильный fromString/toString и идентичность в URL. test_uuid_conversions, test_symbolic_request_state |
| Масса и форматирование | 5 kg → weightGrams=5000; без доказанной единицы — неизвестность. DecimalFormat и SimpleDateFormat учитывают поддержанный pattern. test_review10_inputs |
| SQL dump | INSERT со списком колонок, удвоенные/экранированные кавычки; неподдержанное отмечается. test_review10_inputs |
| Контекст сценария | Учитываются title/description, явный объект шага имеет приоритет. test_review10_inputs |
| Profile, int, sample | Неактивный простой Profile исключён; int/long wrap; настоящий запуск вне репозитория с каталогом sample. Сложные профили остаются возможными с предупреждением |
| fetch/axios/.vue | Поддержка не заявляется; причины видны в отчёте. test_review10_inputs |
| Переносимость | Добавлен полный эталон ограниченных тел Petclinic GET/PUT/GET, но полного HTTP-эталона и доказательства произвольной переносимости нет |

Независимые дополнительные проверки нашли и устранили ошибки RequestHeader, ResponseEntity(status), DocumentHeader, source equals, наследования, унаследованного Id, GeneratedValue соседней сущности и записанных Embedded/enum. Это ограниченные модели, не полная реализация Java/Spring.

## Оставшиеся входы

| Шаг | Неизвестные поля хотя бы в одной альтернативе |
| --- | --- |
| S1.6 | consigneeName, consigneePhone, consigneeWeight, foodType, stationName, storeName |
| S2.6 | foodName, foodPrice, foodType, stationName, storeName |
| S3.6 | documentNumber, name, phoneNumber |
| S3.7 | consigneeName, consigneePhone, consigneeWeight, foodType |
| S3.8 | contactsId |
| S3.14 | weight |
| S4.1 | documentNum, documentType, email, gender |
| S4.3 | documentNumber, documentType, name, phoneNumber |
| S4.7 | contactsId, foodType, stationName, storeName |
| S4.10 | orderId |
| S4.11 | orderId |
| S4.12 | orderId |
| S4.13 | loginId, orderId |
| S5.5 | trainType |
| S6.13 | orderId |
| S7.4 | consigneeName, consigneePhone, consigneeWeight |
| S7.10 | oldTripId, seatType, tripId |
| S7.12 | consignee, id, phone, weight |

Причины различаются:

- В S3.6, S4.1/S4.3 и при изменении получателя нет конкретных новых персональных значений. Старые записи не задают новые имя, документ, email или телефон. Пользователь подтвердил, что дополнительных материалов нет. [Логическое свидетельство неоднозначности](checks/missing-input-witness.json) не участвует в построении ответа.
- Число с kg известно, но единица неквалифицированного backend-поля weight не доказана. Исходный пример 12.3kg в HTML не считается контрактом: обработчик заменяет его сырым значением поля. Для поля weightGrams преобразование, напротив, определено именем.
- foodType/магазин/блюдо зависят от ещё не восстановленных цепочек jQuery DOM. В исходнике есть проверка indexOf('Train') как булевого значения; её нельзя заменять предполагаемым намерением пользователя. Перенос подготовки формы и выбор строки S7 остаются неполными.
- Ветви создания контакта и запросы по внешнему ключу нового аккаунта остаются неоднозначными. Случайный UUID не объявляется отличным от любых старых значений ради снижения счётчика. Расширение несовместимых состояний видно в unknown_tables и предупреждениях.
- В S6 при буквальном имени Ning Bo создание станции сохраняет пробелы/регистр, а конструктор Trip нормализует конечную станцию в ningbo. Последующий точный поиск станции и проверка маршрута расходятся; анализ получает getTickets failed. При таком связывании ID нового заказа для оплаты не возникает. Это результат модели с указанным буквальным связыванием, не runtime-трасса и не доказательство, что все допустимые трактовки сценария завершаются одинаково.
- Поле trainType у TransferTravelInfo присутствует в DTO, но текущий обработчик его не читает. Значение остаётся неизвестным; это не равнозначно неизвестности всего графа.

## Семантические границы

Не полностью поддержаны property-access JPA, custom generators/codecs, validation/security, conditional beans, транзакционный rollback/dirty checking, произвольные фильтры и их регистрация/порядок, URI encoding/custom template handlers, Java reference/boxed/floating-point semantics и произвольные SQL/JS конструкции. Модели не должны считаться полными только потому, что конкретная проверка прошла. Сложные Profile, методные перехватчики, пользовательские кодеки/HTTP error handlers и эвристическое сопоставление host с модулем отмечаются явно.

Точный locale/timezone и момент внутри дня не заданы полностью; numeric formatting использует ограниченную модель, а календарный день контекста представлен началом дня. Date.toString хранится как абстрактная строка с известной формой; путь с ней предполагает стандартное обозначение зоны и отмечается как приближение. Семантика сверялась с [JDK Date](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/Date.html#toString()) и [Hibernate UUIDGenerator](https://docs.hibernate.org/orm/5.4/javadocs/org/hibernate/id/UUIDGenerator.html).

Все восемь сценариев partial. confirmed означает доказанность внутри заявленной модели и конкретных привязок; это не запись настоящего запуска. Полные основания каждого ребра, параметры, условия и альтернативы сохранены в analysis-report.json. Ни S0, ни 489 тестов не доказывают универсальность.
