"""A related-object read rule must not strengthen an internal write helper."""
from analyzer.contracts import ContractIndex
from analyzer.frontend import Frontend
from builders import build


SOURCE = '''import org.springframework.web.bind.annotation.*;
class Invoice {String id; String status;}
class Payment {String id; String invoiceId;}
class Envelope<T> {T data;}
class BalancePaymentController {
 @PostMapping("/payments/balance") Envelope<Payment> payFromBalance(@RequestBody Payment request) {
  debit(request.invoiceId); return new Envelope<Payment>();
 }
 void debit(String invoiceId){}
}
class InvoiceController {
 @PostMapping("/invoices/{invoiceId}/paid") boolean payInvoice(@PathVariable String invoiceId) {return true;}
 @GetMapping("/invoices") List<Invoice> getInvoices(){return null;}
}
class PaymentController {
 @GetMapping("/payments/{paymentId}") Envelope<Payment> getPayment(@PathVariable String paymentId){return null;}
 @GetMapping("/payments/invoice/{invoiceId}") Envelope<Payment> findPaymentByInvoiceId(@PathVariable String invoiceId){return null;}
}'''


def index(tmp_path):
    project, _, ids = build(tmp_path, {'Billing.java': SOURCE})
    return ContractIndex(project, Frontend(project)), ids


def test_write_qualifier_does_not_multiply_internal_reference_score(tmp_path):
    contracts, ids = index(tmp_path)
    action = 'Pay for the invoice from the internal account balance'
    # The independent contract is the public payment operation, not the status
    # endpoint. The same action's "for invoice" must never boost a path ID.
    assert contracts.rank(action)[0][2]['entry'] == ids['BalancePaymentController.payFromBalance']


def test_payment_read_keeps_related_reference_parameter(tmp_path):
    contracts, ids = index(tmp_path)
    assert contracts.rank('Find payment for the invoice')[0][2]['entry'] == ids['PaymentController.findPaymentByInvoiceId']


def test_unqualified_invoice_collection_is_preserved(tmp_path):
    contracts, ids = index(tmp_path)
    assert contracts.rank('Show all invoices')[0][2]['entry'] == ids['InvoiceController.getInvoices']


def test_related_payment_does_not_require_a_record_keyword(tmp_path):
    contracts, ids = index(tmp_path)
    assert contracts.rank('Read the payment of the invoice')[0][2]['entry'] == ids['PaymentController.findPaymentByInvoiceId']


def test_list_of_keeps_collection_noun(tmp_path):
    contracts, ids = index(tmp_path)
    assert contracts.rank('Open the list of all invoices')[0][2]['entry'] == ids['InvoiceController.getInvoices']
