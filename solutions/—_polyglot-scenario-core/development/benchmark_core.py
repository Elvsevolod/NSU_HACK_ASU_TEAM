"""Reproducible full-CLI integration/performance and identifier metamorphisms."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

VARIANT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(VARIANT/"code"),str(VARIANT/"code/tests")]
from support import fixture, scenario


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, stdout, stderr):
    start=time.perf_counter()
    process=subprocess.run(command,capture_output=True,text=True)
    stdout.write_text(process.stdout);stderr.write_text(process.stderr)
    if process.returncode:
        raise RuntimeError(process.stderr)
    return time.perf_counter()-start


def main():
    base=VARIANT/"benchmark/core-integration"
    base.mkdir(parents=True,exist_ok=True)
    root=base/"fixture"
    if (root/"src").exists():
        # fixture() is a fresh writer; keep the fixed inputs instead of rewriting.
        project_data=json.loads((root/"skeleton.json").read_text())
        ids=json.loads((root/"ids.json").read_text())
    else:
        tree=ast.parse((VARIANT/"code/tests/test_adversarial.py").read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="test_symbolic_id_survives_wire_and_later_request")
        strings={n.targets[0].id:ast.literal_eval(n.value) for n in fn.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)}
        python=strings["python"].replace("return session.get(Item,id)","return lookup(session,id)")+"\ndef lookup(session,id):return session.get(Item,id)\n"
        project,_,ids=fixture(root,{"gateway/Gateway.java":strings["java"],"items/main.py":python},["item"],{"item":[]},modules={"gateway":"gateway","items":"items"})
        project_data=project.skeleton
        (root/"ids.json").write_text(json.dumps(ids,indent=2))
    requests=[{"method":"POST","path":"/make","module":"gateway"},
              {"path":"/load/{id}","path_params":{"id":{"$ref":"steps.1.body.id"}},"module":"gateway"}]
    scenario_data=scenario(*requests)
    (root/"scenario.json").write_text(json.dumps(scenario_data,indent=2))
    (root/"context.json").write_text('{"tables":{"item":[]}}\n')
    commands={};reports={};outputs={};walls={}
    common=[sys.executable,"-B",str(VARIANT/"code/offline_run.py"),"--source",str(root/"src"),"--skeleton",str(root/"skeleton.json"),"--context",str(root/"context.json"),"--scenarios",str(root/"scenario.json")]
    cache=base/"ir-cache.json"
    if cache.exists():cache.unlink()
    for mode in ["cold","warm"]:
        output=base/(mode+".json");report=base/(mode+"-report.json")
        command=common+["--output",str(output),"--report",str(report),"--cache",str(cache)]
        walls[mode]=run(command,base/(mode+".stdout.txt"),base/(mode+".stderr.txt"))
        commands[mode]=command;reports[mode]=json.loads(report.read_text());outputs[mode]=json.loads(output.read_text())
    assert outputs["cold"]==outputs["warm"]
    report=reports["cold"]["scenarios"]["arbitrary"]
    assert report["status"]=="complete-in-model",report
    path=report["paths"][0]
    assert path["steps"][0]["response"]["body"]==path["steps"][1]["response"]["body"]
    assert path["steps"][1]["response"]["body"]["quantity"]==6
    expected={("scenario:arbitrary","executes",ids[name]) for name in ["Gateway.make","Gateway.load","main.db","main.create","main.read","main.lookup"]}
    expected|={(ids["Gateway.make"],"remote",ids["main.create"]),(ids["Gateway.load"],"remote",ids["main.read"]),
               (ids["main.read"],"calls",ids["main.lookup"]),(ids["main.create"],"data","storage:item"),(ids["main.lookup"],"data","storage:item")}
    actual={tuple(e[k] for k in ["source","relation","target"]) for e in outputs["cold"]["scenarios"]["arbitrary"]["edges"]}
    assert actual==expected,(actual-expected,expected-actual)
    # Remap every skeleton ID and rename scenario. The analyzer must honor input IDs.
    mapping={key:"renamed-"+str(i) for i,key in enumerate(project_data["nodes"])}
    remapped=json.loads(json.dumps(project_data))
    remapped["nodes"]={mapping[key]:{k:mapping.get(v,v) if isinstance(v,str) and k in {"owner","method"} else v for k,v in meta.items()} for key,meta in remapped["nodes"].items()}
    (root/"renamed-skeleton.json").write_text(json.dumps(remapped))
    renamed=scenario(*requests,identifier="no-numeric-or-domain-code")
    (root/"renamed-scenario.json").write_text(json.dumps(renamed))
    command=common.copy()
    command[command.index("--skeleton")+1]=str(root/"renamed-skeleton.json")
    command[command.index("--scenarios")+1]=str(root/"renamed-scenario.json")
    command += ["--output",str(base/"renamed.json"),"--report",str(base/"renamed-report.json")]
    run(command,base/"renamed.stdout.txt",base/"renamed.stderr.txt")
    inverse={v:k for k,v in mapping.items()}
    changed=json.loads((base/"renamed.json").read_text())["scenarios"][renamed["id"]]["edges"]
    normalized={("scenario:arbitrary" if e["relation"]=="executes" else inverse[e["source"]],e["relation"],inverse[e["target"]]) for e in changed}
    assert normalized==actual
    summary={"passed":True,"fixture":"Synthetic mixed-language integration, not an independent public project", "edge_counts":{rel:sum(e[1]==rel for e in actual) for rel in ["executes","calls","remote","data"]},
             "all_four_nonempty":True,"exact_manual_graph_match":True,"symbolic_id_and_state_preserved":True,"cold_warm_graph_equal":True,"all_input_ids_remapped":True,
             "commands":commands,"wall_seconds":walls,"measurements":{mode:{k:r[k] for k in ["preparation_seconds","analysis_seconds","elapsed_seconds","peak_rss_bytes","IR_cache_hits","lowered_methods","submission_sha256"]} for mode,r in reports.items()}}
    (base/"verification.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(summary,ensure_ascii=False))


if __name__=="__main__":main()
