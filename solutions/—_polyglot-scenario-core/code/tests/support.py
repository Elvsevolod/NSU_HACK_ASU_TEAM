"""Test-only skeleton writer. It does not infer routes, calls or expected edges."""
import ast
import json
from pathlib import Path
import re

from tree_sitter import Language, Parser
import tree_sitter_java

from polygraph.project import Project
from polygraph.state import Store


def fixture(tmp_path, sources, tables=(), rows=None, modules=None, profiles=(), cache=None,configuration=None):
    root = tmp_path / "src"
    root.mkdir(parents=True)
    nodes = {}
    modules = modules or {"app": ""}
    for module, path in modules.items():
        nodes["deployment:" + module] = {"kind": "module", "name": module, "path": path, "deployment_units": [module]}
    ids, counter = {}, 0
    parser = Parser(Language(tree_sitter_java.language()))
    def walk(node):
        yield node
        for child in node.named_children:
            yield from walk(child)
    for file, source in sources.items():
        path = root / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
        module = next((m for m, prefix in modules.items() if not prefix or file.startswith(prefix + "/")), "")
        if file.endswith(".java"):
            tree = parser.parse(source.encode())
            assert not tree.root_node.has_error, (file, tree.root_node)
            package = re.search(r"\bpackage\s+([\w.]+)", source)
            package = package[1] + "." if package else ""
            for decl in walk(tree.root_node):
                if decl.type not in {"class_declaration", "interface_declaration", "enum_declaration"}:
                    continue
                owner = decl.child_by_field_name("name").text.decode()
                tid = "owner:" + file + ":" + owner
                nodes[tid] = {"kind": "type", "fqn": package + owner, "file": file, "module": module}
                body = decl.child_by_field_name("body")
                members=[member for child in body.named_children for member in (child.named_children if child.type=='enum_body_declarations' else [child])] if body else []
                for node in members:
                    if node.type not in {"method_declaration", "constructor_declaration"}:
                        continue
                    name = "<init>" if node.type == "constructor_declaration" else node.child_by_field_name("name").text.decode()
                    counter += 1
                    mid = "opaque-method-" + str(counter)
                    params = [n.child_by_field_name("type").text.decode() for n in node.child_by_field_name("parameters").named_children if n.type == "formal_parameter"]
                    nodes[mid] = {"kind": "method", "name": name, "owner": tid, "module": module, "file": file,
                                  "line": node.start_point.row + 1, "params_as_written": params}
                    ids[owner + "." + name] = mid
        elif file.endswith(".py"):
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    counter += 1
                    mid = "opaque-method-" + str(counter)
                    nodes[mid] = {"kind": "method", "name": node.name, "file": file, "module": module, "line": node.lineno}
                    ids[Path(file).stem + "." + node.name] = mid
    for table in tables:
        nodes["storage:" + table] = {"kind": "data_resource", "name": table, "schema": "app"}
    skeleton = {"project": "independent-fixture", "nodes": nodes, "edges": [], "context": {}}
    path = tmp_path / "skeleton.json"
    path.write_text(json.dumps(skeleton))
    project = Project(root, path, cache, profiles,source_configuration=configuration)
    store = Store({"storage:" + k: tuple(v) for k, v in (rows or {}).items()})
    return project, store, ids


def scenario(*requests, identifier="arbitrary"):
    return {"project": "independent-fixture", "id": identifier, "steps": [{"n": i, "action": "Explicit source-derived request", "request": request} for i, request in enumerate(requests, 1)]}


def edge_set(block, relation=None):
    return {(e["source"], e["relation"], e["target"]) for e in block["edges"] if relation is None or e["relation"] == relation}
