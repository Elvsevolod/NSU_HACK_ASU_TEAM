from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build
from copy import deepcopy
from analyzer.paths import join_states,run_paths
from analyzer.java_collections import JavaObject
import pytest


def test_distinct_source_objects_without_equals_do_not_compare_by_python_fields(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Box {String label="same";}
      class Api {boolean entry(){Box left=new Box();Box right=new Box();return left.equals(right);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{}) is False


def test_a_source_object_alias_preserves_reference_equality(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Box {}
      class Api {boolean entry(){Box left=new Box();Box alias=left;return left.equals(alias);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{}) is True


def test_lombok_equality_is_not_replaced_by_reference_equality(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''@Data class Box {String label="same";}
      class Api {boolean entry(){Box left=new Box();Box right=new Box();return left.equals(right);}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{}) is U
    assert any('equals implementation is unresolved' in warning for warning in engine.warnings)


def test_business_field_with_metadata_name_does_not_change_constructed_runtime_class(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Box {String __type__="BusinessValue";}
      class Api {Object entry(){Box value=new Box();return value.getClass();}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=={'__java_class__':'Box'}


def test_state_join_preserves_an_allocation_copied_into_alternative_paths(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Box {String id;}
      class Api {Box entry(){Box value=new Box();value.id="created";return value;}}'''})
    engine=Engine(project,ScenarioState(db))
    result=engine.run(ids['Api.entry'],{})
    engine.state.history=[{'result':result}]
    left,right=deepcopy(engine.state),deepcopy(engine.state)
    left.browser['branch']='left';right.browser['branch']='right'
    joined=join_states([left,right]);value=joined.history[0]['result']
    assert isinstance(value,JavaObject) and value['id']=='created'
    assert value.java_type=='Box'


def test_two_source_allocations_at_the_same_constructor_site_are_distinct(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Box {}
      class Api {Box make(){return new Box();}boolean entry(){return make().equals(make());}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{}) is False


def test_unknown_equals_argument_retains_both_possible_results(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Box {}
      class Api {String entry(Object input){Box value=new Box();
        if(value.equals(input)){return "same";}return "different";}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{'input':U})
    assert {outcome['result'] for outcome in outcomes}=={'same','different'}
    assert all(outcome['engine'].warnings for outcome in outcomes)


def test_join_of_distinct_allocations_keeps_fields_without_proving_identity(tmp_path):
    from analyzer.engine import merge
    left=JavaObject('Box',{'id':'same-field'})
    right=JavaObject('Box',{'id':'same-field'})
    value=merge(left,right)
    assert isinstance(value,JavaObject) and value['id']=='same-field'
    assert value.java_identity is None


def test_business_metadata_fields_do_not_activate_native_response_models(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Box {
      int __type__=1;boolean __http_entity__=true;boolean __optional__=true;String optional="ordinary";
      String body="body-field";String label="label-field";}
      class Api {Box entry(){Box value=new Box();value.getLabel();return value;}}'''})
    result=Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})
    assert isinstance(result,JavaObject) and result['body']=='body-field'
    from analyzer.models import wire
    assert wire(result)['optional']=='ordinary'


@pytest.mark.parametrize('declarations,expression,expected',[
    ('Box left=new Box();Box right=new Box();','left==right',False),
    ('Box left=new Box();Box alias=left;','left==alias',True),
    ('Map left=new HashMap();Map right=new HashMap();','left==right',False),
    ('Map left=new HashMap();Map alias=left;','left==alias',True),
    ('Map left=new HashMap();Map right=new HashMap(left);','left!=right',True),
])
def test_reference_operators_do_not_use_structural_field_equality(tmp_path,declarations,expression,expected):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Box {}
      class Api {boolean entry(){'''+declarations+'return '+expression+';}}'})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{}) is expected
