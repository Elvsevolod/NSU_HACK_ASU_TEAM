import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


@pytest.mark.parametrize('copy',['Map left=new HashMap(original);','Map left=new HashMap();left.putAll(original);'])
def test_copy_preserves_the_boxed_character_class_of_a_value(tmp_path,copy):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{Object entry(){
      Map original=new HashMap();original.put("key",'x');'''+copy+'''
      Map right=new HashMap();right.put("key","x");return left.equals(right);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{}) is False


def test_java_integer_and_long_values_are_not_equal_even_when_payloads_match(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{Object entry(){
      Map left=new HashMap();left.put("key",1);Map right=new HashMap();right.put("key",1L);return left.equals(right);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{}) is False


def test_erased_value_class_remains_unknown_instead_of_guessing_integer(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{Object entry(Object input){
      Map left=new HashMap();left.put("key",input);Map right=new HashMap();right.put("key",1);return left.equals(right);}}'''})
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Api.entry'],{'input':1}) is U
    assert engine.approximate


def test_http_generic_value_descriptor_controls_receiver_boxing(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import org.springframework.web.client.RestTemplate;
      import org.springframework.core.ParameterizedTypeReference;import org.springframework.http.HttpMethod;
      class Server{@GetMapping("/one") Map one(){Map map=new HashMap();map.put("key",1);return map;}}
      class Client{RestTemplate rest;Object entry(){Map<String,Long> response=rest.exchange("http://service/one",HttpMethod.GET,
      null,new ParameterizedTypeReference<Map<String,Long>>(){}).getBody();Map expected=new HashMap();expected.put("key",1L);
      return expected.equals(response);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Client.entry'],{}) is True
