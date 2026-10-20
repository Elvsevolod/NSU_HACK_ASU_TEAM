# Реализация solution_29_next_steps_review.md — решение № 30

Родитель № 29 сохранён. Выполнены ограниченные C1/C2 и самостоятельные S1/S2, усилены проверки и воспроизведены три дополнительных риска. Итерация завершается на оговорённых в § 7 границах, а не заявлением готовности универсального анализатора. DeepSeek и внешние LLM API не использовались; целевые приложения не запускались.

## Изменения и подтверждения

HashSet хранит уникальные известные скалярные значения с Java equality: boolean/Integer/Long не смешиваются. Результат add, размер, contains/remove, null и копирование проверены. Порядок остаётся неизвестным через List, HTTP, массив и JSON; source hash/equals и неподдержанный порядок callback-потока имеют явную границу. В исходном TT Request пакет станций стал 2 вместо 12 записей, типов поездов — 3 вместо 6. Это не доказательство качества всего поиска.

Map proof проверяет каждый известный элемент без исполнения source callbacks и принимает только чистые, не бросающие false guards. В TT доказан no-op строки 219. Следующий цикл строки 242 содержит выполняемую else-ветвь и возможные удаления; перебор шести групп исчерпывает бюджет. Его успешное расширение не объявлено. Подробности и следующий NL Request: `benchmark/tt-frontier.json`. В независимом каталоге три товара проходят весь HTTP и NL переход до изменения выбранного ID и повторного чтения. Отсутствующая категория обнажила отдельный generic/List bulk boundary: неподдержанная коллекция больше не экспортируется как старый конкретный результат. Пустой TT результат с предупреждением budget не принимается за доказанную пустоту.

Angular callbacks привязаны к конкретному AST-вызову, DI и версии. `.success` получает response.data; `.then` не подменён этим контрактом. Обе цепочки Angular/jQuery создают JWT в исходном Java login и сами проводят его через storage и header. Проверены 401/403, соседние вызовы, затенение, замена сервиса и отключённый API. Actor выбирается до подготовки браузера; credentials и input journal принадлежат actor. Admin без подтверждённых credentials не заимствует пароль passenger. Роль admin/administrator имеет один namespace. Повтор одинакового свидетельства не считается конфликтом, противоречивые источники не разрешаются выбором последнего. На TT сохранены все 9 login frames: source admin UI пишет admin keys; client_token из них не выдуман.

Парная formatter абляция воспроизвела потерю Owner.id. Контракт default Spring ToStringCreator сохраняет сторонние поля, исполняет source getters/toString, их изменения и исключения. Стили и значения вне модели явно ограничены. Реальный Petclinic обновляет прежний ID 1 с нужными полями, сохраняет ровно две строки и перечитывает результат. Старые legacy oracle сохранены; v2 отдельно исправляет source logging edges и Piggy HTTP 400/error-handler. Строгий Piggy 8+3 остаётся регрессионным контролем, а не новым holdout.

@Procedure getNextNumber, @Modifying и source default-method не признаются чтениями по имени. Удаление из этого правила @Override/простого разобранного SELECT оказалось излишне консервативным: стадии E2/G сохраняют эту потерю; H восстанавливает положительное доказательство таких чтений. Functions, multi-statement SQL и неизвестные настройки остаются возможными записями. DTO absence proof отказывает при alias/escape/capture; singleton join сохраняет alias receiver↔cache. Контрпримеры до исправлений сохранены.

## Что остаётся непроверенным или не пройдено

Новый публичный профиль корзины — commit `64273c71575d61db8de6ba1a582b02f6a11103b3`. Входы и предварительный source oracle зафиксированы до первой интерпретации и до настройки под профиль. Сохранена подготовительная ошибка форматирования SQL и её семантически равная правка до Engine. План содержит три платежа, два заказа, две позиции, refund→remote order revert→reread, повторный отказ и неоднозначность. Реальный перенос не пройден: первая библиотечная потеря — Stream.toList в persistence adapter. Не вставлялись ID, успешный auth, состояния или рёбра. Oracle содержит необходимые source edges, поэтому полнота графа/precision/IoU здесь **не измерены**, успех holdout не заявлен. Это явно отрицательный результат, допустимый по § 7 аналитики.

Точный UI payment body содержит только orderId/tripId. Изолированная проба с известным начальным заказом предсказывает внешнюю оплату с userId=null; полный HTTP контроль с userId идёт другим потоком. Оба отличаются от TT NL оплаты с ещё неизвестным orderId/tripId. Готовый заказ, предоставленный auth context Piggy и синтетический source JWT не выданы за восстановление всего пользовательского TT сценария.

Проверка document допускает документированную неполноту codec failure policy, требует её диагностику и строго сравнивает существенные известные значения/граф в заявленном пути. Полная JVM, все framework interceptors, произвольные пользовательские коллекции/equals, SQL и JavaScript не поддержаны. Native Set использует существующий ограниченный резерв продолжений: path_limit не означает ровно N результатов. Worklist/memoization не внедрён без отдельной проверки живой ветви.

## Проверки и измерения

1762 теста; строгие Piggy 8+3, 10+6 мутаций его проверяющих; document 17 мутаций; Petclinic и legacy-v2; многоэлементный inventory HTTP/NL и отрицательные случаи. Это локальная приёмка, не метрика скрытого качества. `development/requirements.json` связывает каждый пункт с доказательством. Witness: исходный Request → actual args → result/exception → DB/browser/bean delta → следующий Request → per-step четыре отношения. Источник токена при возврате к actor ссылается на его настоящий ранний login; неизвестный heap старых TT traces не выдуман.

