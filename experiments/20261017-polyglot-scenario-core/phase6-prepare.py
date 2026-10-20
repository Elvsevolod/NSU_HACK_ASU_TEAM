from pathlib import Path
import hashlib,json
root=Path('/Users/vsevolod/Desktop/NSU_HACK_ASU_TEAM');v=root/'solutions/—_polyglot-scenario-core';e=root/'experiments/20261017-polyglot-scenario-core'
raw=(v/'solution.zip').read_bytes();digest=hashlib.sha256(raw).hexdigest();assert digest=='769390f06bc0213b2d838651ef9fddab9f8f8af494f46cdf64dfd67c4149c4ac'
p=e/'phase6-baseline.zip'
if p.exists():assert p.read_bytes()==raw
else:p.write_bytes(raw)
(e/'phase6-plan.json').write_text(json.dumps({'previous_goal_turn':'progress: phase 5 added verified Spring configuration, validation, advice and time boundaries; packaged and reproduced 348 tests and 15 public traces, broad Java target still failing','objective_unchanged':True,'baseline_sha256':digest,'next_gap':'Lazy Java streams and source method references; then deep DTO/enums/decimal/external responses and full Java/mixed lifecycle proof','DeepSeek_assessment':'Independent review could help effect ownership and lazy semantics. Prior bounded requests repeatedly produced no response; latest attempt 45 seconds ago in preceding phase yielded no substantive result. No new request now; re-evaluate on unexpected evidence. No implementation delegation because human requires read-only.','changes_allowed':['solutions/—_polyglot-scenario-core','its registry text','new experiment artifacts'],'not_a_completion_gate':'Passing bounded stream probes does not establish full public interservice graph or product universality.'},indent=2)+'\n')
print(digest)
