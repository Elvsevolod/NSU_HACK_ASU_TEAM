# ADR 0002 — Tree-sitter runtime and grammar version pins

Date: 2026-10-17
Status: Accepted (spike executed 2026-10-17)
Supersedes: none
Refs: `docs/adr/0001-stack-boundary.md`, `01_MULTILANG_RESEARCH_BRIEF.md`

## Candidate versions (verified on crates.io, 2026-10-17)

- `tree-sitter` runtime: **0.27.1**
- `tree-sitter-java`: **0.23.5**
- `tree-sitter-python`: **0.25.0**
- `tree-sitter-go`: **0.25.0**
- `tree-sitter-javascript`: **0.25.0**
- `tree-sitter-typescript`: **0.23.2**
- `tree-sitter-c-sharp`: **0.23.5**

Key fact from crate metadata inspection: every grammar crate's only normal
dependency is `tree-sitter-language ^0.1` (and `cc` as build dependency);
`tree-sitter` appears only as a **dev** dependency (`^0.24|^0.25.8`). Therefore
crate version ranges do **not** prove runtime/ABI compatibility: the real
spike risk is the grammar's generated `LANGUAGE_VERSION` vs. the `tree-sitter`
0.27.1 runtime (`tree_sitter::LANGUAGE_VERSION`).

## Spike (T-pre)

`crates/grammar-spike` loads all six grammars (plus TSX as the 7th variant)
with the pinned `tree-sitter` runtime and parses one fixture per language;
acceptance = no panic, no ERROR nodes. A failing grammar gets its pin
downgraded and the spike re-run.

## Results

Environment (2026-10-17, macOS 15.7.4 arm64):

- `rustc 1.99.1 (58cf8f9c3 2026-10-13)`, `cargo 1.99.1` — installed via
  `rustup` (minimal profile, stable).
- `cc`/`clang` — Apple clang 17.0.0 (recorded in ADR 0001).

Spike run (`cargo run -p grammar-spike`, exit 0):

```
java: ok (23 bytes)
python: ok (18 bytes)
go: ok (23 bytes)
javascript: ok (16 bytes)
typescript: ok (22 bytes)
tsx: ok (20 bytes)
c-sharp: ok (23 bytes)
SPIKE OK
```

No downgrades needed. Note on exports: `tree-sitter-typescript 0.23.2`
exports `LANGUAGE_TYPESCRIPT` / `LANGUAGE_TSX` (not a single `LANGUAGE`
const); all other pinned grammars export `LANGUAGE`.

## Final pins (normative for the whole workspace)

| Crate | Version |
| --- | --- |
| tree-sitter | 0.27.1 |
| tree-sitter-java | 0.23.5 |
| tree-sitter-python | 0.25.0 |
| tree-sitter-go | 0.25.0 |
| tree-sitter-javascript | 0.25.0 |
| tree-sitter-typescript | 0.23.2 |
| tree-sitter-c-sharp | 0.23.5 |

## Consequences

- Exact versions recorded here are normative for the whole workspace until a
  task re-opens this ADR.
- `tree-sitter-graph` stays out of the dependency set for v0.
