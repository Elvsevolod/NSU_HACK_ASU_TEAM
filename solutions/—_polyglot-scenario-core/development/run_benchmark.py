"""Run the analyzer, then the official evaluator in a separate process."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

VARIANT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=Path, default=VARIANT.parents[1] / "tt-challenge")
    args = parser.parse_args()
    benchmark = VARIANT / "benchmark"
    common = [sys.executable, "-B", str(VARIANT / "code/offline_run.py"), "--source", str(args.case_root / "targets/trainticket"),
              "--skeleton", str(args.case_root / "skeleton/trainticket.json.gz"), "--context", str(args.case_root / "context/db-after-warmup.sql.gz"), "--scenarios", str(args.case_root / "scenarios")]
    commands = []

    def run(command, stem, allowed=(0,), seed="0"):
        started = time.perf_counter()
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": seed}
        result = subprocess.run(command, text=True, capture_output=True, env=env)
        (benchmark / (stem + ".stdout.txt")).write_text(result.stdout)
        (benchmark / (stem + ".stderr.txt")).write_text(result.stderr)
        commands.append({"command": command, "returncode": result.returncode, "wall_seconds": time.perf_counter() - started, "hash_seed": seed})
        if result.returncode not in allowed:
            raise RuntimeError(result.stderr or result.stdout)
        return result.stdout

    run(common + ["--output", str(VARIANT / "submission.json"), "--report", str(benchmark / "analysis-report.json")], "run")
    evaluator = [sys.executable, "-B", str(args.case_root / "platform/evaluate_golden.py")]
    evaluation = json.loads(run(evaluator + [str(args.case_root / "gold/S0.json"), str(VARIANT / "submission.json"), "--json"], "evaluation"))
    (benchmark / "s0-evaluation.json").write_text(json.dumps(evaluation, indent=2, ensure_ascii=False) + "\n")
    run(evaluator + ["--check", str(args.case_root / "skeleton/trainticket.json.gz"), str(VARIANT / "submission.json"), "--json"], "format", allowed=(3,))
    run(common + ["--output", str(benchmark / "repeat.json"), "--report", str(benchmark / "repeat-report.json")], "repeat", seed="17")
    identical = (VARIANT / "submission.json").read_bytes() == (benchmark / "repeat.json").read_bytes()
    assert identical
    report = json.loads((benchmark / "analysis-report.json").read_text())
    result = {"commands": commands, "hash_seed_repeat_identical": identical,
              "sha256": hashlib.sha256((VARIANT / "submission.json").read_bytes()).hexdigest(),
              "local_s0": evaluation["score"], "relations": evaluation["scenarios"]["S0"]["sets"],
              "measurement": {key: report[key] for key in ["preparation_seconds", "analysis_seconds", "elapsed_seconds", "peak_rss_bytes", "source_files", "methods", "endpoints", "lowered_methods", "IR_cache_hits", "model_calls"]}}
    (benchmark / "summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: result[key] for key in ["sha256", "local_s0", "measurement"]}))


if __name__ == "__main__":
    main()
