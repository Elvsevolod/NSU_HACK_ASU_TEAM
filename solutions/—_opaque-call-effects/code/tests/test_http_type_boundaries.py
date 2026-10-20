from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def test_business_dto_named_header_is_not_bound_as_http_headers(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;class DocumentHeader {String title;}
      class Api {@PostMapping("/receipts") String add(@RequestBody DocumentHeader input){return input.title;}}
      class Caller {RestTemplate rest;String entry(){DocumentHeader input=new DocumentHeader();input.title="Receipt";
        return rest.postForObject("http://service/receipts",input,String.class);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='Receipt'


def test_module_substring_host_resolution_is_an_explicit_approximation(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;class Api {@GetMapping("/items") String list(){return "ok";}}
      class Caller {RestTemplate rest;String entry(){return rest.getForObject("http://catalog/items",String.class);}}'''
      },module='catalog-service')
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Caller.entry'],{})=='ok'
    assert engine.approximate and any('host' in warning and 'heuristic' in warning for warning in engine.warnings)


def test_a_source_class_named_rest_template_keeps_its_ordinary_method(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class RestTemplate {
        String getForObject(String url,Class type){return "local";}}
      class Api {@GetMapping("/items") String list(){return "wrong";}}
      class Caller {String entry(){RestTemplate rest=new RestTemplate();
        return rest.getForObject("http://service/items",String.class);}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='local'
    assert ids['Api.list'] not in {target for _,kind,target in engine.edges if kind=='executes'}
    assert (ids['Caller.entry'],'calls',ids['RestTemplate.getForObject']) in engine.edges


def test_an_unresolved_foreign_namesake_does_not_create_an_http_request(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import external.library.RestTemplate;
      class Api {@GetMapping("/items") String list(){return "wrong";}}
      class Caller {RestTemplate rest;String entry(){
        return rest.getForObject("http://service/items",String.class);}}'''})
    engine=Engine(project,ScenarioState(db),conservative=True)
    assert engine.run(ids['Caller.entry'],{}) is U
    assert ids['Api.list'] not in {target for _,kind,target in engine.edges if kind=='executes'}
    assert engine.approximate and engine.warnings
