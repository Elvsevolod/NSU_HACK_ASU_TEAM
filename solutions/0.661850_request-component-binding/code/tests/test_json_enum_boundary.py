import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def test_a_default_enum_response_is_its_constant_name_not_its_fields(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;enum Stage {READY("display");
        private String name;Stage(String name){this.name=name;}}
      class Api {@GetMapping("/stage") Stage stage(){return Stage.READY;}}
      class Caller {RestTemplate rest;String entry(){return (String)rest.getForObject("http://service/stage",Object.class);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='READY'


def test_typed_http_enum_field_roundtrips_without_changing_its_constant(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;enum Stage {READY,WAITING;}
      class Envelope {public Stage stage;}
      class Api {@PostMapping("/stage") Envelope stage(@RequestBody Envelope input){return input;}}
      class Caller {RestTemplate rest;String entry(){Envelope input=new Envelope();input.stage=Stage.READY;
        Envelope output=rest.postForObject("http://service/stage",input,Envelope.class);
        if(output.stage==Stage.READY){return accepted();}return rejected();}
        String accepted(){return "accepted";}String rejected(){return "wrong";}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='accepted'
    assert ids['Caller.rejected'] not in {target for _,kind,target in engine.edges if kind=='executes'}


@pytest.mark.parametrize('custom',[
    '@JsonFormat(shape=JsonFormat.Shape.OBJECT) enum Stage {READY;}',
    'enum Stage {READY;@JsonValue String code(){return "custom";}}',
    'enum Stage {@JsonProperty("custom") READY;}',
])
def test_a_custom_enum_json_representation_stays_explicitly_unresolved(tmp_path,custom):
    project,db,ids=build(tmp_path,{'Api.java':("import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;"+(custom+'''
      class Api {@GetMapping("/stage") Stage stage(){return Stage.READY;}}
      class Caller {RestTemplate rest;Object entry(){return rest.getForObject("http://service/stage",Object.class);}}'''))})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{}) is U
    assert engine.approximate and any('enum JSON' in warning for warning in engine.warnings)


def test_an_ordinary_json_enum_field_does_not_forge_an_enum_value(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;import java.util.*;
      class Data {public String __enum__="Stage.READY";}
      class Api {@GetMapping("/stage") Data stage(){return new Data();}}
      class Caller {RestTemplate rest;String entry(){Map data=(Map)
        rest.getForObject("http://service/stage",Object.class);return (String)data.get("__enum__");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='Stage.READY'


def test_an_enum_response_requested_as_text_can_be_parsed_back_as_json(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;import com.fasterxml.jackson.databind.ObjectMapper;
      enum Stage {READY;}
      class Api {@GetMapping("/stage") Stage stage(){return Stage.READY;}}
      class Caller {RestTemplate rest;String entry(){String text=
        rest.getForObject("http://service/stage",String.class);ObjectMapper mapper=new ObjectMapper();
        return mapper.readValue(text,Stage.class).name();}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='READY'


def test_enum_identity_and_switch_are_not_controlled_by_an_ordinary_field(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''enum Stage {FIRST("same"),SECOND("same");
        private String __enum__;Stage(String value){this.__enum__=value;}}
      class Api {String entry(){if(Stage.FIRST.equals(Stage.SECOND)){return "wrong";}
        Stage stage=Stage.SECOND;switch(stage){case FIRST:return "wrong";
          case SECOND:return "accepted";default:return "wrong";}}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='accepted'
