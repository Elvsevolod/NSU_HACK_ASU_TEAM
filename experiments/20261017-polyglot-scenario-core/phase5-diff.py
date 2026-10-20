from pathlib import Path
from zipfile import ZipFile
import difflib,json
root=Path('/Users/vsevolod/Desktop/NSU_HACK_ASU_TEAM');v=root/'solutions/—_polyglot-scenario-core';exp=root/'experiments/20261017-polyglot-scenario-core';changes={};parts=[]
with ZipFile(exp/'phase5-baseline.zip') as archive:
 for path in sorted((v/'code').rglob('*.py')):
  rel=path.relative_to(v).as_posix();before=archive.read(rel).decode() if rel in archive.namelist() else '';after=path.read_text()
  if before==after:continue
  diff=list(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='phase4/'+rel,tofile='phase5/'+rel));parts.extend(diff)
  changes[rel]={'added':sum(line.startswith('+') and not line.startswith('+++') for line in diff),'removed':sum(line.startswith('-') and not line.startswith('---') for line in diff)}
(exp/'phase5-runtime.diff').write_text(''.join(parts));(exp/'phase5-diff-summary.json').write_text(json.dumps(changes,indent=2)+'\n')
print(json.dumps(changes,indent=2))
