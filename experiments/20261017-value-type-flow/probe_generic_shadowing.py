import sys,tempfile,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];code=root/'solutions/—_value-type-flow/code'
sys.path[:0]=[str(code),str(code/'tests')]
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build
cases={
'class_type_parameter':'''import java.util.*;class Box<String>{String value;String getValue(){return value;}}
 class Api{Object entry(){Box box=new Box();box.value='x';Map map=new HashMap();map.put(box.getValue(),"found");return map.get("x");}}''',
'method_type_parameter':'''import java.util.*;class Api{<String>String identity(String value){return value;}
 Object entry(){Map map=new HashMap();map.put(identity('x'),"found");return map.get("x");}}'''}
results={}
for name,source in cases.items():
 p,db,ids=build(Path(tempfile.mkdtemp(prefix='nsu-generics-')),{'Api.java':source});e=Engine(p,ScenarioState(db));value=e.run(ids['Api.entry'],{})
 results[name]={'unknown':value is U,'value':None if value is U else value,'warnings':sorted(e.warnings)}
Path(__file__).with_name('generic-shadowing-baseline.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
