from analyzer.engine import Engine
from analyzer.state import ScenarioState
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
