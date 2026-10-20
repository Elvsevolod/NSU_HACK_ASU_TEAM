# Этап E6: source Feign interceptors

Исправлено пропущенное исполнение source RequestInterceptor. Проверенная регистрация Component/Bean приводит к вызову `apply`; обычные source calls внутри callback сохраняются, а framework dispatch не создаёт выдуманного `calls` от бизнес-метода к interceptor. `@Value` берётся из конфигурации соответствующего Boot deployment. Состояние bean переносится между запросами одного сценария и изолируется между сценариями.

Native RequestTemplate поддерживает header/removeHeader по сохранённому Feign 10.10.1: регистр имени не влияет на поиск, значения добавляются с устранением дублей, пустой Iterable удаляет заголовок, null String[] бросает NPE. Неподдержанные операции останавливают запрос до отправки. Порядок нескольких callbacks исследуется альтернативами в прежнем бюджете; `@Order` не выдаётся за доказанный порядок старого FactoryBean.

Регистрация ограничена default Boot scan и доказанными native аннотациями. Неизвестные lifecycle, constructors/injection, условная регистрация, custom scope/configuration и mixed OAuth/source order остаются границами. Исправлены отдельные контрпримеры с Profile у Bean factory, повторяющимися слешами path и null overloads. [Исходники framework](feign-interceptors-preflight/sources.json), [полный patch и причинный разбор](feign-interceptors-review/review.json).

54 targeted tests, 2150 code tests, 76 checker tests и 17 интеграционных запусков проходят. S0 — 0,8008928571428572; все восемь ответов TT совпали с E2–E5. E6: 45,99889783300023 с до последней записи отчёта, peak RSS 519684096 байт; [полные измерения](../benchmark/stages/E6-feign-registration-controls/summary.json).

Library теперь передаёт source-configured lms-key в Inventory. Следующая остановка — неподдержанный derived predicate по составному ID. Полная цепочка пока не проходит: partial checks organization explicit5/10, NL1/10, Library0/11 остались прежними. Эти числа не являются full IoU.

До новых предсказаний закреплены employment и healthcare: новые public source revisions, graph/config inputs, RU/EN queries и независимые graph/state expectations. Full transfer ещё не проверен. Формат generated IDs параметрический, AOP в тестовом окружении явно отключён, точные bytes framework error text/time ограничены. [Freeze](semantic-holdouts-frozen-v1/freeze.json). Веса четырёх моделей уже проверялись; подключение модели по умолчанию остаётся отклонённым из-за отсутствия downstream выигрыша.
