import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


@pytest.mark.parametrize('expression',[
 'rest.getForObject("http://service/items/{key}",String.class,"one")',
 'rest.postForObject("http://service/items/{key}","payload",String.class,"one")',
 'rest.exchange("http://service/items/{key}",HttpMethod.GET,null,String.class,"one").getBody()'])
def test_http_uri_variables_follow_the_client_overload_not_the_request_body(tmp_path,expression):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;class Api {
      @GetMapping("/items/{key}") String read(@PathVariable String key){return key;}
      @PostMapping("/items/{key}") String write(@PathVariable String key,@RequestBody String body){return key;}}
      class Caller {RestTemplate rest;String entry(){return '''+expression+''';}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='one'


def test_named_uri_variables_use_the_map_keys(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;import java.util.*;class Api {
      @GetMapping("/items/{key}") String read(@PathVariable String key){return key;}}
      class Caller {RestTemplate rest;String entry(){Map<String,String> vars=new HashMap<>();vars.put("key","two");
        return rest.getForObject("http://service/items/{key}",String.class,vars);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='two'


def test_unexpanded_uri_template_is_never_passed_as_a_known_identifier(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;class Api {
      @GetMapping("/items/{key}") String read(@PathVariable String key){return key;}}
      class Caller {RestTemplate rest;String entry(){return rest.getForObject("http://service/items/{key}",String.class);}}'''})
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Caller.entry'],{}) is U
    assert engine.outcome=='uncaught application exception'
    assert any('IllegalArgumentException' in warning for warning in engine.warnings)
    assert ('','executes',ids['Api.read']) not in engine.edges
