# Этап E7: числовой ID через HTTP

Создание объекта в обоих новых проектах сохраняло fresh Long ID, но следующий запрос терял его при стандартной HTTP-привязке. Исправлен общий мост native integral value → canonical decimal String → same-width Spring named-value conversion. Никакое конкретное число не подставляется. Symbolic identity, ограничения свежести и сценарная изоляция сохраняются; source namesakes, nullable/opaque values, другой разряд и custom conversion не объявляются точными.

До patch 24 из 30 независимых проверок падали. После изменения все 30 проходят; полный набор — 2180 code tests, 117 checker tests и 17 integrations. Ответы TT/S0–S7 не изменились, S0 — 0,8008928571428572. [Измеренный stage](../benchmark/stages/E7-integral-http-identity/summary.json), [patch и парное сравнение](integral-http-review/review.json).

Для employment и healthcare до первых предсказаний заморожены source/config/graph/initial-state inputs и 23 сценария с 74 шагами. Oracle задаёт полные E/C/R/D и persistent rows в явно выбранном синхронном deployment slice. Generated IDs параметрические; AOP и open-in-view явно отключены во входном окружении. Это не запуск приложения и не полный oracle всех возможных framework deployments. Точные bytes framework error message/time ограничены; второго автора разметки нет.

По одному исправленному checker explicit controls выросли с 6/11 до 9/11 в employment и с 2/11 до 6/11 в healthcare. Сами state chains — 8/9 и 5/10; ещё по одному шагу проверяют независимое исходное состояние. Отдельный employment remote-error control не прошёл. Нужны Feign explicit URL/placeholders/query, source error advice/completion и typed wire/order/origin witnesses. Эти данные уже просмотрены и для последующего tuning считаются development.

Checker исправлен отдельно: request1 исключён из outbound count; write policy проверяет ожидаемые method/table/operation и certainty в каждой альтернативе. Сохранились первичные проверки, отдельный пересчёт и отрицательные контроли с missing write только в одной ветви. Frozen oracle, строки входа и saved analyzer predictions не изменялись.

Модель по умолчанию остаётся отклонённым экспериментом. Новых запусков моделей на двух новых приложениях пока нет; прежние четыре локальных пилота сохранены. Цель R01–R08 активна, full semantic transfer не подтверждён. Старые E2/E4/E6 архивы не перезаписываются.
