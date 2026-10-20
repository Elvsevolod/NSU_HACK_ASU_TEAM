# R increment — proof validity, call locator, explicit call outcomes, continuation coordinator

Base: `975ab41` (B38-07). Nothing is pushed. This document reports the R
increment only: what changed in real code, the commands that were run with
their exit codes, how many tests executed, what was proven, and what was not.

## Control line

| control | expected | reproduced |
| --- | --- | --- |
| `submission.json` SHA-256 | `ea3c7ca2cd9f5b9929cdafeb8ba0d593cf995a30999425c64658a46dbc7ae25d` | yes — `semantic.json` is byte-identical |
| reference `report.json` SHA-256 | `253a7a45b13a8d997e8ff28483ef6207baf71e2316bf4ed0abdf72be046ec99d` | yes |
| S0 score | `0.9260149572649572` | yes |
| source `#[test]` declarations | 229 at the base | 229 + 28 gate declarations = **257 executed / 257 passed / 0 failed** |

The base source had 229 test declarations; the review package added 14, R01b
added 2, R03 added 4, and R04/R05 added 8, for 257 declarations, all of which
executed and passed. No test was skipped, filtered or ignored.

## Commits

| commit | title |
| --- | --- |
| `fc74d60` | R01/R02: prove-validity is a join, and a field write is not an old binding |
| `29d2ede` | R01b: only a try's own finally runs on an inline completion |
| `7680cd5` | R03: the call anchor is the invocation's own name token, on its own row |
| `75307c8` | R04/R05: a call has an outcome, and a callee body is entered in the caller's state |

### `fc74d60` — R01/R02

Real code: `semarch-core/src/analysis.rs` (`tainted_blocks` becomes a monotone
join over *every* reaching path plus the gap content of tainted blocks;
`step_tainted`; new `apply_assign` and `invalidate_properties` called from
`run_block`), `semarch-tt/src/engine.rs` (`dead_blocks` refuses a decision whose
block is tainted or whose witness carries a `gap:` label). New source-only gate
`semarch-core/tests/review_975_core.rs`.

Commands: `cargo test -p semarch-core --test review_975_core --locked` → exit 0
(3/3). Whole workspace with the package's files present: 235 passed / 8 failed.

Proven: an absence proof is a property of every path reaching the guard, not of
the first witness, so `gap:` in the first witness is not a certificate; a known
field write invalidates the old binding and a receiver rebind clears the old
object's properties.

Limits: there is no heap model. A read of unknown storage is `Unknown`; a known
constant that a call site used is never replaced by `Unknown`. No global veto on
gaps. Legacy, semantic, audit and S0 are unchanged by this commit.

### `29d2ede` — R01b

Real code: `semarch-frontend-java/src/lowering.rs` and
`semarch-frontend-python/src/lowering.rs` add `run_finally(clause,
Option<BlockId>) -> Option<BlockId>` and use it on the `try` normal path and the
catch/except path instead of `inline_finally`, which ran the whole enclosing
finally stack and leaked an outer `x = 9` into `return x`. Gates:
`semarch-frontend-java/tests/review_975_java.rs` (2/2) and two cases in
`review_b38_python.rs` (15/15).

Commands: per-suite gates → exit 0; whole workspace 239 passed / 6 failed (the
sites and continuations gates, still open at this point). Clippy 0 after
replacing a wrong `let clause = clause?` with an explicit `let Some(..) else`.

Limit: the real Train Ticket checkout has **0** `finally` bodies, so this fix
is not exercised by the answer; it is a source-only correctness fix.

### `7680cd5` — R03

Real code: `semarch-core/src/ir.rs` adds `CallSite::name_span:
Option<SourceSpan>` (`#[serde(default)]`). Both frontends fill it from the
tree-sitter `name`/`attribute` node (the callee token exactly as parsed, with
its own row and byte column). `semarch-tt/src/bodies.rs` uses it in
`FileUnit::{name_span, anchor, anchor_col, site_line}` and falls back to a
string/comment-aware scan (`code_mask`, `matching_open`, `ident_ending_at`,
`is_whole_word`) that finds the invocation's own argument list from its closing
`)`. `semarch-tt/src/engine.rs` now resolves at the name's line.

The only adaptation to the package's prepared files is mechanical: `CallSite`
literals in `graph_tests.rs` (3), `ir_roundtrip.rs`, `analysis_propagation.rs`
(2), `body_analysis.rs`, `guards.rs` and `review_975_core.rs` gained `name_span:
None`. No assertion was changed.

New gate `semarch-tt/tests/review_975_locator.rs` (4/4): a multi-line receiver
keeps the name on its own row; a Cyrillic literal before the name does not
shift the byte column; two same-line invocations get distinct anchors; the
fallback lexer names the *outer* `f(x).f(1)`.

Commands: `review_975_sites` 3/3 and `review_975_locator` 4/4 → exit 0; whole
workspace 246 passed / 3 failed (the three continuations gates); clippy 0;
release build 0.

