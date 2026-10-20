"""The checker must validate every reachable producer, not a chosen row order."""
from copy import deepcopy
import pytest
from analyzer.history_agreement import observation
from check_cart_profile import normalize_nl


def source_trace():
    ready={'id':21,'orderId':11,'status':'APPROVED'};other={'id':22,'orderId':11,'status':'DECLINED'}
    alts=[{'result':[ready,other],'outcome':'returned','selected_objects':[],'exploration':{'complete':True}},
          {'result':[deepcopy(other),deepcopy(ready)],'outcome':'returned','selected_objects':[],'exploration':{'complete':True}}]
    certificate={'step':1,'entry':'payments-read','digest':observation(alts[0]),'exploration':{'complete':True}}
    consumer={'result':{},'outcome':'returned','parameters':{'id':21},'selected_objects':[],
      'exploration':{'complete':True},'bindings':{'id':{'source':'history','reference':'history[0].result[0].id',
        'resolved':True,'producer_observation':certificate}}}
    for alt in alts:alt['entry']='payments-read'
    return {'steps':[{'n':1,'alternatives':alts},{'n':2,'alternatives':[consumer]}]}


def test_same_unique_source_id_is_allowed_across_different_legal_orders():
    result=normalize_nl(source_trace())
    assert result['steps'][1]['producer']['payment_id']==21
    assert result['steps'][1]['producer']['order_id']==11


@pytest.mark.parametrize('mutation',['incomplete','failed','different-id','bad-reference','bad-certificate','wrong-entry'])
def test_missing_agreement_never_gets_a_successful_producer(mutation):
    trace=source_trace();alts=trace['steps'][0]['alternatives'];binding=trace['steps'][1]['alternatives'][0]['bindings']['id']
    if mutation=='incomplete':alts[1]['exploration']['complete']=False
    elif mutation=='failed':alts[1]['outcome']='uncaught application exception'
    elif mutation=='different-id':alts[1]['result'][1]['id']=23
    elif mutation=='bad-reference':binding['reference']='history[0].result[1].id'
    elif mutation=='bad-certificate':binding['producer_observation']['digest']='bad'
    elif mutation=='wrong-entry':binding['producer_observation']['entry']='unrelated-read'
    assert not normalize_nl(trace)['steps'][1].get('producer')
