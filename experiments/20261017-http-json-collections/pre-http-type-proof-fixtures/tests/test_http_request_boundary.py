from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def test_remote_request_map_is_copied_across_the_wire(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {@PostMapping("/update") String update(@RequestBody Map<String,String> input){
        input.put("mode","changed");return input.get("mode");}}
      class Caller {RestTemplate rest;String entry(){Map<String,String> input=new HashMap();
        input.put("mode","original");rest.postForObject("http://service/update",input,String.class);
        return input.get("mode");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='original'


def test_nested_object_request_property_binds_to_a_java_map(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Item {public String id="known";}
      class Envelope {public Object payload;}
      class Api {@PostMapping("/read") String read(@RequestBody Envelope input){
        return (String)((Map)input.payload).get("id");}}
      class Caller {RestTemplate rest;String entry(){Envelope input=new Envelope();
        input.payload=new Item();return rest.postForObject("http://service/read",input,String.class);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='known'


def test_nested_request_property_does_not_keep_the_senders_concrete_subclass(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Base {
        public String id;String label(){return "base";}}
      class Derived extends Base {String label(){return "derived";}}
      class Envelope {public Base payload;}
      class Api {@PostMapping("/read") String read(@RequestBody Envelope input){return input.payload.label();}}
      class Caller {RestTemplate rest;String entry(){Envelope input=new Envelope();input.payload=new Derived();
        return rest.postForObject("http://service/read",input,String.class);}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='base'
    assert ids['Derived.label'] not in {target for _,kind,target in engine.edges if kind=='executes'}


def test_a_declared_map_inside_a_request_dto_retains_typed_values(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Item {public String id="known";String label(){return id;}}
      class Envelope {public Map<String,Item> payload;}
      class Api {@PostMapping("/read") String read(@RequestBody Envelope input){return input.payload.get("one").label();}}
      class Caller {RestTemplate rest;String entry(){Envelope input=new Envelope();input.payload=new HashMap();
        input.payload.put("one",new Item());return rest.postForObject("http://service/read",input,String.class);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='known'


def test_cyclic_request_serialization_stops_before_the_receiving_handler(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {@PostMapping("/read") String read(){return "wrong";}}
      class Caller {RestTemplate rest;String entry(){Map input=new HashMap();input.put("self",input);
        try{return rest.postForObject("http://service/read",input,String.class);}
        catch(HttpMessageNotWritableException failure){return "rejected";}}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='rejected'
    assert ids['Api.read'] not in {target for _,kind,target in engine.edges if kind=='executes'}
    assert any('request serialization failed' in warning for warning in engine.warnings)


def test_a_json_object_sent_to_a_text_parameter_keeps_the_serialized_text_boundary(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      import com.fasterxml.jackson.databind.ObjectMapper;
      class Api {@PostMapping("/read") String read(@RequestBody String text){
        ObjectMapper mapper=new ObjectMapper();Map result=mapper.readValue(text,Map.class);
        return (String)result.get("mode");}}
      class Caller {RestTemplate rest;String entry(){Map input=new HashMap();input.put("mode","ready");
        return rest.postForObject("http://service/read",input,String.class);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='ready'


def test_an_opaque_request_dto_does_not_turn_into_default_field_values(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Envelope {public boolean enabled;}
      class Api {@PostMapping("/read") boolean read(@RequestBody Envelope input){return input.enabled;}}'''})
    engine=Engine(project,ScenarioState(db))
    value=engine.run(ids['Api.read'],{'input':{'__symbol__':'external-input','__type__':'Envelope'}})
    assert value is U and engine.approximate
    assert any('opaque HTTP value' in warning for warning in engine.warnings)
