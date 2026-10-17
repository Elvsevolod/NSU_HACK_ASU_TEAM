from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def test_unknown_receiver_is_not_misreported_as_a_missing_collection_method(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {int entry(List items){return items.size();}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{'items':U}) is U
    assert engine.operation_issues=={('unknown_receiver','size'):1}


def test_known_native_map_view_operation_has_a_separate_support_boundary(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {Object entry(){Map map=new HashMap();map.put("key","value");return map.keySet().spliterator();}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{}) is U
    assert engine.operation_issues=={('unsupported_map_view_operation','spliterator'):1}
