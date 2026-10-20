# Решение №31: результаты G01–G18

Срез документа: 2026-10-18T20:41:19.061044+00:00. Родитель — №30. Принятый код — `G16-report-fastpath`; SHA ответа `25996b7d3d6d20590934c4cc70b3305046ec3cd686b41465021b84fbf032a977`.

Корзина проходит полные explicit и NL цепочки из восьми шагов в явно заданной прикладной границе после аутентификации. Из фактического GET выбран единственный APPROVED payment21/order11; refund сохраняет REFUNDED, remote PATCH переводит order11 в PENDING, сервер строит ответ с total12.5 даже при клиентском Void.class. Повтор даёт409 до записи/remote, отсутствующий999 даёт404, неоднозначный шаг7 не выполняет обработчик, reread сохраняет чужие строки и rejected payment23. Проверены реальные native Long аргументы, контроллеры, ответы, source mapper/total/subtotal, состояния до/после и15 per-step executes обязанностей. Все47 мутаций реальных explicit/NL трасс отвергнуты до нормализации NL. [Проверка](benchmark/regressions-final/cart/checks.json), [мутации](benchmark/regressions-final/cart/mutations/summary.json). Cart уже настроен в этой итерации и не является свежим holdout; v3 усиливает source-derived regression обязанности после реализации, v1/v2 не переписаны.

В TT известный поиск проходит живой Map-фильтр шести групп: типы элемента ORM-списка, case-insensitive OrderColumn и source-generated getters/setter сохранены. Полная NL-цепочка поиск→booking→payment остаётся неполной: source Set<Ticket> equality/hash и следующие distance/list consumers дают явные границы; в S6 таблицы уже неизвестны после более ранних admin input/authentication boundaries. Изолированный payment по объявленным исходным строкам успешен, но не считается полной цепочкой. Реальный UI отправляет orderId/tripId; userId/price в тело не добавлены. [Все103 шага и frontier](benchmark/tt-frontier.json).

Причинный ledger S6 устанавливает первое расширение station/train_type в observer events9/122 внутри AnalysisBoundary writable-closure fallback; subsequent joins переносят unknown. Это не установленная SQL-запись. Исторические шесть union-потерь base→C1 впервые на step8, другие12 step1-рёбер остаются на step7. Отдельный bulk-descriptor ablation и diagnostic order/completion reserves разделяют три фактора; correctness каждого hidden edge неизвестна. В новой версии opaque foreach больше не создаёт известную пустоту. [Ledger](benchmark/overnight/G02/causal-ledger-v2/causal-ledger.json), [исправление одного пути evidence](benchmark/overnight/G02/causal-ledger-v2/evidence-path-erratum.json).

Все объявленные независимые regression gates прошли: PiggyMetrics8+3 с фактическими remote/data/callbacks/state и negative witnesses, Petclinic состояние, inventory/document, два актора/credentials/frontend callback, formatter effects, absence/escape, singleton aliases и collection order. Собственные Python tests/checkers: 1955 passed, exit0; единственный warning — намеренный duplicate ZIP negative. Первоначальные сбои новой гидратации BigDecimal и сохранения null OneToMany не скрыты: их логи сохранены, общий fix и source MRE прошли. Старые legacy oracle по-прежнему видят Petclinic4E+4C и Piggy1E сверх старого списка; эти графы структурно идентичны №30 и не названы новой регрессией/полным precision успехом. [Регрессии](benchmark/regressions-final/results.json), [legacy сравнение](benchmark/legacy-graph-review.json).

Нового реального holdout не было: отсутствует полный заранее замороженный пакет другой предметной области. G15 — not_run, а не переносимость. G06 — experiment_rejected: bounded reuse завершённых независимых вызовов проверен отдельно, scheduler/общие бюджеты не изменены.

