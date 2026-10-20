"""Read-only aggregate instrumentation; no business values or scenario names in counts."""
import collections,json,runpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CODE=ROOT/'solutions/—_http-json-collections/code'
sys.path.insert(0,str(CODE))
import analyzer.engine as engine
from analyzer.java_collections import JavaMap
from analyzer.map_keys import key_spec
from analyzer.state import U
original=engine.library
counts=collections.Counter()
allowed={'int','long','byte','short','char','boolean','String','Integer','Long','Boolean','Character','java.lang.String',None,'unresolved'}
def observed(name,obj,args,receiver,now,**kwargs):
 if isinstance(obj,JavaMap) and args and name in ('get','put','containsKey','remove','getOrDefault'):
  value,hint=args[0],kwargs.get('key_type')
  carrier='unknown' if value is U else type(value).__name__ if type(value) in (str,int,bool,float,list,dict,type(None)) else 'owned-object'
  counts[(name,carrier,hint if hint in allowed else 'other-declared','supported' if key_spec(value,hint) is not None else 'unsupported')]+=1
 return original(name,obj,args,receiver,now,**kwargs)
engine.library=observed
try:
 runpy.run_path(str(CODE/'offline_run.py'),run_name='__main__')
finally:
 output=Path(__file__).with_name('map-key-producer-counts.json')
 output.write_text(json.dumps([{'operation':op,'carrier':carrier,'source_type':hint,'support':support,'calls':count} for (op,carrier,hint,support),count in sorted(counts.items(),key=str)],indent=2)+'\n')
