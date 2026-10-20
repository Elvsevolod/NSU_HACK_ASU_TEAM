# B38 increment — what was run, what passed, what is still red

This file records the native work of the `B38` increment (the review package
`SEMARCH_B38_REVIEW_AND_NEXT_STEP` applied on top of commit `b38fbf0`). Every
number here was produced on this machine by the commands shown; nothing is
copied from a report claiming it.

## B38-01 — native baseline (C1)

Host: macOS, `rustc 1.99.1`, `cargo 1.99.1`. All commands from the project root
(`semarch/Cargo.toml`, `tt-challenge/` and `submission.json` in one directory).

| # | command | result |
|---|---|---|
| 1 | `cargo test --workspace --locked` | 33 suites, **197 passed / 0 failed** |
| 2 | `cargo build --release --locked` | ok |
| 3 | `tt-export --mode legacy --require-sources` | `sha256 ea3c7ca2…` = `submission.json` |
| 4 | `tt-export --mode shadow --require-sources` | answer identical to legacy; `--shadow-out` written |
| 5 | `tt-export --mode semantic --require-sources` | `sha256 59cd3426…`, 79 edges on S0 (legacy 69) |
| 6 | `evaluate_golden.py gold/S0.json <legacy>` | **0.9260149572649572** — executes IoU 0.944 (36/34, TP34 FP2 FN0), calls 0.885 (25/24, TP23 FP2 FN1), remote 1.000 (0/0), data 0.875 (8/7, TP7 FP1 FN0), 69 accepted, 0 rejected |
| 7 | `evaluate_golden.py gold/S0.json <semantic>` | 0.618 — the extra 10 edges (4 `calls` + 1 `remote` + …) are the whole-method fallback for a non-prunable body |
| 8 | `evaluate_golden.py --check <legacy/semantic/shadow>` | exit **3** for all three (format-only success for this evaluator version) |
| 9 | `tt-export --mode legacy` twice | byte-identical (determinism) |

Shadow diff, measured on the real project (8 scenarios), native:

| scenario | legacy executes/calls/remote/data | semantic | agreed | only_legacy | only_semantic |
|---|---|---|---|---|---|
| S0 | 36/25/0/8 | 41/29/1/8 | 33 | 0 | 5 |
| S1 | 211/240/44/46 | 216/244/45/46 | 330 | 0 | 5 |
| S2 | 246/305/67/54 | 251/309/68/54 | 426 | 0 | 5 |
| S3 | 206/228/40/46 | 211/232/41/46 | 314 | 0 | 5 |
| S4 | 217/254/46/48 | 222/258/47/48 | 348 | 0 | 5 |
| S5 | 248/329/63/50 | 253/333/64/50 | 442 | 0 | 5 |
| S6 | 218/240/45/49 | 223/244/46/49 | 334 | 0 | 5 |
| S7 | 203/225/43/43 | 208/229/44/43 | 311 | 0 | 5 |

`only_semantic = 5` in every scenario is the *same* systematic divergence: the
four calls inside the verification-code branch of `TokenServiceImpl#getToken`
plus the `remote` edge they carry, kept because the whole-method gap veto makes
the body non-prunable. It is a fallback, not a proof of extra coverage — the
measured statement is "the semantic engine adds nothing the legacy engine
loses, and adds 5 edges the legacy engine pruned".

Two corrected claims from the review package are confirmed against the real
artifact:
* the open S0 score is `0.9260149572649572`, not the older `0.925748`;
* `--check` exits **3** in this evaluator version and that is the expected
  format-only success.

Artifact drift found while auditing (fixed in C7, no effect on the answer):
`report.json` in the repository was generated at `a4db167`, before `N01`–`N06`;
the current tool emits `sha256 253a7a45…` deterministically (two runs agree) and
the shipped archive contained that newer file. The answer (`submission.json`)
was byte-identical all along.

## Prepared tests (C1), measured on the unmodified revision

