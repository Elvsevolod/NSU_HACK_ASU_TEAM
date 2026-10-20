from analyzer.engine import Engine
from analyzer.state import ScenarioState
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
