from analyzer.contracts import ContractIndex,ContractGrounder
from analyzer.frontend import Frontend
from analyzer.state import ScenarioState
from builders import build


def test_record_reference_uses_payload_schema_and_related_key(tmp_path):
    project,_,ids=build(tmp_path,{'Api.java':'''class Envelope<T>{int status;String msg;T data;Envelope(int s,String m,T d){status=s;msg=m;data=d;}}
      class Warranty{String id;}class WarrantyType{String id;}
      class Api{
       @GetMapping("/warranty/types") Envelope<List<WarrantyType>> getAllWarrantyType(){return null;}
       @GetMapping("/warranty/{warrantyId}") Envelope<Warranty> getWarrantyById(@PathVariable String warrantyId){return null;}
       @GetMapping("/warranty/view/{warrantyId}") Envelope<Warranty> lookUpWarrantyRecord(@PathVariable String warrantyId){return null;}
       @GetMapping("/warranty/shipment/{shipmentId}") Envelope<Warranty> findWarrantyByShipmentId(@PathVariable String shipmentId){return null;}
      }'''})
    index=ContractIndex(project,Frontend(project))
    assert index.rank('Look up the warranty record of the shipment')[0][2]['entry']==ids['Api.findWarrantyByShipmentId']


def test_collection_of_phrase_keeps_its_requested_noun(tmp_path):
    project,_,ids=build(tmp_path,{'Api.java':'''class Order{String id;}class Invoice{String id;}
      class Api{@GetMapping("/orders") List<Order> refreshOrders(){return null;}
       @GetMapping("/invoices") List<Invoice> refreshInvoices(){return null;}
       @GetMapping("/price/{id}") String calculate(@PathVariable String id){return "price";}}'''})
    index=ContractIndex(project,Frontend(project))
    assert index.rank('Refresh the list of orders')[0][2]['entry']==ids['Api.refreshOrders']


def test_unqualified_principal_or_named_lookup_is_semantically_ambiguous(tmp_path):
    project,state,ids=build(tmp_path,{'Api.java':'''class Account{String name;}
      class AccountController{
       @GetMapping("/accounts/{name}") Account getAccountByName(@PathVariable String name){return null;}
       @GetMapping("/accounts/current") Account getCurrentAccount(Principal principal){return null;}
      }'''})
    frontend=Frontend(project);index=ContractIndex(project,frontend)
    state=ScenarioState(state,{})
    grounder=ContractGrounder(project,frontend,index,None,{'facts':{},'choice_rules':[]})
    proposals,detail=grounder.step('Read account',state)
    assert not proposals
    assert set(detail['semantic_candidates'])=={ids['AccountController.getAccountByName'],ids['AccountController.getCurrentAccount']}
    assert detail['grounding_status']=='unresolved_semantic_ambiguity'
    # An explicit request supplies the missing identity contract.
    proposals,_=grounder.step('GET /accounts/current',state)
    assert len(proposals)==1 and proposals[0]['entry']==ids['AccountController.getCurrentAccount']
