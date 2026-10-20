"""Reproduce component benefits, including a paired SMT ablation."""
import ast
import importlib.metadata
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

VARIANT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(VARIANT / "code"), str(VARIANT / "code/tests")]
from support import fixture, scenario
from polygraph.analysis import analyze
from polygraph.kernel import Kernel
from polygraph.project import Project
from polygraph.state import load_context
from polygraph.values import serial


def main():
    result = {"application_executed": False, "external_model_calls": 0,
              "versions": {name: importlib.metadata.version(name) for name in ["sqlglot", "libcst", "z3-solver"]}, "smt_ablation": {}}
    python = '''from fastapi import FastAPI
app=FastAPI()
def impossible():return -1
def possible():return 1
@app.get("/value")
def value(n:int):
    if n>10:
        if n<5:return impossible()
    return possible()
'''
    java = '''import org.springframework.web.bind.annotation.*;
@RestController class Handler {int impossible(){return -1;}int possible(){return 1;}
@GetMapping("/value")int value(@RequestParam int n){if(n>10){if(n<5)return impossible();}return possible();}}'''
    with TemporaryDirectory(prefix="polygraph-oss-") as temporary:
        root = Path(temporary)
        for language, filename, owner, source in [("java", "Handler.java", "Handler", java), ("python", "main.py", "main", python)]:
            p, store, ids = fixture(root / language, {filename: source})
            modes = {}
            for enabled in (False, True):
                block, report = analyze(p, store, {}, scenario({"path": "/value"}), smt=enabled)
                modes["with_z3" if enabled else "without_z3"] = {"edges": block["edges"], "paths": len(report["paths"]), "solver": report["solver"],
                    "impossible_method_in_output": any(edge["target"] == ids[owner + ".impossible"] for edge in block["edges"])}
            assert not modes["with_z3"]["impossible_method_in_output"] and modes["without_z3"]["impossible_method_in_output"]
            result["smt_ablation"][language] = {"source": source, "request": {"path": "/value"}, **modes}
        source = '''from fastapi import FastAPI as API
app=API()
@app.get("/value")
def value():
    try:
        raise ValueError()
    except ValueError, KeyError:
        return 12
'''
        source_root = root / "syntax"; source_root.mkdir()
        (source_root / "main.py").write_text(source)
        raw_error = None
        try:
            ast.parse(source)
        except SyntaxError as exc:
            raw_error = str(exc)
        skeleton = {"project": "syntax", "nodes": {"method:opaque": {"kind": "method", "name": "value", "file": "main.py", "line": 4}}, "edges": []}
        p = Project(source_root, skeleton)
        engine = Kernel(p); engine.scenario_id = "syntax"
        value = engine.request({"path": "/value"})
        assert value.body == 12 and value.status == 200
        result["libcst"] = {"host_ast_error": raw_error, "source": source, "endpoints": len(p.endpoints), "response": value, "diagnostics": p.diagnostics, "source_unchanged": (source_root / "main.py").read_text() == source}
        sql = '''CREATE TABLE "app"."stock" ("id" INTEGER,"description" TEXT,"price" NUMERIC);
INSERT INTO "app"."stock" ("description","price","id") VALUES ('O''Brien; -- text',0.10000000000000000001,3);'''
        p, _, _ = fixture(root / "sql", {}, tables=["stock"])
        path = root / "context.sql"; path.write_text(sql)
        store, _, warnings = load_context(path, p, "postgres")
        assert store.read("storage:stock")[0]["id"] == 3 and not warnings
        result["sqlglot_snapshot"] = {"source": sql, "dialect": "postgres", "tables": store.snapshot(), "warnings": warnings}
    result["passed"] = True
    output = VARIANT / "benchmark/oss-components.json"
    output.write_text(json.dumps(serial(result), ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": True, "ablation": {language: {mode: data[mode]["impossible_method_in_output"] for mode in ["without_z3", "with_z3"]} for language, data in result["smt_ablation"].items()}}))


if __name__ == "__main__":
    main()
