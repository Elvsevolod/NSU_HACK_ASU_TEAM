"""Current source facts vs a pinned independent JavaParser process."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

VARIANT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(VARIANT/'code'))
from analyzer.project import Project

parser=argparse.ArgumentParser();parser.add_argument('--fixtures',type=Path,required=True)
parser.add_argument('--jar',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
java=Path('/Library/Java/JavaVirtualMachines/amazon-corretto-11.jdk/Contents/Home/bin')
compiled=args.output/'classes';compiled.mkdir()
compile_command=[str(java/'javac'),'-cp',str(args.jar),'-d',str(compiled),str(VARIANT/'checks/ExtractorProbe.java')]
compilation=subprocess.run(compile_command,text=True,capture_output=True)
(args.output/'compile.stderr.txt').write_text(compilation.stderr)
compilation.check_returncode()
sources=[];current=set();started=time.perf_counter()
for fixture in sorted(args.fixtures.iterdir()):
    if not (fixture/'skeleton.json').exists():continue
    project=Project(fixture/'skeleton.json',fixture)
    sources.extend(str(path.resolve()) for path in sorted(fixture.rglob('*.java')))
    from analyzer.project import text,walk
    for file,tree in project.trees.items():
        for node in walk(tree.root_node):
            if node.type not in ('method_declaration','constructor_declaration'):continue
            owner=node.parent
            while owner is not None and owner.type not in ('class_declaration','interface_declaration','enum_declaration','record_declaration'):
                owner=owner.parent
            if owner is None:continue
            pars=node.child_by_field_name('parameters')
            types=[text(p.child_by_field_name('type')).replace(' ','') for p in pars.named_children if p.type=='formal_parameter']
            name='<init>' if node.type=='constructor_declaration' else text(node.child_by_field_name('name'))
            current.add((str((fixture/file).resolve()),text(owner.child_by_field_name('name')),name,str(node.start_point.row+1),','.join(types)))
current_seconds=time.perf_counter()-started
command=[str(java/'java'),'-cp',str(compiled)+':'+str(args.jar),'ExtractorProbe',*sources]
started=time.perf_counter();process=subprocess.run(command,text=True,capture_output=True);elapsed=time.perf_counter()-started
(args.output/'javaparser.tsv').write_text(process.stdout);(args.output/'parse.stderr.txt').write_text(process.stderr)
process.check_returncode();alternative={tuple(line.split('\t')) for line in process.stdout.splitlines()}
report={'version':'javaparser-core/3.28.2','jar_sha256':hashlib.sha256(args.jar.read_bytes()).hexdigest(),
    'sources':len(sources),'current_methods':len(current),'javaparser_methods':len(alternative),
    'same_method_facts':current==alternative,'missing':sorted(current-alternative),'extra':sorted(alternative-current),
    'current_full_project_prepare_seconds':current_seconds,'javaparser_parse_process_seconds':elapsed,
    'measurement_scope':'Current includes project metadata preparation; JavaParser is syntax extraction plus process startup; not a pure parser speed ranking',
    'children_peak_rss_bytes':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
    'parse_errors':bool(process.stderr),'target_applications_started':False,
    'decision':'Keep as a development comparator. No measured reduction in final scenario errors; not a production replacement.',
    'limits':['Core syntax pilot only; Symbol Solver/classpath not evaluated','No Spring binding, ORM or scenario execution supplied by extractor']}
(args.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
