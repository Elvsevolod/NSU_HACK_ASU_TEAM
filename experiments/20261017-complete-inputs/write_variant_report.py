"""Describe only the preserved final run; never participate in inference."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET

root=Path('solutions/—_source-request-state')
bench=root/'benchmark'
summary=json.loads((bench/'summary.json').read_text())
audit=json.loads((bench/'binding-audit.json').read_text())
report=json.loads((bench/'analysis-report.json').read_text())
parent=json.loads((bench/'parent-binding-audit.json').read_text())
parent_summary=json.loads(Path('solutions/—_request-state-linking/benchmark/summary.json').read_text())
tests=sum(int(s.get('tests',0)) for s in ET.parse(bench/'pytest.xml').getroot().iter('testsuite'))
unknown=audit['steps_with_absent_or_stored_unknown']
comparison={'parent_variant':9,'variant':10,'site_score':None,'hidden_scenario_scores':None,
  'score_S0':{'previous':0.9509803921568627,'current':summary['score_S0'],'delta':summary['score_S0']-0.9509803921568627},
  'score_S0_variant5':{'previous':0.9260149572649572,'delta':summary['score_S0']-0.9260149572649572},
  'unknown_input_steps':{'previous':parent['steps_with_absent_or_stored_unknown'],'current':unknown,'total':audit['steps'],
      'scope':audit['occurrence_scope']},
  'absent_field_occurrences_first_alternative':{'previous':sum(parent['absent_field_occurrences'].values()),
      'current':sum(audit['absent_field_occurrences'].values())},
  'tests':{'previous':129,'current':tests},
  'elapsed_seconds':{'previous':parent_summary['elapsed_seconds'],'current':summary['elapsed_seconds']},
  'peak_rss_bytes':{'previous':parent_summary['peak_rss_bytes'],'current':summary['peak_rss_bytes']},
  'model_calls_at_runtime':0,'all_unknowns_eliminated':unknown==0,
  'interpretation':'Fewer unknown inputs and fixed counterexamples are local evidence; S0 unchanged vs9 and greater than5. Empty remote IoU is not portability proof.'}
(bench/'comparison.json').write_text(json.dumps(comparison,ensure_ascii=False,indent=2)+'\n')

s0=report['scenarios']['S0']
unknown_s0=[s['n'] for s in s0['steps'] if any(any(item.startswith('Unknown input:') for item in a['unresolved']) for a in s['alternatives'])]
text=f'''# Решение № 10 — source-request-state

Родитель — решение № 9. Исправлены четыре замечания проверки и расширено связывание запросов, параметров и состояния по исходникам. **Неизвестные входы: 52 → {unknown} шагов из {audit['steps']}. Нулевое число неизвестных не достигнуто.** S0 сохранился относительно № 9 и превышает № 5; качество скрытых сценариев и score сайта неизвестны.

| Показатель | Значение |
| --- | --- |
| Score сайта | — (не получен) |
| Тестовый score S0 | {summary['score_S0']:.10f} |
| S0: executes / calls / remote / data | 0.9705882353 / 0.9583333333 / 1 / 0.875 |
| Формат S0–S7 | Проверен, без дубликатов и недопустимых рёбер |
| Время построения ответа | {summary['elapsed_seconds']:.3f} с локально |
| Подготовка / анализ | {summary['preparation_seconds']:.3f} / {summary['analysis_seconds']:.3f} с |
| Пиковый RSS | {summary['peak_rss_bytes']} байт |
| Обращения к моделям при анализе | 0 |
| Тесты | {tests} passed |
| Неизвестные входы S0 | {len(unknown_s0)} шагов |
| Повтор S0 | Рёбра совпали после замены ID сценария и hash seed 0 → 991 |

Измерено на Python {summary['environment']['python']}, {summary['environment']['platform']}; зависимости закреплены в `requirements.txt`. Полные значения — в [summary.json](benchmark/summary.json). Время выше № 9 (135.991 с), RSS выше 340525056 байт. Индекс строится один раз на все восемь сценариев; постоянного кеша между отдельными запусками нет. В S0 `remote=1` — совпадение двух пустых множеств. Это не проверка точности межсервисных вызовов.

## Изменения

- Маршрутизация Spring учитывает HTTP-метод `RequestMapping` и конкретность пути; список сущностей отличается от списка их типов.
- Сохраняются все строки результата репозитория и поле `body` обычного объекта. Ограниченные циклы и неизвестные ветви явно диагностируются.
- Добавлены ленивая обработка Stream filter/map/collect, данные вложенных коллекций, проекции перечислений, точные числовые литералы и исходные подписи полей.
- Порядковый выбор связан с реальным запросом, заполняющим нужный элемент интерфейса. Выбор первого магазина/блюда берётся из предоставленного контекста. Цена и название относятся к одному выбранному объекту.
- Известный ID сохраняет выбор между запросами. Различаются первичные и внешние ID, создание и чтение объектов, исходный порядок списка и порядок создания. Поле другого типа не подставляется по одному совпадающему названию.
- Исправлены ложные привязки даты рождения, времени к дате и кода постороннего перечисления. UI options обрабатываются через исходное выражение запроса. Добавлен ограниченный адаптер Vue row events с проверкой владельца компонента.

Факты проекта извлекаются в `project.py`/`frontend.py`, сценарий связывается с контрактом в `contracts.py`, исполнение и альтернативы анализируются в `engine.py`/`paths.py`, состояние — в `state.py` и модулях provenance/selection. Конкретные сервисы, маршруты, поля, коды и рёбра берутся из входов. В построителе нет условий по Train Ticket и ID S0–S7. Другой проект подключается через аргументы ниже; полный перенос на произвольный Java/Spring-проект не доказан.

## Запуск

Из каталога варианта:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PYTHONHASHSEED=0 .venv/bin/python -B code/offline_run.py \\
  --source ../../tt-challenge/targets/trainticket \\
  --skeleton ../../tt-challenge/skeleton/trainticket.json.gz \\
  --context ../../tt-challenge/context/db-after-warmup.sql.gz \\
  --scenarios ../../tt-challenge/scenarios \\
  --output /tmp/source-state-submission.json \\
  --report /tmp/source-state-report.json
PYTHONPATH=code .venv/bin/python -B -m pytest code/tests -q -p no:cacheprovider
```

Для другого проекта заменяются `--source`, `--skeleton`, `--context` (MySQL dump), `--scenarios`; текстовый контекст берётся из `skeleton.context`. Готовый скелет обязателен. Приложение и Java не запускаются. `offline_run.py` блокирует сеть, дочерние процессы и чтение эталона/прежних ответов; оценка S0 выполняется отдельным процессом после построения. При установке зависимостей нужен доступ к их пакетам; анализ работает без внешних API и локальных моделей. Воспроизводимый эксперимент этой разработки сохранён в `experiments/20261017-complete-inputs/benchmark.py` основного репозитория.

## Проверки и границы результата

Проверены четыре исходных дефекта, независимые контрпримеры, состояние библиотеки/склада и REST/data-цепочка двух сервисов. На настоящих исходниках Spring Petclinic REST v2.1.5 (78 файлов Java, commit `2cd2f9c7a3eee55d7c6d09fa100e02341ae27070`) проходят 11 проб маршрутизации, выбора обработчика и параметров. Полного эталонного графа и интеграционной цепочки записи Petclinic нет. Генерализация на больших независимых проектах требует дальнейшей проверки.

Все восемь сценариев помечены `partial`. Выбор API остаётся лексической гипотезой; предупреждения, неподдержанные конструкции и альтернативы сохранены. {audit['steps_with_top_level_symbolic_params']} шага содержат абстрактные входы нового аккаунта; генерируемые UUID также абстрактны. Это не буквальные значения всех входов. Поддержка Java/Spring ограничена перечисленными моделями, полного JVM/браузера/Jackson/JPA нет, Ktor не реализован.

Конкретные данные нового пассажира, спутника и получателя, а также новое имя/телефон при изменении получателя не заданы. Одновременно часть оставшихся пропусков связана с анализатором: события DOM, индекс строки, выбор запроса, устаревшие URL и расширение несовместимых состояний. Не все оставшиеся неизвестные можно объяснять нехваткой входных данных. Подробности — [DIAGNOSTICS.md](DIAGNOSTICS.md), [аудит каждого шага](benchmark/binding-audit.json), [основания нехватки данных](benchmark/input-evidence.json).

DeepSeek использовался при разработке: закреплённая бесплатная модель, `variant=max`, узкие разрешения на конкретные файлы, без shell и удаления. Проверены модель, заявленная стоимость 0 и нативный skill перед правками; Codex прочитал изменения, проверил независимо и исправил найденные дефекты. [Записи модели](benchmark/deepseek-final-evidence.json), [ещё одна реализация](benchmark/structured-literals-model-evidence.json), [исходные подписи полей](benchmark/source-labels-model-evidence.json). Стоимость 0 относится к этим ответам DeepSeek; расход лимитов Codex этим числом не измеряется.

Сохранены 1599 защищённых файлов кейса, образца, прежних прогонов и вариантов; № 6 и его продолжения этим заданием не изменялись. [Проверка сохранности](benchmark/preservation.json).

## Артефакты

[submission.json](submission.json), [ZIP](solution.zip), [полный отчёт](benchmark/analysis-report.json), [проверка оснований](benchmark/verification.json), [сравнение с № 9](benchmark/comparison.json), [формат](benchmark/format_check.json), [Petclinic](benchmark/petclinic.json), [независимые примеры](benchmark/generalization.json).

SHA-256 ответа: `{summary['submission_sha256']}`. `submission.json` находится в корне архива. На сайт вариант не отправлялся.
'''
(root/'README.md').write_text(text)
print(json.dumps({'unknown_steps':unknown,'tests':tests,'score_S0':summary['score_S0'],'sha256':summary['submission_sha256']},ensure_ascii=False))
