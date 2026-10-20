from pathlib import Path
import json,os,subprocess,time
root=Path('/Users/vsevolod/Desktop/NSU_HACK_ASU_TEAM');base=root/'experiments/20261017-polyglot-scenario-core'
prompt='''Read-only architecture critique. No tools needed. Do not edit files, execute commands, or delegate. The human permits project data sharing but forbids your changes. Respond concisely in text.
Our source-only scenario graph analyzer is Python: Tree-sitter Java, LibCST Python, shared IR/effects/state/kernel, native SQLGlot/Z3/QuickJS/FastAPI/Pydantic/PyJWT/pwdlib. Target apps never run or import. 286 tests, 8 public FastAPI HTTP traces and synthetic mixed Java/Python chains pass; whole-product quality remains low. Java public verification currently only executes 2 prepared method-body cases from unmodified PiggyMetrics.
Next real HTTP chain is PiggyMetrics account update -> Feign statistics service -> repository, with account reads across steps and denial cases. Its source is Spring Boot 2.0.3 + Spring Cloud Finchley. Servlet context paths are in a local Config Server shared directory application.yml and <spring.application.name>.yml; bootstrap.yml names the services. Current analyzer misses these context paths and has one global shallow regex config dictionary. Method security uses @PreAuthorize("#oauth2.hasScope('server') or #name.equals('demo')"). Statistics uses lazy streams/map/methodrefs/reduce, BigDecimal, time, external exchange-rates HTTP and source DTO serializers. Existing framework_entry and authorization_passed assumptions are global and too coarse for a genuine end-to-end claim.
Hypothesis: a reusable per-deployment property index with source/precedence provenance and explicit unknown conflicts; path prefixes applied at protocol boundary without changing skeleton IDs; typed provided authentication/external response snapshots treated as input facts, never manual graph edges. Then shared IR callbacks for bounded Java streams and Python Decimal for BigDecimal. Complete chain must be checked against a fixed manual oracle before any prediction, including graph, statuses, state and explicit unsupported tails. No app-specific names/routes/constants in runtime.
Critique the sequencing and hidden false-success risks, especially property-source precedence, gateway versus servlet paths, security context versus skipping security, service/client interceptor provenance, and lazy callback/effect ownership. Suggest a small falsifying test for the config/path boundary and the least complex useful implementation. Do not invent metrics or propose executing the target app. No code changes.'''
env={**os.environ,'OPENCODE_PERMISSION':json.dumps({'edit':'deny','bash':'deny','task':'deny','external_directory':'deny'})}
args=[str(Path.home()/'.local/bin/opencode-deepseek'),'run','--dir',str(root),'--format','json','--agent','build','--variant','max',prompt]
started=time.monotonic()
with (base/'phase5-consult.jsonl').open('w') as out,(base/'phase5-consult.stderr').open('w') as err:
 try:
  result=subprocess.run(args,cwd=root,env=env,stdout=out,stderr=err,timeout=45);status={'returncode':result.returncode,'timeout':False}
 except subprocess.TimeoutExpired:status={'timeout':True}
status['seconds']=time.monotonic()-started
(base/'phase5-consult-status.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps(status))
