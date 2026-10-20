# Решение № 30 — collection-value-flow

Родитель № 29. Ограниченные HashSet/Map proof, source Angular callback, actor-owned credentials/state, formatter/effects и строгие проверки. Подробности и оставшиеся границы: [IMPLEMENTATION_REVIEW.md](IMPLEMENTATION_REVIEW.md), [карта требований](development/requirements.json).

| Показатель | Значение |
| --- | --- |
| Score сайта | **0,37269**; 1665671, A; Δ к № 29 **+0,01155** |
| Тестовый score S0 | 0.8008928571 |
| S0: executes / calls / remote / data | 0.828571 / 0.625000 / 1.000000 / 0.750000 (remote gold пуст) |
| Формат S0–S7 | Корректен |
| Время построения ответа | 85.148 с локально, Python 3.11.9; расчёт отдельно 67.300 с |

1762 теста. Строгие Piggy 8+3 и отрицательные контроли пройдены; Petclinic сохраняет ID/поля/число строк. Новый независимый cart profile не пройден: Stream.toList. TT поиск остаётся частичным на следующем Map-цикле; полного сценария бронирования и универсальности не заявлено. DeepSeek, модели и внешние LLM API не использовались. Исследуемые приложения не запускались.

Из этой папки:

```sh
python -m pip install -r requirements.txt
python -B code/offline_run.py --source ../../tt-challenge/targets/trainticket --skeleton ../../tt-challenge/skeleton/trainticket.json.gz --context ../../tt-challenge/context --scenarios ../../tt-challenge/scenarios --output /tmp/answer30.json --report /tmp/report30.json
```

SHA-256 submission.json: `1a5f48620fb8e840f17903b78bfff037cf88191f888a452dc609f6970789731a`. Сайт и S0 — разные оценки. Посылка solution.zip сохраняется неизменной после отправки; новые метаданные сайта находятся рядом в benchmark.

Серверная копия совпала с отправленным ZIP по всем байтам. В зачёт возвращён неизменённый № 5: **1665676, A, 0,90987**, рейтинг **0,909870**. [Метаданные и скриншот](benchmark/site-score.json). Внутренний оценённый solution.zip сохранён без пересборки; его README создан до получения score.

| Сценарий | Score сайта | Δ к № 29 |
| --- | --- | --- |
| S1 | 0.39526557 | +0.01669393 |
| S2 | 0.32566251 | +0.01643251 |
| S3 | 0.40794947 | +0.01923918 |
| S4 | 0.34674073 | +0.01720999 |
| S5 | 0.29841313 | +0.00000000 |
| S6 | 0.43871457 | -0.00801283 |
| S7 | 0.39611448 | +0.01933700 |
