from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def test_uuid_dto_property_survives_http_as_a_uuid_value(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.UUID;
      import org.springframework.web.client.RestTemplate;
      class Item {public UUID id;}
      class Api {@GetMapping("/item") Item item(){Item value=new Item();
        value.id=UUID.fromString("00000000-0000-0000-0000-000000000001");return value;}}
      class Caller {RestTemplate rest;String entry(){Item value=rest.getForObject("http://service/item",Item.class);
        return value.id.toString();}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='00000000-0000-0000-0000-000000000001'


def test_a_generated_uuid_keeps_identity_after_a_json_request_response_roundtrip(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.UUID;
      import org.springframework.web.client.RestTemplate;
      class Item {public UUID id;}
      class Api {@PostMapping("/item") Item item(@RequestBody Item value){return value;}}
      class Caller {RestTemplate rest;boolean entry(){Item input=new Item();input.id=UUID.randomUUID();
        Item result=rest.postForObject("http://service/item",input,Item.class);
        return result.id.equals(input.id);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{}) is True


def test_untyped_json_uuid_is_text_not_a_map_of_internal_fields(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.UUID;import java.util.Map;
      import org.springframework.web.client.RestTemplate;
      class Item {public UUID id;}
      class Api {@GetMapping("/item") Item item(){Item value=new Item();value.id=UUID.randomUUID();return value;}}
      class Caller {RestTemplate rest;int entry(){Map value=(Map)rest.getForObject("http://service/item",Object.class);
        return ((String)value.get("id")).length();}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})==36


def test_a_source_dto_named_uuid_does_not_become_a_jdk_uuid(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.Map;
      import org.springframework.web.client.RestTemplate;
      class UUID {public String id="known";}
      class Api {@GetMapping("/item") UUID item(){return new UUID();}}
      class Caller {RestTemplate rest;String entry(){Map value=(Map)
        rest.getForObject("http://service/item",Object.class);return (String)value.get("id");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='known'


def test_a_foreign_uuid_factory_is_not_replaced_by_the_jdk_model(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import external.library.UUID;
      class Api {Object entry(){return UUID.randomUUID();}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{}) is U
    assert engine.approximate and engine.warnings
