from analyzer.contracts import ContractIndex
from analyzer.frontend import Frontend
from analyzer.result_contracts import result_shape
from builders import build


def test_nested_concrete_collection_and_explicit_role_select_full_list(tmp_path):
    project,_,ids=build(tmp_path,{'Api.java':'''import java.util.*;import org.springframework.http.ResponseEntity;
      class Envelope<T>{int status;T data;Envelope(int value,T items){status=value;data=items;}}
      class Invoice{String id;}class Filter{String owner;}
      class AdminInvoiceController{
       @GetMapping("/admin/invoices") ResponseEntity allInvoices(){ArrayList<Invoice> items=new ArrayList<>();
         return ResponseEntity.ok(new Envelope<>(1,items));}}
      class InvoiceController{
       @PostMapping("/invoices/filter") Envelope<List<Invoice>> refreshInvoices(@RequestBody Filter filter){return null;}}
      '''})
    entities,collection=result_shape(project,ids['AdminInvoiceController.allInvoices'])
    assert collection and 'Invoice' in entities
    index=ContractIndex(project,Frontend(project))
    assert index.rank('As the administrator, open the list of all invoices')[0][2]['entry']==ids['AdminInvoiceController.allInvoices']


def test_administrator_role_alias_matches_source_admin_annotation(tmp_path):
    project,_,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Invoice{String id;}class AdminInvoiceController{
       @PreAuthorize("hasRole('ADMIN')") @GetMapping("/invoices") List<Invoice> getAllInvoices(){return null;}}
      '''})
    assert ContractIndex(project,Frontend(project)).rank('As the administrator, show all invoices')[0][2]['entry']==ids['AdminInvoiceController.getAllInvoices']
