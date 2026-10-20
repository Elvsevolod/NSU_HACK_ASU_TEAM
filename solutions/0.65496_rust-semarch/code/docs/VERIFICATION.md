# Verification log

Cumulative log of executed verification steps. Newest at the bottom.
Each entry states what was run, what it proves, and where the evidence lives.

## 2026-10-17 — v0 vertical slice (T01–T08, spike, gates)

### Environment

- macOS 15.7.4 arm64; `rustc/cargo 1.99.1` (rustup minimal/stable);
  Apple clang 17.0.0 (`cc`).
- Train Ticket contest inputs at `../tt-challenge` (never executed — only
  read); the analyzer runs no analyzed applications by construction.

### Grammar spike (T-pre, ADR 0002)

- `cargo run -p grammar-spike` → exit 0, all 7 grammar variants
  (java, python, go, javascript, typescript, tsx, c-sharp) load with
  `tree-sitter 0.27.1` and parse clean fixtures.
- No pin downgrades needed; ts crate export note recorded in ADR 0002.

### Workspace `semarch/` (T01)

- Crates: `semarch-core`, `semarch-frontend-java`, `semarch-frontend-python`,
  `semarch-cli`, plus temp `grammar-spike`. Pinned `workspace.dependencies`.

### Common IR (T02)

- Typed u32 ids, `ValueExpr` v0, `Effect`/`Evidence`/`Action`/`CallSite`/
  `Function`/`FunctionSummary`, `SemanticIndex`.
- Serde round-trip tests: `ir_roundtrip` (9 tests), incl.
  `unknown_is_not_false` (structural distinctness of `Unknown` vs
  `Bool(false)`).

### Discovery (T03)

- `ignore`-walk, `.gitignore` honored even outside a git repo
  (`require_git(false)` — found by the discovery test), extension mapping,
  deterministic order. 3 tests.

### Frontends (T04–T06)

- `LanguageFrontend` trait with capability matrix; spans byte-anchored
  (`SourceSpan::anchor()`).
- Java: package/imports/annotations (`marker_annotation` fallback found via
  tree dump)/methods/callsites/guards; broken source → diagnostics, no panic.
- Python: imports (incl. aliased + from-import)/decorators (raw args between
  parens)/functions/callsites/guards.
- Known honest gaps: assignments and loop structure not materialized (not
  claimed in the capability matrix); Python `self` kept as an explicit
  parameter (normalization belongs to the framework layer).

### Cross-language parity (T07, Gate A) — PASS

- `semarch-cli/tests/parity.rs`: equivalent Java/Python constructs normalize
  to the same IR shapes (method arity modulo explicit `self`, guard shape
  call-vs-operator documented as a *frontend* fact, callsite receiver/args
  equal). No tree-sitter types in core (enforced by import boundaries).

### Minimal CFG + guard policy (T08)

- `linear_cfg` (guards → exit chain), `GuardVerdict`
  (`ProvesTrue|ProvesFalse|Unknown`), `evaluate_condition` (literals only),
  `apply_verdict` (exclusion is an explicit evidence record; `Unknown`
  changes nothing). 4 tests in `cfg_guards`.

### Condition analyzer (T09/T10 v0)

- `semarch-core/src/analysis.rs`: `Env` (scenario bindings),
  `Analyzer::eval_condition`, builtin registry
  (`StringUtils.isEmpty`, literal-receiver `equals`), comparison/arith v0.

### Gate B: Train Ticket verification-code contract — PASS

- `semarch-cli/tests/gate_b_verify_code.rs` on the REAL
  `TokenServiceImpl.java` (never executed): guard
  `!StringUtils.isEmpty(verifyCode)` extracted; with scenario binding
  `verifyCode = ""` → `ProvesFalse` → the HTTP remote effect becomes
  `Excluded` with reason
  `guard_proves_false:StringUtils.isEmpty(verifyCode)==true` (matches gold
  S0 with 0 remote edges); `verifyCode = "abcd"` → `ProvesTrue` → stays
  `Possible`; **no binding** → `Unknown` → stays `Possible`
  (`unknown != false` holds end-to-end).

### S0 baseline reproduction

```
python3 platform/baseline_nlp.py skeleton/trainticket.json.gz targets/trainticket scenarios/*.json -o ans.json --explain
python3 platform/evaluate_golden.py gold/S0.json ans.json
→ ИТОГ — среднее по сценариям эталона (S0): 0.431
```
0 rejected edges; exact reproduction of the published baseline.

### Totals

- `cargo test --release`: **38 passed, 0 failed**; `cargo clippy` warnings: 0.

### Next

- T11: interprocedural propagation beyond builtins (callees with sources in
  the project — param mapping into callee summaries).
- T12: ArchitectureGraph + evidence store; per-service runtime identity by
  module (not classpath).
- Benchmark ladder: pin Istio Bookinfo SHA, `samples/bookinfo/` gold v0.

---

## T11 + T12 — Interprocedural propagation and the architecture graph

Date: 2026-10-17. Algorithms borrowed from open-source (provenance noted in
module docs): summary-based interprocedural propagation (Facebook *Infer* /
Clang Static Analyzer retained-in-reduced shape); call-graph construction
with ambiguity kept unresolved + may-closure reachability (pyan3 / Comex
style); graph machinery on `petgraph` (OSS crate, planned for T12).

### IR changes (v0 additive)

- `Function` gains `returns: Vec<ValueExpr>` (return/exexit expressions, in
  source order; multiple returns are a possible-set) and
  `param_names: Vec<String>` (parallel to `params`; the analyzer binds
  actual arguments by declared names).
- Both frontends collect return expressions in the walk and attach them to
  the innermost containing function by span containment post-pass
  (`assign_returns`, same containment rule reused for call-site ownership).
- Verified against the real `TokenServiceImpl.java`:
  `getServiceUrl` carries `return "http://" + serviceName` exactly, with
  `param_names == ["serviceName"]`.

### Analysis (T11)

- `CallResolver` trait + `SimpleNameResolver` over project functions;
  ambiguity is `Unknown`, never a guess (may-analysis conservativeness).
- `Analyzer::eval_in(expr, frame)` — parameter frames (`Parameter { index }`
  slots and declared-name bindings that shadow the scenario `Env`); callee
  returns are abstract-evaluated under the frame. Recursion depth capped
  (`MAX_DEPTH = 8`), deeper propagation stays `Unknown`.