The 24 prepared tests from the review package were installed unchanged into
`semarch/crates/*/tests/review_b38_*.rs` and run natively. They compile as
written; no API adaptation was needed.

| suite | tests | result at `b38fbf0` |
|---|---|---|
| `semarch-core/tests/review_b38_core.rs` | 4 | **0 pass / 4 fail** |
| `semarch-frontend-java/tests/review_b38_java.rs` | 3 | 0 / 3 |
| `semarch-frontend-python/tests/review_b38_python.rs` | 3 | 0 / 3 |
| `semarch-tt/tests/review_b38_binding.rs` | 5 | 1 / 4 |
| `semarch-tt/tests/review_b38_synthetic.rs` | 5 | 0 / 5 |
| `semarch-tt/tests/review_b38_real_login.rs` | 4 | 2 / 4 |

The five `review_b38_synthetic` failures were **not** semantic: the fixture
writes `args_text` as a JSON array while the real skeleton carries a string, so
the loader rejected the fixture skeleton. Fixed in C3 as a schema-compatibility
change in `skeleton.rs` (`args_text` accepts both shapes, normalised to the
string form); this is a loader tolerance change, not a test edit — the prepared
files are byte-identical to the package.

Note on `review_b38_real_login`: the two passing cases at `b38fbf0` pass for
different reasons than they claim. `real_absent_login_excludes_verify…` passes
because "Log in without a verification code" grounds on
`VerifyCodeController#imageCode` (a wrong entry) and therefore never reaches
`TokenServiceImpl` at all; the assertion is vacuous there. This is recorded as
an open defect (entry grounding, [B38-10]) and is not counted as a pass for
value binding.

## B38-02 — monotone summary records (C2)

`semarch-core/src/analysis.rs`: `returns`/`throws` join every visit instead of
keeping the first (`AbstractValue::join`), `decisions` join verdicts (two
disagreeing visits leave `Unknown`), and a newly-uncertain block now re-enters
the fixed point. The witness path of a joined record is cleared, because one
witness never describes a joined result.

| gate | result |
|---|---|
| `review_b38_core` | **4 pass / 0 fail** |
| `cargo test --workspace --locked --no-fail-fast` | 205 pass / 17 fail (the 17 are the prepared suites of the later commits) |
| `tt-export --mode legacy` | `sha256 ea3c7ca2…` — the contest answer is untouched |
| `tt-export --mode shadow` | answer identical to legacy |
| `tt-export --mode semantic` | `sha256 59cd3426…` — byte-identical to the pre-C2 semantic answer (summary honesty, no behaviour change) |

Remaining red after C2: java 3, python 3, binding 4, synthetic 5, real_login 2.

## B38-03 — exact call-site identity (C3)

`semarch-tt`: the loader reads `col` and `init_literal`, and accepts `args_text`
written either as a string (the contested schema) or as an array (fixture
schema); `graph.rs` gained `SiteResolution` (`Exact`/`Ambiguous`/`Missing`) and
`resolve_site(file, line, callee, arity, anchor_col)`; `bodies.rs` keeps the file
text so a lowered span can be turned back into the token the skeleton reports
(`anchor_col`: the callee name for an invocation, `new` for a constructor call),
and `BodyIndex::resolve` replaced the arity fallback of `find` — a body is only
borrowed when its identity is established (declared arity, then declared line),
otherwise `Ambiguous`/`Missing` and the method is treated as unlowered. The
engine maps each lowered call site once and never broadcasts one IR call's proof
over several skeleton sites.

Column convention, measured, not assumed: the skeleton records a **1-based byte**
column. On the 22 source lines of the project with non-ASCII text, the four call
sites whose byte and character columns differ (`getTime` in
`TravelServiceImpl.java`, `put`/`add` in `GatewayConfiguration.java`) match the
byte convention; Tree-sitter's 0-based byte column is therefore converted by
`+1`. The skeleton's anchor token is the callee name for an invocation and `new`
for a constructor call (`1148/1153` of the `<init>` sites; the other 5 are the
inner `new` of a nested expression, which lower as their own node).

