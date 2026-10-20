from analyzer.engine import Engine
from analyzer.state import ScenarioState
from builders import build


def test_business_dto_named_header_is_not_bound_as_http_headers(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class DocumentHeader {String title;}
      class Api {@PostMapping("/receipts") String add(@RequestBody DocumentHeader input){return input.title;}}
      class Caller {RestTemplate rest;String entry(){DocumentHeader input=new DocumentHeader();input.title="Receipt";
        return rest.postForObject("http://service/receipts",input,String.class);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='Receipt'


def test_module_substring_host_resolution_is_an_explicit_approximation(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {@GetMapping("/items") String list(){return "ok";}}
      class Caller {RestTemplate rest;String entry(){return rest.getForObject("http://catalog/items",String.class);}}'''
      },module='catalog-service')
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Caller.entry'],{})=='ok'
    assert engine.approximate and any('host' in warning and 'heuristic' in warning for warning in engine.warnings)