- Real-source proof: on `TokenServiceImpl.java` the analyzer evaluates
  `getServiceUrl("ts-verification-code-service")` to
  `"http://ts-verification-code-service"` (test
  `graph_real_source::interprocedural_eval_substitutes_url_result`).

### ArchitectureGraph (T12)

- `semarch-core/src/graph.rs`: dense serde-friendly `ArchitectureGraph`
  (`NodeKind::{Function, External}` nodes, `GraphEdge { callsite, callee,
  evidence }` edges). Owner = innermost span-containing function; unique
  name match → `Confirmed`; several matches → `Possible` per candidate;
  no match → `External` node with `Unresolved` evidence (never dropped).
- `may_closure()`: reachability via `petgraph::visit::Dfs` (cycle-safe),
  one entry per function; externals contribute nothing to `executes`.
- Full Train Ticket smoke (`semarch graph targets/trainticket`, ~0.37 s):
  3 209 functions, 18 786 call sites, 1 671 confirmed, 32 402 possible
  (simple-name collisions across services — closed by qualified/type-aware
  resolution in T13+), 13 309 unresolved (library surface, retained).

### Totals

- `cargo test --release`: **53 passed, 0 failed**
  (+15: analysis_propagation 6, graph_tests 5, graph_real_source 4);
  `cargo clippy --all-targets`: 0 warnings.

### Next

- T13 framework adapters above the frontend layer (generic HTTP →
  `Effect::HttpCall` from the URL expression — the `getServiceUrl` result
  is now substitutable at the effect URL); Spring MVC, RabbitMQ, gRPC,
  K8s/Compose later.
- Runtime service identity by module path (audit A01), not a classpath.
- Gate C: same verify-code mechanism through the Python frontend.
- Benchmark ladder: pin Istio Bookinfo SHA, `samples/bookinfo/` gold v0.

## Day 1 — Train Ticket contour v0 (skeleton adapter + entry grounding + export)

**Built**
- `semarch-scenario` (generic L4): identifier-aware tokenizer (camel/snake/acronym),
  conservative stemmer, action-synonym bridge, Okapi BM25, scenario text model.
- `semarch-tt` (Train Ticket adapter): skeleton loader (gzip, typed, open schema),
  resolution engine (G1 dispatch, G2 declarations, G3 Spring Data proxies,
  G4 ORM entity materialization, G5 framework callbacks), UI fact extractor,
  route/UI entry index, contest exporter.
- `semarch tt-export`: one command → `submission.json` for all scenarios (~0.15 s).

**Mechanisms are switchable and ablated on S0**

| config | S0 score | executes IoU | calls IoU | data IoU |
|---|---|---|---|---|
| all on (default) | **0.558** | 0.744 | 0.613 | 0.875 |
| `--disable callbacks` | 0.507 | 0.558 | 0.613 | 0.857 |
| `--disable entities` | 0.542 | 0.725 | 0.567 | 0.875 |
| `--disable callbacks,entities` | 0.487 | 0.525 | 0.567 | 0.857 |

Every mechanism pays for itself; none is assumed.

**Gate results**
- Skeleton loaded: 15 229 nodes / 19 573 edges; 1 538 methods, 8 961 call sites,
  27 repository types (102 proxy methods), 33 tables, 262 endpoints, 1 349 UI facts.
- Entry grounding on S0: all 5 gold entries are selected (login, contacts,
  both order controllers, consign) → recall 1.0 at the entry level.
- Export contract: `relation` key, ids copied verbatim, 0 rejected edges,
  `evaluate_golden.py --check` passes for S0–S7.

**Residual gap (measured, not assumed)** — S0 executes has 9 extra / 2 missing:
- 6 extras are the **verify-code branch** (`if (!StringUtils.isEmpty(verifyCode))`)
  plus `orElseThrow(() -> new UserOperationException(...))`: both need *input/state*
  evaluation, i.e. the Day-2 lever;
- 4 extras are ORM-materialized constructors of entities the answer does not count
  (`Contacts`, ts-common `Order`, `User`) — gold's own heuristic is inconsistent here;
- 2 missing are enum `getCode()` calls that the skeleton never resolved.

## Day 2 — optional-feature guards + name resolution (G6, G7)

**Two new mechanisms, both ablated on the only open oracle (S0).**

| # | mechanism | contract it derives from |
|---|---|---|
| G6 | a call site behind an optional feature the scenario omits does not run | the request carries the feature flag; the scenario states the intent |
| G7 | a call on a *type-named* receiver resolves to that type's method | Java name resolution (`SeatClass.FIRSTCLASS.getCode()`, `StringUtils.Date2String(d)`) |

**Measured on S0 (gold: 34 executes / 24 calls / 0 remote / 7 data):**

| config | S0 score | executes | calls | remote | data |
|---|---|---|---|---|---|
| all on | **0.926** | 0.944 | 0.885 | 1.000 | 0.875 |
| `--disable guards` | 0.591 | 0.791 | 0.697 | 0.000 | 0.875 |
| `--disable static` | 0.855 | 0.842 | 0.704 | 1.000 | 0.875 |
| `--disable guards,static` | 0.558 | 0.744 | 0.613 | 0.000 | 0.875 |

G6 is worth +0.335 and G7 +0.036 on this scenario; neither is assumed.

**G6 in detail.** 110 feature guards are extracted from the project's own
source. A guard counts only when its condition is a *single* predicate leaf —
`!isEmpty(verifyCode)`, `isEnableFood()`, `x != null` — with the feature name
taken from the callee or the tested value. A disjunction of several independent
flags (a filter composition, true whenever any flag is set) and a comparison of
business state (`getStatus() == 1`) are deliberately **not** pruned: the
scenario does not say which way they resolve. Effect on S0: the verify-code
branch (`if (!StringUtils.isEmpty(verifyCode))`) is dead for a login step that
never mentions a code, which removes 5 `executes`, 4 `calls` and the only
`remote` edge.

**G4 corrected.** Entity materialization now resolves the repository's element
type to *one* type instead of matching by simple name. The previous version
pulled in every same-named `Order` of the project (a `ts-common` entity that is
never instantiated by the read), inventing 1 `executes` and 3 `calls` edges.

**Residual gap on S0 (69 edges emitted, 0 rejected).** 2 extra `executes`
(`UserOperationException#<init>` from an `orElseThrow` lambda — a DB-state
question, and one ORM-materialized `Contacts#<init>`), 2 extra `calls`, 1 extra
`data` (`loadUserByUsername` reads two tables; gold credits only one), and 1
missing `calls` edge (`getToken → User#getPassword()`, which the source never
calls — it calls `dto.getPassword()`). These are gold-side heuristics, not
mechanism failures, and they are the honest ceiling of a mechanism-based answer.

