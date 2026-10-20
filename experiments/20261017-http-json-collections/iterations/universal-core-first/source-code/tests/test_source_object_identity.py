from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


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
