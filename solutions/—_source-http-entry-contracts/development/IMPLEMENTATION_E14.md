# Проверенный этап E14

Рабочий отчёт: `solution_31_models_and_static_analysis_review.md`, SHA256 `4a1c9f985808aacd4e35816d028779586407c13bf74f938df14a71b859a29592`. Родитель №32 и ранее поставленные архивы не менялись. Цель R01–R08 остаётся активной.

## Исполнение и транспорт

E8 добавил явный Feign URL, scoped placeholders, путь клиента и ограниченную стандартную привязку query. Проверены URI encoding, повторные значения, null/empty и порядок finite List. Source interceptor исполняется до отправки. Неизвестные converters, registration и transport policies остаются границами.

E9 заменил field projection ответа Feign на существующий JavaBean lifecycle. Исполняются исходные setters и default constructor; reflection-only getters/constructors исключены из экспортируемых рёбер по контракту организаторов. Успех нельзя продолжить после отказа декодирования. Native Boot defaults применяются при доказанной аннотации; custom/opaque codec beans и неподтверждённые overrides останавливают декодирование. Default DecodeException — runtime-ошибка Feign, а не исходный Jackson IOException.

E10 разрешает короткое имя класса builder по исходникам, не по непроверенному spelling скелета. Native Lombok annotation отделена от namesake; build сохраняет shared references и native scalar kinds. Custom builders, generics/inheritance, field initializers, Singular, NonNull и Builder.Default остаются за пределами проверенного subset.

E11 сохраняет canonical decimal String от non-null native integral символа в исходной конкатенации и сообщении исключения. Spring HttpStatus.value() возвращает int; одноимённый source enum вызывает свой метод. В двух старых Java fixtures отсутствовали импорты HttpStatus; добавлены реальные импорты, строгие assertions сохранены.

E12 переносит сообщение default Feign error в source Throwable.getMessage() как String с происхождением от конкретного запроса и ответа. Буквальные bytes, charset/reason/body truncation не выдумываются. E13 устраняет расхождение digest с сериализованной датой. Новые request/SQL witnesses содержат native kinds и request ID.

При E10 обнаружен откат TT S4: чрезмерный запрет любого source constructor исключил generated AllArgsConstructor при наличии отдельного no-arg constructor. В E14 самостоятельный пример доказывает, что builder не запускает no-arg body. Разрешён доказанный native AllArgsConstructor с другой source-сигнатурой. Все три потерянных ребра S4 восстановлены. Промежуточные результаты E10–E13 сохранены как реальные откаты, не переписаны.

Контракты сверены с [Lombok Builder](https://projectlombok.org/features/Builder), [Constructor](https://projectlombok.org/features/Constructor), исходниками [Feign 10.10.1](https://github.com/OpenFeign/feign/blob/10.10.1/core/src/main/java/feign/FeignException.java), [13.5](https://github.com/OpenFeign/feign/blob/13.5/core/src/main/java/feign/FeignException.java), SpringDecoder/ResponseEntityDecoder и Boot JacksonAutoConfiguration. Локальные source receipts — `feign-wire-preflight`, `feign-decoder-preflight`; Context7 использован для правил Lombok/Spring. Целевые Java приложения не запускались.

## Проверки и ограничения

E14: 2319 тестов кода, 158 checker tests и все 17 integration runs проходят. TT: S0 `0.8008928571428572`, format errors/warnings пусты. Все восемь answers снова совпадают с E7; SHA256 `95927fa5eb50b7d9f26d13a1c9e224bb2b803a9a6b07aa1c42996beaa15c371d`. Измеренный TT run: 47.61546475000068 s до последней записи, подготовка 7.563195249997079 s, анализ 28.272921249983483 s, peak RSS 523976704 bytes. Это наблюдение данного запуска, без обещания ускорения или hidden site score.

Для двух новых приложений исходный graph/state oracle заморожен до inference. Дополнение typed wire/SQL/origin checker подготовлено после просмотра semantic outcomes; expected values взяты из исходного oracle, input recipes и source, а не predictions. Оно честно помечено как development extension. Original oracle, inputs и старые traces не менялись. Негативные controls отклоняют неверный remote kind, SQL order, history digest, лишний response и не связанное с транспортом сообщение ошибки. Исторические cart/document checkers принимают новое kind-поле только после его проверки, сохраняя все прежние value/type обязанности.

| Явные HTTP controls | Прошло |
| --- | --- |
| employment: state chain + fresh state + remote error | 10/11 |
| healthcare: state chain + fresh state | 11/11 |

Эти проверки включают каждый alternative E/C/R/D, полные persistent rows, точный внешний wire, порядок remote сообщений и actual encoded responses, Long kinds, ordered SQL и complete agreeing history producer. Healthcare проходит повторный отказ и удалённую ошибку. Employment останавливается на неизвестном исходном handler отсутствующего маршрута существующего сервиса: default MVC 404 ещё не доказан. Полного transfer claim нет: это заявленный synchronous AOP-disabled slice; второго независимого автора oracle и exact framework error bytes нет.

Семантика A/B одна и та же E14. Employment NL: baseline EN0/13, RU2/13; lexical EN2/13, RU2/13. Healthcare: baseline EN1/13, RU2/13; lexical EN2/13, RU2/13. Индивидуальная удачная привязка не считается завершённой цепочкой.

## Новое сравнение retrieval

На ранее замороженных 40 запросах двух новых приложений сравнили общий Unicode BM25 и ранее выбранный CodeRank, без смены модели/thresholds по test. Corpus — 119 source handlers. CodeRank R1/R3/R6: 13/32, 19/32, 27/32, MRR 0.5453519571. BM25: 6/32, 11/32, 22/32, MRR 0.3699714782. У обоих accept0/40, false reject32/32, false accept0/8. Ранжирование улучшилось, калиброванного использования на новой области нет; default-модель по-прежнему отклонена.

CodeRank фактически запущен offline на MPS fp32: load1.5519240420 s, index0.4870207920 s, query0.6864697920 s, RSS1492516864 bytes. Cache123 hits/68 misses: 28 новых source documents и 40 новых queries потребовали forward. Всего51 forward batches, включая smoke и три отдельно измеренных warm forwards. MPS allocated555165696/driver1118617600 bytes; эти значения не складываются с RSS как независимые физические области. Первый sandboxed MPS preflight упал до query inference, разрешённый локальный повтор выполнен. Network/process/labels audit counters = 0. Другие три модели сохраняют ранее измеренный пилот и повторно не запускались.

## Доказательства и следующий шаг

[Stage diffs и causal review](transport-review-e14/review.json), [точные transport checks](transport-checker-e14/checks.json), [A/B lexical](transport-checker-e14-lexical/checks.json), [retrieval evaluation](../benchmark/real-retrieval-evaluation.json).

Далее: доказать default absent-route dispatch с отказом при custom policies; разобрать NL binding/history/refusal по шагам. Модель не может заменить недостающий producer или подтвердить выполнение. Новые наблюдавшиеся приложения теперь development для последующего tuning. На сайт и в remote repository ничего не отправлялось.