## Day 2 (continued) — generality gate, audit trail, and what remains unknown

### Generality gate: rename independence

`crates/semarch-tt/tests/generality.rs` (3 tests, milliseconds) builds a toy
project — *not* Train Ticket — with a handler, a Spring Data repository, an
entity, a servlet filter, a `UserDetailsService`/`UserDetails` pair, one guarded
optional branch and one static-receiver call. It then rebuilds the same program
with the whole vocabulary swapped (module, every type, every method, the entity,
the table, the filter, the principal, the scenario id, and the prose that grounds
the step) and asserts that the predicted structure is identical:

| assertion | what it proves |
|---|---|
| identical `executes`/`calls`/`data` counts and identical behaviour flags in both vocabularies | no mechanism depends on a name |
| the mapped handler is always grounded as an entry | entry grounding follows the route, not the id |
| a repository proxy never appears in `executes`; its SQL is credited to the caller | G3 |
| the entity's no-arg constructor is materialized | G4 |
| the filter executes and the principal's member is read | G5 |
| the guarded helper call appears iff the step names the feature | G6 |
| the static-receiver call resolves | G7 |
| the exporter rejects nothing, in both vocabularies | no id is ever invented |

A fourth check (same file) turns G6 off through `ResolutionConfig` on the toy
project and asserts the branch comes back, so the ablation switch itself is
covered by a test rather than by a CLI flag alone.

### Audit trail

`semarch tt-report <root> --out report.json` re-derives, from the skeleton, the
evidence behind every predicted edge and the reason every executed method is in
the answer. On the current answer:

| scenario | edges | edges without a project call site | entries explained | call sites killed by G6 |
|---|---|---|---|---|
| S0 | 69 | 0 | 36 | 6 |
| S1–S7 | 377–639 | 0 | 158–241 | 6 |

Every answer edge is backed by a concrete call site (`file:line`, receiver,
skeleton relation: `calls`, `runtime_dispatch`, `name-resolution`, `data_access`,
`remote_call`). The G7 edges show up explicitly as `name-resolution`, e.g.
`order.entity.Order#<init>() → edu.fudan.common.entity.SeatClass#getCode()` at
`order/entity/Order.java:80`. Nothing about the run depends on the golden file:
the report is a function of skeleton, sources and scenario text.

### State of the gates

| gate | result |
|---|---|
| `cargo test` | 91 passed, 0 failed (incl. the generality gate) |
| `cargo clippy --all-targets` | 0 warnings |
| `semarch tt-export tt-challenge --out submission.json` | 8 scenarios, 0.15 s |
| `evaluate_golden.py --check` | 0 rejected edges in all 8 scenarios |
| `evaluate_golden.py gold/S0.json` | **0.926** (executes 0.944, calls 0.885, remote 1.000, data 0.875) |

### What is *not* verified, and the risk it carries

S0 is the only labelled scenario; S1–S7 have inputs but no gold. Everything above
is therefore calibrated on a six-step read-only flow. Three consequences are
recorded honestly rather than papered over:

1. **Over-approximation is unmeasured on steps that mutate state.** S0's steps
   only read. Steps that create or cancel an order run larger service chains
   (payment, seats, notification), so the S1–S7 edge counts (377–639) are not
   comparable to S0's 69 and cannot be checked locally.
2. **Business-state branches are deliberately not pruned.** The engine prunes an
   optional-feature branch only when the guard is a single predicate leaf
   (`!isEmpty(x)`, `isEnableX()`), never a disjunction of independent flags or a
   comparison of stored state (`order.getStatus() == 1`). Resolving the latter
   needs the initial database (`context/db-after-warmup.sql.gz`) and a SQL subset;
   that work is not done, and guessing would remove edges the gold keeps —
   measured as a regression when attempted.
3. **The `remote` relation has no local positive example.** Its score on S0 is
   1.0 only because both sets are empty (the rule says an empty pair scores 1).
   The engine emits a `remote` edge only where the skeleton has a `remote_call`
   fact from a reachable call site, and never from a gateway route alone — the
   conservative reading of the contest rule — but that choice is unmeasured.

The one labelled comparison that exists is favourable: on S0 the answer matches
the previous best local result (0.926) exactly, and the mechanisms that produce
it are the ones ablated above.

## 2026-10-18 — инкремент P1-lite: привязка входа к шагу

### Что запускалось

```
cargo test                                  # 96 passed, 0 failed
cargo clippy --all-targets                  # 0 warnings
semarch tt-export tt-challenge --out submission.json   # дважды, sha256 совпал
semarch tt-report tt-challenge --out report.json
python3 tt-challenge/platform/evaluate_golden.py gold/S0.json submission.json
python3 tt-challenge/platform/evaluate_golden.py --check skeleton/trainticket.json.gz submission.json
semarch/target/release/examples/entry_audit tt-challenge    # 103 шага, выбранный вход + кандидаты
```

### Что это доказывает

* **Контроль не сломан.** S0 = **0.926** (executes 0.944 / calls 0.885 /
  remote 1.000 / data 0.875) — ровно как до инкремента; 69 рёбер, 0 отклонённых
  во всех восьми сценариях. Шесть шагов S0 по-прежнему дают нужный обработчик,
  и все пять входов эталона (`getToken`, `findContactsByAccountId`,
  `OrderController#queryOrdersForRefresh`, `OrderOtherController#queryOrdersForRefresh`,
  `ConsignController#findByAccountId`) выбраны.
* **Ответ детерминирован.** Два прогона `tt-export` дали побайтово одинаковый
  файл (`sha256 ea3c7ca2…`), несмотря на то что канал контракта и канал операции
  добавляют работы.
* **Изменение входа измеримо и локализовано.** Аудит входов сравнивался пошагово
  между сборкой до инкремента и после (см. таблицу в
  [`adr/0005-entry-grounding.md`](adr/0005-entry-grounding.md)): из 103 шагов
  изменились 9, из них два — подтверждённые исправления (`addPrice` → `preserve`
  на «Book … first-class seat … assurance», `findByOrderId` →
  `queryOrdersForRefresh` на «filtered by the 'Cancel' status»), одно — снятие
  хеджа из пяти одноимённых `queryAll`, одно — тонкая ничья 0.995 против 1.000
  (`rebook` → `payDifference`). Ни один шаг S0 не изменился.

