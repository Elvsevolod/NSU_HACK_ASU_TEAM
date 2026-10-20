import pytest
from analyzer.provenance import history_value
from analyzer.state import U
from builders import build

SOURCE='''class Invoice{@Id String id;}class Weather{String forecast;}
class Api{@GetMapping("/invoices") List<Invoice> list(){return null;}
@GetMapping("/invoices/{invoiceId}") String show(@PathVariable String invoiceId){return invoiceId;}
@GetMapping("/weather") Weather weather(){return null;}}'''


@pytest.mark.parametrize('values,ordinal,expected',[
    ([U,'C'],'first',None),
    (['A','A','B'],'second','A'),
    (['A','A','B'],'third','B'),
])
def test_ordinals_use_original_slots_and_duplicate_positions(tmp_path,values,ordinal,expected):
    project,_,ids=build(tmp_path,{'Api.java':SOURCE})
    history=[{'entry':ids['Api.list'],'result':[{'__type__':'Invoice','id':value} for value in values]}]
    result=history_value(project,ids['Api.show'],'invoiceId','Open '+ordinal+' invoice',history)
    assert result is None if expected is None else result[1]==expected


def test_unknown_unrelated_producer_does_not_erase_known_invoice_order(tmp_path):
    project,_,ids=build(tmp_path,{'Api.java':SOURCE})
    history=[{'entry':ids['Api.list'],'result':[{'__type__':'Invoice','id':'A'}]},
        {'entry':ids['Api.weather'],'result':U}]
    assert history_value(project,ids['Api.show'],'invoiceId','Open first invoice',history)==('history[0].result[0].id','A')
