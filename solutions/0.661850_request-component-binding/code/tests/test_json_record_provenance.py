from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def test_a_source_dto_requested_as_object_exposes_only_actual_json_fields(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;import java.util.*;
      class Item {public String id="known";}
      class Api {@GetMapping("/item") Item item(){return new Item();}}
      class Caller {RestTemplate rest;String entry(){Map result=(Map)
        rest.getForObject("http://service/item",Object.class);
        if(result.containsKey("__type__")||result.containsKey("__http_entity__")){return "fake-field";}
        return (String)result.get("id");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='known'


def test_an_orm_record_requested_as_object_has_the_same_data_boundary(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;import java.util.*;
      class Api {Store store;@GetMapping("/item") Item item(){return store.findById("known").get();}}
      @Entity @Table(name="items") class Item {@Id public String id;}
      interface Store extends JpaRepository<Item,String>{}
      class Caller {RestTemplate rest;String entry(){Map result=(Map)
        rest.getForObject("http://service/item",Object.class);return (String)result.get("id");}}'''},rows={'items':[{'id':'known'}]})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='known'


def test_real_business_fields_cannot_be_mistaken_for_response_or_json_metadata(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;import java.util.*;
      class Item {public String __type__="business-type";public String __json__="business-json";public String body="business-body";}
      class Api {@GetMapping("/item") Item item(){return new Item();}}
      class Caller {RestTemplate rest;String entry(){Map result=(Map)
        rest.getForObject("http://service/item",Object.class);
        return result.get("__type__")+"/"+result.get("__json__")+"/"+result.get("body");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='business-type/business-json/business-body'


def test_typed_json_roundtrip_restores_a_dto_map_property(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      import com.fasterxml.jackson.databind.ObjectMapper;
      class Envelope {public Map<String,String> payload;}
      class Api {String entry(){Envelope value=new Envelope();value.payload=new HashMap();
        value.payload.put("mode","ready");ObjectMapper mapper=new ObjectMapper();
        String text=mapper.writeValueAsString(value);
        Envelope decoded=mapper.readValue(text,Envelope.class);return decoded.payload.get("mode");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='ready'


def test_a_json_source_schema_does_not_make_a_raw_map_a_pojo_instance(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;class Item {public String id="known";}
      class Api {@GetMapping("/item") Item item(){return new Item();}}
      class Caller {RestTemplate rest;String entry(){try{Object data=
        rest.getForObject("http://service/item",Object.class);Item item=(Item)data;
        return after(item);}catch(ClassCastException failure){return "rejected";}}
        String after(Item item){return "wrong";}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='rejected'
    assert ids['Caller.after'] not in {target for _,kind,target in engine.edges if kind=='executes'}