Расчёт parent30→candidate: 67.266877→65.666914с; preparation 6.328514→6.646167с; полная запись 85.118660→89.395566с. Report serialization 11.488528→17.045513с. RSS 459784192→557957120байт. Репорты выросли; полный цикл и память ухудшились. Prepared расчёт 53.787440/52.360761с сохраняет exact answer и typed witness hash, исходные DB/context неизменны. Report-only fast path проверен побайтно; нормализация циклов включается только при circular reference. Одна пара не доказывает тренд, повтор не включает полную запись отчётов, OS cache не очищался. [Фазы/окружение](benchmark/cost-comparison.json).

Сайт: 0.39232, статус verified, посылка 1665875. Восстановление №5: verified, посылка 1665877. Локальный S0 отдельно: 0.8008928571428572; пустой remote IoU1 не доказывает межсервисную точность. [Сайт](benchmark/site-score.json), [restore](benchmark/site-best-restored.json). До получения verdict эти записи pending; старый passed не копируется.

## Статусы очереди

Verified относится к заявленному bounded результату цели. Для G13 промпт допускает точно локализованный оставшийся frontier; это не выполненная полная TT цепочка. G06/G15 имеют прямо разрешённые иные статусы.

| Цель | Фактический статус | Evidence | Ограничение / следующий шаг |
| --- | --- | --- | --- |
| G01 | verified | [baseline-gates.json](benchmark/overnight/G01/baseline-gates.json), [baseline-comparison-normalized.json](benchmark/overnight/G01/baseline-comparison-normalized.json) | Проверено в заявленном ограниченном контракте. |
| G02 | verified | [causal-ledger-v2](benchmark/overnight/G02/causal-ledger-v2), [G01-parent30--G02-bulk-contract-only.json](benchmark/comparisons/G01-parent30--G02-bulk-contract-only.json) | Скрытый эталон S6 отсутствует; причины наблюдаемой дельты разделены. |
| G03 | verified | [G03-unknown-foreach](benchmark/stages/G03-unknown-foreach), [G01-parent30--G03-unknown-foreach.json](benchmark/comparisons/G01-parent30--G03-unknown-foreach.json) | Проверено в заявленном ограниченном контракте. |
| G04 | verified | [G01-parent30--G04-bulk-consumers.json](benchmark/comparisons/G01-parent30--G04-bulk-consumers.json), [G03-unknown-foreach--G04-bulk-consumers.json](benchmark/comparisons/G03-unknown-foreach--G04-bulk-consumers.json) | Проверено в заявленном ограниченном контракте. |
| G05 | verified | [tt-generated-setter-consumer](benchmark/overnight/G13/tt-generated-setter-consumer), [G13-live-route-filter](benchmark/stages/G13-live-route-filter) | Проверено в заявленном ограниченном контракте. |
| G06 | experiment_rejected | [residual-state-pilot-v5](benchmark/overnight/G06/residual-state-pilot-v5), [G06-residual-state-decision](development/checkpoints/G06-residual-state-decision) | Пилот не включён в scheduler; отрицательное интеграционное решение. |
| G07 | verified | [missing-witnesses-are-failures](benchmark/overnight/G07/missing-witnesses-are-failures), [accepted-full-suite](benchmark/overnight/G09/accepted-full-suite) | Проверено в заявленном ограниченном контракте. |
| G08 | verified | [accepted-full-suite](benchmark/overnight/G09/accepted-full-suite), [diamond-source-typing](benchmark/overnight/G09/diamond-source-typing) | Проверено в заявленном ограниченном контракте. |
| G09 | verified | [state-and-producer-witness](benchmark/overnight/G12/state-and-producer-witness), [full-suite-linked-state](benchmark/overnight/G12/full-suite-linked-state) | Проверено в заявленном ограниченном контракте. |
| G10 | verified | [state-and-producer-witness](benchmark/overnight/G12/state-and-producer-witness), [full-suite-linked-state](benchmark/overnight/G12/full-suite-linked-state) | Проверено в заявленном ограниченном контракте. |
| G11 | verified | [state-and-producer-witness](benchmark/overnight/G12/state-and-producer-witness), [full-suite-linked-state](benchmark/overnight/G12/full-suite-linked-state) | Проверено в заявленном ограниченном контракте. |
| G12 | verified | [cart-transfer-final](benchmark/cart-transfer-final), [final-code-and-checker-suite](benchmark/overnight/G14/final-code-and-checker-suite) | Проверено в заявленном ограниченном контракте. |
| G13 | verified | [tt-frontier.json](benchmark/tt-frontier.json), [G01-parent30--G16-report-fastpath.json](benchmark/comparisons/G01-parent30--G16-report-fastpath.json) | Полная TT NL-цепочка не пройдена; принят точный оставшийся frontier по альтернативе G13. |
| G14 | verified | [legacy-graph-review.json](benchmark/legacy-graph-review.json), [protected-integrity.json](benchmark/protected-integrity.json) | Проверено в заявленном ограниченном контракте. |
| G15 | not_run | [holdout-availability.json](benchmark/holdout-availability.json) | Нет нового полного замороженного реального пакета source/skeleton/context/scenarios/oracle. |
| G16 | verified | [results.json](benchmark/report-phase-profile/results.json), [prepared-report-only-delta.json](benchmark/prepared-report-only-delta.json) | Одна локальная пара и два prepared-повтора; память и полное время выросли. |
| G17 | verified | [server-verification.json](benchmark/server-verification.json), [site-best-restored.json](benchmark/site-best-restored.json) | Сайт: 0.39232, статус verified, посылка 1665875. Восстановление №5: verified, посылка 1665877. |
| G18 | verified | [analytical-corrected-verification-logs](benchmark/analytical-corrected-verification-logs), [analytical-package-defect.json](benchmark/analytical-package-defect.json) | Проверка архива и его SHA находятся в отдельном внешнем .check.json; оценённый judge ZIP не пересобирается. |

