"""Document only saved measurements after the checked complete run."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / 'solutions/—_request-state-linking'
B = V / 'benchmark'
X = Path(__file__).parent
summary = json.loads((B / 'summary.json').read_text())
evaluation = json.loads((B / 'evaluation.json').read_text())
report = json.loads((B / 'analysis-report.json').read_text())
audit = json.loads((B / 'binding-audit.json').read_text())
baseline = json.loads((X / 'baseline-audit-final.json').read_text())
parent = json.loads((ROOT / 'solutions/—_predicate-state-analysis/benchmark/summary.json').read_text())
fifth = json.loads((ROOT / 'solutions/0.909870_field-constructor-projection/benchmark/evaluation.json').read_text())
tests = ET.parse(B / 'pytest.xml').getroot()
suite = list(tests)[0] if tests.tag == 'testsuites' else tests
assert suite.attrib['failures'] == '0' and suite.attrib['errors'] == '0'
test_count = int(suite.attrib['tests'])
assert test_count == 129
assert summary['score_S0'] > fifth['score'] and summary['run_complete']
assert summary['submission_sha256'] == hashlib.sha256((V / 'submission.json').read_bytes()).hexdigest()
for source, name in [('delegation-review.json', 'deepseek-review.json'),
                     ('deepseek-final-model-evidence.json', 'deepseek-model.json'),
                     ('baseline-audit-final.json', 'parent-binding-audit.json')]:
    shutil.copy2(X / source, B / name)


def unknown_steps(block):
    return sum(any(any(w.startswith('Unknown input: ') for w in a['unresolved'])
                   for a in s['alternatives']) for s in block['steps'])


old_report = json.loads((ROOT / 'solutions/—_predicate-state-analysis/benchmark/analysis-report.json').read_text())
per_scenario = {sid: {'before_unknown_steps': unknown_steps(old_report['scenarios'][sid]),
                      'after_unknown_steps': unknown_steps(block), 'steps': len(block['steps']),
                      'status': block['analysis_status']} for sid, block in report['scenarios'].items()}
comparison = {'score_S0': summary['score_S0'], 'variant5_score_S0': fifth['score'],
    'delta_S0_vs_5': summary['score_S0'] - fifth['score'],
    'parent8_score_S0': parent['score_S0'], 'delta_S0_vs_parent8': summary['score_S0'] - parent['score_S0'],
    'unknown_steps_before': baseline['steps_with_absent_or_stored_unknown'],
    'unknown_steps_after': audit['steps_with_absent_or_stored_unknown'],
    'missing_field_occurrences_before': sum(baseline['absent_field_occurrences'].values()),
    'missing_field_occurrences_after': sum(audit['absent_field_occurrences'].values()),
    'field_occurrence_scope': audit['occurrence_scope'], 'scenarios': per_scenario,
    'seconds_parent8': parent['elapsed_seconds'], 'seconds_current': summary['elapsed_seconds'],
    'peak_rss_bytes_parent8': parent['peak_rss_bytes'], 'peak_rss_bytes_current': summary['peak_rss_bytes'],
    'tests_passed': test_count, 'site_score': None}
(B / 'comparison.json').write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + '\n')
rows = '\n'.join(f"| {sid} | {r['steps']} | {r['before_unknown_steps']} | {r['after_unknown_steps']} |" for sid, r in per_scenario.items())
text = f'''# Решение № 9 — request-state-linking

Родитель: № 8. Самостоятельный снимок переносимого анализатора Java/Spring на Python. Исправляет извлечение запросов JavaScript и привязку параметров, переносит типизированные результаты между шагами. Имена проектов, сервисов, маршрутов, бизнес-состояний и сценариев в правила не заложены; факты берутся из анализируемых исходников, скелета, контекста и действий.

Условие остановки выполнено: локальный S0 **{summary['score_S0']:.10f}** строго выше **{fifth['score']:.10f}** у № 5, разница **+{comparison['delta_S0_vs_5']:.10f}**. Относительно родительского № 8 прирост **+{comparison['delta_S0_vs_parent8']:.10f}**. Это измерения открытого S0; качество скрытых сценариев и score сайта неизвестны.

| Показатель | Значение |
| --- | --- |
| Score сайта | — (не получен) |
| Тестовый score S0 | {summary['score_S0']:.10f} |
| S0: executes / calls / remote / data | {summary['iou']['executes']:.10f} / {summary['iou']['calls']:.10f} / 1 / {summary['iou']['data']:.10f} |
| Формат S0–S7 | Проверен, без отклонений и дубликатов |
| Время построения ответа | {summary['elapsed_seconds']:.3f} с локально, все 103 шага |
| Подготовка индекса / анализ | {summary['preparation_seconds']:.3f} / {summary['analysis_seconds']:.3f} с |
| Пиковая RSS | {summary['peak_rss_bytes']} байт ({summary['peak_rss_bytes']/1024**2:.2f} МиБ) |
| Окружение | Python {summary['environment']['python']}, macOS 15.3.1, arm64 |
| Обращения к моделям при анализе | 0 |
| Тесты | {test_count} пройдено |

В S0 `remote=1` означает совпадение двух пустых множеств, а не проверку реальной межсервисной цепочки. Все восемь отчётов сохраняют статус `partial`: параметры могут быть определены, а семантика библиотек, ветвей или выбранного запроса — ещё приближённой. У № 8 полный прогон занимал {parent['elapsed_seconds']:.3f} с и {parent['peak_rss_bytes']} байт RSS; текущий вариант работает медленнее и использует немного больше памяти. Индекс строится один раз на все сценарии.

Изменения:

- Обёртки `this.helper(path, body)` связываются только внутри того же объектного литерала. Перекрытие имён и вложенные функции не смешивают запросы. Для анонимной стрелочной функции сохраняется имя действия внешнего метода.
- Маршрут сопоставляется по структуре полного URL: один динамический фрагмент занимает один сегмент. Известные параметры пути и запроса сохраняются, даже если другой фрагмент неизвестен. Учитываются `name`, `value`, необязательность и объявленное значение по умолчанию у HTTP-параметров.
- Присваивания под неизвестными условиями, вычисляемые свойства и неизвестные повторные присваивания снимают прежнее знание. Неполное тело не служит основанием считать свойства отсутствующими.
- Значения по умолчанию DTO применяются только к доказанно отсутствующим свойствам полного объекта. Пользовательские Jackson-десериализаторы и исполняемые конструкторы исключены из этого приближения. Ошибка преобразования типа остаётся неизвестным входом.
- История хранит результаты отдельно для каждого пути. Идентификатор связывается с типом объекта и объявленным полем; произвольный `String id` другого объекта не подходит. Поддержаны явные порядковые ссылки и различие между порядком создания и порядком списка. Неоднозначность и конфликт после объединения путей сохраняют неизвестность.
- Явные фильтры выводятся из простых методов DTO, присваивающих флаги и параметры, и из объявленных перечислений. Неопределённые или неоднозначные фильтры видны в диагностике. Ранжирование учитывает действие, источник UI и покрытие полей; оно остаётся эвристическим.

Счётчик шагов с неизвестными входами снизился **с 82 до {audit['steps_with_absent_or_stored_unknown']} из 103**. В S0 неизвестных входов нет. Число отсутствующих полей в первой альтернативе шага — **{comparison['missing_field_occurrences_before']} → {comparison['missing_field_occurrences_after']}**. Дополнительно проверяются неизвестные значения, уже записанные в параметры: раньше такие значения не всегда попадали в сообщение `Unknown input`. Символические входы в двух шагах считаются отдельно и не означают известного конкретного значения.

| Сценарий | Шагов | Неизвестные входы у № 8 | У № 9 |
| --- | --- | --- | --- |
{rows}

Все неизвестные входы устранить не удалось. Наиболее заметные пробелы: условные URL, назначаемые через переменные, цепочки событий HTML/DOM, выбор строк таблиц, регистрация и перенос новых пользователей. Часть действий покупки по-прежнему выбирает внутренний API из-за отсутствующей связи с UI. Сокращение неизвестных входов само по себе не доказывает правильность выбранного обработчика; S1–S7 проверены по формату и основаниям, без закрытого эталона.

Поддержка ограничена реализованными конструкциями Java/Spring и JavaScript; это не полная JVM или браузер. В частности, остаются пробелы в наследовании полей JPA, пользовательских кодеках Jackson, Bean Validation, сложных JS-алиасах, асинхронных событиях и некоторых библиотечных операциях. Подстановка исходных значений формы не заменяет понимание всех действий пользователя. В диагностике различаются возможные и подтверждённые в модели рёбра; даже подтверждение условно относительно выбранного контракта.

Проверка переносимости включает склад, библиотеку и два сервиса магазина/расчётов: состояние, ветвления, REST/data и независимость сценариев. Дополнительно проверен публичный [Spring Petclinic REST v2.1.5](https://github.com/spring-petclinic/spring-petclinic-rest/tree/v2.1.5), commit `2cd2f9c7a3eee55d7c6d09fa100e02341ae27070`: 78 Java-файлов, 5748 строк, 322 метода, 33 обработчика. Четыре проверки выбора обработчика и буквальных параметров прошли. Скелет для этой проверки построен отдельным тестовым генератором; полной оценки четырёх видов рёбер и цепочки состояния Petclinic нет. Поэтому полная переносимость на произвольные приложения не заявляется. Сам Petclinic не запускался.

DeepSeek использовался при разработке через закреплённый `opencode/deepseek-v4.1-flash-free`, `--variant max`. Нативный Karpathy Guidelines загружен до первой правки. Ему были доступны для записи только `frontend.py` нового варианта и новый тест; при исправлениях — только `frontend.py`. Shell и другие исполнители запрещены. Codex прочитал весь дифф, выявил дефекты независимыми контрпримерами, вернул замечания и самостоятельно проверил исправления. Тесты не ослаблялись. В экспортированной сессии 72 сообщения модели, заявленная стоимость — 0; это данные разработки, не времени анализа. Журналы хранятся отдельно в `experiments/20261017-state-binding/`.

Для запуска из папки варианта:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -B code/offline_run.py \\
  --source ../../tt-challenge/targets/trainticket \\
  --skeleton ../../tt-challenge/skeleton/trainticket.json.gz \\
  --context ../../tt-challenge/context \\
  --scenarios ../../tt-challenge/scenarios \\
  --output submission.json --report benchmark/analysis-report.json
```

Для другого Java/Spring-проекта заменяются входные пути. Нужен готовый скелет в схеме организаторов; его построение не входит в анализатор. Исходное приложение и его сервисы не запускаются. Для сравнения с сохранённым результатом используйте новые пути `--output` и `--report`.

```bash
PYTHONPATH=code .venv/bin/python -B -m pytest code/tests -q -p no:cacheprovider
.venv/bin/python -B code/check_generalization.py --directory /tmp/independent-check
.venv/bin/python -B checks/audit_bindings.py . \\
  --skeleton ../../tt-challenge/skeleton/trainticket.json.gz \\
  --source ../../tt-challenge/targets/trainticket \\
  --output /tmp/binding-audit.json
```

Воспроизведение пробы Petclinic после загрузки указанного тега, без Maven/JVM:

```bash
.venv/bin/python -B checks/check_petclinic.py \\
  --repository /path/to/spring-petclinic-rest \\
  --work-dir /tmp/new-petclinic-input --output /tmp/petclinic-probe.json
```

SHA-256 полного `submission.json`: `{summary['submission_sha256']}`.

Измерения: [summary.json](benchmark/summary.json), [evaluation.json](benchmark/evaluation.json), [сравнение](benchmark/comparison.json), [привязки](benchmark/binding-audit.json), [полный отчёт](benchmark/analysis-report.json), [проверка оснований](benchmark/verification.json), [Petclinic](benchmark/petclinic.json). Изменённые ID сценария и hash seed 0/991 дали те же рёбра S0; см. [воспроизводимость](benchmark/reproducibility.json). Перед прогоном и после него совпали хеши кода. Эталон доступен только отдельному оценщику: сетевые обращения и чтение прежних ответов при построении запрещены audit hook. Две заблокированные попытки системных команд относятся к сбору `platform.platform()` (`uname`, `file`), что отдельно воспроизведено в [offline-environment-probes.json](benchmark/offline-environment-probes.json).

Сохранены без изменений 1497 файлов исходного кейса, образца, № 1–5, № 7–8. № 6 и его продолжения ведёт другой чат; здесь они не менялись. Архив [solution.zip](solution.zip) содержит `submission.json` в корне, код, инструкции и результаты проверок; его хеш и проверка целостности — [archive-check.json](benchmark/archive-check.json). На сайт архив не отправлялся.
'''
(V / 'README.md').write_text(text)
index_path = ROOT / 'solutions/README.md'
index = index_path.read_text()
row = f"| 9 | request-state-linking | — | {summary['score_S0']:.10f} | [README](—_request-state-linking/README.md) |".replace('0.', '0,')
anchor = '| 8 | predicate-state-analysis | — | 0,8434829060 | [README](—_predicate-state-analysis/README.md) |'
assert anchor in index
if '| 9 |' in index:
    index = re.sub(r'^\| 9 \|[^\n]*$', row, index, flags=re.M)
else:
    index = index.replace(anchor, anchor + '\n' + row)
index = re.sub(r'\n\nРешение № 9 — \[request-state-linking\][^\n]*\n', '\n', index)
index += f'''\n\nРешение № 9 — [request-state-linking](—_request-state-linking/README.md), родитель № 8. Локальный S0 вырос до **{summary['score_S0']:.10f}**, превысив № 5 (**0,9260149573**); score сайта не получен. Неизвестные входы: **82 → {audit['steps_with_absent_or_stored_unknown']} шага из 103**, в S0 — 0. Исправлены обёртки JavaScript, области видимости и структура URL; добавлены типизированные ссылки на результаты, порядковый выбор и фильтры из методов DTO/перечислений. **{test_count} тестов** пройдены, формат и основания S0–S7 проверены, S0 воспроизводится с другим ID/hash seed. Полный прогон — **{summary['elapsed_seconds']:.3f} с**, подготовка — **{summary['preparation_seconds']:.3f} с**, RSS — **{summary['peak_rss_bytes']} байт**, обращений к моделям при анализе — 0; время и память выше № 8. Проверены независимые микропроекты и четыре пробы выбора обработчиков/параметров на 78 Java-файлах Petclinic REST; полной оценки графа Petclinic нет. Все сценарии остаются `partial`; оставшиеся пропуски и границы переносимости перечислены в README. [ZIP № 9](—_request-state-linking/solution.zip).\n'''
index_path.write_text(index)
print(json.dumps(comparison, ensure_ascii=False))
