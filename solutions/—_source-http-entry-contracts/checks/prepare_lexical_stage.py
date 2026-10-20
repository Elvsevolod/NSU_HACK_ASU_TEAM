"""Keep semantic/binding bytes of A; replace only the retrieval class for B."""
import difflib,hashlib,json,shutil
from pathlib import Path
V=Path(__file__).resolve().parents[1]
target=V/'development/stages/B-R07-lexical'
assert not target.exists();target.mkdir(parents=True)
shutil.copytree(V/'development/stages/B00-parent31/code',target/'code')
file=target/'code/analyzer/contracts.py';before=file.read_text();current=(V/'code/analyzer/contracts.py').read_text()
def bounds(source):return source.index('class ContractIndex:'),source.index('\ndef explicit_value(')
left,right=bounds(before);a,b=bounds(current)
after=before[:left]+current[a:b]+before[right:];file.write_text(after)
for name in ('retrieval_sources.py','lexical_retrieval.py'):shutil.copyfile(V/'code/analyzer'/name,target/'code/analyzer'/name)
(target/'retrieval-only.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='A/contracts.py',tofile='B/contracts.py')))
(target/'IDENTITY.md').write_text('B uses exact B00-parent31 language/HTTP/binding/execution files. Only ContractIndex gets tokenizer/intent hooks and two retrieval-only modules are added. The Grounder outside that class stays byte-identical. No producer, execution or budget repair is transplanted.\n')
manifest={p.relative_to(target/'code').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((target/'code').rglob('*')) if p.is_file()}
(target/'code-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'stage':'B-R07-lexical','files':len(manifest)}))
