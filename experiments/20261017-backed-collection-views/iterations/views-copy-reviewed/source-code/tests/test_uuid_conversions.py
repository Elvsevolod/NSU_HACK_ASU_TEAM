from analyzer.engine import Engine
from analyzer.state import ScenarioState
from builders import build


def test_uuid_parse_is_not_string_identity_and_round_trip_keeps_the_value(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.UUID;class Api {boolean entry(){
      String text="00000000-0000-0000-0000-000000000001";
      UUID value=UUID.fromString(text);return !value.equals(text)&&value.toString().equals(text);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{}) is True


def test_symbolic_uuid_round_trip_preserves_the_same_generated_identity(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.UUID;class Api {boolean entry(){UUID id=UUID.randomUUID();
      String text=id.toString();return UUID.fromString(text).equals(id)&&UUID.fromString(text).toString().equals(text);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{}) is True


def test_invalid_uuid_text_throws_before_following_calls(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.UUID;class Api {void entry(){UUID.fromString("invalid");after();}void after(){}}'''})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert engine.outcome=='uncaught application exception'
    assert ids['Api.after'] not in {t for _,r,t in engine.edges if r=='calls'}


def test_native_uuid_path_parameter_is_converted_back_to_its_text_value(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'import java.util.UUID;class Api {String entry(UUID id){return id.toString();}}'})
    value='00000000-0000-0000-0000-000000000001'
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{'id':value})==value
