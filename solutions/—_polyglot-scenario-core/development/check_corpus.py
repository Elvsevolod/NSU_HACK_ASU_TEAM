"""Independent source declaration skeleton and fixed manual body oracle checker.

Usage: python -B development/check_corpus.py --java ROOT --python BACKEND --output DIR
This is development tooling; it neither imports nor runs the target applications.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from tree_sitter import Language, Parser
import tree_sitter_java
import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider
from polygraph.kernel import Kernel
from polygraph.project import Project
from polygraph.state import State, Store
from polygraph.values import Object, Raised, serial, wire


def declarations(root, language, tables):
    """Only identities/locations, no route/edge inference and no product frontend."""
    nodes, names, sources, parse_errors = {}, {}, {}, []
    parser = Parser(Language(tree_sitter_java.language()))
    def walk(node):
        yield node
        for child in node.named_children:
            yield from walk(child)
    files = sorted(root.rglob("*.java" if language == "java" else "*.py"))
    for path in files:
        file = path.relative_to(root).as_posix()
        if set(path.relative_to(root).parts) & {"tests", "test", ".venv", "__pycache__"}:
            continue
        if language == "java" and "/src/main/java/" not in "/" + file:
            continue
        source = path.read_bytes()
        sources[file] = hashlib.sha256(source).hexdigest()
        module = file.split("/")[0] if language == "java" else "backend"
        nodes["deployment:" + module] = {"kind":"module","name":module,"path":module if language=="java" else "","deployment_units":[module]}
        if language == "java":
            tree = parser.parse(source)
            package = re.search(rb"\bpackage\s+([\w.]+)",source)
            package = package[1].decode()+"." if package else ""
            for owner in walk(tree.root_node):
                if owner.type not in {"class_declaration","interface_declaration","enum_declaration"}:
                    continue
                short=owner.child_by_field_name("name").text.decode()
                tid="owner:"+file+":"+short
                nodes[tid]={"kind":"type","fqn":package+short,"file":file,"module":module}
                body=owner.child_by_field_name("body")
                members=[member for child in body.named_children for member in (child.named_children if child.type=='enum_body_declarations' else [child])] if body else []
                for method in members:
                    if method.type not in {"method_declaration","constructor_declaration"}:continue
                    name="<init>" if method.type=="constructor_declaration" else method.child_by_field_name("name").text.decode()
                    params=[p.child_by_field_name("type").text.decode() for p in method.child_by_field_name("parameters").named_children if p.type=="formal_parameter"]
                    label=short+"."+name
                    mid="method:"+module+":"+package+short+"#"+name+"("+",".join(params)+")"
                    nodes[mid]={"kind":"method","name":name,"owner":tid,"module":module,"file":file,"line":method.start_point.row+1,"params_as_written":params}
                    names[label]=mid
        else:
            try:
                wrapper=MetadataWrapper(cst.parse_module(source),unsafe_skip_copy=True)
                positions=wrapper.resolve(PositionProvider)
            except cst.ParserSyntaxError as exc:
                parse_errors.append({"file":file,"error":str(exc)})
                continue
            for method,position in positions.items():
                if isinstance(method,cst.FunctionDef):
                    name=method.name.value
                    mid="method:backend:"+file+"#"+name+":"+str(position.start.line)
                    nodes[mid]={"kind":"method","name":name,"module":module,"file":file,"line":position.start.line}
                    if file.endswith("api/routes/items.py"):
                        names[name]=mid
    for name in tables:
        nodes["resource:"+name]={"kind":"data_resource","name":name,"schema":"context"}
    return {"project":"public-"+language,"nodes":nodes,"edges":[]},names,sources,parse_errors


def metrics(expected, actual):
    result={}
    for relation in ["executes","calls","remote","data"]:
        gold={e for e in expected if e[1]==relation};pred={e for e in actual if e[1]==relation}
        result[relation]={"expected":len(gold),"predicted":len(pred),"intersection":len(gold&pred),
                          "iou":len(gold&pred)/len(gold|pred) if gold|pred else 1.,
                          "precision":len(gold&pred)/len(pred) if pred else None,
                          "recall":len(gold&pred)/len(gold) if gold else None,
                          "missing":[list(e) for e in sorted(gold-pred)],"extra":[list(e) for e in sorted(pred-gold)],"empty_both":not(gold|pred)}
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--java",type=Path,required=True);parser.add_argument("--python",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    reference_path=Path(__file__).with_name("corpus_reference.json")
    reference=json.loads(reference_path.read_text())
    report={"reference_sha256":hashlib.sha256(reference_path.read_bytes()).hexdigest(),"application_executed":False,"scope":reference["scope"],"projects":{}}
    for language,root,tables in [("java",args.java,["accounts","datapoints"]),("python",args.python,["user","item"])]:
        skeleton,names,sources,parse_errors=declarations(root,language,tables)
        (args.output/(language+"-skeleton.json")).write_text(json.dumps(skeleton,indent=2))
        started=time.perf_counter();project=Project(root,skeleton);preparation=time.perf_counter()-started
        project_report={"source_files":len(sources),"source_sha256":sources,"parse_errors":parse_errors,"preparation_seconds":preparation,"cases":[],"project_diagnostics":project.diagnostics}
        report["projects"][language]=project_report
        for case in reference[language]["cases"]:
            item_id="00000000-0000-4000-8000-000000000001"
            user_id="10000000-0000-4000-8000-000000000001"
            owner_id=user_id if case.get("owner","u1")=="u1" else "20000000-0000-4000-8000-000000000001"
            state=State(Store({"resource:accounts":({"name":"alex","note":"Before","lastSeen":None,"incomes":[],"expenses":[],"saving":None},)})) if language=="java" else State(Store({"resource:item":() if case.get("empty") else ({"id":item_id,"title":"Before","description":"keep","owner_id":owner_id,"created_at":None,"owner":None},),"resource:user":()}))
            engine=Kernel(project,state);engine.scenario_id=case["id"]
            result,status,error=None,200,None;started=time.perf_counter()
            try:
                if language=="java":
                    key=project.method_by_id[names[case["entry"]]]
                    method=project.methods[key];receiver=engine.create(method.owner,span=method.span,bean=True)
                    result=engine.execute_method(key,(case["account_name"],),receiver=receiver)
                else:
                    session=engine.state.new("sqlmodel.Session")
                    user=engine.create("User",kwargs={"id":user_id,"is_superuser":False,"is_active":True})
                    # The oracle supplies already-constructed framework inputs.
                    # Their construction belongs to preparation, outside this trace.
                    engine.edges.clear();engine.events.clear();engine.diagnostics.clear()
                    for operation in case["sequence"]:
                        key=project.method_by_id[names[operation]]
                        values={"session":session,"current_user":user,"id":item_id}
                        if operation=="update_item":values["item_in"]=engine.create("ItemUpdate",kwargs={"title":"After"})
                        result=engine.execute_method(key,kwargs=values)
            except Raised as exc:
                error=exc.typ;status=exc.value.fields.get("status_code",500) if isinstance(exc.value,Object) else 500
            except Exception as exc:
                error=type(exc).__name__+": "+str(exc);status=500
            expected={("scenario:"+case["id"],"executes",names[name]) for name in case["methods"]}
            expected|={(names[a],"calls",names[b]) for a,b in case.get("calls",[])}
            expected|={(names[a],"data","resource:"+table) for a,table in case.get("data",[])}
            comparison=metrics(expected,set(engine.edges))
            state_output=engine.state.store.snapshot();returned=wire(result)
            checks={"edges":all(not m["missing"] and not m["extra"] for m in comparison.values())}
            if "exception" in case:checks["exception"]=error==case["exception"]
            elif language=="java":checks["result"]=isinstance(returned,dict) and returned.get("note")==case["expected_note"] and error is None
            if "status" in case:checks["status"]=status==case["status"]
            if "expected_title" in case:checks["state"]=state_output["resource:item"][0]["title"]==case["expected_title"] and state_output["resource:item"][0]["description"]==case["expected_description"]
            if case.get("expected_empty"):checks["empty"]=state_output["resource:item"]==[]
            project_report["cases"].append({"id":case["id"],"passed":all(checks.values()),"checks":checks,"relations":comparison,"result":returned,"status":status,"exception":error,"state":state_output,"diagnostics":engine.diagnostics,"analysis_seconds":time.perf_counter()-started})
    (args.output/"corpus-results.json").write_text(json.dumps(serial(report),ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({lang:{"cases":len(r["cases"]),"passed":sum(c["passed"] for c in r["cases"]),"source_files":r["source_files"]} for lang,r in report["projects"].items()}))


if __name__=="__main__":main()
