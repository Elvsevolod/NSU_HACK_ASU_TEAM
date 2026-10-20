#!/bin/sh
# Package the contest answer.
#
#   ./scripts/package_submission.sh [challenge-root] [out-zip]
#
# Defaults: challenge-root = ../../tt-challenge (the organizer inputs sitting
# next to this repository), out-zip = submission.zip in the working directory.
#
# The archive contains `submission.json` at its root (the only file the platform
# requires), the complete tool sources, the audit trail of the answer, and a
# README with the exact commands to reproduce it. Compiled artifacts
# (`target/`) are never packaged: the platform re-runs the code itself.
set -eu

here=$(cd "$(dirname "$0")/.." && pwd)
challenge=${1:-"$here/../tt-challenge"}
out=${2:-"$PWD/submission.zip"}

if [ ! -d "$challenge/skeleton" ] || [ ! -d "$challenge/scenarios" ]; then
    echo "usage: $0 <challenge-root with skeleton/ and scenarios/> [out.zip]" >&2
    exit 2
fi
# Resolve before changing directory, so relative arguments still work.
challenge=$(cd "$challenge" && pwd)
out_dir=$(cd "$(dirname "$out")" && pwd)
out=$out_dir/$(basename "$out")

cd "$here"
cargo build --release -p semarch-cli

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT

./target/release/semarch tt-export "$challenge" --out "$stage/submission.json"
./target/release/semarch tt-report "$challenge" --out "$stage/report.json"

mkdir -p "$stage/semarch"
tar -cf - \
    --exclude=target \
    --exclude='*.rlib' \
    Cargo.toml Cargo.lock README.md crates docs scripts |
    (cd "$stage/semarch" && tar -xf -)

cat >"$stage/README.md" <<'TXT'
# Train Ticket execution-graph answer (Rust)

`submission.json` in this archive is the answer for the eight scenarios of the
challenge. It was produced entirely by static analysis of the provided skeleton,
sources and scenario texts: the project was never started, and no runtime trace
was used.

## Reproduce

The tool needs the organizer inputs (`skeleton/`, `scenarios/`, `targets/`) and a
Rust toolchain (1.85+). No network access is required.

```sh
cargo build --release --manifest-path semarch/Cargo.toml -p semarch-cli
semarch/target/release/semarch tt-export <challenge-root> --out submission.json
```

`<challenge-root>` is the directory holding `skeleton/`, `scenarios/` and
`targets/`. The run takes about 0.15 s and is deterministic: the same inputs
produce a byte-identical `submission.json`.

## Verify

```sh
cargo test --manifest-path semarch/Cargo.toml          # 229 tests, incl. the generality gate
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
TXT

( cd "$stage" && zip -qr "$out" submission.json report.json README.md semarch )
echo "wrote $out"
unzip -l "$out" | tail -3
