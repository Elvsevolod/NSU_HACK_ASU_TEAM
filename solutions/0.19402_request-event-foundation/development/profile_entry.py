"""Optional development stack sampling; runs only the Python analyzer."""
import faulthandler
from pathlib import Path
import runpy
import sys

script=Path(sys.argv[1]).resolve()
sys.argv=sys.argv[1:]
sys.path.insert(0,str(script.parent))
faulthandler.dump_traceback_later(30,repeat=True)
try:runpy.run_path(str(script),run_name='__main__')
finally:faulthandler.cancel_dump_traceback_later()
