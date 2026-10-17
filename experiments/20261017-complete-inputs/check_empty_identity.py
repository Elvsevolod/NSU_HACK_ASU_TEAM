import sys
from pathlib import Path
sys.path[:0]=['solutions/—_source-request-state/code','solutions/—_source-request-state/code/tests']
from builders import build
from analyzer.frontend import Frontend
from analyzer.contracts import ContractGrounder,ContractIndex
from analyzer.state import ScenarioState
root=Path('/private/tmp/nsu-empty-identity-probe')
project,db,_=build(root,{'Api.java':'''class Api {
  @PostMapping("/invoices/details") String show(@RequestBody Lookup input){return input.invoiceId;}
} class Lookup {String invoiceId;} class Invoice {@Id String id;}'''})
(root/'ui.js').write_text('''new Vue({data:{invoiceId:""},methods:{show(){ $.ajax({url:"/invoices/details",type:"POST",data:{invoiceId:this.invoiceId}}); }}});''')
frontend=Frontend(project)
choices,_=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}}).step('Read the invoice',ScenarioState(db))
print(choices[0]['params'],choices[0]['unresolved'])
assert 'invoiceId' not in choices[0]['params']
