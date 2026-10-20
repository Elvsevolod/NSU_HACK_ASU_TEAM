import pytest
from analyzer.engine import Engine
from analyzer.native_storage import JavaList
from analyzer.state import ScenarioState, U
from builders import build


@pytest.mark.parametrize('operation,expected',[('indexOf',0),('lastIndexOf',2)])
def test_search_direction_and_receiver_unchanged(tmp_path,operation,expected):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{
      Object entry(){List<String> names=Arrays.asList("A","B","A");
      int index=names.'''+operation+'''("A");return Arrays.asList(index,names);}}'''})
    e=Engine(p,ScenarioState(db));result=e.run(ids['Api.entry'],{})
    assert result==[expected,['A','B','A']] and result.kinds[0]=='Integer'
    assert not e.approximate


@pytest.mark.parametrize('operation,expected',[('indexOf',1),('lastIndexOf',1)])
def test_source_equals_callback_order_and_effects(tmp_path,operation,expected):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Key{int checks=0;public boolean equals(Object x){checks++;return x==null;}}
      class Api{Object entry(){Key key=new Key();List<Object> values=Arrays.asList("A",null,"B");
      int pos=values.'''+operation+'''(key);return Arrays.asList(pos,key.checks);}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==[expected,2]
    assert ('','executes',ids['Key.equals']) in e.edges


@pytest.mark.parametrize('operation', ['indexOf', 'lastIndexOf'])
def test_equality_throw_skips_suffix(tmp_path, operation):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Key{public boolean equals(Object x){throw new IllegalStateException();}}
      class Api{int entry(){List<Object> values=Arrays.asList("A");values.OPERATION(new Key());return after();}
      int after(){return 9;}}'''.replace('OPERATION', operation)})
    e=Engine(p,ScenarioState(db));e.run(ids['Api.entry'],{})
    assert e.outcome=='uncaught application exception'
    assert ('','executes',ids['Api.after']) not in e.edges


@pytest.mark.parametrize('operation,expected_trace', [('indexOf', 'AB'), ('lastIndexOf', 'CB')])
def test_callback_encounter_order_and_method_return_consumer(tmp_path, operation, expected_trace):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Key{String seen="";public boolean equals(Object x){seen=seen+x;return "B".equals(x);}}
      class Api{int find(List<Object> values,Key key){return values.OPERATION(key);}
        Object entry(){Key key=new Key();List<Object> values=Arrays.asList("A","B","C");
          List<Object> alias=values;int pos=find(values,key);Object first=alias.get(0);Object last=alias.get(2);
          return Arrays.asList(pos,key.seen,first,last,alias==values);}}'''.replace('OPERATION',operation)})
    e=Engine(p,ScenarioState(db));result=e.run(ids['Api.entry'],{})
    assert result == [1, expected_trace, 'A', 'C', True], (result, sorted(e.warnings), e.effect_events)
    assert result.kinds[0] == 'Integer' and not e.approximate
    assert ('','executes',ids['Api.find']) in e.edges


@pytest.mark.parametrize('opaque,ordered',[(True,True),(False,False)])
def test_unproved_membership_or_order_does_not_choose_an_index(tmp_path,opaque,ordered):
    p,db,ids=build(tmp_path,{'Api.java':'import java.util.*;class Api{int entry(List<String> names){return names.indexOf("B");}}'})
    names=JavaList(['A','B'],['String','String']);names.opaque=opaque;names.order_known=ordered
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{'names':names}) is U


def test_unknown_wrapper_class_does_not_invent_equality(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'import java.util.*;class Api{int entry(List<Object> values,Object key){return values.indexOf(key);}}'})
    values=JavaList([1],[None]);e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{'values':values,'key':1}) is U
