import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState
from builders import build


@pytest.mark.parametrize('statement',[
 '{int key=1;}',
 'if(true){int key=1;}',
 'for(int key=0;key<2;key++){}',
 'try{throw new IllegalStateException();}catch(IllegalStateException key){}',
 'switch(1){case 1:{int key=1;break;}default:break;}',
])
def test_local_bindings_stop_shadowing_a_field_after_leaving_their_scope(tmp_path,statement):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api {String key="outer";
      Object inspect(){'''+statement+'''Map map=new HashMap();map.put(key,"found");return map.get("outer");}}
      class Start{Object entry(){return new Api().inspect();}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Start.entry'],{})=='found'


def test_block_scope_retains_assignments_to_outer_locals_and_object_side_effects(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api {Object entry(){
      String answer="old";Map map=new HashMap();{int temporary=1;answer="new";map.put("key","value");}
      return answer+map.get("key");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='newvalue'


def test_typed_callback_does_not_change_an_enclosing_field_type_or_value(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import java.util.stream.Collectors;
      class Api {String key="outer";Object inspect(){Map map=new HashMap();Arrays.asList(1).stream()
      .map((Integer key)->{map.put(key,"inner");return key;}).collect(Collectors.toList());
      map.put(key,"found");return map.get("outer");}}
      class Start{Object entry(){return new Api().inspect();}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Start.entry'],{})=='found'