Proven: `f(f(1))`, `f("f(0)")`, `f(/* f( */ 1)` and a multi-line receiver no
longer anchor at the wrong token or the wrong row.

Limit: the fallback is still a scan, kept only for hand-built call sites no
frontend produced. The `tt-semantic` audit hash moved `66beb6fb` → `d6db6fb6`
because `CallSite` serialises `name_span`; the scored answer stayed `ea3c7ca2`.

### `75307c8` — R04/R05

Real code:

* new `semarch-core/src/invocation.rs`: `CallOutcome { Returns(value), Void,
  NoNormal, Unknown, Cutoff }` with `value()`, `may_return_normally()`,
  `describe()`, `join()`; `CallTargetProvider`; `CalleeBody`.
* `semarch-core/src/analysis.rs`: `AnalyzeInputs` / `analyze_body_with` (the
  5-argument `analyze_body` is kept as a wrapper); `Analyzer` gains
  `targets`/`file`/`depth_level`/`cache`; `eval_callee_body` enters the callee as
  its own ordered body, binding the actual arguments to the declared parameter
  **names** and carrying the receiver's known properties by handle; `returns`
  non-empty → `Returns`/`Void`, empty with no `Widened` gap → `NoNormal`, empty
  but `Widened` → `Cutoff`; `run_block` now evaluates `Statement::Eval`, cuts
  the rest of the block when a value is bottom, and treats a `Branch`/`Return`/
  `Throw` whose own expression is bottom as not reached;
  `ReturnSite.has_value`; `BodyAnalysis.{call_outcomes, no_return_blocks}`; an
  `OutcomeCache` memo keyed by identity, bound arguments and entry depth.
* `semarch-tt/src/invocations.rs`: `BodyProvider` over `BodyIndex`, resolving
  at line 0 so a same-name same-arity overload set stays unresolved instead of
  guessed.
* `semarch-tt/src/engine.rs`: `dead_blocks` turns a never-returning block into
  the same kind of certificate as a guard (skipped for a `gap:` witness or a
  tainted block); `walk`'s worklist carries the call's certainty, `visit_key`
  includes it, and `expand` enters the callee with the caller's certainty.

Commands at this commit: `cargo test --workspace --locked --no-fail-fast` →
exit 0, 257 passed / 0 failed; `cargo clippy --workspace --all-targets
--locked` → exit 0, 0 warnings; `cargo build --release --workspace --locked` →
exit 0.

Gate R:

* `review_975_continuations` (from the package) 6/6 — it was 2/6 at the base and
  3/6 after R01/R02. `helper("")` → false prunes the later remote; `helper("X")`
  → true keeps it; a helper that returns `Unknown` keeps a possible
  continuation; a throw-only helper makes the caller's normal continuation
  unreachable; a possibly-taken call cannot make the callee's remote
  unconditionally confirmed (`status != "confirmed"`).
* `review_975_gate_r` (own) 4/4 — a callee that assigns a local before
  `return <local>` (the flat-return shortcut would see an unknown local); two
  calls of one helper with different arguments stay independent; two same-named
  helpers in different files are not one summary, in both directions.
* `review_975_invocation` (own) 4/4 — only `NoNormal` cuts the caller; `Unknown`
  and `Cutoff` are not absences; `join()` never turns a returning visit into an
  absence.

