"""Keyword-group order is checked against Python call semantics, not app names."""
from polygraph.analysis import analyze
from polygraph.grounding import reference
from polygraph.values import Symbol, Text
from support import fixture, scenario, edge_set


def test_dictionary_expansion_into_source_function_binds_values(tmp_path):
    p,store,ids=fixture(tmp_path,{'main.py':'''from fastapi import FastAPI
app=FastAPI()
def combine(*,a,b=4):return a+b
@app.get("/value")
def value():
    payload={"a":3}
    return combine(**payload,b=8)
'''})
    _,detail=analyze(p,store,{},scenario({'path':'/value'}))
    assert detail['paths'][0]['steps'][0]['response']['body']==11


def test_duplicate_mapping_evaluates_explicit_group_but_never_enters_callee(tmp_path):
    p,store,ids=fixture(tmp_path,{'main.py':'''from fastapi import FastAPI
app=FastAPI()
def first():return 2
def second():return 3
def never(*,a,b):return 7
@app.get("/value")
def value():return never(**{"a":1},a=first(),b=second())
'''})
    block,detail=analyze(p,store,{},scenario({'path':'/value'}))
    assert {e[2] for e in edge_set(block,'executes')}=={ids['main.value'],ids['main.first'],ids['main.second']}
    assert detail['paths'][0]['steps'][0]['response']['status']==500


def test_nonstring_keyword_name_is_rejected_after_later_argument_evaluation(tmp_path):
    p,store,ids=fixture(tmp_path,{'main.py':'''from fastapi import FastAPI
app=FastAPI()
def later():return 9
def never(*,a):return 7
@app.get("/value")
def value():return never(**{1:2},a=later())
'''})
    block,detail=analyze(p,store,{},scenario({'path':'/value'}))
    assert {e[2] for e in edge_set(block,'executes')}=={ids['main.value'],ids['main.later']}
    assert detail['paths'][0]['steps'][0]['response']['status']==500


def test_history_string_composition_preserves_symbolic_identity():
    symbol=Symbol('id','UUID')
    assert reference({'$concat':['Bearer ',{'$ref':'token'}]},{'token':'real-token'})=='Bearer real-token'
    assert reference({'$concat':['/items/',{'$ref':'id'}]},{'id':symbol})==Text(('/items/',symbol))
