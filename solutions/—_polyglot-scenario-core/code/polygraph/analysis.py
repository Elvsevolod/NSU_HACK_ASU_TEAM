"""Bounded path replay with independent scenario states and explicit coverage."""
from collections import deque
from copy import deepcopy

from .grounding import Grounder
from .kernel import BranchPoint, Incomplete, Infeasible, Kernel
from .state import State
from .values import Raised, Unknown, serial


def analyze(project, initial, context, scenario, grounder=None, path_limit=16, loop_limit=32, depth_limit=32, step_limit=30000, policy="may", smt=True, smt_timeout_ms=50):
    if context.get('configuration',project.source_configuration)!=project.source_configuration:
        raise ValueError('Deployment configuration differs from the project index; rebuild Project with this configuration')
    grounder = grounder if grounder is not None else Grounder(project)
    pending, paths, frontier = deque([()]), [], []
    attempts = 0
    solver_totals = {"checks": 0, "pruned_outcomes": 0, "unknown": 0, "seconds": 0.0}
    solver_failures = set()
    attempt_limit = path_limit * 8 + 1
    while pending and len(paths) < path_limit and attempts < attempt_limit:
        decisions = pending.popleft()
        engine = Kernel(project, State(deepcopy(initial)), decisions, loop_limit, depth_limit, step_limit, context, smt, smt_timeout_ms)
        engine.scenario_id = str(scenario["id"])
        steps, history, coverage = [], {"steps": {}}, "complete"
        attempts += 1
        try:
            for index, step in enumerate(scenario.get("steps", []), 1):
                request, binding = grounder.bind(engine, scenario, step, history)
                if request is None:
                    coverage = "unknown-input"
                    break
                response = engine.request(request)
                record = {"step": step.get("n", index), "grounding": binding, "request": request, "response": response}
                steps.append(record)
                history["steps"][str(step.get("n", index))] = {"body": response.body, "status": response.status, "headers": response.headers}
                if not grounder.apply_response(engine, binding, response):
                    break
                if type(response.status) is int and response.status >= 400:
                    break
                if isinstance(response.status, Unknown):
                    engine.note("unknown-step-status", "A failed step may stop the scenario")
                    if engine.choose((False, True), "scenario stop after unknown HTTP status"):
                        break
        except BranchPoint as branch:
            frontier.append({"edges": deepcopy(engine.edges), "label": branch.label})
            for choice in branch.choices:
                pending.append(decisions + (choice,))
            continue
        except Incomplete:
            coverage = "cutoff"
        except Infeasible:
            continue
        except Raised as exc:
            engine.note("scenario-exception", "Scenario stops at an uncaught exception", exception=exc.typ)
            coverage = "exception"
        finally:
            for name, value in engine.solver.statistics.items():
                solver_totals[name] += value
            solver_failures.update(engine.solver.failures)
        paths.append({"decisions": list(decisions), "edges": engine.edges, "steps": steps, "events": engine.events,
                      "diagnostics": engine.diagnostics, "coverage": coverage, "partial": engine.partial,
                      "state": engine.state.store.snapshot(), "operations": engine.operations})
    may = set().union(*(set(path["edges"]) for path in paths), *(item["edges"] for item in frontier))
    fully_explored = not pending and all(path["coverage"] != "cutoff" for path in paths)
    must = set.intersection(*(set(path["edges"]) for path in paths)) if paths and fully_explored else set()
    selected = may if policy == "may" else must
    output = {"method": "polyglot-ir-" + policy,
              "edges": [{"source": a, "relation": b, "target": c} for a, b, c in sorted(selected)]}
    evidence = {}
    for path in paths + frontier:
        for edge, reasons in path["edges"].items():
            key = " | ".join(edge)
            evidence.setdefault(key, [])
            for reason in reasons:
                if reason not in evidence[key]:
                    evidence[key].append(reason)
    for path in paths:
        path["edges"] = [{"source": a, "relation": b, "target": c} for a, b, c in sorted(path["edges"])]
    detail = {"status": "complete-in-model" if fully_explored and not any(p["partial"] for p in paths) else "partial",
              "projection": policy, "paths": paths, "path_attempts": attempts, "pending_paths": len(pending),
              "path_attempt_limit": attempt_limit,
              "path_budget_exhausted": bool(pending), "fully_explored_in_model": fully_explored,
              "must": [{"source": a, "relation": b, "target": c} for a, b, c in sorted(must)],
              "may": output["edges"] if policy == "may" else [{"source": a, "relation": b, "target": c} for a, b, c in sorted(may)],
              "solver": {"enabled": smt, "timeout_ms": smt_timeout_ms, **solver_totals, "failures": sorted(solver_failures)},
              "evidence": evidence, "scope": "Observed/model-supported effects; opaque tails may contain additional unknown effects"}
    return output, serial(detail)


def validate(project, submission):
    if submission.get("project") != project.skeleton["project"]:
        raise ValueError("Submission project differs from skeleton")
    for scenario, block in submission["scenarios"].items():
        seen = set()
        for edge in block["edges"]:
            source, relation, target = (edge[k] for k in ["source", "relation", "target"])
            signature = source, relation, target
            if signature in seen:
                raise ValueError("Duplicate edge")
            seen.add(signature)
            if relation not in {"executes", "calls", "remote", "data"} or target not in project.nodes:
                raise ValueError("Invalid edge kind or target")
            if relation == "executes":
                if source != "scenario:" + scenario or project.nodes[target].get("kind") != "method":
                    raise ValueError("Invalid executes edge")
            elif source not in project.nodes or project.nodes[source].get("kind") != "method":
                raise ValueError("Invalid source method")
            elif project.nodes[target].get("kind") != ("data_resource" if relation == "data" else "method"):
                raise ValueError("Invalid target kind")
