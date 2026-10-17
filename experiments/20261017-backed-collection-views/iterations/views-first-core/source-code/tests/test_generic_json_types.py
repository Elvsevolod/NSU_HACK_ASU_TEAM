from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build
from analyzer.project import Project
import json


def test_parameterized_http_response_keeps_nested_source_types(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      import org.springframework.web.client.RestTemplate;
      import org.springframework.core.ParameterizedTypeReference;
      import org.springframework.http.HttpMethod;
      class Item {public String id="known";}
      class Box<T> {public T payload;}
      class Api {@GetMapping("/item") Box item(){Box value=new Box();
        value.payload=Arrays.asList(new Item());return value;}}
      class Caller {RestTemplate rest;String entry(){Box<List<Item>> value=rest.exchange(
        "http://service/item",HttpMethod.GET,null,new ParameterizedTypeReference<Box<List<Item>>>(){}).getBody();
        return value.payload.get(0).id;}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='known'
    assert not engine.warnings


def test_a_typed_response_map_key_variable_uses_its_declared_argument(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      import org.springframework.web.client.RestTemplate;
      import org.springframework.core.ParameterizedTypeReference;
      import org.springframework.http.HttpMethod;
      class Item {public String id="known";}
      class Box<K,V> {public Map<K,V> payload;}
      class Api {@GetMapping("/item") Box item(){Box value=new Box();Map data=new HashMap();
        data.put("one",new Item());value.payload=data;return value;}}
      class Caller {RestTemplate rest;String entry(){Box<String,Item> value=rest.exchange(
        "http://service/item",HttpMethod.GET,null,new ParameterizedTypeReference<Box<String,Item>>(){}).getBody();
        return value.payload.get("one").id;}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='known'


def test_jackson_type_factory_supplies_a_parametric_read_value_type(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      import com.fasterxml.jackson.databind.ObjectMapper;
      class Item {public String id="known";}
      class Box<T> {public T payload;}
      class Api {String entry(){Box source=new Box();source.payload=new Item();ObjectMapper mapper=new ObjectMapper();
        String text=mapper.writeValueAsString(source);
        Box<Item> value=mapper.readValue(text,mapper.getTypeFactory().constructParametricType(Box.class,Item.class));
        return value.payload.id;}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='known'


def test_jackson_type_reference_is_an_owned_type_description(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      import com.fasterxml.jackson.databind.ObjectMapper;
      import com.fasterxml.jackson.core.type.TypeReference;
      class Item {public String id="known";}
      class Api {String entry(){ObjectMapper mapper=new ObjectMapper();
        String text=mapper.writeValueAsString(Arrays.asList(new Item()));
        List<Item> value=mapper.readValue(text,new TypeReference<List<Item>>(){});return value.get(0).id;}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='known'


def test_foreign_type_reference_namesake_is_not_a_native_type_token(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import external.library.TypeReference;
      class Api {Object entry(){return new TypeReference<String>(){};}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{}) is U
    assert any('anonymous class' in warning for warning in engine.warnings)


def test_generic_argument_retains_its_use_site_imports(tmp_path):
    project,db,ids=build(tmp_path,{
      'Box.java':'package schemas;public class Box<T> {public T payload;}',
      'Map.java':'package schemas;public class Map {}',
      'Api.java':'''package server;import schemas.Box;
        class Api {@GetMapping("/item") Box item(){Box result=new Box();
          java.util.Map data=new java.util.HashMap();data.put("mode","known");result.payload=data;return result;}}''',
      'Caller.java':'''package client;import schemas.Box;import java.util.Map;
        import org.springframework.web.client.RestTemplate;import org.springframework.core.ParameterizedTypeReference;
        import org.springframework.http.HttpMethod;
        class Caller {RestTemplate rest;String entry(){Box<Map<String,String>> result=rest.exchange(
          "http://service/item",HttpMethod.GET,null,new ParameterizedTypeReference<Box<Map<String,String>>>(){}).getBody();
          return result.payload.get("mode");}}''',
    })
    skeleton=project.skeleton
    packages={'Box.java':'schemas','Map.java':'schemas','Api.java':'server','Caller.java':'client'}
    for node in skeleton['nodes'].values():
        if node['kind']=='type':node['fqn']=packages[node['file']]+'.'+node['fqn']
    (tmp_path/'skeleton.json').write_text(json.dumps(skeleton))
    project=Project(tmp_path/'skeleton.json',tmp_path)
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='known'
