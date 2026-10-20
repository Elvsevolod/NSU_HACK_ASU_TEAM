"""Adversarial transport, ordering, native-kind and history-origin controls."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from semantic_holdout_checker33 import match
from semantic_wire_checker33 import evaluate_wire,history_matches,decimal,text_match,observation


def fixture():
    spec={'target':'entry','deployment':'unit','method':'GET','path':['items',7],'query':{},'headers':{},'body':{'missing':True},
          'status':200,'authority':'http://unit:8080','bound':{'id':{'declared_type':'java.lang.Long','native_kind':'Long','value':7}}}
    query={'deployment':'unit','method':'GET','path':['items','7'],'query':{},'query_complete':True,'headers':{},
           'body':{'missing':True},'url':'http://unit:8080/items/7','provenance':{}}
    operation={'method':'reader','resource':'table','operation':'findById','request_id':1,'argument_kinds':['Long'],'arguments':[7]}
    wanted={'outer':spec,'remotes':[],'bound':spec['bound'],'history':{},'operations':[operation]}
    actual={'requests':[{'id':1,'entry':'entry','request':query,'bound_arguments':[{'name':'id','declared_type':'java.lang.Long','native_kind':'Long','value':7}]}],
            'responses':[{'request':1,'status':200}],'events':[],'result':'ok',
            'data_operations':[{**deepcopy(operation),'sql_emitted':True,'datastore_event':True,'uncertain_write':False}]}
    assert all(evaluate_wire(wanted,actual,[],{},match).values())
    return wanted,actual


@pytest.mark.parametrize('field,value',[('deployment','other'),('method','POST'),('path',['items','8']),
    ('query',{'other':['7']}),('query_complete',False),('headers',{'x':['extra']}),('body',{}),('url','http://wrong:8080/items/7')])
def test_exact_outer_wire_rejects_individually_wrong_components(field,value):
    wanted,actual=fixture();actual['requests'][0]['request'][field]=value
    assert not all(evaluate_wire(wanted,actual,[],{},match).values())


@pytest.mark.parametrize('field,value',[('method','other'),('resource','other'),('operation','deleteById'),
    ('request_id',2),('argument_kinds',['Integer']),('arguments',['7']),('sql_emitted',False),
    ('datastore_event',False),('uncertain_write',True)])
def test_exact_sql_witness_checks_operation_value_kind_and_origin(field,value):
    wanted,actual=fixture();actual['data_operations'][0][field]=value
    assert not evaluate_wire(wanted,actual,[],{},match)['ordered_sql']


def test_sql_order_and_cardinality_are_not_set_comparisons():
    wanted,actual=fixture();second={**deepcopy(wanted['operations'][0]),'method':'other','arguments':[8]}
    wanted['operations'].append(second);actual['data_operations'].append({**second,'sql_emitted':True,'datastore_event':True,'uncertain_write':False})
    assert all(evaluate_wire(wanted,actual,[],{},match).values())
    actual['data_operations'].reverse()
    assert not evaluate_wire(wanted,actual,[],{},match)['ordered_sql']


@pytest.mark.parametrize('field,value',[('native_kind','Integer'),('declared_type','java.lang.Integer'),('value','7')])
def test_binding_requires_native_long_and_numeric_value(field,value):
    wanted,actual=fixture();actual['requests'][0]['bound_arguments'][0][field]=value
    assert not all(evaluate_wire(wanted,actual,[],{},match).values())


def test_symbolic_text_matches_only_the_exact_integral_origin():
    symbol={'__symbol__':'new','__type__':'Long','__constraints__':['non_null']};bindings={'created':symbol}
    expected={'$identity':'created'};value={'__symbol__':'new:decimal','__type__':'String','__constraints__':['non_null'],
        '__integral_text__':True,'__integral_bits__':64,'__integral_origin__':symbol}
    assert text_match([expected],value,bindings)
    for key,wrong in [('__integral_bits__',32),('__symbol__','other'),('__integral_origin__',{'__symbol__':'different','__type__':'Long'})]:
        bad={**value,key:wrong};assert not text_match([expected],bad,bindings)
    assert not text_match([expected],{'__symbol__':'opaque','__type__':'String'},bindings)


def history_fixture():
    wanted,actual=fixture();prior={'outcome':'returned','exploration':{'complete':True},'entry':'creator',
        'result':{'id':7},'selected_objects':[]}
    proof={'source':'history','resolved':True,'reference':'history[0].result.id',
           'producer_observation':{'step':1,'entry':'creator','digest':observation(prior),'exploration':{'complete':True}}}
    actual['requests'][0]['request']['provenance']={'bindings':{'id':proof}}
    wanted['history']={'id':{'step':1,'entry':'creator','reference':'history[0].result.id','value':7}}
    return wanted,actual,[{'alternatives':[prior]}]


@pytest.mark.parametrize('change',['wrong_digest','wrong_entry','wrong_step','wrong_path','not_history','unresolved','partial','failed_alternative','disagreeing_alternative'])
def test_history_requires_the_actual_complete_agreeing_producer(change):
    wanted,actual,prior=history_fixture()
    assert history_matches(wanted,actual,prior,{},match)
    proof=actual['requests'][0]['request']['provenance']['bindings']['id'];seen=proof['producer_observation']
    if change=='wrong_digest':seen['digest']='guessed'
    if change=='wrong_entry':seen['entry']='other'
    if change=='wrong_step':seen['step']=2
    if change=='wrong_path':proof['reference']='history[0].result.other'
    if change=='not_history':proof['source']='database'
    if change=='unresolved':proof['resolved']=False
    if change=='partial':prior[0]['alternatives'][0]['exploration']['complete']=False
    if change.endswith('alternative'):
        bad=deepcopy(prior[0]['alternatives'][0])
        if change=='failed_alternative':bad['outcome']='uncaught application exception'
        else:bad['result']['id']=8
        prior[0]['alternatives'].append(bad)
    assert not history_matches(wanted,actual,prior,{},match)


def test_remote_bound_kind_is_checked_independently_of_the_outer_request():
    wanted,actual=fixture();remote=deepcopy(wanted['outer']);remote['source']='entry';wanted['remotes']=[remote]
    event=deepcopy(actual['requests'][0]);event['id']=2;actual['requests'].append(event)
    actual['responses'].append({'request':2,'status':200})
    actual['events']=[{'edge':{'source':'entry','relation':'remote','target':'entry'},'values':{'target_request':2}}]
    assert all(evaluate_wire(wanted,actual,[],{},match).values())
    event['bound_arguments'][0]['native_kind']='Integer'
    assert not all(evaluate_wire(wanted,actual,[],{},match).values())


@pytest.mark.parametrize('change',['client','body','request','status','digest'])
def test_native_error_message_must_refer_to_its_actual_transport(change):
    from semantic_wire_checker33 import error_origins
    wanted,actual=fixture();event=actual['requests'][0];event['id']=2
    event['request']['provenance']['client_method']='method:client#read()'
    event['transport_response']={'request':2,'status':404,'body':{'message':'missing'}}
    fact={'model_version':'feign-default-error-message/1','request_id':2,'status':404,
        'client_method':'method:client#read()','response_body':{'message':'missing'},
        'request':{key:deepcopy(event['request'][key]) for key in ('deployment','method','url','path','query','query_complete')},
        'exact_text':False,'limits':[]}
    def message():return {'__type__':'String','__constraints__':['non_null'],'__feign_error_message__':fact,
        '__symbol__':'feign-message-'+hashlib.sha256(json.dumps(fact,sort_keys=True,ensure_ascii=True).encode()).hexdigest()[:20]}
    assert error_origins(message(),[event])
    if change=='client':fact['client_method']='method:wrong#read()'
    if change=='body':fact['response_body']={'message':'other'}
    if change=='request':fact['request']['path']=['other']
    if change=='status':fact['status']=500
    value=message()
    if change=='digest':value['__symbol__']='feign-message-forged'
    assert not error_origins(value,[event])


def test_orphan_or_duplicate_response_is_not_an_observed_exchange():
    wanted,actual=fixture();actual['responses'].append({'request':99,'status':200})
    assert not all(evaluate_wire(wanted,actual,[],{},match).values())
