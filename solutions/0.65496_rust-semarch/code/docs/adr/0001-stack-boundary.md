# ADR 0001 — Stack boundary: Rust core + Tree-sitter frontends

Date: 2026-10-17
Status: Accepted

## Context

We build a lightweight semantic architectural/behaviour analyzer of
microservice code (source + graph + scenario text + initial state →
executes/calls/remote/data). The primary contest target is Train Ticket
(submission ZIP with `submission.json`, S0–S7). The product must generalize to
multi-language projects afterwards (Tier-A: Java, Python, Go, JavaScript,
TypeScript, C#).

The legacy plan `PLAN_TRAIN_TICKET_ANALYZER.md` used Java + JavaParser. The
completed audit (`docs/INPUT_AUDIT.md`, formerly
`TRAIN_TICKET_AGENT_AUDIT.txt`) verified its Train Ticket-specific findings,
but the architectural decision stands: **the semantic core is language-neutral;
JavaParser is not the main architecture.**

## Decision

1. **Primary stack: Rust + Tree-sitter.**
   - `semarch-core` — Common Semantic IR, ProjectDiscovery, `LanguageFrontend`
     trait, CFG/guards/values. No Tree-sitter AST nodes leak into core.
   - `semarch-frontend-*` — per-language Tree-sitter frontends converting
     normalized semantic facts into core IR.
   - Train Ticket canonical IDs stay inside the special adapter/exporter
     (`semarch-seed`, later phase). No new contest IDs are synthesized; IDs are
     copied verbatim from skeleton `nodes`.
2. **Contest rules honored:**
   - sources may be read and compiled, but Train Ticket / its services / traces
     are never run to infer behavior;
   - no hardcoded per-scenario answers (no `scenario_id == "S7"` branches);
   - no fabricated IDs; `relation` field (not `type`);
   - `unknown != false`; every semantic edge carries evidence with status
     (`confirmed | possible | excluded | unresolved`);
   - the `instance.json → solution.json` rule of the other contest task does
     NOT apply here.
3. **No internal LLM agent in the product.** ML is only an optional
   `SemanticRanker` (candidate: `jinaai/jina-embeddings-v2-base-code`,
   Python sandbox until an explicit ONNX-in-Rust decision passes Gate ML).
4. **Dependencies added only by vertical tasks** (no heavy engines "just in
   case"). Baseline infra: `petgraph`, `ignore`, `serde`, `serde_json`,
   `clap`, `anyhow`/`thiserror`, `indexmap`, `tree-sitter` + grammar crates.
5. **Benchmarks ladder:** Train Ticket S0 (scored, gold reproducible: 
   `python3 platform/baseline_nlp.py skeleton/trainticket.json.gz
   targets/trainticket scenarios/*.json -o ans.json --explain` then
   `python3 platform/evaluate_golden.py gold/S0.json ans.json`) → Istio
   Bookinfo `samples/bookinfo/` (gold v0) → Online Boutique (gRPC, 11
   services) → OpenTelemetry Demo. Exact commit SHAs pinned; no runtime traces
   as oracle; own gold/manifests stored, third-party repos not vendored.

## Environment verification (2026-10-17, macOS 15.7.4 arm64)

- `cc` — present (`/usr/bin/cc`, Apple clang 17.0.0) — required because all
  grammar crates compile C sources via the `cc` build dependency.
- `clang` — present (`/usr/bin/clang`, Apple clang 17.0.0).
- `cargo` / `rustc` / `rustup` — **absent**; installed via `rustup` (minimal
  profile, stable toolchain) as a prerequisite of T01. Exact version recorded
  in `docs/adr/0002-grammar-pin.md` when available.

## Consequences

- JavaParser/Java-specific knowledge is confined to Train Ticket
  adapter/exporter design notes (audit findings A1–A13), not to core.
- Language support is a capability matrix per frontend, not a boolean.
- Framework semantics (Spring/Flask/gRPC) live above the frontend layer; the
  frontend never knows about frameworks.
