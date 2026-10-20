# Матрица готовности №33, E21

E25 дополняет R06 исправлением default response eligibility после отдельного actual HTTP500 reproducer. 2418 code tests,159 checker tests,17 integrations проходят; [границы и fixture corrections](development/IMPLEMENTATION_E25.md). Артефакты E21 ниже исторические. Полное завершение цели ещё не доказано.

Цель R01–R08 активна. Проверенные локальные механизмы, завершённые отрицательные эксперименты и непрошедший полный перенос отмечены отдельно. 2370 code tests, 158 checker tests и 17 integrations проходят; site score неизвестен.

| Обязательство | Статус | Доказанная граница / следующее действие |
| --- | --- | --- |
| R01: static storage, initialization, isolation | verified, bounded local/integration | Сохранён механизм №32; новые charset controls и полный набор проходят. Нет полного JVM class initialization. |
| R02: List.indexOf/get, native kind, bounds | verified, local/regression | Прежние primitive/boxed/source namesake/guard tests проходят в полном наборе. |
| R03: Stream completion / Optional presence | verified, bounded local/integration | Сохранены return/throw, reuse, finite forEach и Optional controls. Произвольные terminal/callbacks не добавлялись. |
| R04: source/generated Set equality/hash | verified, bounded local/integration | Сохранён принятый scope; абстрактный repository Set не объявляется конкретным HashSet. |
| R05: first-loss / один stop-only summary | verified, bounded local | 168 записей нового downstream ledger; summary не стал общим scheduler. Неопределённые слои не выдаются за установленную единственную причину. |
| R06: ORM order / history producer agreement | verified, bounded local/integration | Прежние order/alias/producer controls проходят. TT post-auth цепочка в исходном контексте не подтверждена. |
| R06: новый response-backed history choice | verified, bounded development | 31 source fixture, завершённые typed producers и два digest. Singular GET, один PathVariable, явная английская prior-creation ссылка. Compound/UI/неполные origins не разрешаются автоматически. |
| R07: исходный frozen A/B №32 | verified, historical experiment | Данные, splits, source facts и исходные A/B результаты сохранены; новый B не принят автоматически. |
| R07: licensing retrieval holdout | verified, retrieval only | 12 разрешимых запросов и4 отказа; не полный state/graph oracle. После просмотра результатов — development. |
| R07: два новых реальных source dataset | verified, bounded source-engineered oracle | Employment и healthcare: исходники/config/skeleton/state, 23 сценария/74 шага frozen до inference. Нет dynamic ground truth и второго независимого автора oracle; error bytes и некоторые framework defaults partial. |
| R07: новые explicit chains | failed/partial full transfer | Строгие E/C/R/D каждого alternative, native binding, wire/response, ordered SQL/state/origin: employment10/11, healthcare11/11. Missing-route remote error не пройден. |
| R07: новые NL chains | failed/partial full transfer | На E20 lexical12/44 точных execution steps плюс8/8 отказов; строгий wire/origin gate не проходит. Заголовки и происхождение ID не выдумывались, oracle не менялся. |
| R07: organization/library | failed, historical partial | Сохранены отдельные partial oracle и причинные разборы: organization explicit5/10, library0/11 по прежнему partial chain checker. Эти проекты уже development. |
| R08: разрешения, веса, runtime и code audit | verified on this Mac/MPS | UniXcoder, CodeT5+110M embedding, CodeRankEmbed и Qwen реально выполнены offline; custom source проверен, strict local weights. |
| R08: ranking/cost/context ablation | verified, pilot | Выбор/пороги закреплены на dev. Новый CodeRank query test R1 13/32 против BM25 6/32, accept0/40 у обоих; переноса полного исполнения это не доказывает. |
| R08: paired downstream | verified, experiment completed | Старое сравнение четырёх моделей сохранено. Новый CodeRank E20 same/expanded:5/44 execution steps противlexical12/44, плюс8/8 отказов у каждого, explicit answers unchanged и audit0. |
| R08: model default adoption | experiment_rejected | Устойчивой downstream-пользы не показано. Нельзя принять модель по одному ranking улучшению на уже наблюдавшихся приложениях. |
| R08: CPU/другой Mac/quantization/обучение | not_run | Не входят в проверенный MPS-пилот; model runtime не объявлен проверенным на этих конфигурациях. |
| R08: reranker | not_run, deferred by evidence | Пока преобладают refusal/binding/semantics потери, дополнительная модель не имеет доказанной downstream-пользы. |
| Literal JSON body/order/ownership | verified, bounded local/integration | E15–E16, 20 fixtures: сохранены значения, omission/null, native kinds, setter order; JSON metadata не становится внутренним symbol. |
| Полный source-faithful TT UI | failed / boundary recorded | Admin callback/client guard и completion budgets сохранены; guard не отключался, значений credentials/price/userId не подставлялось. |
| Default отсутствующий route | source preflight verified; implementation pending | Pinned Boot3.4.1/Spring6.2.1 прочитаны. Полный mapping/resource/classpath/error-policy proof отсутствует; произвольный404/body не добавлен. |
| Локальный regression/TT replay E21 | verified including actual compact extraction | 2370/158/17, все8 TT answers совпали, S0 прежний; compact offline audit0. Analytical v5 verified:16 427 hashes,actual extraction,freshS0format и все новые metric rechecks. Receipt находится рядом с ZIP; внутренний document freeze не переписывался. |

Точные источники: [stage patches](development/history-review-e21/review.json), [E15–E16](development/IMPLEMENTATION_E16.md), [E17–E21](development/IMPLEMENTATION_E21.md), [парный model review](development/semantic-model-review-e20/review.json), [полные прежние model результаты](development/review33-final/model-summary.json), [строгий E21 transport checker](development/transport-checker-e21-lexical/checks.json), [missing-route preflight](development/missing-route-preflight/DECISION.md).

Компактные E2/E4/E6/E7/E14/E16 и аналитические v1–v4 сохраняются со своими receipt. Последний ранее доставленный полный архив — E14 v4, SHA2561e8096069d650d6fb8463e3597b3c873e2f902dc8b788ea1c8b5e2faa327c57f. Новые исходники и ответы не подменяют эти замороженные результаты.