Все 103 шага сопоставлены по entry, wire/actual args, результату, состоянию и четырём типам рёбер; полные трассы и hash witnesses сохранены. Rank ContractIndex не менялся; общий scheduler/path budget не менялся. Стадия E упала на nullable receiver metadata; ошибка, исправление E2 и окончательное H сохранены. Стадии раздельны, сочетание также измерено.

| Стадия | SHA ответа (префикс) | Исходы / ошибка |
| --- | --- | --- |
| C1-C2-S1-S2 | 1a5f48620fb8 | {'returned': 194, 'uncaught application exception': 208, 'analysis completion budget exhausted': 542, 'HTTP binding failure': 2, 'unsupported_semantics boundary': 8} |
| C1-scalar-hashset | b30e667181c5 | {'returned': 193, 'uncaught application exception': 195, 'analysis completion budget exhausted': 533, 'HTTP binding failure': 2, 'unsupported_semantics boundary': 4} |
| C2-noop-map-filter | 1a5f48620fb8 | {'returned': 193, 'uncaught application exception': 195, 'analysis completion budget exhausted': 533, 'HTTP binding failure': 2, 'unsupported_semantics boundary': 4} |
| E-effects-and-order-boundaries | — | 1 |
| E2-effects-and-order-boundaries | 17854fb6585e | {'returned': 194, 'uncaught application exception': 208, 'analysis completion budget exhausted': 542, 'HTTP binding failure': 2, 'unsupported_semantics boundary': 8} |
| F-formatter-effects | 1a5f48620fb8 | {'returned': 194, 'uncaught application exception': 208, 'analysis completion budget exhausted': 542, 'HTTP binding failure': 2, 'unsupported_semantics boundary': 8} |
| G-final | 17854fb6585e | {'returned': 194, 'uncaught application exception': 208, 'analysis completion budget exhausted': 542, 'HTTP binding failure': 2, 'unsupported_semantics boundary': 8} |
| H-source-proven-read-effects | 1a5f48620fb8 | {'returned': 194, 'uncaught application exception': 208, 'analysis completion budget exhausted': 542, 'HTTP binding failure': 2, 'unsupported_semantics boundary': 8} |
| S1-angular-legacy | 1f634b961b98 | {'returned': 193, 'uncaught application exception': 195, 'analysis completion budget exhausted': 533, 'HTTP binding failure': 2, 'unsupported_semantics boundary': 4} |
| S2-actor-credentials | 1f634b961b98 | {'returned': 194, 'uncaught application exception': 208, 'analysis completion budget exhausted': 542, 'HTTP binding failure': 2, 'unsupported_semantics boundary': 8} |
| base | 1f634b961b98 | {'returned': 193, 'uncaught application exception': 195, 'analysis completion budget exhausted': 533, 'HTTP binding failure': 2, 'unsupported_semantics boundary': 4} |
| fair-base | 1f634b961b98 | {'returned': 193, 'uncaught application exception': 195, 'analysis completion budget exhausted': 533, 'HTTP binding failure': 2, 'unsupported_semantics boundary': 4} |

Локальный S0: 0.8008928571; IoU E/C/R/D: 0.828571/0.625000/1.000000/0.750000. Remote gold пуст; эта единица не является положительной remote-проверкой. Формат S0–S7 корректен.

Python 3.11.9. Полное время 85.148 с; подготовка 6.404 с; расчёт 67.300 с; запись отчётов 11.410 с; RSS 451428352 байт. Повтор на одном готовом индексе: 55.944 / 54.957 с, ответы byte-identical. Старое поле analysis_seconds включало сериализацию; для честного сравнения baseline повторён с той же инструментализацией (fair-base). Числа описывают локальные прогоны без согласованного SLA и статистического доказательства ускорения.

SHA ответа: `1a5f48620fb8e840f17903b78bfff037cf88191f888a452dc609f6970789731a`. `offline_run.py` блокирует network/process/reference reads. Все 19654 защищённых файла проверены; Finder metadata отмечается отдельно. Исторические абсолютные команды сохранены как данные; действующие команды в README относительные.

## Воспроизведение

Из корня варианта, с тем же tt-challenge:

```sh
python -B code/offline_run.py --source ../../tt-challenge/targets/trainticket --skeleton ../../tt-challenge/skeleton/trainticket.json.gz --context ../../tt-challenge/context --scenarios ../../tt-challenge/scenarios --output /tmp/answer30.json --report /tmp/report30.json
PYTHONPATH=code python -B -m pytest -q code/tests
python -B checks/run_document_journey.py --output /tmp/documents30
python -B checks/check_document_mutations.py --input /tmp/documents30
python -B checks/run_cart_profile.py --output /tmp/cart30
python -B checks/check_cart_profile.py --trace /tmp/cart30 --output /tmp/cart30-check.json
```

Зависимости — requirements.txt. Полный source review и code.patch находятся в development. Новая посылка, её извлечённый replay, сайт и восстановление лучшего результата фиксируются отдельно в benchmark; получение оценки не изменяет уже отправленный ZIP.

## Сайт и зафиксированная посылка

Посылка **1665671**, A, **0,37269**; к № 29 **+0,01155**, к лучшему № 5 **−0,53718**. S6 снизился на **0,00801283**, S5 не изменился; все точные сценарные оценки и дельты в benchmark/site-score.json. Серверный ZIP совпал по всем байтам; распакованный replay воспроизвёл восемь ответов и 1762 теста. Оценённый архив не пересобирался. В зачёт восстановлен неизменный № 5, посылка **1665676**, A, **0,90987**, рейтинг **0,909870**; серверная копия также совпала. Это наблюдения сайта, не доказательство качества значений или универсальности.
