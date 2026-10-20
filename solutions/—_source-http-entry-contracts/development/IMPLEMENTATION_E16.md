# E15–E16: буквальное JSON-тело в NL

После E14 правильный create-handler выбирался, но строковые поля из JSON превращались в `: `, а числа пропускались. E15 выделяет единственный завершающий JSON-объект после двоеточия или знака равенства, сохраняет его целиком и передаёт обычному HTTP/Jackson binder. Параметры пути извлекаются из текста перед телом. Для UI и неоднозначного field-labelled объекта такой обход не применяется. Повторяющиеся ключи, неоднозначные тела, невалидный JSON и числа вне конечного диапазона дают явный отказ.

До исправления 13 исходных контрпримеров падали. Дополнительный overflow-контроль тоже упал до проверки конечности числа. Первая полная проверка E15 нашла конфликт введённого локального имени с существующей переменной UI; имя исправлено, прежние UI assertions сохранены. Финальный E15: 2335 code tests, 158 checker tests, 17 integrations. Артефакты первой неудачной и последующих проверок сохранены отдельно.

E16 устраняет вторую потерю: обычный dict терял порядок JSON-токенов и позволял служебным именам данных выглядеть как внутренний символический Long. JSON теперь имеет собственный JsonObject carrier, который сохраняется при freeze/thaw неизменяемого Request. Четыре новых контрпримера падали на E15; после исправления проходят обе последовательности эффектных setters и оба metadata-name контроля. Входы, oracle и проверочные assertions не ослаблены.

Финальные выполненные проверки E16:

- `benchmark/json-wire-ownership-full`: 2339 passed.
- `benchmark/json-wire-ownership-checker`: 158 passed; warning относится к намеренному duplicate ZIP negative control.
- `benchmark/json-wire-ownership-integration/results.json`: все 17 запусков passed.
- `benchmark/stages/E16-json-wire-ownership`: 48,30534075000469 с, peak RSS 524222464 bytes, все восемь ответов TT совпали с E14, SHA256 `95927fa5eb50b7d9f26d13a1c9e224bb2b803a9a6b07aa1c42996beaa15c371d`.

В `development/stages/E15-inline-json-body` и `E16-json-wire-ownership` сохранён измеренный код. Точные команды и hashes — в соответствующих `run.json`; before-контроли — в `benchmark/inline-json-*`.

Полный transport gate не подменяется числом прошедших unit tests. На неизменённых новых проектах E16 A/B по строгому checker: employment explicit10/11, NL baseline0/13 EN и2/13 RU, lexical2/13 в каждом языке; healthcare explicit11/11, baseline1/13 EN и2/13 RU, lexical2/13 в каждом языке. Семантические значения первого JSON create-step теперь точны, но wire содержит явно неизвестный остаток заголовков. В NL history также наблюдаются эквивалентные ID через created_objects вместо ожидаемого response path; строгий transport checker это не засчитывает. Неизвестность не закрывалась выдуманными заголовками и ожидаемый oracle не менялся.

Дальнейшая отдельная работа: источник и полная история как основание выбора singular-read при отказе lexical ranking; default missing-route dispatch остаётся границей. Эти проверки не являются новой untouched оценкой переноса: проекты уже наблюдались и теперь development. Модель и frozen thresholds не менялись; DeepSeek/API/целевые JVM не запускались.
