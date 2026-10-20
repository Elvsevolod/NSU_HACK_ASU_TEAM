from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def test_a_json_string_property_is_not_a_map_of_its_internal_representation(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      import com.fasterxml.jackson.databind.ObjectMapper;import org.springframework.web.client.RestTemplate;
      class Envelope {public String encoded;}
      class Api {@GetMapping("/item") Envelope item(){Envelope result=new Envelope();
        Map map=new HashMap();map.put("mode","known");result.encoded=new ObjectMapper().writeValueAsString(map);return result;}}
      class Caller {RestTemplate rest;String entry(){Map result=(Map)rest.getForObject("http://service/item",Object.class);
        Object encoded=result.get("encoded");try{Map value=(Map)encoded;return wrong();}
        catch(ClassCastException failure){return "rejected";}}String wrong(){return "wrong";}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='rejected'
    assert ids['Caller.wrong'] not in {target for _,kind,target in engine.edges if kind=='executes'}


def test_source_exception_runtime_type_is_not_a_business_field(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Failure extends RuntimeException {
        public String __type__="IllegalArgumentException";}
      class Api {String entry(){try{throw new Failure();}
        catch(IllegalArgumentException failure){return wrong();}
        catch(Failure failure){return "rejected";}}String wrong(){return "wrong";}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})=='rejected'
    assert ids['Api.wrong'] not in {target for _,kind,target in engine.edges if kind=='executes'}


def test_unknown_json_property_cannot_supply_a_differently_cased_java_field(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      import com.fasterxml.jackson.databind.ObjectMapper;
      class Item {public String id;}
      class Api {String entry(){Map input=new HashMap();input.put("ID","wrong-known");
        ObjectMapper mapper=new ObjectMapper();String text=mapper.writeValueAsString(input);
        Item result=mapper.readValue(text,Item.class);return result.id;}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{}) is U
    assert not engine.approximate
    assert engine.outcome=='uncaught application exception'
    assert any('com.fasterxml.jackson.databind.JsonMappingException' in warning for warning in engine.warnings)


def test_an_enum_business_field_does_not_forge_its_runtime_class(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''enum Stage {READY("business");
        private String __type__;Stage(String value){this.__type__=value;}}
      class Api {Object entry(){return Stage.READY.getClass();}}'''})
    engine=Engine(project,ScenarioState(db),conservative=True)
    assert engine.run(ids['Api.entry'],{}) is U
    assert engine.approximate and engine.warnings
