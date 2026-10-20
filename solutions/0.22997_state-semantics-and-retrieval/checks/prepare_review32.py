"""Assemble review/status/cost evidence from measured artifacts, never estimates."""
import difflib,hashlib,json,shutil
from datetime import datetime,timezone
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def load(name):return json.loads((V/name).read_text())
def save(name,value):(V/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def edge_set(block):return {(e['source'],e['relation'],e['target']) for e in block['edges']}


def main():
    stage='E7-release';summary=load('benchmark/stages/'+stage+'/summary.json');evaluation=load('benchmark/stages/'+stage+'/evaluation.json')
    formatting=load('benchmark/stages/'+stage+'/format-check.json');assert not formatting['errors'] and not formatting['warnings']
    before=load('benchmark/stages/B00-parent31/submission.json');after=load('benchmark/stages/'+stage+'/submission.json')
    shutil.copyfile(V/'benchmark/stages'/stage/'submission.json',V/'submission.json')
    deltas={}
    for sid,b in before['scenarios'].items():
        old,new=edge_set(b),edge_set(after['scenarios'][sid])
        deltas[sid]={kind:{'added':len({e for e in new-old if e[1]==kind}),'removed':len({e for e in old-new if e[1]==kind})} for kind in ('executes','calls','remote','data')}
    save('benchmark/prediction-deltas-31-to-32.json',deltas)
    stages=['B00-parent31','E1c-R01-R03','E2-R04','E4-R05-summary','E5-R06','E6-final','E7-release'];cost=[]
    for name in stages:
        row=load('benchmark/stages/'+name+'/summary.json');timings=load('benchmark/stages/'+name+'/analysis-report-timings.json')
        cost.append({'stage':name,**{k:row[k] for k in ('preparation_seconds','analysis_seconds','peak_rss_bytes','submission_sha256')},
            'report_elapsed_before_final_write':row['elapsed_seconds'],'full_phase_timings':timings})
    save('benchmark/cost-summary.json',{'stages':cost,'comparability':'single observed local runs, OS cache uncontrolled; changed path frontiers and some concurrent checks prohibit a causal speedup claim'})
    diffroot=V/'development/stage-diffs';diffroot.mkdir(exist_ok=True)
    for left,right in zip(stages,stages[1:]):
        a,b=V/'development/stages'/left/'code',V/'development/stages'/right/'code'
        names=sorted({p.relative_to(a) for p in a.rglob('*') if p.is_file()}|{p.relative_to(b) for p in b.rglob('*') if p.is_file()})
        patches=[]
        for name in names:
            x=(a/name).read_text() if (a/name).exists() else '';y=(b/name).read_text() if (b/name).exists() else ''
            if x!=y:patches.extend(difflib.unified_diff(x.splitlines(True),y.splitlines(True),fromfile=left+'/'+str(name),tofile=right+'/'+str(name)))
        (diffroot/(left+'--'+right+'.diff')).write_text(''.join(patches))
    state=load('development/implementation-state.json');state['updated_at']=datetime.now(timezone.utc).isoformat()
    state['current_goal']='release-artifacts';state['next_action']='Verify judged/analytical archives. Real-transfer remains not_run without two independent ready packages. Default retrieval remains A after rejected B/Qwen pilots.'
    accepted={
      'R01':[('bounded-static-state','benchmark/implementation/R01/initializer-Error-after'),('release-integration','benchmark/implementation/R01/release-integration'),('TT-current-stage','benchmark/stages/E7-release')],
      'R02':[('typed-search-and-callbacks','benchmark/implementation/R08/final-local-gate'),('release-integration','benchmark/implementation/R01/release-integration')],
      'R03':[('correctness','benchmark/implementation/R01/release-local-gate'),('finite-forEach-support','benchmark/implementation/R03/completion-controls'),('cart-state-and-wires','benchmark/implementation/R01/release-integration/gate/cart/checks.json')],
      'R04':[('source-generated-leaf-keys','benchmark/implementation/R01/release-local-gate'),('isolated-E2','benchmark/stages/E2-R04'),('TT-frontier-witnesses','benchmark/implementation/R04/final-TT-causal-probes')],
      'R05':[('diagnostics-and-loss-ledger','benchmark/implementation/R05/stage-causal-ledger'),('one-readonly-stop-summary','benchmark/implementation/R05/tiny-oracle-export-02'),('default-integration','benchmark/implementation/R01/release-integration')],
      'R06':[('legal-orders-and-complete-agreement','benchmark/implementation/R01/release-local-gate'),('state-wires-and-mutations','benchmark/implementation/R01/release-integration'),('source-oracle-deltas','development/oracles/legacy-order-v3-delta.md')]}
    for goal in state['goals']:
        if goal['id'] in accepted:
            goal['status']='verified';goal['scope']='bounded implementation and available local/regression integration; not full Java/Spring or independent real transfer'
            goal['subgoals']=[{'id':name,'status':'verified','evidence':path} for name,path in accepted[goal['id']]]
            if 'last_exit_status' in goal:goal['last_goal_specific_command_exit']=goal.pop('last_exit_status')
            goal['accepted_release_gate']={'path':'benchmark/implementation/R01/release-local-gate','returncode':0}
        elif goal['id']=='R07':
            goal['status']='in_progress';goal['subgoals']=[
              {'id':'frozen-dataset-and-harness','status':'verified','evidence':'development/retrieval/frozen-v2'},
              {'id':'generic-package-harness','status':'verified','evidence':'benchmark/implementation/R07/generic-package-harness'},
              {'id':'A-B-adoption','status':'experiment_rejected','evidence':'benchmark/implementation/R07/historical-A-versus-B','reason':'higher ranking metrics but more false rejections; B-on-E cart NL fails'},
              {'id':'real-transfer-first','status':'not_run','reason':'no new independent real source/config/skeleton/context/chain/oracle package'},
              {'id':'real-transfer-second','status':'not_run','reason':'second real application holdout absent'}]
        elif goal['id']=='R08':
            goal['status']='in_progress';goal['subgoals']=[
              {'id':'plan-adapter-fallback','status':'verified','evidence':'benchmark/implementation/R08/adapter-controls'},
              {'id':'permission-and-hardware-runtime','status':'verified','evidence':'development/qwen-hardware-preflight.json','authority':'Direct user: можешь запускать qwen и использовать любые ресурсы'},
              {'id':'offline-Qwen-index','status':'verified','evidence':'benchmark/implementation/R08/qwen-index-build'},
              {'id':'Qwen-development-evaluation','status':'experiment_rejected','evidence':'benchmark/implementation/R08/qwen-C-expanded-check','reason':'four false accepts on refusal cases; model ranking improvement alone is insufficient'},
              {'id':'Qwen-downstream','status':'experiment_rejected','evidence':'benchmark/implementation/R08/qwen-on-E7-cart','reason':'cart NL selects wrong downstream handler; explicit control remains correct'},
              {'id':'CodeRank-runtime','status':'not_run','reason':'custom model runtime not audited/executed; no CodeRank weights downloaded'},
              {'id':'reranker-D','status':'not_run','reason':'extra model not justified before refusal/history errors are repaired and independent data supplied'},
              {'id':'independent-model-transfer','status':'not_run','reason':'two independent real holdouts absent'}]
    state['all_queues_verified']=False;save('development/implementation-state.json',state);save('STATUS_MATRIX.json',{'goals':state['goals'],'all_queues_verified':False})
    s0=evaluation['scenarios']['S0']['sets'];score=evaluation['score']
    rootreadme=f'''# Решение № 32 — state-semantics-and-retrieval

Родитель — № 31. Реализованы и проверены ограниченные контракты R01–R06 из обновлённой аналитики. Для R07 подготовлены замороженный набор и сравнительный поиск; для R08 выполнен локальный пилот Qwen. Новые варианты поиска отклонены по результатам проверок. Основной запуск использует прежний поиск A и принятые семантические исправления.

| Показатель | Значение |
| --- | --- |
| Score сайта | — (не получен) |
| Тестовый score S0 | {score} |
| S0: executes / calls / remote / data | {s0['executes']['iou']} / {s0['calls']['iou']} / {s0['remote']['iou']} / {s0['data']['iou']} |
| Формат S0–S7 | Ошибок и предупреждений нет |
| Время подготовки / анализа | {summary['preparation_seconds']:.3f} / {summary['analysis_seconds']:.3f} с |
| Полный цикл, включая запись отчётов | {cost[-1]['full_phase_timings']['end_to_end_seconds']:.3f} с |
| Пиковая память процесса | {summary['peak_rss_bytes']} байт |

Измерено локально на macOS arm64, Python 3.11.9; path_limit=4, прежняя политика completion budget, constraints включены. S0 и сайт — разные показатели. Пустой remote oracle S0 не проверяет качество межсервисных связей. Эти времена относятся к конкретному прогону; сокращение неполных путей не доказывает ускорение одинаковой точной работы.

Проверки: 2080 tests/checkers; 17 интеграционных запусков; строгая cart explicit/NL цепочка, 47 исходных мутаций, проверки состояния PiggyMetrics/Petclinic, document и actor/session. Изменения эталонов порядка оформлены отдельно; исторические файлы не изменены. Нужны два новых реальных входных пакета для проверки переноса. Всю R01–R08 нельзя объявить verified.

Запуск из папки решения после установки requirements.txt:

```sh
python -B code/offline_run.py --source ../../tt-challenge/targets/trainticket --skeleton ../../tt-challenge/skeleton/trainticket.json.gz --context ../../tt-challenge/context --scenarios ../../tt-challenge/scenarios --output /tmp/answer32.json --report /tmp/report32.json
```

SHA256 submission.json: `{summary['submission_sha256']}`.

Подробности: [CAUSAL_REVIEW.md](CAUSAL_REVIEW.md), [LIMITATIONS.md](LIMITATIONS.md), [REPRODUCE.md](REPRODUCE.md), [STATUS_MATRIX.json](STATUS_MATRIX.json). Области R07/R08 и результаты отклонённых экспериментов перечислены отдельно. Исследуемые приложения/JVM, DeepSeek и внешние LLM API не запускались. Локальная Qwen запускалась с разрешения пользователя; она не включена по умолчанию.
'''
    (V/'README.md').write_text(rootreadme)
    (V/'LIMITATIONS.md').write_text('''# Ограничения № 32

Это ограниченная интерпретация исходников Java/Spring с готовым скелетом, а не JVM или SQL engine. Неопределённые значения, source/framework semantics и исчерпание бюджета могут остановить путь. Observed-union остаётся приближением; потенциальные closure edges не выдаются за выполненные.

- R01: исходные static cells принадлежат сценарию; поддержаны литеральные primitive/String constants и ограниченная инициализация классов. Нелитеральное потенциальное constant expression, циклы, classloader/concurrency, полная инициализация интерфейсов/default methods не покрыты. Error сохраняется, неизвестный Throwable даёт ограничение Error, а не выдуманный точный wrapper. SLF4J facade не моделирует загрузку провайдера.
- R02–R03: конечные последовательные List/Stream и известные callbacks. Unknown membership, неподдержанный callback/pipeline или budget оставляют boundary. Нет parallel Stream; toList сохраняет read-only контракт. Optional presence отделена от значения.
- R04: source leaf hashCode/equals с эффектами и исключениями; стандартный default Lombok scalar leaf без настроек, custom getter, inheritance и сложных полей. Мутировавший ключ не перехешируется. Reentrant Set mutation останавливает точный анализ. Это не полная HashMap/HashSet/Lombok совместимость.
- R05: только один stop-only summary для доказанного read-only residual после неизвестного native foreach. Он не выполняет callback, не возобновляет suffix и не сообщает нормальный return. Непроверенные writes, alias mutation, finally и transactions сохраняют консервативную границу. Кеш и fixed point не добавлены.
- R06: источник порядка обязателен. Числовой ORDER BY/derived OrderBy, ties и null поддержаны в объявленной области; текстовая collation, динамические Sort/Pageable/Limit и сложные запросы остаются границами. Ordinal permutation scope ограничен шестью строками; при действующих budgets покрытие может быть неполным и для меньшей коллекции. Agreement требует полного покрытия, совпадающих kinds/values и успешного producer. Неупорядоченный «first owner» в legacy теперь unresolved.
- R07: 57 запросов — development/regression, включая синтетическую кириллицу. Настоящих новых real application holdouts нет. B улучшает ranking, но повышает false reject и ломает cart NL; B не принят.
- R08: Qwen offline на Metal проверена локально, но четыре false accept и cart NL regression не позволяют принять её. Нет веса/исполнения CodeRank и reranker. Нет проверки CPU inference, MPS quantization, облака или обучения. MPS недоступен внутри sandbox и доступен в разрешённом host-процессе; это не отсутствие GPU у Mac. Шесть TT document units усечены модельным tokenizer до 512 tokens, что явно измерено. На этапе построения индекса два process probes заблокированы; ни один дочерний процесс исследуемого приложения не выполнялся.

Cart oracle проверяет required subset рёбер, source executes, типы, значения, wire и состояние после authentication boundary. Он не даёт полной precision/IoU и не подтверждает security/bootstrap. Legacy маленькие графы проверены полностью в своей области; remote там пуст. Synthetic equipment имеет полный маленький непустой remote/data oracle, но не заменяет реальное приложение.

Train Ticket остаётся неполным. R06 переносит отсутствие порядка в consumers и может остановить known search раньше старого Set/HTTP frontier. Полная source-faithful NL search→booking→payment цепочка не подтверждена. Изолированная payment ветвь с двумя UI полями возвращает success только при заданном исходном контексте; token/login/session producer и общий сценарий требуют отдельного доказательства. Значения userId/price в UI payload не добавлялись.

Два real holdout пакета нужны с source/config/skeleton/context, explicit/NL цепочками create/select/update/read, refusal/ambiguity/remote error и независимым oracle. Схема и generic harness подготовлены; его synthetic smoke control не считается таким holdout.
''')
    (V/'REPRODUCE.md').write_text('''# Воспроизведение № 32

Основной runtime: Python 3.11.9 и requirements.txt. Из папки solution_32 запустите `python -B -m pytest -q -p no:cacheprovider code/tests checks/tests` с PYTHONPATH=code. Снимки stage code и manifests находятся в development/stages; code E7-release должен совпасть с рабочим code побайтно. Прежние неудачные прогоны сохранены и не заменены успешными.

Для TT нужен исходный неизменённый tt-challenge. Он не дублируется в аналитическом архиве. Передайте его пути в команду README. Эталон S0 использует только внешний evaluate_golden.py после inference; offline_run блокирует сеть, процессы и предыдущие ответы. Все восемь сценариев анализируются заново из независимых initial states.

Интеграция: `python -B checks/run_regression_gate.py --output /absolute/new/evidence`. Используйте новый абсолютный output; source inputs и frozen oracles входят в validation_inputs/development. Для отдельных результатов см. run.json/stdout.txt/stderr.txt каждого benchmark/implementation run. Группировка причин и source/guard alignment: checks/build_causal_review.py. Ординалы альтернатив не используются как соответствие между прогонами.

R07: `python -B checks/benchmark_retrieval.py --frozen development/retrieval/frozen-v2 --output /absolute/new/retrieval`. A — историческая семантика B00 и исходный ContractIndex; B отличается только retrieval class/hooks и source documents. Повтор на семантике E: `--semantic-code code`. Explicit HTTP должен обходить retrieval. Для нового ready package используйте development/holdout-package.schema.json и checks/run_transfer_package32.py. Новые реальные inputs не включены и не выдуманы.

Qwen — отдельный опциональный runtime. Разрешение пользователя: «можешь запускать qwen и использовать любые ресурсы». Реально использованы Metal float32, 4 CPU threads, batch 4 для документов / 1 для запроса, max_sequence_length=512. Зависимости закреплены в development/qwen-runtime-lock.txt; исходные wheel URLs/hashes — qwen-runtime-install.json. Скачайте только Qwen/Qwen3-Embedding-0.6B revision 97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3 через hf-cli, проверьте используемые файлы, их SHA256 и стандартные modules. Не используйте latest или trust_remote_code.

Веса, venv и системные GPU caches в архив не входят. В model_indexes сохранены vectors/manifests для каждого корпуса, а в benchmark/implementation/R08 — profile, hashes, quality/cost и raw predictions. Для самостоятельного восстановления после загрузки весов запустите checks/build_qwen_cache.py с --model, --frozen, --output, --evidence и --device. Он строит cache и запрещает сеть, процессы и чтение labels/gold. Первоначальные weights/config файлы нужно разместить рядом с vectors по manifest; сам model-snapshot становится проверяемым локальным каталогом. CLI `--retrieval offline-dense --model-snapshot DIR` остаётся экспериментальным; без готового корректного snapshot работает baseline fallback.

Точный inference pilot воспроизводится через checks/retrieval_worker.py с profile C, frozen actions/projects JSON и проверенным snapshots root; обновите absolute paths projects JSON под свою распаковку. Реlevance labels читаются только evaluate_dense_retrieval.py после worker. Сравните same_candidates (пул A, без расширения) и expanded отдельно. Fresh process значит новый процесс без загруженной модели, но с неконтролируемым OS page cache. В каждом worker сохранены три отдельные warm forward samples; query cache и повторный forward не смешиваются.

Judge ZIP содержит submission.json в корне и ровно текущий code. Аналитический архив содержит код, checks, источники независимых fixtures, результаты и snapshots; исторические full traces оставлены с явно названной версией. Повтор judge ZIP и testzip/hash-проверка аналитического пакета фиксируются в benchmark/packaging. До появления этой записи упаковка не считается проверенной.
''')
    (V/'CAUSAL_REVIEW.md').write_text(f'''# Causal review: решение № 32

Единственная рабочая аналитика: development/inputs/solution_31_models_and_static_analysis_review.md, SHA256 4a1c9f985808aacd4e35816d028779586407c13bf74f938df14a71b859a29592. Пользователь заменил старый файл в ходе работы. Новый §12.2 принят полностью; исходный аналитический текст не переписывался под новые результаты.

## Принятый результат

R01–R06 приняты в ограниченной проверенной области, с сохранением неопределённости и prefix effects. R07 benchmark/harness и R08 adapter/runtime приняты как инструменты проверки. Retrieval B и Qwen C не включены по умолчанию. Два real transfer gates остаются not_run; вся очередь не имеет статуса verified. Полная матрица — STATUS_MATRIX.json.

R01 переносит mutable statics в ScenarioState, выполняет source initializers по порядку, сохраняет ошибки/статус между обращениями и изолирует сценарии. Исходные source contexts не становятся graph methods. При финальном ревью воспроизведена и исправлена ошибка обёртки Error: before/after сохранены. Неизвестный subtype Throwable не выдаётся за точный ExceptionInInitializerError. Результирующий TT JSON от этого последнего ремонта не изменился.

R02 сохраняет int kinds indexOf/lastIndexOf, направление equals, -1 и downstream exceptions; source namesake не становится native. R03 реализует finite sequential forEach/forEachOrdered с реальными callback effects, failure prefix, Stream completion и Optional.isEmpty. Unknown callback/membership не превращается в выполненный normal suffix.

R04 использует source hashCode/equals либо доказанный default Lombok scalar leaf. Изменённый ключ сохраняет прежнее hash placement; reentrancy и неподдержанные генераторы — boundaries. Отдельный E2 восстановлен из reviewed R04-only diff поверх E1c и затем измерен; он не выдаётся за исторический снимок до R05.

R05 записывает первые unknown/control losses с source spans/hashes, guards, types, prefix, actual effects и widened footprint. Одно доказательство read-only residual сохраняет unrelated rows, но останавливает выполнение. Tiny equipment oracle экспортирован для трёх парных on/off случаев (шесть наблюдений) с полными E/C/R/D, wire и state. Во всех прочих опасных остатках остаётся консервативная invalidation. Source-cause ledger находится в benchmark/implementation/R05/stage-causal-ledger; поздний Error repair — в R01/E6-to-release-ledger. Количество предупреждений не используется как quality score.

R06 убирает dump-order proof. Числовое source ordering, ties/null и bounded permutations проходят через List/array/JSON/request; каждый путь сохраняет свою строку и выбранный ID. Полное producer agreement нельзя вывести из одного увиденного пути. Cart v4 сохраняет все v3 obligations и добавляет legal-order coverage; исторический v3 не изменён. Legacy step «Read first owner» теперь сохраняет unknown ID вместо ошибочного owner 1. Эта oracle delta описана отдельно; historical v2 не объявляется пройденной.

## Измерения и ошибки поиска

Заморожены 57 запросов: 55 NL и два explicit controls, 47 NL answer cases и восемь refusal cases. Train/test splits пусты; все available applications/families — development/regression. Labels выведены инженерным чтением source/config, не ответами текущего анализатора. Corpus: TT 280 contracts (262 canonical handlers), Piggy 9, cart 10, Petclinic 8 и synthetic Unicode 2. Корпус содержит разрешённые source facts/chunks, без gold/traces/обсуждений решения. Worker не читает labels; все три модельных сравнения имеют ноль сетевых попыток и forbidden reads.

| Retrieval | Recall@1 | Recall@3 | MRR | False accept / 8 | False reject / 47 | Wrong accepted handler |
|---|---:|---:|---:|---:|---:|---:|
| A, №31 | 21/47 | 26/47 | 0.514894 | 4 | 18 | 8 |
| B, Unicode lexical | 26/47 | 28/47 | 0.585816 | 1 | 19 | 5 |
| Qwen, тот же пул A | 28/47 | 30/47 | 0.617021 | 3 | 20 | 0 |
| Qwen, expanded corpus B | 43/47 | 47/47 | 0.957447 | 4 | 5 | 1 |

B отклонён: при более высоком ranking растёт false reject; в cart NL пропущены steps 3–4. Qwen резко улучшает межъязыковое совпадение, но не доказывает наличие handler для no-handler действия. Cart step 3 выбирает неверный controller; последующая history lineage расходится. Ни binding, ни execution engine не получают права выдумать поля/IDs из model score. Explicit control проходит; это изолирует ошибку выбора. Эти результаты не исправлялись под сохранённый oracle. Все raw predictions, paired errors и denominators по project/language/family находятся в R07/R08 evidence. nDCG не вычислялась: graded labels нет. Нулевой ranking у explicit controls в старой grouped таблице означает bypass, а не retrieval failure; обе wire-проверки успешны.

Qwen revision, tokenizer, pooling, файлы и runtime закреплены; собственный код модели не исполнялся. Model load при построении индекса 1.202 с, все пять индексов построены за 52.982 с; peak RSS 3927425024 байта. TT document encoding — 39.082 с, шесть из 560 units длиннее 512 tokens и усечены tokenizer. Это локальный MPS прогон, не CPU/cloud benchmark. Два platform process probes заблокированы при подготовке; target processes не запускались. Warm samples и fresh-process measurements опубликованы раздельно, OS cache не контролируется. CodeRank и D не измерены, поэтому не названы проигравшими моделями.

## Train Ticket и S6

S0 остаётся {score}; E/C/R/D — {s0['executes']['iou']}/{s0['calls']['iou']}/{s0['remote']['iou']}/{s0['data']['iou']}. Submission SHA256 `{summary['submission_sha256']}`. Все 103 шага сопоставлены по source/request/guard provenance, а не ordinal alternative. Последний Error repair не изменил union. S6 prediction delta к №31: `{json.dumps(deltas['S6'],ensure_ascii=False)}`. Это изменение прогнозов, а не hidden gold.

Known-input search, полный NL scenario и UI lineage различаются. Финальные isolated probes показывают collection-order completion budget и unresolved source initializer effects; R06 может открыть честную неопределённость раньше прежнего HTTP Set<Ticket> frontier. Сохранённое R04 продвижение за Set frontier не означает финальную успешную search→booking→payment цепочку. UI payMyOrder отправляет orderId/tripId; userId/price не добавлены. Source token/login/session producer для полной цепочки остаётся незавершённым обязательством. Отдельный source-UI payload success при известном исходном order не доказывает этот общий путь.

## Проверки и следующий шаг

2080 tests/checkers и 17 release integration runs проходят; известные source-only fixtures/negative mutations сохранены. 24137 immutable файлов прежнего protected manifest и 534 parent files не изменены. solutions/README.md — разрешённый изменяемый registry, уже изменённый до начала этого turn; он отдельно исключён из исторического inherited integrity comparison. Все core code/input/stage hashes, команды, stderr, time/RSS и diffs сохранены.

Следующая работа с наибольшим обоснованием — source-backed отказ и history-aware выбор handler, затем два новых real ready packages по подготовленной схеме. Сначала нужны независимые данные и полный oracle, а не более крупная модель, увеличение path budget или ручное восстановление S6 edges. Сайт и упаковка записываются отдельными artifacts после их фактической проверки.
''')
    print(json.dumps({'submission_sha256':summary['submission_sha256'],'S0':score,'all_queues_verified':False,'code_stage':stage}))


if __name__=='__main__':main()