### Состояние гейтов

| gate | result |
|---|---|
| `cargo test` | 96 passed, 0 failed (incl. the generality gate) |
| `cargo clippy --all-targets` | 0 warnings |
| `tt-export` twice | byte-identical (`sha256 ea3c7ca2…`) |
| `--check` | 0 rejected edges in all 8 scenarios |
| `gold/S0.json` | **0.926** (unchanged) |

### Что осталось непроверенным

1. Скрытые сценарии не размечены: исправления входов проверены по текстам
   веб-клиента (какой запрос шлёт кнопка/страница), а не по эталону. Там, где
   клиент не делает отдельного запроса («Open the new order», «Check the price of
   the order»), верный вход неизвестен и выбранный остаётся предположением.
2. Ничьи с разрывом в доли процента (`rebook` 1.000 против `payDifference`
   0.995) не хеджируются: политика «почти ничьей» действует внутри семейства
   одноимённых обработчиков. Общее хеджирование измерено (S0 не меняется, входов
   в скрытых сценариях больше) и намеренно выключено.
3. Таблица семейств операций тонкая по построению: она исправляет только те
   глаголы, для которых доказано расхождение прозы и кода (`book`/`preserve`,
   `change`/`update`). Проза, называющая операцию словом, которого нет ни в
   одной таблице (`refund` против `refound`), остаётся без поддержки.
4. Полевые списки без вводного слова (скобочное перечисление, притяжательный
   оборот) добавлены в канал контракта после общей проверки: S0 не изменился,
   выбранный вход не изменился ни на одном из 103 шагов, но `registerUser` на
   шаге регистрации поднялся 0.559 → 0.897. Это расширение покрытия канала, а
   не исправление: разрыв с `createNewContacts` держит канал действия.
5. Легаси-интерфейс (`targets/trainticket/ts-ui-dashboard/static/js/`) зовёт
   сервисы короткими путями (`POST /register`), которых нет в таблице маршрутов
   шлюза (`ts-gateway-service/.../application.yml` — только `/api/v1/…`), поэтому
   факты легаси-страниц не привязываются. Единственный шаг, где верный вход
   известен и достижим только так, — регистрация пассажира (`UserController#registerUser`);
   он остаётся невыбранным.



## 2026-10-18 — N01: честное per-step решение, манифест прогона, strict-sources

Инкремент N01 из `planning/BACKLOG.csv` (P0, M). Правка ничего не меняет в
ответе: она исправляет *наблюдаемость* решения и делает деградацию входа явной.

### Что изменено

1. **Per-step решение перестало быть объединением.** `EntryIndex` получил
   `select_per_step` / `select_step`, возвращающий `StepSelection { members,
   reason }`; `select_scenario` (ответ) теперь строится только поверх него —
   один путь для ответа и для отчёта. `reason` — устойчивый идентификатор
   правила: `no_candidate | single_variant | sibling_named | sibling_base |
   sibling_hedged`.
2. **`Candidate` различает два факта.** `selected_this_step` — решение именно
   этого шага; `selected` — объединение по шагам (совместимость со старой
   схемой отчёта). Раньше одно поле выдавало объединение за per-step решение.
3. **`StepReport`** несёт `reason` и `selected_this_step` (список методов шага).
4. **`RunManifest`** в `report.json`: `engine` (имя, версия, схемы
   ответа/отчёта), `config` (entry_ratio, max_candidates, G1–G7), `inputs`
   (Fingerprints `fnv1a64:` файла скелета, каталога сценариев и Java-исходников
   проекта; `absent`/`unavailable` вместо сокрытия) и `diagnostics`.
5. **Единая конфигурация.** `tt-report` принимает те же `--disable`, что и
   `tt-export`; оба строят `AnalyzerConfig` одной функцией `analyzer_config`.
   Абляция теперь имеет сопоставимый отчёт, а не отчёт с дефолтом.
6. **Деградация входа явна.** `LoadOptions { require_sources }`: отсутствие
   checkout’а даёт диагностику `guard_sources_unavailable` (severity
   `degraded`) и `ui_evidence_absent` (info); при `--require-sources` — жёсткую
   ошибку. Тихая загрузка «успешно, но без G6» устранена.
7. **`Report.schema_version = 2`** (`manifest::REPORT_SCHEMA_VERSION`).

Хеш FNV-1a 64 бита — общедоступный алгоритм (Fowler–Noll–Vo, public domain);
значение помечено `fnv1a64:`, чтобы его нельзя было спутать с sha256 релизной
проверки (`scripts/reproduce_rust.py` хеширует выход sha256).

### Что это доказывает

- Шаг, не выбравший вход, больше не может быть прочитан как выбравший его:
  тест `per_step_selection_is_not_the_union` строит проект, где `beta` попадает
  в ранжирование шага 1 (общий токен класса) и входит в объединение, но
  `selected_this_step == false` у шага 1 и `selected == true`.
- Отсутствие исходников не выглядит чистым прогоном: тест
  `a_missing_checkout_is_an_explicit_degradation_or_a_hard_error` проверяет
  диагностику, `inputs.project_sources_java == "unavailable"`, `guard_count == 0`
  и ошибку в strict-режиме.
- Манифест описывает прогон: тест
  `run_manifest_records_inputs_config_and_engine` проверяет engine, 7
  механизмов, три fingerprint’а и совпадение `source_hash` между двумя
  загрузками.

### Гейты (после N01)

| gate | result |
|---|---|
| `cargo test --workspace` | 103 passed, 0 failed (было 96; +3 N01, +2 hash, +2 manifest) |
| `cargo clippy --workspace --all-targets` | 0 warnings |
| `cargo fmt --check` | не является гейтом: workspace никогда не был rustfmt-чистым (нетронутый `grammar-spike` расходится), массовое переформатирование дало бы диффы вне инкремента |
| `tt-export` ×2 | byte-identical (`sha256 ea3c7ca2…` — равен a4db167) |
| `--check` | 0 отклонённых рёбер во всех 8 сценариях |
| `gold/S0.json` | **0.926** (не изменился) |
| `scripts/reproduce_rust.py --ablations` | 37 команд, 0 не-passed, `byte_equal: true` |

