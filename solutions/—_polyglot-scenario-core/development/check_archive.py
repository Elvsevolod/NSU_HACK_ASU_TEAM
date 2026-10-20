"""Test the packaged code in an isolated directory and reproduce a saved graph."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

VARIANT = Path(__file__).resolve().parents[1]


def main():
    archive = VARIANT / "solution.zip"
    with TemporaryDirectory(prefix="polygraph-archive-") as temporary:
        root = Path(temporary)
        with ZipFile(archive) as source:
            assert all(not name.startswith("/") and ".." not in Path(name).parts for name in source.namelist())
            source.extractall(root)
        frozen = json.loads((root / "development/code-freeze.json").read_text())["files"]
        assert all(hashlib.sha256((root / name).read_bytes()).hexdigest() == digest for name, digest in frozen.items())
        env = {**os.environ, "PYTHONPATH": str(root / "code"), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "29"}
        tests = subprocess.run([sys.executable, "-B", "-m", "pytest", "code/tests", "-q", "-p", "no:cacheprovider"], cwd=root, env=env, capture_output=True, text=True)
        (VARIANT / "benchmark/standalone-tests.stdout.txt").write_text(tests.stdout)
        (VARIANT / "benchmark/standalone-tests.stderr.txt").write_text(tests.stderr)
        assert tests.returncode == 0, tests.stdout + tests.stderr
        fixture = root / "benchmark/core-integration/fixture"
        args = [sys.executable, "-B", "code/offline_run.py", "--source", str(fixture / "src"), "--skeleton", str(fixture / "skeleton.json"),
                "--context", str(fixture / "context.json"), "--scenarios", str(fixture / "scenario.json"), "--output", str(root / "new.json"), "--report", str(root / "report.json")]
        result = subprocess.run(args, cwd=root, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert json.loads((root / "new.json").read_text()) == json.loads((root / "benchmark/core-integration/cold.json").read_text())
        ui_fixture=root/'benchmark/ui-integration/fixture'
        ui_args=[sys.executable,'-B','code/offline_run.py','--source',str(ui_fixture/'src'),'--skeleton',str(ui_fixture/'skeleton.json'),
                 '--context',str(ui_fixture/'context.json'),'--scenarios',str(ui_fixture/'scenario.json'),'--output',str(root/'new-ui.json'),'--report',str(root/'ui-report.json')]
        ui_result=subprocess.run(ui_args,cwd=root,env=env,capture_output=True,text=True)
        assert ui_result.returncode==0,ui_result.stderr
        assert json.loads((root/'new-ui.json').read_text())==json.loads((root/'benchmark/ui-integration/cold.json').read_text())
        http_base=root/'benchmark/public-http';http=json.loads((http_base/'results.json').read_text())
        assert all(hashlib.sha256((http_base/'fixture/src'/file).read_bytes()).hexdigest()==digest for file,digest in http['analysis_source_sha256'].items())
        for case in http['cases']:
            label=case['id'];output=root/(label+'.json');diagnostics=root/(label+'-report.json')
            command=[sys.executable,'-B','code/offline_run.py','--source',str(http_base/'fixture/src'),'--skeleton',str(http_base/'skeleton.json'),
                     '--context',str(http_base/(label+'-context.json')),'--scenarios',str(http_base/(label+'-scenario.json')),
                     '--sql-dialect','postgres','--path-limit','32','--output',str(output),'--report',str(diagnostics)]
            process=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True)
            assert process.returncode==0,process.stderr
            assert json.loads(output.read_text())==json.loads((http_base/(label+'-cold.json')).read_text())
            actual=json.loads(diagnostics.read_text())['scenarios'][label]['paths']
            saved=case['detail']['paths']
            assert [{k:p[k] for k in ['steps','state','coverage']} for p in actual]==[{k:p[k] for k in ['steps','state','coverage']} for p in saved]
        spring_base=root/'benchmark/public-spring';spring=json.loads((spring_base/'results.json').read_text())
        assert all(hashlib.sha256((spring_base/'fixture/src'/file).read_bytes()).hexdigest()==digest for file,digest in spring['fixture_sha256'].items())
        for case in spring['cases']:
            label=case['id'];output=root/(label+'.json');diagnostics=root/(label+'-report.json')
            command=[sys.executable,'-B','code/offline_run.py','--source',str(spring_base/'fixture/src'),'--skeleton',str(spring_base/'skeleton.json'),
                     '--context',str(spring_base/(label+'-context.json')),'--scenarios',str(spring_base/(label+'-scenario.json')),
                     '--path-limit','16','--output',str(output),'--report',str(diagnostics)]
            process=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True)
            assert process.returncode==0,process.stderr
            assert json.loads(output.read_text())==json.loads((spring_base/(label+'-cold.json')).read_text())
            actual=json.loads(diagnostics.read_text())['scenarios'][label]['paths'];saved=case['detail']['paths']
            assert [{k:p[k] for k in ['steps','state','coverage']} for p in actual]==[{k:p[k] for k in ['steps','state','coverage']} for p in saved]
        report = {"passed": True, "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "code_hashes_match_freeze": True,
                  "tests_stdout": tests.stdout, "test_returncode": tests.returncode, "standalone_CLI_returncode": result.returncode,
                  "standalone_graph_matches_saved": True, "application_executed": False}
        report['standalone_UI_graph_matches_saved']=True
        report['standalone_public_HTTP_graphs_steps_state_equal']=len(http['cases'])
        report['standalone_public_Spring_graphs_steps_state_equal']=len(spring['cases'])
        report['public_Spring_failed_targets_reproduced']=[case['id'] for case in spring['cases'] if not case['passed']]
        report['full_Spring_HTTP_support_proven']=False
        (VARIANT / "benchmark/archive-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({key: report[key] for key in ["passed", "archive_sha256", "standalone_graph_matches_saved"]}))
        print(tests.stdout)


if __name__ == "__main__":
    main()
