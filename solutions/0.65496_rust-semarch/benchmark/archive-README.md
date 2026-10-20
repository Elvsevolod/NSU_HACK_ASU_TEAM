# Train Ticket execution-graph answer (Rust)

`submission.json` in this archive is the answer for the eight scenarios of the
challenge. It was produced entirely by static analysis of the provided skeleton,
sources and scenario texts: the project was never started, and no runtime trace
was used.

## Reproduce

The tool needs the organizer inputs (`skeleton/`, `scenarios/`, `targets/`) and a
Rust toolchain compatible with the locked dependencies. The first build may
need network access to download Cargo dependencies; analysis itself is local.

```sh
cargo build --release --locked --manifest-path semarch/Cargo.toml -p semarch-cli
semarch/target/release/semarch tt-export <challenge-root> --out submission.json
```

`<challenge-root>` is the directory holding `skeleton/`, `scenarios/` and
`targets/`. The run takes about 0.15 s and is deterministic: the same inputs
produce a byte-identical `submission.json`.

## Verify

```sh
cargo test --manifest-path semarch/Cargo.toml          # includes the generality gate
semarch/target/release/semarch tt-report <challenge-root> --out report.json
semarch/target/release/semarch tt-semantic <challenge-root> --out audit.json
```

`report.json` is the audit trail of the answer: for every edge it names the
skeleton call site (`file:line`, receiver) and the relation the edge rests on,
and for every call site the scenario's feature set kills it names the feature
that would revive it. `audit.json` is the semantic trail of the same run: the
bound request fields with their provenance, the guard decisions, the call sites
each decision proves dead (with its certificate), and the coverage counters.
See `semarch/README.md` for the method and the measured ablation table, and
`semarch/docs/` for the decision records.