Лог воспроизведения (изолированный `CARGO_TARGET_DIR`): `commands.json`,
`determinism.json`, `report.json`, `report_without_*.json` — сохранены в каталоге
прогона; на машине разработчика скрипт завершился за ~31 с (455 % CPU).

### Что осталось непроверенным

1. `reason` описывает *правило отбора*, а не качество входа: тонкая ничья
   (`rebook` → `payDifference`, 1.000 против 0.995) помечается
   `single_variant`, потому что семейство одноимённых обработчиков её не видит.
2. Манифест фиксирует вход, но не доказывает, что именно эти исходники дали
   ответ: связь «вход → G6-обрезка» проверяется регрессией S0, а не хешем.
3. `RunManifest` намеренно не включает хеш UI-исходников (число фактов
   сообщается в `skeleton.ui_facts`); при необходимости добавить в N02.

## 2026-10-18 — N02: структурные границы охраны и проверяемая связь ребра

Инкремент N02 из `planning/BACKLOG.csv` (P0, M; issues I04, I15). Ответ снова
не изменился: правка убирает ложные обрезки и ложную уверенность в отчёте.

### Что изменено

1. **`GuardCondition` различает предикат, `then`-тело и `else`** (`core/frontend.rs`):
   `span` (предикат), `then_span` (охраняемое тело), `else_span`, `body_span`
   (всё выражение, оставлен для совместимости) и `body_always_runs`.
2. **Java-фронтенд** (`frontend-java/src/lib.rs`) берёт `consequence` как
   `then_span`, `alternative` как `else_span`; `do { … } while (cond)` получает
   `then_span = None` и `body_always_runs = true`, потому что тело исполняется
   хотя бы раз. Python-фронтенд обновлён тем же правилом (`consequence`/`body`).
3. **G6 охраняет только `then`-тело** (`tt/guards.rs`). Область — диапазон строк
   (скелет даёт для места вызова только строку); строка, общая для предиката и
   начала тела, исключается через `guarded_first_row`.
4. **Связь ребра стала проверяемой** (`tt/graph.rs`): `CallFact` несёт
   `receiver_type`, `args_text`, `string_args` (и `end_line`), а `evidence_for`
   возвращает `mapping: unique | ambiguous | contract`, список `witnesses` со
   всеми местами вызова и причину. Раньше выбиралось первое место по паре
   (файл, имя) — посговый выбор, который нельзя проверить (I15).

### Измерение на реальном проекте

- Диапазон охраны `TokenServiceImpl#getToken(...)`: предикат на строке 65
  (`if (!StringUtils.isEmpty(verifyCode)) {`), тело — со строки 66.
  **До:** обрезалось 6 мест вызова, включая `StringUtils.isEmpty` на строке 65 —
  предикат ошибочно считался мёртвым. **После:** 5 обрезок; строка 65 жива,
  `restTemplate.exchange` на строке 67 остаётся обрезанным при отсутствии
  `verifyCode` в сценарии. Это ровно пример `@65`/`@67` из приёмки N02.
- Число обрезок одинаково во всех восьми сценариях: было 6 → стало 5.
- Отчёт теперь честно помечает рёбра, обоснованные несколькими местами вызова:
  S0 8, S1 50, S2 72, S3 49, S4 56, S5 62, S6 55, S7 45. Рёбер без
  проектного места вызова по-прежнему 0.

### Гейты (после N02)

| gate | result |
|---|---|
| `cargo test --workspace` | 112 passed, 0 failed (+9: 4 structural spans, 2 guard regions, 3 witness mapping) |
| `cargo clippy --workspace --all-targets` | 0 warnings |
| `tt-export` ×2 | byte-identical (`sha256 ea3c7ca2…`) и равен `submission.json` |
| `--check` | exit 3 (только формат), 0 отклонённых рёбер |
| `gold/S0.json` | **0.926** (не изменился) |
| шаг-аудит | 103 шага, 0 изменений выбранного входа |

### Что осталось непроверенным

1. `end_line` всегда `None`: скелет конкурса не заполняет `end` у мест вызова.
   Поле сохранено как перенос схемы, а не как измеренная возможность.
2. Связь `ambiguous` — утверждение о *наблюдаемости*, а не о качестве: если одно
   место вызова истинно, а другое — нет, скелет этого не различает, и отчёт
   этого не утверждает.
3. Область охраны остаётся построчной: вызов на строке тела, но до предиката
   (однострочный `if (c) call();`), не обрезается. Это выбрано сознательно —
   ложная обрезка живого вызова дороже пропуска гипотетической обрезки.

## 2026-10-18 — N03/N04: упорядоченный IR, домен значений, анализ тела

Инкремент N03+N04 критического пути плана (коммит 3 из 5). Ответ конкурса
**не менялся**: это модель выполнения под N05/N06, а не новый способ считать
рёбра.

### Что изменено

1. **Ядро** (`core/src/ir.rs`): `Statement` / `Terminator` / `BasicBlock` /
   `FunctionBody`; `GapReason` дополнен `NotInFactContract`.
2. **Домен значений** (`core/src/value.rs`): `Unreachable | Unknown | Null |
   Bool | Int(i64) | Float | Str`, решётка `join`, `truth`, `not`, `unary`,
   `binary`, `describe`; решения, где языки расходятся, принимает
   `LanguageProfile` (целочисленность деления, знак остатка, истинность,
   смысл `&&`/`||`).
3. **Построитель тел** (`core/src/lowering.rs`): `BodyBuilder` (свежие блоки,
   временные `$t<n>`, охраны, пробелы) и `validate`, который проверяет
   структурные инварианты: достижимость из `entry`, наличие целей у
   терминаторов, уникальность ID блоков, разрешимость ссылок на охраны.
4. **Анализ тела** (`core/src/analysis.rs`): рабочий список по блокам, `Env`
   (имя → `AbstractValue`), слияние окружений `join`-ом, решённые условия
   оставляют одну ветвь, нерешённые — обе плюс метку `g<id>=then|else` в
   путь-свидетель; межпроцедурная сводка через `CallResolver` с ограничением
   глубины; `Widened` как страховка.
5. **Java-понижение** (`frontend-java/src/lowering.rs`): полный набор
   операторов, `finally` во всех завершениях, тернарный оператор и
   `&&`/`||` с протяжкой continuation-блока, рекурсия в локальные/анонимные
   классы и вложенные объявления.
6. **Python-понижение** (`frontend-python/src/lowering.rs`): `if`/`elif`/`else`,
   `while`/`for` (+`else`), `return`/`raise`, `try`/`except`/`finally`,
   тернарный оператор, `and`/`or`, цепочки сравнений, `+=`, неявный
   `return None`, пробелы для `with`/`match`/`assert`/включений.

