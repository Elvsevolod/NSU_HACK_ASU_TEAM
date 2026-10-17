# AGENTS.md — вход для агента

Рабочая папка нашей команды — `solutions_G/`. Новые варианты создаются и ведутся **только** в ней.

Начни с `solutions_G/README.md` — там маршрут чтения. **Правила, ограничения и принципы собраны в одном месте — `solutions_G/docs/hackathon-rules.md`; здесь они не повторяются, но действовать нужно строго по ним.**

## Стартовый промпт для нового агента

> Работаем только в `solutions_G/`. Первым делом прочитай `solutions_G/README.md` и пройди маршрут чтения из него, начиная с `solutions_G/docs/hackathon-rules.md`. Действуй строго по правилам и процедуре оттуда. Новые идеи не реализуй сразу — сначала запиши в `solutions_G/docs/ideas.md` и дождись отбора.

## Карта репозитория

- `tt-challenge/` — сам кейс: краткое ТЗ `README.md`, справочник `REFERENCE.md`, исходники `targets/trainticket/`, скелет-граф `skeleton/trainticket.json.gz`, сценарии `scenarios/S0–S7.json`, открытый эталон `gold/S0.json`, состояние баз `context/`, программы-примеры `platform/baseline_*.py` и образцы ответов `examples/*.json`. Только чтение.
- `sample/` — образец посылки организаторам: `README.md` с форматом отправки, `submission.json` и `code/`. Показывает, как выглядит архив: `submission.json` обязательно в корне. Только чтение.
- `skills/` — наши кастомные скиллы проекта: `solution-versions` (ведение вариантов), `s0-check` (проверка варианта), `submission-pack` (сборка посылки). Подключены через `opencode.json` (`skills: ["./skills"]`), загружаются по требованию.
- `solutions/` — общие варианты решения, заполняются строго по `skills/solution-versions/SKILL.md`. Сводная таблица — в `solutions/README.md`.
- `solutions_G/` — наша рабочая папка: варианты команды G и их документация.
- `AGENTS.md` — этот файл.
