"""Generate review from actual version31 evidence; pending site outcomes stay pending."""
import hashlib,json,re,shlex
from pathlib import Path
from datetime import datetime,timezone
V=Path(__file__).resolve().parents[1]


def read(name):return json.loads((V/name).read_text())
def save(name,text):(V/name).write_text(text.rstrip()+'\n')
def edge_set(block):return {(e['source'],e['relation'],e['target']) for e in block['edges']}


def main():
    meta=read('benchmark/final/metadata.json');score=read('benchmark/final/evaluation.json');cost=read('benchmark/cost-comparison.json')
    state=read('development/overnight-state.json');site=read('benchmark/site-score.json') if (V/'benchmark/site-score.json').exists() else {'status':'pending','score_display':'—'}
    restore=read('benchmark/site-best-restored.json') if (V/'benchmark/site-best-restored.json').exists() else {'status':'pending'}
    archive=read('benchmark/archive-check.json') if (V/'benchmark/archive-check.json').exists() else None
    before=read('benchmark/stages/G01-parent30/submission.json');after=read('submission.json');delta={}
    for sid in before['scenarios']:
        a=edge_set(before['scenarios'][sid]);b=edge_set(after['scenarios'][sid])
        delta[sid]={r:{'before':sum(e[1]==r for e in a),'after':sum(e[1]==r for e in b),'added':len({e for e in b-a if e[1]==r}),'removed':len({e for e in a-b if e[1]==r})} for r in ('executes','calls','remote','data')}
    unit_path=V/'benchmark/analytical-corrected-verification-logs/tests.stdout.txt'
    if not unit_path.exists():unit_path=V/'benchmark/overnight/G14/exact-final-all-unit-checkers/stdout.txt'
    units=unit_path.read_text();count=int(re.search(r'(\d+) passed',units)[1])
    t=cost['phase_runs'][meta['stage']];p=cost['phase_runs']['G16-parent30-paired'];repeated=cost['prepared']['runs']
    site_line=f"Сайт: {site.get('score_display','—')}, статус {site['status']}, посылка {site.get('submission_id','не получена')}. Восстановление №5: {restore.get('status','pending')}, посылка {restore.get('submission_id','не получена')}."
    issues={'G02':'Скрытый эталон S6 отсутствует; причины наблюдаемой дельты разделены.',
      'G06':'Пилот не включён в scheduler; отрицательное интеграционное решение.',
      'G13':'Полная TT NL-цепочка не пройдена; принят точный оставшийся frontier по альтернативе G13.',
      'G15':'Нет нового полного замороженного реального пакета source/skeleton/context/scenarios/oracle.',
      'G16':'Одна локальная пара и два prepared-повтора; память и полное время выросли.',
      'G17':site_line,'G18':'Проверка архива и его SHA находятся в отдельном внешнем .check.json; оценённый judge ZIP не пересобирается.'}
    table=['| Цель | Фактический статус | Evidence | Ограничение / следующий шаг |','| --- | --- | --- | --- |']
    for g in state['goals']:
        paths=g.get('evidence_paths',[]);evidence=', '.join('['+Path(n).name+']('+n+')' for n in paths[-2:]) or '[журнал](development/overnight-log.md)'
        table.append('| '+g['goal_id']+' | '+g['status']+' | '+evidence+' | '+issues.get(g['goal_id'],'Проверено в заявленном ограниченном контракте.')+' |')
    review=f'''# Решение №31: результаты G01–G18

Срез документа: {datetime.now(timezone.utc).isoformat()}. Родитель — №30. Принятый код — `{meta['stage']}`; SHA ответа `{meta['submission_sha256']}`.

Корзина проходит полные explicit и NL цепочки из восьми шагов в явно заданной прикладной границе после аутентификации. Из фактического GET выбран единственный APPROVED payment21/order11; refund сохраняет REFUNDED, remote PATCH переводит order11 в PENDING, сервер строит ответ с total12.5 даже при клиентском Void.class. Повтор даёт409 до записи/remote, отсутствующий999 даёт404, неоднозначный шаг7 не выполняет обработчик, reread сохраняет чужие строки и rejected payment23. Проверены реальные native Long аргументы, контроллеры, ответы, source mapper/total/subtotal, состояния до/после и15 per-step executes обязанностей. Все47 мутаций реальных explicit/NL трасс отвергнуты до нормализации NL. [Проверка](benchmark/regressions-final/cart/checks.json), [мутации](benchmark/regressions-final/cart/mutations/summary.json). Cart уже настроен в этой итерации и не является свежим holdout; v3 усиливает source-derived regression обязанности после реализации, v1/v2 не переписаны.

В TT известный поиск проходит живой Map-фильтр шести групп: типы элемента ORM-списка, case-insensitive OrderColumn и source-generated getters/setter сохранены. Полная NL-цепочка поиск→booking→payment остаётся неполной: source Set<Ticket> equality/hash и следующие distance/list consumers дают явные границы; в S6 таблицы уже неизвестны после более ранних admin input/authentication boundaries. Изолированный payment по объявленным исходным строкам успешен, но не считается полной цепочкой. Реальный UI отправляет orderId/tripId; userId/price в тело не добавлены. [Все103 шага и frontier](benchmark/tt-frontier.json).

Причинный ledger S6 устанавливает первое расширение station/train_type в observer events9/122 внутри AnalysisBoundary writable-closure fallback; subsequent joins переносят unknown. Это не установленная SQL-запись. Исторические шесть union-потерь base→C1 впервые на step8, другие12 step1-рёбер остаются на step7. Отдельный bulk-descriptor ablation и diagnostic order/completion reserves разделяют три фактора; correctness каждого hidden edge неизвестна. В новой версии opaque foreach больше не создаёт известную пустоту. [Ledger](benchmark/overnight/G02/causal-ledger-v2/causal-ledger.json), [исправление одного пути evidence](benchmark/overnight/G02/causal-ledger-v2/evidence-path-erratum.json).

Все объявленные независимые regression gates прошли: PiggyMetrics8+3 с фактическими remote/data/callbacks/state и negative witnesses, Petclinic состояние, inventory/document, два актора/credentials/frontend callback, formatter effects, absence/escape, singleton aliases и collection order. Собственные Python tests/checkers: {count} passed, exit0; единственный warning — намеренный duplicate ZIP negative. Первоначальные сбои новой гидратации BigDecimal и сохранения null OneToMany не скрыты: их логи сохранены, общий fix и source MRE прошли. Старые legacy oracle по-прежнему видят Petclinic4E+4C и Piggy1E сверх старого списка; эти графы структурно идентичны №30 и не названы новой регрессией/полным precision успехом. [Регрессии](benchmark/regressions-final/results.json), [legacy сравнение](benchmark/legacy-graph-review.json).

Нового реального holdout не было: отсутствует полный заранее замороженный пакет другой предметной области. G15 — not_run, а не переносимость. G06 — experiment_rejected: bounded reuse завершённых независимых вызовов проверен отдельно, scheduler/общие бюджеты не изменены.

Расчёт parent30→candidate: {p['analysis_seconds']:.6f}→{t['analysis_seconds']:.6f}с; preparation {p['preparation_seconds']:.6f}→{t['preparation_seconds']:.6f}с; полная запись {p['end_to_end_seconds']:.6f}→{t['end_to_end_seconds']:.6f}с. Report serialization {p['report_serialization_seconds']:.6f}→{t['report_serialization_seconds']:.6f}с. RSS {read('benchmark/stages/G16-parent30-paired/summary.json')['peak_rss_bytes']}→{t['peak_rss_bytes']}байт. Репорты выросли; полный цикл и память ухудшились. Prepared расчёт {repeated[0]['analysis_seconds']:.6f}/{repeated[1]['analysis_seconds']:.6f}с сохраняет exact answer и typed witness hash, исходные DB/context неизменны. Report-only fast path проверен побайтно; нормализация циклов включается только при circular reference. Одна пара не доказывает тренд, повтор не включает полную запись отчётов, OS cache не очищался. [Фазы/окружение](benchmark/cost-comparison.json).

{site_line} Локальный S0 отдельно: {score['score']}; пустой remote IoU1 не доказывает межсервисную точность. [Сайт](benchmark/site-score.json), [restore](benchmark/site-best-restored.json). До получения verdict эти записи pending; старый passed не копируется.

## Статусы очереди

Verified относится к заявленному bounded результату цели. Для G13 промпт допускает точно локализованный оставшийся frontier; это не выполненная полная TT цепочка. G06/G15 имеют прямо разрешённые иные статусы.

{chr(10).join(table)}

## Изменения и основания

Поддержаны unknown/null/empty distinctions и безопасный foreach boundary; Collection consumers removeAll/retainAll и общая reference compatibility; проверяемые commuting Map removals; Stream.toList materialization/unmodifiable/lifecycle/order; Optional.map presence/callback/throw; MVC handler specificity и servlet arguments; source/config RestTemplate Apache PATCH с host+port; canonical/guard-only record и component accessor; typed sequential reduce/method references и точные SQL BigDecimal; ограниченное ORM scalar storage без выдуманных unchanged-child UPDATE; source-enum/focus/related-ID NL provenance. Каждая граница и negative counterexample сохранены. Это не полная JVM/ORM/Spring реализация.

Фактические дельты четырёх отношений относительно parent30:

| Сценарий | E before→after | C before→after | R before→after | D before→after |
| --- | --- | --- | --- | --- |
'''
    for sid,d in delta.items():review+='| '+sid+' | '+' | '.join(str(d[r]['before'])+'→'+str(d[r]['after']) for r in ('executes','calls','remote','data'))+' |\n'
    if site.get('scenario_scores'):
        review+='\n## Реальный сайт: изменения S1–S7\n\n| Сценарий | №31 | Δ к №30 |\n| --- | --- | --- |\n'
        for sid,value in site['scenario_scores'].items():review+='| '+sid+' | '+value+' | '+site['delta_scenarios_from_parent'][sid]+' |\n'
        review+='\nS6 ухудшился на0,05903470; S5 без изменения. Общий score вырос на0,01963. Это не доказательство правильности скрытых рёбер.\n'
    review+='\nПолные added/removed tuples по каждому шагу — benchmark/comparisons. Изменение observed-union не является само по себе точностью. Baseline/source/stage SHA сохранены; старые решения, tt-challenge, sample и runs не изменены. DeepSeek, внешние LLM API, модели и целевые JVM/сервисы не запускались.\n'
    save('FINAL_REVIEW.md',review);save('IMPLEMENTATION_REVIEW.md',review)
    relations=score['scenarios']['S0']['sets']
    readme=f'''# Решение №31 — typed-collection-continuations

Родитель №30. Реализованы source-derived коллекции/consumer types, Stream.toList/Optional, MVC/PATCH/reduce и полная корзина с переносом состояния. TT живой фильтр пройден; полная TT NL-цепочка остаётся частичной. [Результаты всех18 целей](FINAL_REVIEW.md), [воспроизведение](REPRODUCE.md), [ограничения](LIMITATIONS.md).

| Показатель | Значение |
| --- | --- |
| Score сайта | {site.get('score_display','—')} ({site['status']}) |
| Тестовый score S0 | {score['score']} |
| S0: executes / calls / remote / data IoU | {' / '.join(str(relations[r]['iou']) for r in ('executes','calls','remote','data'))} |
| Формат S0–S7 | Пройден, все8 ответов,103 шага |
| Время построения ответа | Локально Python{meta['environment']['python']}: расчёт{t['analysis_seconds']:.3f}с, полный цикл{t['end_to_end_seconds']:.3f}с |
| Peak RSS | {t['peak_rss_bytes']}байт, Darwin raw bytes |
| Проверки | {count} passed; real-source и synthetic gates с разной областью oracle |

Запуск из этой папки после установки requirements в отдельную среду:

```sh
python -B code/offline_run.py --source ../../tt-challenge/targets/trainticket --skeleton ../../tt-challenge/skeleton/trainticket.json.gz --context ../../tt-challenge/context --scenarios ../../tt-challenge/scenarios --output /tmp/answer31.json --report /tmp/report31.json
```

SHA ответа: `{meta['submission_sha256']}`. {site_line}

Код/ответ/judge ZIP после оценки неизменны. README внутри judge ZIP — отдельный pre-site snapshot; workspace docs обновляются по фактическому verdict. Моделей/внешних LLM API/DeepSeek нет. Полные target sources TT намеренно не дублируются; exact input manifest прилагается. Пустой S0 remote не является remote validation.
'''
    save('README.md',readme)
    limits='''# Границы №31

- Полная TT NL цепочка поиск→booking→payment не пройдена. Source Set<Ticket> equality/hash, последующие distance/list consumer операции и раннее unknown состояние S6 описаны в benchmark/tt-frontier.json. Изолированные payment пробы не заменяют producer.
- Default path limit4 и общий completion reserve сохранены; observed-union содержит приближения. G06 checker-only эксперимент не включён. Скрытого E/C/R/D oracle нет.
- Cart проверен в explicit application-after-authentication scope. JWT/security/startup, полная validation и неизвестные framework configurations не объявлены поддержанными. Полная dependency/JVM сборка не выполнялась. V3 oracle — postimplementation regression extension; cart не holdout.
- Stream поддержан только для описанных sequential standard JDK операций и доказанных source типов. Custom namesakes, opaque membership/order, unsupported overload/parallel/identity и callbacks с непредставимыми эффектами дают границы. Нет заявления о полном Java21/JDK/Boot support.
- ORM physical storage ограничен известными scalar/enum/foreign-key columns и проверенными unchanged существующими children. Новые/изменённые cascade children, orphan/removal/provider dirty checking не выдумываются. Null entity поле не превращается в известный пустой read.
- MVC advice ordering/scoped ambiguity, неразрешённые @Bean factories/profiles/environment/deployment и многие библиотеки остаются unsupported. Диагностика не подавляется ради pass; для formatter locale/codec completeness сохраняются явные ограничения.
- BigDecimal точен для поддержанных операций/SQL lexemes; unsupported rounding/precision остаётся boundary. Diagnostic cycles представлены $cycle_ref только в отчёте, исходный heap/wire не меняется.
- Piggy/cart required-edge oracle не даёт полного precision/IoU. Legacy старые edge lists сохраняют extras относительно source formatter/MVC, эти extras были и в №30. Маленькие synthetic точные oracle не заменяют новый реальный проект.
- G15 not_run: нет полного нового реального пакета source+готовый skeleton+context+explicit/NL scenarios+pre-result oracle. Конкретный missing-input список — benchmark/holdout-availability.json.
- Время/RSS измерены на одной машине Darwin/arm64/Python3.11.9; Windows/Linux runtime не запускались. Нормализация Linux KiB проверена fixture. Полное время и память выше parent30; SLA/статистический тренд не заявлены.
- Не запускались target Java/JVM, Maven/Gradle, Docker/сервисы, модели, DeepSeek, внешние LLM API. Анализатору нужен готовый skeleton; его построение с нуля вне задачи.
'''
    save('LIMITATIONS.md',limits)
    commands=[]
    for path in sorted((V/'benchmark/overnight').rglob('run.json')):
        x=json.loads(path.read_text());commands.append({'evidence':str(path.relative_to(V)),'command':x.get('command'),'cwd_at_run':x.get('cwd'),'started_at':x.get('started_at'),'returncode':x.get('returncode'),'timed_out':x.get('timed_out'),'elapsed_seconds':x.get('elapsed_seconds')})
    (V/'benchmark/command-index.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
    reproduce='''# Воспроизведение №31

CWD — корень извлечённого solution_31 либо соответствующая solutions/<score>_typed-collection-continuations. Python3.11.9 и exact packages — requirements.txt и benchmark/final/metadata.json. Все Java fixtures только парсятся. Исторические команды установки/сервисов/моделей не запускать.

Фактически выполненные команды, CWD, UTC timestamp, exit/timeout, code/input hashes, stdout/stderr находятся в benchmark/command-index.json и связанных benchmark/overnight/Gxx/<label>/run.json. Ошибки предыдущих попыток сохранены. После переименования папки исходные абсолютные historical CWD остаются свидетельством; для нового запуска использовать текущий CWD и новые output paths. Не перезаписывать benchmark/final или assessed ZIP.

Полный tt-challenge нужен отдельно: skeleton/trainticket.json.gz, context/db-after-warmup.sql.gz, scenarios/S0–S7.json, targets/trainticket. Точные хеши основных файлов входа — development/input-sha256.json; source fingerprint — benchmark/final/summary.json, hashes исходников TT — development/protected-files.json. Исходники TT не включены: без них full TT replay не воспроизводится. Real regression source/config/skeleton/context/oracle в validation_inputs и development/oracles включены полностью. Они не являются секретной judge-разметкой.

Без запуска target apps:

```sh
PYTHONPATH=code python -B -m pytest -q -p no:cacheprovider code/tests checks/tests
python -B checks/run_regression_gate.py --output /tmp/regressions31-new
python -B checks/run_cart_profile.py --output /tmp/cart31-new
python -B checks/check_cart_profile.py --trace /tmp/cart31-new --output /tmp/cart31-new/checks.json
python -B checks/check_cart_mutations.py --trace /tmp/cart31-new --output /tmp/cart31-new/mutations
```

Это интерфейсы действительно выполненных проверок с заменённым output. Результаты текущего прогона — benchmark/regressions-final; actual exit0 основного набора1953 passed — benchmark/overnight/G14/exact-final-all-unit-checkers. Исправленный упаковщик добавляет2 meaningful negative/link controls; итоговый extracted run —1955 passed в benchmark/analytical-corrected-verification-logs/tests.stdout.txt. Format/gold — отдельные checker-процессы; inference не читает oracle/expected.

TT и точный judge archive, где TT_CHALLENGE — абсолютная папка исходного challenge:

```sh
python -B code/offline_run.py --source "$TT_CHALLENGE/targets/trainticket" --skeleton "$TT_CHALLENGE/skeleton/trainticket.json.gz" --context "$TT_CHALLENGE/context" --scenarios "$TT_CHALLENGE/scenarios" --output /tmp/answer31-new.json --report /tmp/report31-new.json
python -B "$TT_CHALLENGE/platform/evaluate_golden.py" --check "$TT_CHALLENGE/skeleton/trainticket.json.gz" /tmp/answer31-new.json --json
python -B "$TT_CHALLENGE/platform/evaluate_golden.py" "$TT_CHALLENGE/gold/S0.json" /tmp/answer31-new.json --json
python -B checks/replay_archive.py --archive solution.zip --source "$TT_CHALLENGE/targets/trainticket" --skeleton "$TT_CHALLENGE/skeleton/trainticket.json.gz" --context "$TT_CHALLENGE/context" --scenarios "$TT_CHALLENGE/scenarios" --output /tmp/archive31-new
python -B checks/repeat_prepared.py --source "$TT_CHALLENGE/targets/trainticket" --skeleton "$TT_CHALLENGE/skeleton/trainticket.json.gz" --context "$TT_CHALLENGE/context" --scenarios "$TT_CHALLENGE/scenarios" --expected submission.json --output /tmp/repeat31-new.json --repetitions 2
```

Path limit4, constraints on, observed-union. Prepared expected — comparator only; DB/context остаются исходными. Prepared measured code отличается от final только report-write helper/test; analyze/finite_report и inference state не менялись (benchmark/prepared-report-only-delta.json). Последующий exact ZIP replay проверяет final code.

Для восстановления исключённого промежуточного full report: python -B checks/stage_benchmark.py G02-bulk-contract-only --existing-snapshot --challenge "$TT_CHALLENGE" --output /tmp/G02-report31-new. Интерфейс с --output добавлен после основного прогона; именно эта команда ещё не выполнялась. Исходная фактическая команда без этого flag сохранена в command-index. Для новой current-code стадии использовать новый stage-name либо явный offline CLI. Сохранённые development/stages и benchmark/stages неизменяемы. В компактном analytical ZIP избыточные промежуточные full reports могут отсутствовать; точные omission hashes и влияние перечисляет PACKAGE_OMISSIONS.json, snapshots/comparisons и ключевые baseline/final traces сохранены.

Ещё не выполнено: свежий real holdout (точные отсутствующие входы в benchmark/holdout-availability.json), полный TT цепочный успех за локализованной границей, target/JVM execution (вне разрешённого scope). Следующий допустимый semantic эксперимент — source-generic Set<object> equals/hash callback MRE перед дальнейшим TT поиском. Ни одна из этих проверок не записана как passed.
'''
    save('REPRODUCE.md',reproduce)
    save('development/contract-sources.md','''# Первичные контракты

Контракты проверены чтением официальных Java21 API и Spring reference через Context7; приложения/JVM не запускались. Spring current reference7.0.9 не доказывает точную разрешённую транзитивную версию cart Boot4.0.6.

- Java21 Stream: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html
- Java21 Optional: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html
- Java21 Collection/List/HashSet: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Collection.html
- Throwable: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Throwable.html
- LocalDateTime: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/LocalDateTime.html
- Spring MVC exception specificity/arguments: https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-exceptionhandler.html
- RestTemplate request factory/PATCH: https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/client/RestTemplate.html
- OrderColumn contiguous positions: https://jakarta.ee/specifications/platform/9/apidocs/jakarta/persistence/ordercolumn

Case-insensitive SQL column lookup ограничен объявленными CREATE identifiers, а не угадыванием полей по домену. Version-specific full JDK/ORM behavior не заявлен.
''')
    print(json.dumps({'documents_written':6,'site_status':site['status'],'tests':count,'G18':next(g['status'] for g in state['goals'] if g['goal_id']=='G18')}))


if __name__=='__main__':main()