### Найденные дефекты (не «подгонка тестов»)

Тесты писались как проверка свойств и нашли четыре настоящие ошибки:

1. `lower_try` в **обоих** фронтендах снимал `finally` со стека **до**
   встраивания в нормальный путь. Следствие: `audit()` терялся на нормальном
   завершении и во всех `catch`-ветвях. Исправлено: клауза снимается после
   встраивания во все завершения.
2. Python: у `except_clause`/`finally_clause`/`else_clause` **нет поля `body`**
   (suite — обычный `block`), поэтому очистка молча не встраивалась. Добавлен
   `suite_body`; исправлены `lower_try`, `inline_finally`, `else_clause`.
3. Python: `x = 0` и `x += 1` приходят как `expression_statement` → `assignment`,
   а не как отдельные операторы; они понижались как **выражения** и давали
   `UnsupportedExpression`, то есть присваивания не понижались вообще. Кроме
   того, у `augmented_assignment` нет полей `left`/`right`, а
   `comparison_operator` хранит операторы в повторяющемся поле `operators` —
   позиционное чтение давало неверный оператор (`a < b` → «unmapped binary
   operator `b`»). Исправлено: присваивания делегируются оператору, операнды
   берутся по полям, цепочки сравнений собираются явно.
4. Оба фронтенда записывали пробел «statements after a definite exit» **для
   самого** завершающего оператора (`return`/`throw` последним в блоке).
   Исправлено: пробел ставится только на операторы после завершения.

Плюс два дефекта качества доказательств/воспроизводимости:

5. `record_effect` оставлял первое наблюдение эффекта. Блок, впервые посещённый
   по достоверному пути (тело цикла на первой итерации), навсегда получал
   `Confirmed`, хотя далее достигался и по условному. Исправлено: при повторном
   посещении доказательство может только слабеть (`Confirmed → Possible`).
6. `tt-report` был **недетерминированным**: `sk.nodes` — `HashMap`, поэтому
   порядок `call_sites_of` зависел от процесса, и два прогона давали разные
   `pruned[0]`/`witnesses` (а `evidence_for` вдобавок брал первое совпадение).
   Исправлено: id-списки сортируются при сборке графа, `evidence_for` сортирует
   свидетелей по (строка, id). Ответ не изменился, отчёт стал побайтово
   воспроизводимым.

### Соответствие фикстурам плана

| фикстура плана (`benchmarks/TEST_FIXTURES`) | где покрыта |
|---|---|
| `BranchCases.java`: `negative`, `early`, `finallyCase`, `conditional`, `firstDo`, `shortCircuit` | `frontend-java/tests/cfg_lowering.rs`: `early_return_leaves_a_reachable_rest`, `try_finally_runs_on_the_return_path`, `ternary_retains_both_candidate_calls`, `do_while_runs_its_body_before_testing`, `short_circuit_right_hand_side_is_guarded`, `guard_references_always_resolve` |
| `branch_cases.py`: `early`, `finally_case`, `conditional` | `frontend-python/tests/cfg_lowering.rs`: одноимённые свойства + `loop_with_else…`, `while_with_else_is_lowered` |
| `regression_core.rs::integer_addition_preserves_equality` | `core/tests/scalar_semantics.rs::integer_arithmetic_is_exact_above_the_float_limit` (API сменился: `eval` возвращает `AbstractValue`, а не `ValueExpr`) |
| `regression_guards.rs`: «отсутствие слова не доказывает ложность», «предикат не обрезается», «`else` не внутри `then`» | `tt/tests/n02_guard_regions.rs` (`only_the_then_body_is_a_guarded_region`, `the_predicate_row_is_not_part_of_the_region`) + `core/tests/cfg_guards.rs` |
| `regression_frontend.rs::ternary_retains_both_candidate_calls…` (плоские callsites обоих плеч) | **не выполняется намеренно**: плоский обход не посещает второе плечо тернарного оператора в `return`. Понижение сохраняет оба плеча как CFG-пути, а отсутствие callsite записывается как `UnresolvedCall` (`ternary_arm_without_a_flat_call_site_is_recorded_not_dropped`). Исправление меняет конкурсный ответ, поэтому вынесено из N03/N04 |

### Измерение корпуса (новый инструмент)

`crates/semarch-tt/examples/lowering_census.rs` — понижение всех Java-файлов
проекта с проверкой `validate` и подсчётом пробелов. Это же — стресс-тест
понижения на реальном коде.

```text
files parsed: 635 (failed: 0)
function bodies: 2815 (empty: 0)
basic blocks: 7274
statements: 24087
guards: 1485
exit blocks: 3298
invalid bodies: 0
gaps: 3153
  NotInFactContract: 2692   (2652 `new`, 40 `this(…)/super(…)`)
  ExceptionDispatch: 69
  UnresolvedCall: 168
  UnsupportedExpression: 168
  UnsupportedStatement: 56
```

Полная матрица поддержки с расшифровкой — `docs/SUPPORT_MATRIX.md`.
Тела: 2 815 больше 1 538 методов скелета, потому что измеряются все Java-файлы
`targets/`, включая модули вне скелета и конструкторы.

### Гейты (после N03/N04)

| gate | result |
|---|---|
| `cargo test --workspace` | **180 passed**, 0 failed (было 112; +13 Java, +15 Python, +17 значений, +23 анализа тела, +1 структурный) |
| `cargo clippy --workspace --all-targets` | 0 warnings |
| `tt-export` ×2 | побайтово одинаково, `sha256 ea3c7ca2…`, равно `submission.json` |
| `--check` | exit 3 (только формат), 0 отклонённых рёбер |
| `gold/S0.json` | **0.926** (executes 0.944 / calls 0.885 / remote 1.000 / data 0.875) — не изменился |
| шаг-аудит | 103 шага, выбранный вход не изменился |
| `scripts/reproduce_rust.py --ablations` | 37 команд, 0 не passed, `byte_equal: true` |
| `tt-report` ×2 | побайтово одинаково (было недетерминировано, см. дефект 6) |

### Что осталось непроверенным

1. **Нет корпуса для Python**: измерение пробелов есть только для Java
   (в `targets/` нет Python-кода). Python-понижение проверено свойствами на
   фикстурах плана (`branch_cases.py`, `early_return`, `try/finally`,
   `and`/`or`, `for/else`, `match`), но не объёмом.
