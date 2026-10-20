"""Replay the packaged CLI outside this repository with a legal sample input."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

VARIANT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(VARIANT/'code'),str(VARIANT/'code/tests')]
from builders import build

parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
work=Path(tempfile.mkdtemp(prefix='nsu-sample-cli-',dir='/private/tmp'))
sample=work/'sample'
project,_,ids=build(sample,{'Api.java':'''class BookController {@Autowired BookStore store;
  @GetMapping("/books") List<Book> list(){return store.findAll();}}
  @Entity @Table(name="books") class Book {@Id String id;String name;}
  interface BookStore extends JpaRepository<Book,String>{List<Book> findAll();}'''},rows={'books':[{'id':'one','name':'Atlas'}]})
scenarios=sample/'scenarios.json'
scenarios.write_text(json.dumps({'id':'sample-folder-check','project':'fixture','steps':[{'n':1,'action':'List all books'}]})+'\n')
code=work/'standalone-code'
shutil.copytree(VARIANT/'code',code,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','*.pyc'))
command=[sys.executable,'-B',str(code/'offline_run.py'),'--source',str(sample),'--skeleton',str(sample/'skeleton.json'),
         '--context',str(sample/'initial.sql'),'--scenarios',str(scenarios),
         '--output',str(work/'prediction.json'),'--report',str(work/'report.json')]
completed=subprocess.run(command,cwd=work,capture_output=True,text=True)
(work/'stdout.txt').write_text(completed.stdout)
(work/'stderr.txt').write_text(completed.stderr)
if completed.returncode:raise RuntimeError(completed.stderr)
prediction=json.loads((work/'prediction.json').read_text())
audit=json.loads((work/'report-offline-audit.json').read_text())
expected={(ids['BookController.list'],'data','res:table:service.books'),
          ('scenario:sample-folder-check','executes',ids['BookController.list'])}
actual={(e['source'],e['relation'],e['target']) for e in prediction['scenarios']['sample-folder-check']['edges']}
report={'passed':actual==expected and not any(audit[key] for key in ('blocked_network','blocked_processes','blocked_reference_reads')),
        'standalone_work_directory':str(work),'code_and_inputs_outside_repository':True,
        'input_folder_name':'sample','audit':audit,'expected_edges':sorted(expected),'actual_edges':sorted(actual),
        'application_started':False}
args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
assert report['passed']
