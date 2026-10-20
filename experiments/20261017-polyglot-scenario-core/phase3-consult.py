from pathlib import Path
import json, os, subprocess, time
root=Path('/Users/vsevolod/Desktop/NSU_HACK_ASU_TEAM')
base=root/'experiments/20261017-polyglot-scenario-core'
prompt="""Read-only architecture critique. Do not write files, run shell commands or delegate. The user allows project data sharing but requires you to change nothing. Work only with this supplied description; tools are unnecessary.
We implement a source-only Python microservice scenario analyzer with one shared IR/kernel for Java/Spring and Python/FastAPI. No target application is imported or run. Graph method/table IDs are supplied. Real deps: Tree-sitter, LibCST, SQLGlot, Z3, Rank-BM25. Current 133 tests and 7 bounded public body probes pass, but full natural-language scenario quality is poor; framework lifecycle, UI preparation and result/history binding remain incomplete.
We can reuse an existing standalone UI module (~3000 lines) that parses HTML/JS with html5lib/Tree-sitter, extracts ajax request configs, URL cases/guards, payload expressions, response effects, page/form/DOM/storage state. It currently uses an Enum unknown sentinel, an undefined sentinel, and dictionaries encoding typed symbols. New backend IR uses Unknown(reason), Symbol(identity,type,sort), Text(parts), Object(identity,type,fields). Proposal: copy only UI extraction/evaluation/state helpers, not its Java engine or project/database layer; provide endpoint-facts facade; adapt browser values in/out without inventing literal IDs. Keep UI state per scenario/path, separate from server heaps; apply only source-observed response callbacks; ambiguous guards and route selection remain hypotheses, never confirmed execution.
Critique this integration. Identify concrete failure modes (typed identity, omission vs null/undefined, transport ownership, guards/events, response status/callback semantics, alias mutation, frame provenance, replay, and footprint). Give minimal adversarial experiments and the simplest safe boundary. Also suggest when to replace the legacy evaluator with a mature OSS component; no invented benchmarks. No code or file changes, only a concise substantive answer."""
env=os.environ.copy();env['OPENCODE_PERMISSION']=json.dumps({'edit':'deny','bash':'deny','task':'deny','external_directory':'deny'})
args=[str(Path.home()/'.local/bin/opencode-deepseek'),'run','--dir',str(root),'--format','json','--agent','build','--variant','max',prompt]
start=time.monotonic();result={}
with (base/'phase3-consult.jsonl').open('w') as out,(base/'phase3-consult.stderr').open('w') as err:
 try:
  process=subprocess.run(args,cwd=root,env=env,stdout=out,stderr=err,timeout=75)
  result={'returncode':process.returncode,'timeout':False}
 except subprocess.TimeoutExpired:
  result={'timeout':True}
result['seconds']=time.monotonic()-start
(base/'phase3-consult-status.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