| gate | result |
|---|---|
| `review_b38_synthetic::same_line_same_name_does_not_share_liveness` | **pass** (two `send()` on one line no longer share liveness) |
| `review_b38_synthetic` | 1 pass / 4 fail (the four remaining need B38-06/07) |
| `cargo test --workspace --locked --no-fail-fast` | 205 pass / 16 fail |
| `tt-export --mode legacy` / `--mode shadow` | `sha256 ea3c7ca2…` — untouched |
| `tt-export --mode semantic` | `sha256 59cd3426…` — byte-identical to the pre-C3 answer |
| `--shadow-out` | counts unchanged; 22 **added** notes per scenario (`site:…:anchor_column`, `no_lowered_body:<reason>`), none removed |
| `cargo clippy --workspace --all-targets` | clean |

Coverage measured over every lowered body (516 files, 18 655 lowered calls):

| resolution | calls |
|---|---|
| `Exact` via unique `file:line:callee` | 6 550 |
| `Exact` via anchor column | 244 |
| `Exact` via arity | 0 |
| `Ambiguous` | **0** |
| no skeleton call site at that location | 11 861 |

The 11 861 are calls the skeleton tool does not record — most visibly every
`new`: the Java frontend lowers an object creation to a `NotInFactContract` gap
and not to a `<init>` call site, so the skeleton's 1 153 `<init>` sites never
have a lowered counterpart and are always kept live. That is conservative (no
edge is dropped) but it is also why constructor edges stay unprovable.

The audit package's own same-line collision list (`callsite_collisions.json`,
126 groups, 259 sites — reproduced independently here: 126 groups, all 126 with
distinct columns) resolves as follows: **118 groups fully resolved by the anchor
column (242 sites), 0 by arity, 0 left ambiguous**, 6 groups (`<init>`, no
lowered counterpart) and 2 partial groups (one of two occurrences is not lowered
at the reported line, e.g. `WebSecurityConfig.java:50 passwordEncoder`) stay
unresolved and therefore unpruned. One IR call no longer claims several skeleton
sites, and no site is suppressed on a shared proof.

Body identity over the 1 538 skeleton methods: 1 005 by arity, 2 by declared
line, 531 with no body at all (interfaces, abstract declarations and
constructors — no lowered body, so every call site of those methods stays live).

Remaining red after C3: java 3, python 3, binding 4, synthetic 4, real_login 2.

## B38-04 — honest values and the task-package context (C4)

Three fixes, all in `request.rs` (plus the loader and the engine).

**Literals are the text as written (B09).** `words()` used to lower-case and
split a clause into alphanumeric tokens, and the value was taken from those
tokens: `AbC-4578` was reported as `abc`, `-12.50` as `12`, and
`FDSE_microservice` lost its underscore. A payload word is now a `Word { raw,
lower, tokens }` — the raw slice with the surrounding punctuation trimmed (a
leading `-`/`_` kept, so a negative number survives), the lower-cased text for
the stopword tables, and the tokens for matching a field name. Matching is
unchanged; the *value* is `raw`.

