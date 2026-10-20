import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.request import Request
from analyzer.state import ScenarioState,U
from builders import build


def run(tmp_path,body):
    project,db,ids=build(tmp_path,{'Api.java':'import java.util.*;class Api{Object entry(){'+body+'}}'})
    engine=Engine(project,ScenarioState(db))
    return engine.run(ids['Api.entry'],{}),engine


def test_duplicate_add_cardinality_membership_remove_and_null(tmp_path):
    result,engine=run(tmp_path,'''Set<String> codes=new HashSet<>();
      boolean first=codes.add("A");boolean second=codes.add("A");
      codes.add(null);codes.add(null);int count=codes.size();
      boolean has=codes.contains("A");boolean removed=codes.remove("A");
      boolean again=codes.remove("A");return Arrays.asList(first,second,count,has,removed,again,codes.size(),codes.contains(null));''')
    assert result==[True,False,2,True,True,False,1,True]
    assert not engine.approximate


def test_copy_preserves_membership_and_does_not_invent_encounter_order(tmp_path):
    result,engine=run(tmp_path,'''Set<String> codes=new HashSet<>();codes.add("B");codes.add("A");codes.add("B");
       List<String> copied=new ArrayList<>(codes);return copied;''')
    assert len(result)==2 and set(result)=={'A','B'}
    assert result.order_known is False
    assert not engine.approximate


def test_order_dependent_list_index_stays_unresolved(tmp_path):
    result,engine=run(tmp_path,'''Set<String> codes=new HashSet<>();codes.add("B");codes.add("A");
       List<String> copied=new ArrayList<>(codes);return copied.get(0);''')
    assert result is U and any('order' in warning.lower() for warning in engine.warnings)


def test_unknown_encounter_order_does_not_hide_known_bounds_failure(tmp_path):
    result,engine=run(tmp_path,'''Set<String> codes=new HashSet<>();codes.add("B");codes.add("A");
       try{return new ArrayList<>(codes).get(4);}catch(IndexOutOfBoundsException failure){return "rejected";}''')
    assert result=='rejected'


def test_java_boolean_integer_and_wrapper_width_remain_distinct(tmp_path):
    result,_=run(tmp_path,'''Set<Object> values=new HashSet<>();values.add(true);values.add(1);values.add(1L);
       return values.size();''')
    assert result==3


def test_unknown_key_invalidates_only_set_knowledge(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{
      int entry(String key){Set<String> codes=new HashSet<>();codes.add("A");codes.add(key);return codes.size();}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{'key':U}) is U
    assert any('Set' in warning for warning in engine.warnings)


def test_user_collection_and_user_equality_are_not_native_string_set(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Product{public boolean equals(Object other){return true;}public int hashCode(){return 7;}}
      class Api{int entry(){Set<Product> values=new HashSet<>();values.add(new Product());values.add(new Product());return values.size();}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{}) is U
    assert any('Set' in warning for warning in engine.warnings)


@pytest.mark.parametrize('limit',[1,4,8])
def test_set_iteration_never_claims_one_specific_first_element(tmp_path,limit):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{
      String entry(){Set<String> values=new HashSet<>();values.add("A");values.add("B");
        for(String value:values){return value;}return "empty";}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{},limit=limit)
    returned={row['result'] for row in outcomes if row['engine'].outcome=='returned'}
    assert returned=={'A','B'}


def test_request_freeze_keeps_unspecified_order_metadata(tmp_path):
    values,_=run(tmp_path,'''Set<String> codes=new HashSet<>();codes.add("B");codes.add("A");return new ArrayList<>(codes);''')
    request=Request.http('warehouse','POST','/lookup',body=values)
    assert request.body.order_known is False
    assert request.record()['collection_shapes']==[{'path':'body','size':2,'order':'unspecified'}]