Proven fixes: an explicit call point with a result slot, a normal continuation
(the block's successor) and the reached `throws` as the exceptional one; a
helper that throws only cuts the caller's later remote with a certificate; a
field write is not pruned using the old binding; caller certainty crosses the
call boundary.

Limits and honest notes:

* The nested-body analysis was first written without a memo and the real
  project's semantic export **did not finish**; the `OutcomeCache` fixed it and
  the export now runs in about 3 s. This is reported because it was a real
  regression seen in this work, not a hypothetical.
* `NoNormal` is a proof only for a converged sweep; a `Widened` gap yields
  `Cutoff`. There is no dedicated end-to-end widening test — the guard is
  design-only in this increment.
* The memo is shared for one top-level analysis; the engine re-analyzes per
  queue state, and a method can now be visited under both certainties.
* The `tt-semantic` audit hashes `d6db6fb6` → `56c9f968`: per-step `effects`
  now mark effects reached through a possibly-taken call as `possible` instead
  of `confirmed` (R05), and `sites.resolved_exact` counts the extra per-visit
  resolutions. It is an internal artifact; the scored answer is byte-identical
  (`ea3c7ca2`).

## Gate R evidence at HEAD

| command | exit | result |
| --- | --- | --- |
| `cargo test --workspace --locked --no-fail-fast` | 0 | 257 passed / 0 failed |
| `cargo clippy --workspace --all-targets --locked` | 0 | 0 warnings |
| `cargo build --release --workspace --locked` | 0 | release binary built |
| `tt-export --mode legacy` | 0 | `ea3c7ca2` |
| `tt-export --mode semantic` | 0 | `ea3c7ca2` == `submission.json` |
| `tt-export --mode shadow --shadow-out` | 0 | 8 diff entries, all agreed |
| `tt-semantic` ×2 | 0 | `56c9f968` both times |
| `tt-report` | 0 | `253a7a45` |
| `evaluate_golden.py gold/S0.json semantic.json` | 0 | S0 `0.9260149572649572` |
| `evaluate_golden.py --check` | 3 | format only; 514 accepted edges for S7, none rejected |

`cargo fmt --all` was **not** run: HEAD is not rustfmt-clean (323 hunks across
the tree), so every change was hand-applied as a minimal diff.

## S0 false positives and false negatives

S0 is the only scenario with a reference answer. The prediction is
byte-identical to the base, so these are the same 4 IoUs as before R.

* executes: pred 36, gold 34, tp 34, FN 0, FP 2 —
  `method:ts-auth-service:auth.exception.UserOperationException#<init>(java.lang.String)`,
  `method:ts-contacts-service:contacts.entity.Contacts#<init>()`.
  Cause: both are constructors reached from a call expression; the graph has
  no separate node kind for "allocated, not executed as a handler", so a
  constructor invocation is reported as an executed method.
* calls: pred 25, gold 24, tp 23, FN 1, FP 2.
  * FN `getToken(BasicAuthDto, HttpHeaders) → User#getPassword()`.
  * FP `getToken(BasicAuthDto, HttpHeaders) → UserOperationException#<init>(String)`.
  * FP `queryOrders(QueryInfo, String, HttpHeaders) → StringUtils#String2Date(String)`.
* remote: pred 0, gold 0.
* data: pred 8, gold 7, tp 7, FP 1 —
  `loadUserByUsername(String) → res:table:ts-auth-service.user_roles`.

**Flagged attribution issue (not fixed).** The intended call is a name
collision, not a missing edge: the real receiver of `getPassword()` in
`TokenServiceImpl#getToken` is the `BasicAuthDto dto` parameter, i.e.
`auth.dto.BasicAuthDto#getPassword`, while the graph binds the simple name
`getPassword` to `auth.entity.User#getPassword`. The two receivers are not the
same object and must not be merged; fixing it needs receiver-type-aware getter
attribution (a DTO-shape step), which is outside this increment. The matching
FP (`UserOperationException#<init>`) has the same root: a constructor chosen by
simple name.

## S1–S7 — coverage only, no score claimed

There is no reference answer for S1–S7 in the package; only format is checked.
Accepted edges (no rejects): S0 69, S1 541, S2 672, S3 520, S4 565, S5 690,
S6 552, S7 514. `--check` rejects none.

Legacy and semantic agree on every scenario (`only_legacy=0`,
`only_semantic=0`); `shadow.diff.json` is a list of 8. Semantic per-scenario
sizes are in the export log. No hidden score is inferred from these numbers.

## Manifest

```
commit=75307c8aab9ce5d0bc8a19e168042cc8985e1952
base=975ab41
skeleton_sha256=765f38d8b528268d38be5154fd2f512cf383809df814bc3c5bdb5d9bf1a1faba
gold_S0_sha256=483b4365c11be25ac8118d1d535f993a85b18568c0981f18d715027b87d7e2ce
targets_tree_sha256=e76a03234ee86fba2a28f0ba88df9aecaa8d30376cf876021dbadad27e2f4e65 (1131 files)
context_tree_sha256=a890f897031038a221cd8ce6080c022e5d32e84fd7dd2a07ee7df188c261d69c
legacy.json=ea3c7ca2cd9f5b9929cdafeb8ba0d593cf995a30999425c64658a46dbc7ae25d
semantic.json=ea3c7ca2cd9f5b9929cdafeb8ba0d593cf995a30999425c64658a46dbc7ae25d
audit.json=56c9f9684a1e33e9217912f5d58ab02e3a7ac98aecfd4b54d2618db42cfacb54
audit2.json=56c9f9684a1e33e9217912f5d58ab02e3a7ac98aecfd4b54d2618db42cfacb54
report.json=253a7a45b13a8d997e8ff28483ef6207baf71e2316bf4ed0abdf72be046ec99d
evaluate_golden.py=721b956221f0d75c9d8da9a04464526aeb03751d8bbea944d5655457a0c6997f
```

## Unresolved, cut off, or not started

* The `Token → User#getPassword` attribution above, and the constructor-as-call
  FPs, remain open.
* The real Train Ticket source has no `finally` bodies, so R01b is unmeasured on
  it.
* The `Widened`→`Cutoff` guard has no end-to-end test.
* The engine's per-visit counters and effect statuses changed; only the scored
  answer was held constant.
* Not started (must not begin before Gate R): H01–H04 (separate
  `HttpRequest`/`Endpoint` binding → client error policy → caller continuation,
  plus `contracts/http_fixture`), and `StateSnapshot`/`Delta`.
* Nothing was pushed; the reference `submission.json` and the reference
  `report.json` were never overwritten.
