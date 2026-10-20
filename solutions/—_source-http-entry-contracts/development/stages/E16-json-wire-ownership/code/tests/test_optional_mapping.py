import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def model(tmp_path,body):
    return build(tmp_path,{'Api.java':'''import java.util.*;
    class Api {int visits;Object entry(){visits=0;BODY} String mark(String x){visits++;return x+"!";}}'''.replace('BODY',body)})


@pytest.mark.parametrize('body,want',[
 ('Optional<String> s=Optional.empty();s.map(x->mark(x));return visits;',0),
 ('return Optional.of("x").map(x->mark(x)).orElseThrow();','x!'),
 ('return Optional.of("x").map(x->null).isPresent();',False),
 ('return Optional.ofNullable(null).map(x->mark(x)).isPresent();',False)])
def test_optional_map_presence_values_and_callbacks(tmp_path,body,want):
    p,db,ids=model(tmp_path,body);e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==want
    assert ((ids['Api.entry'],'calls',ids['Api.mark']) in e.edges)==(want=='x!')


@pytest.mark.parametrize('body',[
 'return Optional.empty().map(null);','return Optional.of("x").map(null);',
 'return Optional.of("x").map(x->{mark(x);throw new IllegalStateException();});'])
def test_null_mapper_and_throw_never_complete_normally(tmp_path,body):
    p,db,ids=model(tmp_path,body);e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='uncaught application exception'
    if 'throw' in body:assert (ids['Api.entry'],'calls',ids['Api.mark']) in e.edges


def test_unknown_optional_is_not_made_empty(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
     class Api {Object entry(Optional<String> value){return value.map(x->x+"!");}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{'value':{'__optional__':True,'optional':U}}) is U
    assert e.outcome=='unsupported_semantics boundary'
