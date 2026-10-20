import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import sys
import time

from .analysis import analyze, validate
from .grounding import Grounder
from .project import Project, RUNTIME_PACKAGES, read_json
from .state import load_context
from .ui_extract.native import statistics as js_statistics
from .security_models import CALLS as native_security_calls


def main():
    parser = argparse.ArgumentParser(description="Source-only Java/Spring and Python/FastAPI scenario analyzer")
    for key in ["source", "skeleton", "scenarios", "output", "report"]:
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--profile", action="append", default=[])
    parser.add_argument("--policy", choices=["may", "must"], default="may")
    parser.add_argument("--path-limit", type=int, default=16)
    parser.add_argument("--loop-limit", type=int, default=32)
    parser.add_argument("--depth-limit", type=int, default=32)
    parser.add_argument("--step-limit", type=int, default=30000)
    parser.add_argument("--sql-dialect", default="mysql")
    parser.add_argument("--no-smt", action="store_true")
    parser.add_argument("--smt-timeout-ms", type=int, default=50)
    args = parser.parse_args()
    if any(v < 1 for v in [args.path_limit, args.loop_limit, args.depth_limit, args.step_limit, args.smt_timeout_ms]):
        parser.error("Budgets must be positive")
    start = time.perf_counter()
    js_before = js_statistics()
    security_before=dict(native_security_calls)
    context_path=args.context
    if context_path and context_path.is_dir():
        candidates=[path for path in context_path.iterdir() if path.suffix in {'.json','.sql','.gz'}]
        context_path=candidates[0] if len(candidates)==1 else None
    startup=read_json(context_path) if context_path and context_path.suffix=='.json' else {}
    project = Project(args.source, args.skeleton, args.cache, args.profile,startup.get('globals',{}),startup.get('configuration',{}))
    initial, context, warnings = load_context(args.context, project, args.sql_dialect)
    context = {**context, "sql_dialect": args.sql_dialect}
    grounder = Grounder(project)
    prepared = time.perf_counter() - start
    files = sorted(args.scenarios.glob("*.json")) if args.scenarios.is_dir() else [args.scenarios]
    scenarios = [read_json(p) for p in files]
    if not scenarios or len({s["id"] for s in scenarios}) != len(scenarios) or any(s.get("project") != project.skeleton["project"] for s in scenarios):
        parser.error("Missing/duplicate scenarios or project mismatch")
    submission = {"project": project.skeleton["project"], "scenarios": {}}
    input_paths = [args.skeleton, *files]
    if args.context:
        input_paths.extend([args.context] if args.context.is_file() else sorted(p for p in args.context.iterdir() if p.is_file()))
    report = {"version": 13, "fingerprint": project.fingerprint, "projection_policy": args.policy,
              "preparation_seconds": prepared, "model_calls": 0, "application_executed": False,
              "context_warnings": warnings, "scenarios": {}, "environment": {"python": platform.python_version(),
              "platform": "-".join((platform.system(), platform.release(), platform.machine())), "packages": {name: importlib.metadata.version(name) for name in RUNTIME_PACKAGES}},
              "sql_dialect": args.sql_dialect, "smt_enabled": not args.no_smt, "smt_timeout_ms": args.smt_timeout_ms,
              "budgets": {k: getattr(args, k) for k in ["path_limit", "loop_limit", "depth_limit", "step_limit"]},
              "inputs": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in input_paths}}
    for scenario in scenarios:
        block, detail = analyze(project, initial, context, scenario, grounder, args.path_limit, args.loop_limit, args.depth_limit, args.step_limit, args.policy, not args.no_smt, args.smt_timeout_ms)
        submission["scenarios"][str(scenario["id"])] = block
        report["scenarios"][str(scenario["id"])] = detail
    validate(project, submission)
    project.save_cache()
    js_after = js_statistics()
    js_after['calls'] -= js_before['calls']
    js_after['seconds'] -= js_before['seconds']
    report.update({"analysis_seconds": time.perf_counter() - start - prepared,
                   "elapsed_seconds": time.perf_counter() - start, "source_files": len(project.sources),
                   "methods": len(project.methods), "endpoints": len(project.endpoints), "lowered_methods": project.lowered,
                   "IR_cache_hits": project.cache_hits, "project_diagnostics": project.diagnostics,
                   "source_framework_versions": project.framework_versions,
                   "deployment_configuration":project.configuration.summary(),
                   "frontend":grounder.ui.summary(), "native_javascript":js_after,
                   "native_security":{k:native_security_calls[k]-security_before[k] for k in native_security_calls},
                   "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(submission, ensure_ascii=False, indent=2) + "\n")
    report["submission_sha256"] = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ["elapsed_seconds", "preparation_seconds", "analysis_seconds", "endpoints", "lowered_methods", "IR_cache_hits", "submission_sha256"]}))
