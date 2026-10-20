"""Approved runtime bootstrap followed by audited offline source execution."""
import json,os,platform,resource,runpy,sys,time
from pathlib import Path
V=Path(__file__).resolve().parents[1];sys.path.insert(0,str(V/'code'))
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
import torch
from sentence_transformers import SentenceTransformer
from offline_run import audit,audit_stats,declared_inputs
environment=platform.platform()
declared_inputs.append(((V/'validation_inputs/shopping-cart').resolve(),True))
sys.addaudithook(audit)
start=time.perf_counter();sys.argv[0]=str(V/'checks/run_cart_profile.py')
try:runpy.run_path(str(V/'checks/run_cart_profile.py'),run_name='__main__')
finally:
    path=Path(sys.argv[sys.argv.index('--output')+1]);path.mkdir(parents=True,exist_ok=True)
    (path/'model-cost.json').write_text(json.dumps({'wall_seconds_after_runtime_import':time.perf_counter()-start,
      'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'audit':audit_stats,'environment':environment,
      'mps_driver_allocated_bytes_at_end':torch.mps.driver_allocated_memory() if torch.backends.mps.is_available() else None},indent=2)+'\n')
