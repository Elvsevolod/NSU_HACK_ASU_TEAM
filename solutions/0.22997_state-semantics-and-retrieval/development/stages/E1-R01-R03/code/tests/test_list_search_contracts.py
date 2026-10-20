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


def test_equality_throw_skips_suffix(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Key{public boolean equals(Object x){throw new IllegalStateException();}}
      class Api{int entry(){List<Object> values=Arrays.asList("A");values.indexOf(new Key());return after();}
      int after(){return 9;}}'''})
    e=Engine(p,ScenarioState(db));e.run(ids['Api.entry'],{})
    assert e.outcome=='uncaught application exception'
    assert ('','executes',ids['Api.after']) not in e.edges


@pytest.mark.parametrize('opaque,ordered',[(True,True),(False,False)])
def test_unproved_membership_or_order_does_not_choose_an_index(tmp_path,opaque,ordered):
    p,db,ids=build(tmp_path,{'Api.java':'import java.util.*;class Api{int entry(List<String> names){return names.indexOf("B");}}'})
    names=JavaList(['A','B'],['String','String']);names.opaque=opaque;names.order_known=ordered
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{'names':names}) is U


def test_unknown_wrapper_class_does_not_invent_equality(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'import java.util.*;class Api{int entry(List<Object> values,Object key){return values.indexOf(key);}}'})
    values=JavaList([1],[None]);e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{'values':values,'key':1}) is U
