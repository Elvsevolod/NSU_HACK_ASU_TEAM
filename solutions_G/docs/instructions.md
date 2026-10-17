# Инструкции: процедура ведения варианта

Как создать, запустить, проверить и записать вариант в `solutions_G/`. Рамка работы (что можно и нельзя, язык, профиль, принципы) — **только** в [hackathon-rules.md](hackathon-rules.md); здесь она не повторяется.

## Шаг 1. Выбрать идею

Возьми **одну** идею из [ideas.md](ideas.md). Если список пуст — новых идей нет: сначала обсуди идею и запиши её.

## Шаг 2. Создать вариант

- Путь: `solutions_G/—_<feature>/`, номер следующий по порядку.
- Состав, имя и бенчмарк — по [SKILL.md](../../skills/solution-versions/SKILL.md).
- Код родителя, если он есть, копируется **снимком** в `code/`; корневой вариант (без родителя) пишется с нуля. Изменяемый код другого варианта не импортируется в любом случае.
- Создание варианта **не** означает отправку на сайт.

## Шаг 3. Внести изменение

Держи изменение в границах одной идеи: одна идея — один вариант.

## Шаг 4. Запустить

Команды выполняются из папки варианта. Нужен исходный пакет организаторов; при другом расположении замени пути. **Готовая команда зависит от того, на чём строится вариант**: у варианта с родителем она в README родителя, у корневого — в README варианта или из примера ниже. Пример для линии № 5:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -B code/run.py \
  --source ../../tt-challenge/targets/trainticket \
  --skeleton ../../tt-challenge/skeleton/trainticket.json.gz \
  --context ../../tt-challenge/context \
  --scenarios ../../tt-challenge/scenarios \
  --output submission.json \
  --report benchmark/analysis-report.json
```

На Windows задай `PYTHONUTF8=1` (в сценариях есть U+2014, системная кодировка cp1251 ломает чтение) и `PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1`.

## Шаг 5. Проверить

```bash
# Локальный S0 по открытому эталону
.venv/bin/python -B ../../tt-challenge/platform/evaluate_golden.py \
  ../../tt-challenge/gold/S0.json submission.json --json
# Формат S0–S7 (код возврата 3 — ожидаемый режим format_only)
.venv/bin/python -B ../../tt-challenge/platform/evaluate_golden.py \
  --check ../../tt-challenge/skeleton/trainticket.json.gz submission.json --json
```

Критерий зависит от вида варианта:

- **Структурный рефактор** — ответ **байт-в-байт** как родитель (сверь `submission.json` по всем сценариям).
- **Изменяющий ответ** — байт-в-байт не требуется и невозможен: ответ **обязан измениться**, иначе изменение ничего не дало. Сравнивай с родителем по каждому сценарию и виду связи.
- **Корневой вариант (без родителя)** — сверять побайтово не с чем: критерий это новый `submission.json`, локальный S0, формат-чек и тесты.
- Тесты: `PYTHONPATH=code .venv/bin/python -B -m pytest code/tests -q` (нужен `pytest==9.1.1`).

## Шаг 6. Записать результат

- README варианта — бенчмарк (по `SKILL.md`).
- [results.md](results.md) — строка с номером, фичей, родителем, score сайта, S0, изменением вывода, тестами, датой.
- `benchmark/` — сохранённые отчёты проверок; `code/` — снимок кода.
- [ideas.md](ideas.md) — обновить статус использованной идеи.

## Оценка сайта

Ставится только по факту, из предоставленного скриншота (принцип 6 в [hackathon-rules.md](hackathon-rules.md)). Порядок записи, хешей и переименования папки — в [SKILL.md](../../skills/solution-versions/SKILL.md).