## Изменения и основания

Поддержаны unknown/null/empty distinctions и безопасный foreach boundary; Collection consumers removeAll/retainAll и общая reference compatibility; проверяемые commuting Map removals; Stream.toList materialization/unmodifiable/lifecycle/order; Optional.map presence/callback/throw; MVC handler specificity и servlet arguments; source/config RestTemplate Apache PATCH с host+port; canonical/guard-only record и component accessor; typed sequential reduce/method references и точные SQL BigDecimal; ограниченное ORM scalar storage без выдуманных unchanged-child UPDATE; source-enum/focus/related-ID NL provenance. Каждая граница и negative counterexample сохранены. Это не полная JVM/ORM/Spring реализация.

Фактические дельты четырёх отношений относительно parent30:

| Сценарий | E before→after | C before→after | R before→after | D before→after |
| --- | --- | --- | --- | --- |
| S0 | 30→30 | 15→15 | 0→0 | 7→7 |
| S1 | 104→116 | 98→111 | 14→16 | 24→25 |
| S2 | 103→114 | 94→107 | 12→14 | 20→21 |
| S3 | 93→106 | 84→97 | 10→12 | 22→23 |
| S4 | 91→103 | 90→103 | 11→13 | 19→20 |
| S5 | 108→108 | 115→115 | 16→16 | 12→12 |
| S6 | 116→107 | 98→86 | 18→14 | 16→15 |
| S7 | 93→105 | 82→95 | 13→15 | 17→18 |

## Реальный сайт: изменения S1–S7

| Сценарий | №31 | Δ к №30 |
| --- | --- | --- |
| S1 | 0.43284093 | 0.03757536 |
| S2 | 0.36126784 | 0.03560533 |
| S3 | 0.45315187 | 0.04520240 |
| S4 | 0.38424834 | 0.03750761 |
| S5 | 0.29841313 | 0E-8 |
| S6 | 0.37967987 | -0.05903470 |
| S7 | 0.43666662 | 0.04055214 |

S6 ухудшился на0,05903470; S5 без изменения. Общий score вырос на0,01963. Это не доказательство правильности скрытых рёбер.

Полные added/removed tuples по каждому шагу — benchmark/comparisons. Изменение observed-union не является само по себе точностью. Baseline/source/stage SHA сохранены; старые решения, tt-challenge, sample и runs не изменены. DeepSeek, внешние LLM API, модели и целевые JVM/сервисы не запускались.
