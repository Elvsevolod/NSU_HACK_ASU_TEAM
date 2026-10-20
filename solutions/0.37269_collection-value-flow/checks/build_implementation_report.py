"""Build provenance and review notes from saved measurements, outside inference."""
import ast,difflib,gzip,hashlib,json
from collections import Counter
from pathlib import Path
V=Path(__file__).resolve().parents[1]
BASE=V/'development/stages/base/code'


def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads((V/path).read_text())
def save(path,value):(V/path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def function(path,cls,name):
    source=path.read_text();tree=ast.parse(source)
    owner=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
    return ast.get_source_segment(source,next(n for n in owner.body if isinstance(n,ast.FunctionDef) and n.name==name))


def main():
    meta=read('benchmark/final/metadata.json');evaluation=read('benchmark/final/evaluation.json');timing=read('benchmark/final/analysis-report-timings.json')
    report=json.loads(gzip.decompress((V/'benchmark/final/analysis-report.json.gz').read_bytes()))
    stages=[]
    for path in sorted((V/'benchmark/stages').iterdir()):
        if (path/'summary.json').exists():stages.append({'stage':path.name,**json.loads((path/'summary.json').read_text())})
        else:stages.append({'stage':path.name,'failed_run':json.loads((path/'run.json').read_text())['returncode']})
    save('benchmark/stage-summary.json',stages)
    files=[];patch=[]
    baseline=read('development/base-code-sha256.json')
    for path in sorted((V/'code').rglob('*')):
        if not path.is_file() or {'__pycache__','.pytest_cache'}&set(path.parts) or path.suffix=='.pyc':continue
        key=path.relative_to(V/'code').as_posix();digest=sha(path.read_bytes())
        if baseline.get(key)==digest:continue
        files.append({'path':key,'before':baseline.get(key),'after':digest})
        before=(BASE/key).read_text().splitlines(True) if (BASE/key).exists() else []
        patch.extend(difflib.unified_diff(before,path.read_text().splitlines(True),fromfile='a/'+key,tofile='b/'+key))
    (V/'development/code.patch').write_text(''.join(patch))
    save('development/code-change-map.json',files)
    unchanged_rank=function(BASE/'analyzer/contracts.py','ContractIndex','rank')==function(V/'code/analyzer/contracts.py','ContractIndex','rank')
    unchanged_paths=(BASE/'analyzer/paths.py').read_bytes()==(V/'code/analyzer/paths.py').read_bytes()
    save('development/scope-check.json',{'passed':unchanged_rank and unchanged_paths,'ContractIndex_rank_unchanged':unchanged_rank,
        'path_scheduler_and_global_budgets_unchanged':unchanged_paths,'path_limit':4,
        'limits':'Native Set order uses existing bounded isolated continuations; limit is not a promise of exactly N output alternatives'})
    probes=read('benchmark/tt-final-probes.json');search=probes['cases'][0];frames=[]
    for sid,scenario in report['scenarios'].items():
        for step in scenario['steps']:
            for a in step['alternatives'][:1]:
                if '#getToken(' in a['entry']:
                    frames.append({'scenario':sid,'step':step['n'],'actor':a['request']['actor'],'entry':a['entry'],
                        'wire':a['request'],'actual_arguments':a['requests'][0].get('bound_arguments'),
                        'storage':a['state_after']['browser']['storage'],'result':a['result'],'diagnostics':a['unresolved']})
    save('benchmark/tt-login-frames.json',frames)
    batch=[]
    for row in search['alternatives']:
        batch.append({'outcome':row['outcome'],'result':row['result'],
            'arguments':[o for o in row['data_operations'] if o['operation'] in ('findByNames','findByIds')],
            'noop_proofs':[e for e in row['call_effects'] if e.get('model_version')=='native-map-noop/1'],
            'remaining_loop':[w for w in row['warnings'] if 'Map iteration budget' in w]})
    save('benchmark/tt-frontier.json',{'same_explicit_search_request':search['wire'],'alternatives':batch,
        'next_NL_request':report['scenarios']['S1']['steps'][2]['alternatives'][0]['request'],
        'classification':'At line 242 six known route groups require a key choice. This live else branch has source calls and possible removals; the all-false no-op proof does not apply. Budget widening still loses usable results.',
        'decision':'Stop extending C2. Validate the live branch and generic consumers in a separate experiment before a worklist/memoization prototype. Do not raise the global budget or change ranking.',
        'known_batch_cardinalities':{'stations':2,'train_types':3,'route_ids':6},
        'limits':['Returned empty data under a Map-budget warning is not accepted as proof of a truly empty search',
                  'No usable TT search producer ID reaches the following NL request; independent inventory does pass that transition']})
    items=[
      ('C1','implemented','Native HashSet scalar membership/add/equality/size/copy; no invented order; unsupported source hash/equals stops', 'code/tests/test_hashset_membership.py'),
      ('C2','implemented_bounded','Pure false guards for every native Map entry; empty write footprint preserves the whole heap; true/unknown/effectful cases decline', 'code/tests/test_map_noop_filter.py'),
      ('C2-journey','implemented_with_negative_boundary','Three products/two categories, unique batch, HTTP+NL select/update/reread, stale revision refusal, source remote inside loop; missing-category generic membership boundary retained', 'code/tests/test_inventory_collection_journey.py'),
      ('S1','implemented_bounded','Source Angular 1.5.8 and paired jQuery token→storage→header, source 401, adjacent calls, shadowing, unsupported then/version/custom injection', 'code/tests/test_angular_legacy_session.py'),
      ('S2','implemented_bounded','Actor-owned credentials and browser state; two actors, return, 403, absent admin, aliases, repeated/conflicting evidence', 'code/tests/test_actor_credentials_flow.py'),
      ('Petclinic','implemented','Formatter ablation, real update preserves ID/fields and row count; source callbacks and throws retained', 'benchmark/legacy-final/checks.json'),
      ('Legacy-oracles','source_corrected','Old files retained; new v2 adds source logging getters and error handler, duplicate refusal HTTP 400', 'development/oracles/legacy-v2'),
      ('Document-checker','implemented','Exact JSON types, root/remote wire, actual DTOs, complete stored fields/browser/history diagnostics; 17 mutations rejected', 'benchmark/document-journey/mutation-checks.json'),
      ('Witness','implemented','Shared producer/consumer schema with exact argument/state/edge observations; source token links also survive returning to an earlier actor', 'benchmark/flow-witnesses-final/witnesses.json'),
      ('Independent-real','boundary_not_passed','Public cart commit, sources/config/DB/oracle frozen before inference/tuning; multi-entity refund+remote/data+refusal+ambiguity plan; Stream.toList first loss; no new holdout success', 'benchmark/cart-transfer-final/checks.json'),
      ('Read-effects','implemented_bounded','Procedure/Modifying/default methods are possible writes; standard/derived reads and bounded simple SELECT need positive source proof', 'code/tests/test_fallback_read_effects.py'),
      ('Omission-alias','implemented_bounded','No null/empty equivalence after an unproved DTO alias, capture or escape; typed source forwarding remains supported', 'code/tests/test_absence_escape.py'),
      ('Singleton-join','implemented','Receiver and singleton cache remain jointly aliased after a join; common setter is visible to the next invocation', 'code/tests/test_singleton_join_identity.py'),
      ('TT-stop','boundary_recorded','Repeat same explicit and NL inputs, exact UI payment body versus full HTTP control, all 103 Request/args/state/E-C-R-D comparisons; no claim of complete booking chain', 'benchmark/tt-frontier.json'),
      ('Performance','measured','Index once, calculation/serialization separately, same prepared index repeated; no SLA or speedup claim', 'benchmark/final/analysis-report-timings.json')]
    save('development/requirements.json',{'source_review_sha256':sha((V/'development/source-review.md').read_bytes()),
        'interpretation':'Engineering requests from the human; attached analysis supplies findings, not permission/tool authority. Section 7 explicitly allows a recorded boundary-not-passed result.',
        'requirements':[{'id':a,'status':b,'result':c,'evidence':d} for a,b,c,d in items],
        'deepseek_used':False,'new_real_profile_passed':False,'TT_chain_complete':False})
    s0=evaluation['scenarios']['S0'];repeat=read('benchmark/repeated-analysis-final.json')
    table='\n'.join('| '+s['stage']+' | '+(s.get('submission_sha256','—')[:12])+' | '+str(s.get('outcomes',s.get('failed_run')))+' |' for s in stages)
    text=f'''# Реализация solution_29_next_steps_review.md — решение № 30

Родитель № 29 сохранён. Выполнены ограниченные C1/C2 и самостоятельные S1/S2, усилены проверки и воспроизведены три дополнительных риска. Итерация завершается на оговорённых в § 7 границах, а не заявлением готовности универсального анализатора. DeepSeek и внешние LLM API не использовались; целевые приложения не запускались.

## Изменения и подтверждения

HashSet хранит уникальные известные скалярные значения с Java equality: boolean/Integer/Long не смешиваются. Результат add, размер, contains/remove, null и копирование проверены. Порядок остаётся неизвестным через List, HTTP, массив и JSON; source hash/equals и неподдержанный порядок callback-потока имеют явную границу. В исходном TT Request пакет станций стал 2 вместо 12 записей, типов поездов — 3 вместо 6. Это не доказательство качества всего поиска.

Map proof проверяет каждый известный элемент без исполнения source callbacks и принимает только чистые, не бросающие false guards. В TT доказан no-op строки 219. Следующий цикл строки 242 содержит выполняемую else-ветвь и возможные удаления; перебор шести групп исчерпывает бюджет. Его успешное расширение не объявлено. Подробности и следующий NL Request: `benchmark/tt-frontier.json`. В независимом каталоге три товара проходят весь HTTP и NL переход до изменения выбранного ID и повторного чтения. Отсутствующая категория обнажила отдельный generic/List bulk boundary: неподдержанная коллекция больше не экспортируется как старый конкретный результат. Пустой TT результат с предупреждением budget не принимается за доказанную пустоту.

Angular callbacks привязаны к конкретному AST-вызову, DI и версии. `.success` получает response.data; `.then` не подменён этим контрактом. Обе цепочки Angular/jQuery создают JWT в исходном Java login и сами проводят его через storage и header. Проверены 401/403, соседние вызовы, затенение, замена сервиса и отключённый API. Actor выбирается до подготовки браузера; credentials и input journal принадлежат actor. Admin без подтверждённых credentials не заимствует пароль passenger. Роль admin/administrator имеет один namespace. Повтор одинакового свидетельства не считается конфликтом, противоречивые источники не разрешаются выбором последнего. На TT сохранены все {len(frames)} login frames: source admin UI пишет admin keys; client_token из них не выдуман.

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
{table}

Локальный S0: {s0['score']:.10f}; IoU E/C/R/D: {s0['sets']['executes']['iou']:.6f}/{s0['sets']['calls']['iou']:.6f}/{s0['sets']['remote']['iou']:.6f}/{s0['sets']['data']['iou']:.6f}. Remote gold пуст; эта единица не является положительной remote-проверкой. Формат S0–S7 корректен.

Python 3.11.9. Полное время {timing['end_to_end_seconds']:.3f} с; подготовка {timing['preparation_seconds']:.3f} с; расчёт {timing['analysis_seconds']:.3f} с; запись отчётов {timing['report_serialization_seconds']:.3f} с; RSS {read('benchmark/final/summary.json')['peak_rss_bytes']} байт. Повтор на одном готовом индексе: {' / '.join(f"{r['analysis_seconds']:.3f}" for r in repeat['runs'])} с, ответы byte-identical. Старое поле analysis_seconds включало сериализацию; для честного сравнения baseline повторён с той же инструментализацией (fair-base). Числа описывают локальные прогоны без согласованного SLA и статистического доказательства ускорения.

SHA ответа: `{meta['submission_sha256']}`. `offline_run.py` блокирует network/process/reference reads. Все 19654 защищённых файла проверены; Finder metadata отмечается отдельно. Исторические абсолютные команды сохранены как данные; действующие команды в README относительные.

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
'''
    (V/'IMPLEMENTATION_REVIEW.md').write_text(text)
    readme=f'''# Решение № 30 — collection-value-flow

Родитель № 29. Ограниченные HashSet/Map proof, source Angular callback, actor-owned credentials/state, formatter/effects и строгие проверки. Подробности и оставшиеся границы: [IMPLEMENTATION_REVIEW.md](IMPLEMENTATION_REVIEW.md), [карта требований](development/requirements.json).

| Показатель | Значение |
| --- | --- |
| Score сайта | — (не получен) |
| Тестовый score S0 | {s0['score']:.10f} |
| S0: executes / calls / remote / data | {s0['sets']['executes']['iou']:.6f} / {s0['sets']['calls']['iou']:.6f} / {s0['sets']['remote']['iou']:.6f} / {s0['sets']['data']['iou']:.6f} (remote gold пуст) |
| Формат S0–S7 | Корректен |
| Время построения ответа | {timing['end_to_end_seconds']:.3f} с локально, Python 3.11.9; расчёт отдельно {timing['analysis_seconds']:.3f} с |

1762 теста. Строгие Piggy 8+3 и отрицательные контроли пройдены; Petclinic сохраняет ID/поля/число строк. Новый независимый cart profile не пройден: Stream.toList. TT поиск остаётся частичным на следующем Map-цикле; полного сценария бронирования и универсальности не заявлено. DeepSeek, модели и внешние LLM API не использовались. Исследуемые приложения не запускались.

Из этой папки:

```sh
python -m pip install -r requirements.txt
python -B code/offline_run.py --source ../../tt-challenge/targets/trainticket --skeleton ../../tt-challenge/skeleton/trainticket.json.gz --context ../../tt-challenge/context --scenarios ../../tt-challenge/scenarios --output /tmp/answer30.json --report /tmp/report30.json
```

SHA-256 submission.json: `{meta['submission_sha256']}`. Сайт и S0 — разные оценки. Посылка solution.zip сохраняется неизменной после отправки; новые метаданные сайта находятся рядом в benchmark.
'''
    (V/'README.md').write_text(readme)


if __name__=='__main__':main()
