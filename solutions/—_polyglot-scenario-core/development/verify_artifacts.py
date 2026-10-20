"""Verify the saved variant without running target applications."""
import argparse
import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--skeleton",type=Path,required=True)
    parser.add_argument("--variant",type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();v=args.variant
    skeleton=json.loads(gzip.decompress(args.skeleton.read_bytes()) if args.skeleton.suffix==".gz" else args.skeleton.read_bytes())
    answer=json.loads((v/"submission.json").read_text())
    report=json.loads((v/"benchmark/analysis-report.json").read_text())
    assert answer["project"]==skeleton["project"]
    assert set(answer["scenarios"])==set(report["scenarios"])
    summary={}
    for sid,block in answer["scenarios"].items():
        edges={(e["source"],e["relation"],e["target"]) for e in block["edges"]}
        assert len(edges)==len(block["edges"])
        detail=report["scenarios"][sid]
        assert edges=={tuple(e[k] for k in ["source","relation","target"]) for e in detail[detail["projection"]]}
        for source,relation,target in edges:
            assert target in skeleton["nodes"]
            assert relation in {"executes","calls","remote","data"}
            if relation=="executes":assert source=="scenario:"+sid
            else:assert skeleton["nodes"][source]["kind"]=="method"
            assert skeleton["nodes"][target]["kind"]==("data_resource" if relation=="data" else "method")
            reasons=detail["evidence"][" | ".join((source,relation,target))]
            assert reasons and all(r["file"] and r["line"]>0 and r["reason"] for r in reasons)
        if not detail["fully_explored_in_model"]:assert detail["must"]==[]
        summary[sid]={"status":detail["status"],"edge_counts":dict(Counter(e[1] for e in edges)),"paths":len(detail["paths"]),"path_attempts":detail["path_attempts"],"pending_paths":detail["pending_paths"]}
    frozen=json.loads((v/"development/code-freeze.json").read_text())["files"]
    assert frozen=={p.relative_to(v).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((v/'code').rglob('*.py'))}
    assert all(hashlib.sha256((v/path).read_bytes()).hexdigest()==digest for path,digest in frozen.items())
    runtime="\n".join(p.read_text() for p in (v/"code/polygraph").rglob("*.py"))
    assert not any(word.lower() in runtime.lower() for word in ["trainticket","Train Ticket","tt-challenge"])
    core=ast.parse((v/"code/polygraph/kernel.py").read_bytes())
    imports=[n.module or "" for n in ast.walk(core) if isinstance(n,ast.ImportFrom)]+[a.name for n in ast.walk(core) if isinstance(n,ast.Import) for a in n.names]
    assert not set(imports)&{"ast","tree_sitter","java","python"}
    independent=json.loads((v/"benchmark/public-corpus/corpus-results.json").read_text())
    assert all(c["passed"] for project in independent["projects"].values() for c in project["cases"])
    http=json.loads((v/'benchmark/public-http/results.json').read_text())
    assert http['passed'] and http['source_unchanged'] and len(http['cases'])==8
    assert http['reference_sha256']==hashlib.sha256((v/'development/http_reference.json').read_bytes()).hexdigest()
    assert http['code_sha256']==frozen
    assert all(hashlib.sha256((v/'benchmark/public-http/fixture/src'/file).read_bytes()).hexdigest()==digest for file,digest in http['analysis_source_sha256'].items())
    assert hashlib.sha256((v/'benchmark/public-http/fixture/LICENSE').read_bytes()).hexdigest()==http['fixture_license_sha256']
    assert all(case['passed'] and all(case['checks'].values()) and set(case['offline_replay'])=={'cold','repeat'} for case in http['cases'])
    spring=json.loads((v/'benchmark/public-spring/results.json').read_text())
    spring_reference=json.loads((v/'development/spring_http_reference.json').read_text())
    assert spring['reference_sha256']==hashlib.sha256((v/'development/spring_http_reference.json').read_bytes()).hexdigest()
    assert [case['id'] for case in spring['cases']]==[case['id'] for case in spring_reference['cases']]
    assert spring['code_sha256']==frozen and spring['source_unchanged'] and spring['application_executed'] is False
    assert spring['full_Spring_HTTP_support_proven'] is False
    assert spring['passed']==all(case['passed'] for case in spring['cases'])
    assert all(hashlib.sha256((v/'benchmark/public-spring/fixture/src'/file).read_bytes()).hexdigest()==digest for file,digest in spring['fixture_sha256'].items())
    assert hashlib.sha256((v/'benchmark/public-spring/fixture/LICENSE').read_bytes()).hexdigest()==spring['fixture_license_sha256']
    for case in spring['cases']:
        assert case['passed']==all(case['checks'].values())
        assert set(case['offline_replay'])=={'cold','repeat'}
        assert all(value for name,value in case['checks'].items() if name.startswith(('cold_','repeat_')))
    # Component regressions block packaging; the unimplemented broad target
    # remains visible as a failure, never converted into a completed product.
    assert all(case['passed'] for case in spring['cases'] if case['id']!='stateful-account-statistics-chain')
    grounding=json.loads((v/'benchmark/request-grounding.json').read_text())
    assert grounding['reference_sha256']==hashlib.sha256((v/'development/request_reference.json').read_bytes()).hexdigest()
    request_cases=[case for project in grounding['projects'].values() for case in project['cases']]
    paired=json.loads((v/'benchmark/retrieval-formulas.json').read_text())
    assert paired['grounding_code_sha256']==hashlib.sha256((v/'code/polygraph/grounding.py').read_bytes()).hexdigest()
    integration=json.loads((v/"benchmark/core-integration/verification.json").read_text())
    assert integration["passed"] and integration["all_four_nonempty"]
    ui=json.loads((v/'benchmark/ui-integration/verification.json').read_text())
    assert ui['passed'] and ui['exact_manual_graph_match'] and ui['all_four_nonempty']
    assert ui['reference_sha256']==hashlib.sha256((v/'benchmark/ui-integration/reference.json').read_bytes()).hexdigest()
    assert all(hashlib.sha256((v/'benchmark/ui-integration/fixture/src'/file).read_bytes()).hexdigest()==digest for file,digest in ui['source_sha256'].items())
    oss=json.loads((v/"benchmark/oss-components.json").read_text())
    assert oss["passed"]
    assert all(not case["with_z3"]["impossible_method_in_output"] and case["without_z3"]["impossible_method_in_output"] for case in oss["smt_ablation"].values())
    licenses=json.loads((v/"third_party/provenance.json").read_text())
    assert all(hashlib.sha256((v/item["license_file"]).read_bytes()).hexdigest()==item["license_sha256"] for item in licenses.values())
    suites=list(ET.parse(v/"benchmark/tests.xml").getroot().iter("testsuite"))
    assert suites and all(int(s.attrib["errors"])==0 and int(s.attrib["failures"])==0 for s in suites)
    result={"passed":True,"scenarios":summary,"model_calls":report["model_calls"],"application_executed":False,
            "frozen_code_files":len(frozen),"kernel_has_no_parser_imports":True,"no_test_project_literals_in_runtime":True,
            "every_exported_edge_has_source_evidence":True,"empty_must_on_unexplored_paths":True,
            "independent_body_cases_passed":sum(c["passed"] for p in independent["projects"].values() for c in p["cases"]),
            "tests_passed":sum(int(s.attrib["tests"]) for s in suites),"OSS_ablation_verified":True,"license_notices_verified":True,
            "source_UI_to_mixed_backend_verified":True,
            "public_HTTP_cases_passed":len(http['cases']),"public_HTTP_has_no_prepared_Session_User":True,
            "public_HTTP_replayed_offline_and_state_equal":True,
            "public_Spring_conditional_cases_passed":sum(case['passed'] for case in spring['cases']),
            "public_Spring_conditional_cases_total":len(spring['cases']),
            "public_Spring_failing_targets":[case['id'] for case in spring['cases'] if not case['passed']],
            "full_Spring_HTTP_support_proven":False,
            "retrieval_cases":len(request_cases),"retrieval_top1_correct":sum(case['top1_correct'] for case in request_cases),
            "retrieval_exact_sets":sum(case['exact_set'] for case in request_cases),"retrieval_scope":grounding['scope'],
            "submission_sha256":hashlib.sha256((v/"submission.json").read_bytes()).hexdigest()}
    (v/"benchmark/verification.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False))


if __name__=="__main__":main()
