from analyzer.engine import Engine
from analyzer.state import ScenarioState
from builders import build


def test_source_enum_string_field_keeps_its_declared_kind_in_key_construction(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      enum Code{REVIEW("R",1);private String label;private int code;
        Code(String input,int value){this.label=input;this.code=value;}String label(){return label;}}
      class Key{String value(){return Code.REVIEW.label()+"7";}}
      class Api{String entry(){Key key=new Key();Map<String,String> items=new HashMap<>();
        items.put(key.value(),"found");return items.get("R7");}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})=='found' and not engine.approximate