2. **Понижение не влияет на ответ**: `bodies` потребляются только движком
   (`--mode semantic|shadow`), а сдаваемый артефакт по-прежнему строит legacy.
   См. N05/N06 ниже.
3. **`break`/`continue` без учёта меток**: `Terminator::Gap` даёт may-execute,
   но не точный порядок. Для `switch` это значит, что тела `case` считаются
   возможными независимо от значения селектора.
4. **Поля и статические инициализаторы** не являются `FunctionBody`; их вызовы
   не регистрирует и плоский обход. Это записано как известная дыра, а не
   исправлено в этом инкременте.

---

## N05/N06 — привязка запроса и движок состояний сценария

Что проверено: слова шага становятся **типизированными полями запроса**,
значения проходят через аксессор и локальную переменную в условие, условие
решает, живо ли место вызова, а решение записывается доказательством. Ответ
конкурса при этом не меняется. Решение — `docs/adr/0007`.

### Вертикаль `verifyCode` на реальном проекте

Тест `crates/semarch-tt/tests/n06_semantic_login.rs` идёт production-путём —
загрузчик конкурса, привязка входа (ADR 0005), привязка запроса, CFG-анализ,
экспорт:

```text
шаг «Log in with username admin and verification code 4578»
  → BasicAuthDto.verificationCode = "4578"      (origin: payload)
  → TokenServiceImpl#getToken, dto.getVerificationCode()  (JavaBeans-аксессор)
  → String verifyCode = …                       (локальная привязка)
  → if (!StringUtils.isEmpty(verifyCode))        (g0: proves_true)
  → restTemplate.exchange(… /verifycode/verify/ …)  remote, status = confirmed
```

| свойство | проверка | результат |
|---|---|---|
| поле берётся из скелета | `BoundRequest` содержит `verificationCode` c `declared = "String"` | да |
| значение из прозы | шаг с кодом → `Literal("4578")` | да |
| аксессор без ручного `env` | `dto.getVerificationCode()` резолвится в связанное поле | да |
| доказательство | у шага есть `g0: proves_true` с символами условия | да |
| положительный `remote` | ребро `remote` со `status = confirmed` и целью `VerifyCodeController` | да |
| молчание ≠ отсутствие | шаг «Log in with username and password» → `Unknown`, ребро `possible`, вердикт `unknown` | да |
| экспорт не изобретает ID | `export::build` → 0 отклонённых рёбер, `remote`-ребро в блоке | да |
| ответ не изменился | тот же JSON пиннится FNV-1a в тесте (`fnv1a64:4145150f03aec303`) | да |

Фикстурный тест `crates/semarch-tt/tests/n05_value_binding.rs` (игрушечный
проект: `@PostMapping` + `BasicDto` + `StringUtils.isEmpty` + `remote_call`)
различает все четыре состояния значения на одном и том же коде:

| слова шага | привязка | вердикт | ребро `remote` |
|---|---|---|---|
| «with verification code 4578» | `Literal("4578")` | `proves_true` | `confirmed` |
| «with an empty verification code» | `Empty` | `proves_false` | нет (записано в `suppressed`) |
| «without a verification code» | `Absent` (→ `Null`) | `proves_false` | нет |
| «with username passenger» | `Unknown` | `unknown` | `possible` |
| «Book a ticket with train food» | `Literal("1")` из статической опции | — | — |
| «Book a ticket» | `Unknown` (опция не выбрана) | — | — |

Дополнительно проверено: два шага к одному обработчику с разными значениями
дают разные исходы, а слова второго шага не переписывают первый
(`a_later_step_never_rewrites_an_earlier_one`), и статические опции UI отделены
от списков, приходящих в рантайме (`a_static_option_binds_but_a_runtime_fetched_list_does_not`).

### Тень: движок против legacy на всех сценариях

`semarch tt-export tt-challenge --mode shadow` (ответ — снова legacy,
`sha256 ea3c7ca2…`):

| сценарий | legacy (calls/remote/data) | semantic | agreed | only_legacy | only_semantic |
|---|---|---|---|---|---|
| S0 | 25 / 0 / 8 | 29 / 1 / 8 | 33 | 0 | 5 |
| S1 | 240 / 44 / 46 | 244 / 45 / 46 | 330 | 0 | 5 |
| S2 | 305 / 67 / 54 | 309 / 68 / 54 | 426 | 0 | 5 |
| S3 | 228 / 40 / 46 | 232 / 41 / 46 | 314 | 0 | 5 |
| S4 | 254 / 46 / 48 | 258 / 47 / 48 | 348 | 0 | 5 |
| S5 | 329 / 63 / 50 | 333 / 64 / 50 | 442 | 0 | 5 |
| S6 | 240 / 45 / 49 | 244 / 46 / 49 | 334 | 0 | 5 |
| S7 | 225 / 43 / 43 | 229 / 44 / 43 | 311 | 0 | 5 |

`only_legacy = 0` и `only_legacy_executes = 0` во всех сценариях: движок
воспроизводит legacy **точно** и ничего не теряет. Каждое добавленное ребро —
это то, что legacy отсекал по словам сценария (G6): четыре вызова и один
`remote`-вызов сервиса verification-code. У каждого ребра в диффе есть
объяснение, у каждого шага — пробелы и подавленные места вызова.

### Гейты (после N05/N06)

| gate | result |
|---|---|
| `cargo test --workspace` | **197 passed**, 0 failed (было 180; +6 модульных тестов привязки, +5 фикстурных N05, +6 N06 на реальном проекте) |
| `cargo clippy --workspace --all-targets` | 0 warnings |
| `tt-export` ×2 | побайтово одинаково, `sha256 ea3c7ca2…`, равно `submission.json` |
| `--check` | exit 3 (только формат), 0 отклонённых рёбер |
| `gold/S0.json` | **0.926** (executes 0.944 / calls 0.885 / remote 1.000 / data 0.875) — не изменился |
| `scripts/reproduce_rust.py --ablations` | 37 команд, 0 не passed, `byte_equal: true` |

### Что осталось непроверенным (N05/N06)

1. **Копии значений через аргументы** не передаются: объект едет по дескриптору
   (свойства переезжают под имя параметра), но примитив, прочитанный из поля
   или возвращённый помощником, в вызываемый метод не попадает. Записано как
   граница движка.
