import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


@pytest.mark.parametrize('declaration,field_type',[
    ('class Envelope','Map<String,String>'),('class Envelope','Object'),('class Envelope<T>','T'),
])
def test_declared_or_erased_map_property_is_restored_at_the_client(tmp_path,declaration,field_type):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;import java.util.*;
      '''+declaration+''' {'''+field_type+''' payload;}
      class Api {@GetMapping("/settings") Envelope settings(){Map flags=new HashMap();
        flags.put("mode","ready");Envelope value=new Envelope();value.payload=flags;return value;}}
      class Caller {RestTemplate rest;String entry(){
        Envelope response=rest.getForObject("http://service/settings",Envelope.class);
        return (String)((Map)response.payload).get("mode");}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='ready'


def test_object_class_decodes_untyped_json_objects_as_maps(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;import java.util.*;
      class Api {@GetMapping("/settings") Map settings(){Map flags=new HashMap();
        flags.put("mode","ready");return flags;}}
      class Caller {RestTemplate rest;String entry(){
        Object response=rest.getForObject("http://service/settings",Object.class);
        return (String)((Map)response).get("mode");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='ready'


def test_a_declared_business_object_is_not_unwrapped_by_an_internal_field_name(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;import java.util.*;
      class Detail {String __map__="ordinary";}
      class Envelope {Detail payload;}
      class Api {@GetMapping("/settings") Envelope settings(){Envelope value=new Envelope();
        value.payload=new Detail();return value;}}
      class Caller {RestTemplate rest;String entry(){Envelope response=
        rest.getForObject("http://service/settings",Envelope.class);return response.payload.__map__;}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='ordinary'


@pytest.mark.parametrize('detail',[
    'class Base<T> {T payload;} class Envelope extends Base<String> {}',
    'class Bound {} class Envelope<T extends Bound> {T payload;}',
    '@JsonDeserialize(using=Custom.class) class Envelope {Object payload;}',
])
def test_unsupported_binding_is_diagnosed_instead_of_assuming_an_untyped_map(tmp_path,detail):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;import java.util.*;
      '''+detail+''' class Api {@GetMapping("/settings") Envelope settings(){Map flags=new HashMap();
        flags.put("mode","ready");Envelope value=new Envelope();value.payload=flags;return value;}}
      class Caller {RestTemplate rest;Object entry(){Envelope value=
        rest.getForObject("http://service/settings",Envelope.class);return value.payload;}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{}) is U
    assert engine.approximate and any('JSON binding' in warning or 'property substitution' in warning for warning in engine.warnings)


def test_generic_map_and_list_properties_decode_their_declared_dto_values(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;import java.util.*;
      class Detail {String label="known";String label(){return label;}}
      class Envelope {Map<String,List<Detail>> payload;}
      class Api {@GetMapping("/settings") Envelope settings(){Map flags=new HashMap();
        flags.put("items",Arrays.asList(new Detail()));Envelope value=new Envelope();
        value.payload=flags;return value;}}
      class Caller {RestTemplate rest;String entry(){Envelope response=
        rest.getForObject("http://service/settings",Envelope.class);
        return response.payload.get("items").get(0).label();}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='known'
