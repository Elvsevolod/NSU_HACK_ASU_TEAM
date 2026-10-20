# Решение №31 — typed-collection-continuations

Родитель №30. Реализованы source-derived коллекции/consumer types, Stream.toList/Optional, MVC/PATCH/reduce и полная корзина с переносом состояния. TT живой фильтр пройден; полная TT NL-цепочка остаётся частичной. [Результаты всех18 целей](FINAL_REVIEW.md), [воспроизведение](REPRODUCE.md), [ограничения](LIMITATIONS.md).

| Показатель | Значение |
| --- | --- |
| Score сайта | 0.39232 (verified) |
| Тестовый score S0 | 0.8008928571428572 |
| S0: executes / calls / remote / data IoU | 0.8285714285714286 / 0.625 / 1.0 / 0.75 |
| Формат S0–S7 | Пройден, все8 ответов,103 шага |
| Время построения ответа | Локально Python3.11.9: расчёт65.667с, полный цикл89.396с |
| Peak RSS | 557957120байт, Darwin raw bytes |
| Проверки | 1955 passed; real-source и synthetic gates с разной областью oracle |

Запуск из этой папки после установки requirements в отдельную среду:

```sh
python -B code/offline_run.py --source ../../tt-challenge/targets/trainticket --skeleton ../../tt-challenge/skeleton/trainticket.json.gz --context ../../tt-challenge/context --scenarios ../../tt-challenge/scenarios --output /tmp/answer31.json --report /tmp/report31.json
```

SHA ответа: `25996b7d3d6d20590934c4cc70b3305046ec3cd686b41465021b84fbf032a977`. Сайт: 0.39232, статус verified, посылка 1665875. Восстановление №5: verified, посылка 1665877.

Код/ответ/judge ZIP после оценки неизменны. README внутри judge ZIP — отдельный pre-site snapshot; workspace docs обновляются по фактическому verdict. Моделей/внешних LLM API/DeepSeek нет. Полные target sources TT намеренно не дублируются; exact input manifest прилагается. Пустой S0 remote не является remote validation.
