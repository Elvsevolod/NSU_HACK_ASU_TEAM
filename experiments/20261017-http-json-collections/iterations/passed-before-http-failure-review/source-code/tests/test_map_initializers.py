import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def test_native_map_instance_initializer_preserves_entries_and_captured_values(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {String entry(){String captured="known";
        Map result=new HashMap(){{put("mode",captured);put(7,"integer");}};
        if("known".equals(result.get("mode"))){return accepted();}return rejected();}
        String accepted(){return "accepted";}String rejected(){return "wrong";}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})=='accepted'
    assert ids['Api.rejected'] not in {target for _,kind,target in engine.edges if kind=='executes'}
    assert not engine.warnings


def test_initializer_put_does_not_call_an_enclosing_namesake(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {String entry(){Map result=new HashMap(){{put("mode","known");}};
        return (String)result.get("mode");}
        Object put(String key,String value){return "wrong";}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})=='known'
    assert ids['Api.put'] not in {target for _,kind,target in engine.edges if kind=='executes'}


@pytest.mark.parametrize('body',[
    '{{put("mode","before");}public Object get(Object key){return "after";}}',
    '{{put("mode",helper());}}',
])
def test_unsupported_subclass_or_implicit_outer_scope_stays_unknown(tmp_path,body):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {Object entry(){return new HashMap()'''+body+''';}
        String helper(){return "opaque";}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{}) is U
    assert any('anonymous class' in warning for warning in engine.warnings)


def test_super_constructor_failure_prevents_initializer_argument_calls(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {String entry(){Api outer=this;try{
        new HashMap(-1){{put("mode",outer.next());}};return "wrong";
        }catch(IllegalArgumentException failure){return "rejected";}}
        String next(){return "wrong";}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})=='rejected'
    assert ids['Api.next'] not in {target for _,kind,target in engine.edges if kind=='executes'}