2. **Куча и поля объекта** не моделируются (N08): значение, записанное в поле и
   прочитанное позже, — `Unknown`.
3. **Значения перечислений** из исходников не читаются; статический `<option>`
   рядом с подходящей меткой связывается, иначе — `Unknown` с провенансом.
4. **Отсечение выключено при пробелах понижения**: метод с любым `AnalysisGap`
   сохраняет все свои места вызова. Это делает движок строго консервативнее
   там, где доказательство неполно.
5. **Места вызова, которых нет в плоских фактах** (плечи тернарного оператора в
   `return`) остаются живыми без IR-подтверждения и считаются в
   `unlowered_call_sites`.

> **Устарело (2026-10-19).** Пункты 4 и 5 описывают состояние до инкремента
> B38 и больше не верны: глобальное вето снято (пункт 4), плечи тернарного
> оператора понижаются (пункт 5). Действующее правило — сертификат на месте
> вызова, см. ADR 0008 и раздел «2026-10-19 — инкремент B38 (C1–C7)» ниже.
> Таблица тени в разделе выше тоже устарела: `only_semantic` стал 0 на всех
> сценариях.

## 2026-10-19 — инкремент B38 (C1–C7): доказательство на месте вызова

Применён ревью-пакет `SEMARCH_B38_REVIEW_AND_NEXT_STEP` поверх `b38fbf0`. Всё
ниже измерено на этой машине, команды приведены целиком. Разбор по коммитам —
`docs/B38_INCREMENT.md`, решения — ADR 0008.

### Что запускалось

| # | команда | результат |
|---|---|---|
| 1 | `cargo test --workspace --locked --no-fail-fast` | **40 наборов, 229 passed / 0 failed** |
| 2 | `cargo clippy --workspace --all-targets --locked` | 0 warnings |
| 3 | `cargo build --release --locked` | ok |
| 4 | `tt-export --mode legacy --require-sources` | `sha256 ea3c7ca2…` = `submission.json` |
| 5 | `tt-export --mode shadow --require-sources --shadow-out d.json` | ответ = legacy; дифф `9eeed004…` |
| 6 | `tt-export --mode semantic --require-sources` | `sha256 ea3c7ca2…` (совпал с legacy) |
| 7 | `tt-semantic … --require-sources` дважды | побайтово одинаково: `66beb6fb…` |
| 8 | `tt-report --out report.json` | `253a7a45b13a8d997e8ff28483ef6207baf71e2316bf4ed0abdf72be046ec99d` |
| 9 | `evaluate_golden.py gold/S0.json` (legacy и semantic) | **0.9260149572649572** оба |
| 10 | `evaluate_golden.py --check` (legacy, semantic, shadow) | exit 3 — только формат, 0 отклонённых рёбер |
| 11 | `cargo test -p semarch-tt --test b38_login_gate -- --nocapture` | 5/5 |

### S0: четыре IoU и ошибки

| отношение | IoU | точность | полнота | сдано | эталон | совпало | FP | FN |
|---|---|---|---|---|---|---|---|---|
| `executes` | 0.944 | 0.94 | 1.00 | 36 | 34 | 34 | 2 | 0 |
| `calls` | 0.885 | 0.92 | 0.96 | 25 | 24 | 23 | 2 | 1 |
| `remote` | 1.000 | — | — | 0 | 0 | 0 | 0 | 0 |
| `data` | 0.875 | 0.88 | 1.00 | 8 | 7 | 7 | 1 | 0 |

Семантический путь теперь совпадает с legacy и по этим числам. До инкремента он
давал **0.618** (41/29/1/8): пять лишних `executes`, четыре лишних `calls` и один
лишний `remote` — и все они были ложными, порождёнными gap-блоками, размечавшими
себя достижимыми ниоткуда (B38-05).

### Свидетель на реальном `TokenServiceImpl#getToken` (`b38_login_gate`)

```text
entry     method:ts-auth-service:auth.controller.UserController#getToken(auth.dto.BasicAuthDto,org.springframework.http.HttpHeaders)
binding   verificationCode = absent (context)   // «the task package states "no verification code at login"»
decision  g0 proves_false line 65 path []       // безусловный путь, симв. [StringUtils, verifyCode]
excluded  exchange@67:55, getBody@72:29, info@76:24 — один сертификат, блоки [2,4,5,6]
sites     resolved=58, ambiguous=0, missing=7, no_body=1, kept={skeleton_site_absent_from_lowered_body: 18}, suppressed=3
```

Счётчик `kept` не содержит причины-вето: в этой цепочке нет ни одного места
вызова, сохранённого «потому что в методе есть `new`».

### Что перестало быть верным

1. Таблица тени выше (`only_semantic = 5`): теперь `only_legacy = 0` **и**
   `only_semantic = 0` во всех восьми сценариях, а `--mode semantic` побайтово
   равен legacy (`ea3c7ca2…`).
2. Пункты 4 и 5 списка «что осталось непроверенным» (N05/N06): глобальное вето
   снято, плечи тернарного оператора понижаются. Помечены в тексте.
3. `report.json` в корне репозитория был устаревшим (`16d96bf…` от `a4db167`);
   приведён к детерминированному выводу инструмента (`253a7a45…`).
4. README обещал 197 тестов; теперь 229 в 40 наборах.

### Что осталось непроверенным (и не заявляется сделанным)

1. **`manifest` в `report.json`** пока не содержит commit движка и хешей UI/context
   входов (план B38-10). В нём: `engine{name,version}`, `config`, `inputs{sources,
   scenarios,skeleton}`, `diagnostics`.
2. **Сертификат — про блок, а не про значение**: место вызова в достижимом блоке
   с несовместимым значением остаётся живым. Именно поэтому 2 `executes`, 2
   `calls` и 1 `data` ложноположительных рёбер S0 сохраняются и считаются.
3. **Балл не вырос**: 0.926 была и осталась. Инкремент купил провенанс, а не
   оценку; это заявленный результат, а не недоделка.
4. **Исправления B38-06 на конкурсном проекте не наблюдаемы**: в загруженном
   проекте (479 Java-файлов под корнями скелета) нет ни одного `finally` и ни
   одного тернарного оператора с вложенным `?` или `&&`/`||` в плече
   (`old-docs/` в скелет не входит: 0 узлов). Они пиннятся фикстурными наборами
   `review_b38_java` / `review_b38_python`.
5. **Полноты нет**: `unknown != false` и незакрытые пробелы остаются фактами
   отчёта, а не молчанием.
