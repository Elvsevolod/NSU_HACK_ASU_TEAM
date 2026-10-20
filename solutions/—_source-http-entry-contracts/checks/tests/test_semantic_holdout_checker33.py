"""False-success controls for exact rows, graphs, native identity and producer."""
from copy import deepcopy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from semantic_holdout_checker33 import graph_metrics,match,state_matches,bind_producer,outgoing_requests,write_policy,evaluate_case


def test_graph_penalizes_extras_and_misses_separately():
    gold=[{'source':'a','relation':'calls','target':'b'}]
    actual=[{'source':'a','relation':'calls','target':'c'}]
    row=graph_metrics(gold,actual)['calls']
    assert (row['tp'],row['fp'],row['fn'],row['iou'])==(0,1,1,0)
    assert graph_metrics([],[])['remote']['iou']==1


def test_external_request_is_not_counted_as_an_outbound_call():
    outer={'id':1,'request':{'deployment':'entry'}}
    remote={'id':2,'request':{'deployment':'other'}}
    assert outgoing_requests({'requests':[outer]})==[]
    assert outgoing_requests({'requests':[outer,remote]})==[remote]


def write_example():
    wanted={'operations':[{'method':'save-method','table':'table','operation':'save','writes':True}]}
    operation={'method':'save-method','resource':'table','operation':'save','datastore_event':True,'sql_emitted':True,'uncertain_write':False}
    return wanted,{'data_operations':[operation]}


@pytest.mark.parametrize('field,value',[('method','other-method'),('resource','other-table'),('operation','deleteById'),
    ('datastore_event',False),('sql_emitted',False),('uncertain_write',True)])
def test_write_witness_requires_the_correct_source_table_operation_and_certainty(field,value):
    wanted,good=write_example();bad=deepcopy(good);bad['data_operations'][0][field]=value
    assert write_policy(wanted,good)
    assert not write_policy(wanted,bad)


def test_one_good_alternative_does_not_hide_a_missing_write_in_another():
    wanted,good=write_example()
    wanted.update(edges=[],entry='entry',status=200,result='ok',tables={'table':[]})
    good.update(edges=[],entry='entry',outcome='returned',exploration={'complete':True},result='ok',
        state_after={'tables':{'table':[]}},responses=[{'request':1,'status':200}],requests=[{'id':1,'request':{}}])
    case={'steps':[wanted]}
    result=lambda alts:evaluate_case(case,{'steps':[{'alternatives':alts}]},{'table':[]})
    assert result([good,deepcopy(good)])['passed']
    bad=deepcopy(good);bad['data_operations']=[]
    assert not result([good,bad])['passed']
    assert not result([bad,bad])['passed']


def test_unknown_and_boolean_are_not_concrete_numeric_results():
    assert not match(1,True,{})
    assert not match({'id':1},{'id':{'unknown':True}},{})
    assert not match({'id':1},{'id':1,'extra':2},{})


def test_full_rows_reject_extras_missing_duplicates_and_unknown_tables():
    wanted={'s.t':[{'id':1},{'id':2}]}
    assert state_matches(wanted,{'tables':{'s.t':[{'id':2},{'id':1}]}},{})
    for actual in ({'s.t':[{'id':1},{'id':1}]},{'s.t':[{'id':1}]},{'s.t':[{'id':1},{'id':2}],'s.extra':[]}):
        assert not state_matches(wanted,{'tables':actual},{})
    assert not state_matches(wanted,{'tables':wanted,'unknown_tables':['s.t']},{})


def producer_example():
    identity={'$identity':'new','native_kind':'Long','fresh':True}
    expected={'producer':{'identity':'new','response_path':['id']},'tables':{'s.t':[{'id':9},{'id':identity}]}}
    symbol={'__symbol__':'generated','__type__':'Long','__constraints__':['non_null'],'__distinct_from__':[9]}
    alternative={'outcome':'returned','exploration':{'complete':True},'result':{'id':symbol}}
    return expected,alternative,{'s.t':[{'id':9}]}


def test_generated_identity_is_bound_only_by_an_agreeing_complete_producer():
    expected,a,initial=producer_example();bindings={}
    assert bind_producer(expected,[a,deepcopy(a)],bindings,initial)
    assert match({'$identity':'new'},a['result']['id'],bindings)
    other=deepcopy(a);other['result']['id']['__symbol__']='different'
    assert not bind_producer(expected,[a,other],{},initial)


@pytest.mark.parametrize('change',['null','unknown','wrong_kind','not_fresh','partial','failed','missing'])
def test_a_bad_producer_cannot_be_rescued_by_one_good_alternative(change):
    expected,a,initial=producer_example();bad=deepcopy(a)
    if change=='null':bad['result']['id']=None
    if change=='unknown':bad['result']['id']={'unknown':True}
    if change=='wrong_kind':bad['result']['id']['__type__']='Integer'
    if change=='not_fresh':bad['result']['id']['__distinct_from__']=[]
    if change=='partial':bad['exploration']['complete']=False
    if change=='failed':bad['outcome']='HTTP error response'
    if change=='missing':bad['result']={}
    assert not bind_producer(expected,[a,bad],{},initial)