**Omission is `null` only with evidence (B14).** `BoundValue::abstract_value`
no longer turns `Absent` into `Null` from the declared type alone:
`FieldEvidence { deserialized, init_literal }` decides, and
`BoundValue::omitted_value` seeds `Null` only when the field travels in a
**deserialized body** (the handler parameter is annotated `@RequestBody` or
`@ModelAttribute`) **and** the field declares no initializer of its own.
`BoundRequest::env` is the evidence-free form (an omitted field seeds nothing);
`env_with_evidence` is what the engine uses. The evidence is read from the
skeleton (`skeleton.rs` now keeps a `parameter` node's `type`/`index`), and the
rule is recorded per field.

**The package's context is input (B02).** `skeleton.rs` now keeps the top-level
`context` block (it was dropped by the loader), and `request::context_facts`
reads `context.account` per clause: a negator, a field phrase that must match one
of *this handler's* declared fields, and a scope word after `at`/`on`/`during`
that must match the step's action or the handler's route. A clause without a
scope is a statement about the starting point as such. `apply_context` fills only
the fields the step left **open** (`Unknown`) — a stated value is never
overwritten — and records origin `context` with the clause as provenance.
`AnalyzerConfig::use_context` (on by default, `--disable context` on the CLI)
turns the second source off; that is the ablation the generic-silence case
needs.

Measured on the contested project, the four login wordings, guard = the real
`TokenServiceImpl#getToken` decision:

| step action | `use_context` on | `use_context` off |
|---|---|---|
| "…with an empty verification code" | `Empty`/payload → **proves_false** | same |
| "…with username and password" | **`Absent`/context** → **proves_false** | `Unknown`/unmentioned → **unknown** |
| "…with verification code 4578" | `Literal("4578")` → **proves_true** | same |
| "…without a verification code" | grounded on `VerifyCodeController#imageCode`, no `verificationCode` field bound | same |

The last row is the entry-grounding artifact already reported: the action's
words ("without a verification code") outweigh "log in" for the ranker, so that
wording does not reach the login handler at all. It is recorded, not papered
over; the real default is proved on the wording that does ground on the login
handler.

A new `tt-semantic` command writes the audit trail the per-commit rule needs:
per scenario and step the entries, every bound field with its value, origin and
provenance, the guard decisions, the effects with their proofs, the suppressed
call sites, the call-site coverage counters and the remaining gaps. For S0 step 1
it prints, among the rest, `verificationCode = absent (context)` with
`the task package states "no verification code at login" (at login)`, the
decision `TokenServiceImpl#getToken → proves_false`, and the counter
`kept = {lowering_gaps_disable_pruning: 3, skeleton_site_absent_from_lowered_body: 20}`
— that is the B01 veto, still holding the remote call in place.

| gate | result |
|---|---|
| `review_b38_binding` | **5/5 pass** (was 1/5) |
| `n05_value_binding`, `n06_semantic_login` | 5/5 and 6/6 (the two tests that encoded the old contracts now state the new ones) |
| `cargo test --workspace --locked --no-fail-fast` | 211 pass / 12 fail |
| `tt-export` legacy, shadow, semantic | `ea3c7ca2…`, `ea3c7ca2…`, `59cd3426…` — all unchanged |
| `--shadow-out` | byte-identical to C3 (`eca6de1e…`) |
| evaluator S0 / `--check` | 0.9260149572649572 / exit 3 |
| `cargo clippy --workspace --all-targets` | clean |

The semantic answer is unchanged because the B01 veto still disables pruning for
the login method: the binding and the guard verdict are now right, and the remote
edge is still carried. Suppressing it — with a certificate — is C5.

Remaining red after C4: java 3, python 3, synthetic 4, real_login 2.

## B38-05 — the proof is per call site (C5)

Three defects, one mechanism each. All numbers below are from this machine; the
commands are the ones in the gate table.

### 1. Gap content is a may-path out of the construct, not reachable from nowhere

`analyze_body` used to seed **every** gap block as reachable with an empty
environment. That is how a `new HttpEntity(headers)` inside an arm the guard had
just proved false brought the whole arm's call sites back: the seeded content
block `goto`s the arm's continuation, so the `restTemplate.exchange` behind the
verification-code branch was reached on a witness nobody had proved. It was not
a completeness win, it was a leak — and it was exactly the 5 `only_semantic`
edges per scenario, i.e. the average of four IoUs that put S0 at **0.618**.

* `AnalysisGap.owner` (`ir.rs`) is the block whose normal continuation runs
  alongside the gap; `BodyBuilder::gap_block(..., owner)` (`lowering.rs`) takes
  it, and all five call sites pass `cur` (java: `lower_try` catch,
  `gap_container`; python: `except`/`else` handler, `gap_container`,
  `value_gap_container`).
* `analyze_body` no longer seeds; `run_block` returns the content block as a
  **may** successor of its owner, with the owner's environment and the witness
  label `gap:<reason>`. A gap inside a dead arm stays dead; a gap on a live path
  is analysed with that path's values.
* A *mutation-capable* reason (`UnsupportedStatement`, `UnsupportedExpression`,
  `Widened`) also taints the fall-through edge, so a decision taken after an
  unmodeled construct is not accepted as a proof (`gap:<reason>` on its witness
  path). A pure value gap (`new Foo()`, `NotInFactContract`) keeps the
  continuation clean: it changes no tracked binding.
* `BodyAnalysis.tainted_blocks` records which blocks are reached only on such a
  witness.

Tests: `body_analysis::a_gap_block_keeps_its_effects_possible` (rewritten to the
new contract: the content block is named by its owner and stays `Possible`) and
the new `a_gap_block_owned_by_a_dead_arm_stays_dead`, which pins the leak:
`if (false)` owns a `new Foo()` content block holding a call, and the call stays
dead.

### 2. Call observations: a callee is entered with the values the call passed

* `CallObservation { env, receiver, args }`; `record_effect` evaluates the
  receiver and the arguments **in the block-local environment** (not the
  method entry state) and `BodyAnalysis.observations` keys them by
  `(block, call site)`, joining a re-visit (`CallObservation::join`).
* The engine hands the observation to `expand` → `bind_arguments`. A `Symbolic`
  argument now binds **by value** when the caller's variable has one
  (`String code = dto.getVerificationCode(); helper(code);` passes the empty
  string) in addition to the existing property transfer for object handles; a
  literal argument uses the observed value instead of re-evaluating it.
* `walk`'s visit set is keyed by `(method, environment fingerprint)` instead of
  the method alone: the same body reached with two different argument values is
  two analyses. This is what makes `helper("")` and `helper("X")` two visits
  with two verdicts, and their remote effects the union of both.

### 3. Pruning is a certificate per call site, not a property of the method

`let prunable = analysis.gaps.is_empty()` is gone, and with it the cause
`lowering_gaps_disable_pruning` ("this method contains an unrelated `new`, so
keep everything the legacy flood finds"). So is `exclusion_reason`, which
claimed "the CFG proves this call site unreachable" without naming a decision.

* `dead_blocks(body, analysis)`: for every decision whose witness path carries
  **no** `gap:` label, walk the arm the verdict cuts off (`dead_arm`, stopping at
  any block another path reaches — a shared exit is not dead) and return the
  blocks plus the decision that proves each of them
  (`DeadBlock { guard, line, verdict, path, block, blocks }`).
* `block_of_call_site(body)`: which basic block each lowered call site sits in.
  A skeleton site is dropped only when its own block is in the dead set, and the
  drop is recorded as a `Suppression { call_site, callee, certificate }`.
* Every other lowered, unreached site is **kept** with the cause
  `no_exclusion_certificate`, and a site the frontend never lowered keeps
  `skeleton_site_absent_from_lowered_body`.

Measured on the real login, `tt-semantic … --scenarios S0`, step 1 (this is the
end-to-end proof the review asked for, on the actual `TokenServiceImpl`):

| element | value |
|---|---|
| entry | `method:ts-auth-service:auth.controller.UserController#getToken(auth.dto.BasicAuthDto,org.springframework.http.HttpHeaders)` |
| bound request | `verificationCode = absent`, origin `context`, provenance `the task package states "no verification code at login" (at login)`; `username`/`password` `unknown` (payload) |
| decision | `TokenServiceImpl#getToken`, guard `g0`, line **65**, `proves_false`, witness path ``[]``, symbols `[StringUtils, verifyCode]` |
| suppressed 1 | `exchange` @ 67:55 — guard `g0` line 65 `proves_false` (path unconditional); blocks `[2,4,5,6]` |
| suppressed 2 | `getBody` @ 72:29 — same certificate |
| suppressed 3 | `info` @ 76:24 — same certificate |
| kept causes (step 1) | `{skeleton_site_absent_from_lowered_body: 18}` — the veto cause is gone |
| gaps (honest) | `TokenServiceImpl#getToken:ExceptionDispatch@85` (the `catch`), `NotInFactContract@49`, … |

| gate | before (C4) | after (C5) |
|---|---|---|
| `cargo test --workspace --locked --no-fail-fast` | 211 pass / 12 fail | **218 pass / 6 fail** |
| `review_b38_synthetic` | 1/5 | **5/5** |
| `review_b38_real_login` | 2/4 | **4/4** |
| `tt-export --mode legacy` / `--mode shadow` | `ea3c7ca2…` | `ea3c7ca2…` (unchanged) |
| `tt-export --mode semantic` | `59cd3426…` | `ea3c7ca2…` |
| `evaluate_golden.py gold/S0.json <semantic>` | 0.618 | **0.9260149572649572** — four IoUs identical to legacy (executes 0.944, calls 0.885, remote 1.000, data 0.875) |
| shadow `only_legacy` / `only_semantic` | 0 / 5 per scenario | **0 / 0** |
| `--shadow-out` hash | `eca6de1e…` | `9eeed004d31a5f2906692c038023db887c8324f241731f0aa27c833b65fc7e0e` |
| `evaluate_golden.py --check` | exit 3 | exit 3 |
| `cargo clippy --workspace --all-targets` | clean | clean |

Read honestly: the semantic answer is now byte-identical to the legacy answer on
all 8 scenarios, so C5 buys **no score**. What it changes is the *kind* of claim:
the 0.926 is no longer inherited from the legacy path on this scenario, it is
re-derived (the semantic run prunes nothing legacy keeps, and adds nothing
legacy lacks) and every dropped edge now names the guard, the line, the verdict
and the blocks that prove it. The five edges the semantic path used to add were
false positives from the seeded gap blocks — the ledger for the `0.618 → 0.926`
delta is exactly those 5 executes, 4 calls and 1 remote the gold never had.
What the semantic path still does *not* do is remove the remaining S0 false
positives (2 `executes`, 2 `calls`, 1 `data`): no decision proves them dead, so
they are kept and counted, which is the correct behaviour for a prover.

Remaining red after C5: java 3, python 3 — both in `lowering.rs` (`before`/return
propagation, abrupt `finally`, nested ternary exits), which is C6.

## B38-06a — the audit trail is byte-stable (C6, part 1)

Found while re-measuring C5: two runs of the same command produced **different
files** with the same facts.

```
./semarch/target/release/semarch tt-semantic tt-challenge --out a.json --require-sources
./semarch/target/release/semarch tt-semantic tt-challenge --out b.json --require-sources
```

`Skeleton.nodes` is a `HashMap<String, Node>`, and `request_field_decls` pushed
each type's fields in iteration order, so the `fields` array of every binding —
and the `gaps` list that mirrors it — came out in a run-dependent order. The
*set* was right; the artifact was not, which makes every quoted audit hash
unreproducible.

* `semarch-tt/src/request.rs::request_field_decls` now sorts each owner's
  declarations by `(name, type_raw)`. `handler_fields` keeps the descriptor
  order (already deterministic) and still dedups by name, so the visible order
  is fixed end to end.
* Two consecutive full audits are now byte-identical:
  `66beb6fb520828f45f3dc6b1a25eeafb9e9dbbf362e748ac17bd54ff36185c9d`.
* The answer is untouched: `tt-export` legacy/semantic/shadow all stay
  `ea3c7ca2…`, the shadow diff stays `9eeed004…`. This is observability only;
  the C5 numbers were re-checked against a re-run and hold.

### Numbering

The section numbers below follow the commit order in this repository. The plan's
own B38-05 (lossless binding, context) is the section **B38-04** here
(`bc3c7bf`), and the plan's B38-06/B38-07 (the call observed at its execution
point, the local uncertainty with useful pruning) are the section **B38-05**
here (`062d8c3`).

## B38-06 — completion-aware lowering (C6, part 2)

The last six prepared tests, all red since `b38fbf0`: java
`return_is_evaluated_before_finally`, `return_in_finally_overrides_pending_return`,
`nested_ternary_uses_actual_branch_exits`; python the same three with
`nested_conditional_uses_actual_branch_exits`. Three defects, each in both
frontends.

### 1. A ternary arm's exit is not the block it entered

`lower_ternary` terminated `then_block`/`else_block` — the blocks the arms were
*entered* in — with `Goto join`. When an arm's expression materialized blocks of
its own (a nested ternary), the arm's value ended somewhere else, so that
`Goto` overwrote the nested branch's terminator and the arm's value was lost
(`return true ? (false ? 1 : 2) : 3` gave `Unknown`, `reached_blocks [0,1,6]`).
Each arm now records where its value actually ended and *that* block gets the
`Goto`; the nested branch survives and the value is the arm's.

Python had a second, independent bug in the same function: it read the three
parts through `child_by_field_name("condition"/"body"/"alternative")`, but
**tree-sitter-python declares no fields on `conditional_expression`**
(`node-types.json`: `"fields": {}`). All three were `None`, so every Python
ternary was an `Unknown` condition over two `Unknown` arms. The parts are now
taken positionally — the grammar's source order is
`consequence if condition else alternative`.

### 2. `return x;` reads `x` before the `finally` body runs

`lower_return` evaluated the value, inlined the `finally` body, and *then*
emitted `Terminator::Return { value }`, so
`int x = 1; try { return x; } finally { x = 2; }` returned **2**. `lower_return`
and `lower_throw`/`lower_raise` now stamp the value into a fresh temporary
(`stamped`, and only when a `finally` clause is active — no temporaries for
plain returns) before the clause body is lowered, and the completion carries the
temporary.

### 3. A diverging `finally` supersedes the pending completion

`inline_finally` returned a block even when a clause body diverged, and the
caller then wrote its own `Return`/`Goto` into that block — overwriting the
clause's terminator. Hence `try { return 1; } finally { return 2; }` returned
**1**, and an unreachable statement after a `try` whose `finally` always
returns looked reachable. `inline_finally` now returns `Option<BlockId>`:
`None` means "a clause body diverged". `lower_return`, `lower_throw`/
`lower_raise`, the normal path of `lower_try` and every catch/except arm then
**drop** their pending completion instead of emitting it. Nesting stays correct
because a `return` inside a clause re-enters `lower_return` with only the
clauses *outside* it active, so it inlines those on its way out.

Files: `crates/semarch-frontend-java/src/lowering.rs` (`lower_ternary`,
`lower_return`, `lower_throw`, `stamped`, `inline_finally`, `lower_try`),
`crates/semarch-frontend-python/src/lowering.rs` (same functions, python names
`lower_raise`, `suite_body`). Diff: 171 insertions / 54 deletions over two
files; no test file was modified — the prepared suites were already the spec.

| gate | C5 (`062d8c3`) | C6 |
|---|---|---|
| `cargo test --workspace --locked --no-fail-fast` | 218 pass / 6 fail | **224 pass / 0 fail** |
| `review_b38_java` | 0/3 | **3/3** |
| `review_b38_python` | 0/3 | **3/3** |
| `tt-export` legacy / semantic / shadow | `ea3c7ca2…` | `ea3c7ca2…` |
| `--shadow-out` | `9eeed004…` | `9eeed004…` |
| S0 `evaluate_golden.py` | 0.9260149572649572 | unchanged |
| `evaluate_golden.py --check` | exit 3 | exit 3 |
| `cargo clippy --workspace --all-targets` | clean | clean |

**Reach, measured rather than assumed.** These fixes change no fact of the
contest project, and that is verifiable, not lucky: the skeleton covers 442
files / 1538 methods and excludes `old-docs/`; across the 479 Java files under
the loaded roots there is **no `finally` clause at all**, and no ternary whose
true arm contains a nested `?` or a `&&`/`||`. A full C5-binary audit and a full
C6-binary audit, compared step by step with the binding order normalised, are
identical in `decisions`, `effects`, `suppressions`, `sites`, `gaps` and
`prediction` — the only delta anywhere is the ordering fixed in B38-06a. The
fixes are pinned by the two prepared frontend suites, which is what they were
prepared for; they say nothing about Train Ticket, and are not claimed to.

Remaining red after C6: **none**.

## B38-07 — доставка: повторный прогон, документы и архив (C7)

Седьмой коммит инкремента (нумерация разделов — по порядку коммитов; соответствие
фазам плана — в таблице прогресса, §13.6 отчёта).

Инкремент закончен не тогда, когда тесты зелёные, а тогда, когда то, что о нём
написано, воспроизводится. Этот шаг ничего не меняет в поведении; он приводит
документы в соответствие с измеренным состоянием и пересобирает поставку.

### Приведено в соответствие

| артефакт | было | стало |
|---|---|---|
| `report.json` (корень) | `16d96bf…` от коммита `a4db167` (устарел) | `253a7a45b13a8d997e8ff28483ef6207baf71e2316bf4ed0abdf72be046ec99d` — вывод `tt-report` на текущем коде |
| `semarch/README.md` | «197 тестов» | «224 теста в 40 наборах» + раздел про совпадение semantic и legacy и про то, что его ценность — провенанс, а не балл |
| `scripts/package_submission.sh` (README архива) | «91 tests» | «229 tests» + `tt-semantic` в разделе проверки |
| `docs/SUPPORT_MATRIX.md` | вето `pruning_disabled_by_lowering_gaps`, `Absent → Null` по типу, «копия значения не берётся» | сертификат отсечения, честность свидетельского пути, `Null` только по доказательству, контекст пакета, скаляр по значению, выход плеча тернарного оператора |
| `docs/VERIFICATION.md` | таблица тени `only_semantic = 5`, вето, плечи тернарного оператора как «непроверенное» | помечено устаревшим; добавлен раздел «2026-10-19 — инкремент B38 (C1–C7)» со всеми командами, четырьмя IoU S0 и FP/FN |
| `REPORT_FOR_EXPERT.md` | §6.5 читал пять ложных рёбер как «осознанное расхождение» | исправлено явно (§13.1) + новый §13 «Инкремент B38» с коммитами, свидетелем, измерениями, прогрессом B38-01…10 и незакрытыми пунктами |
| `docs/adr/` | 0001…0007 | добавлен `0008-gap-ownership-and-exclusion-certificates.md` |

`report.json` — артефакт аудита, а не ответ: правка его не влияет на
`submission.json` (`ea3c7ca2…` до и после).

### Добавленный тест

`crates/semarch-tt/tests/b38_login_gate.rs` (5 тестов) пиннит полную цепочку на
настоящем `TokenServiceImpl#getToken`: единственный вход, `verificationCode =
absent (context)`, решение `g0` строка 65 `proves_false`, три отсечённых места
вызова с одним сертификатом (блоки `[2,4,5,6]`), отсутствие `remote` к сервису
кодов, абляция (`--disable context` возвращает ребро) и положительный контроль
(названный код сохраняет ребро). Подготовленные наборы `review_b38_*` — это
спецификация ревью-пакета; этот файл — пин инкремента.

### Итоговый прогон

```text
cargo test --workspace --locked --no-fail-fast   -> 40 наборов, 229 passed / 0 failed
cargo clippy --workspace --all-targets --locked  -> 0
tt-export  legacy / semantic / shadow            -> ea3c7ca2… (= submission.json)
           --shadow-out                          -> 9eeed004…, only_legacy=0, only_semantic=0
tt-semantic дважды                               -> 66beb6fb… (байтово одинаково)
tt-report                                        -> 253a7a45…
evaluate_golden.py gold/S0.json (legacy|semantic) -> 0.9260149572649572
evaluate_golden.py --check                       -> exit 3 (только формат)
```
