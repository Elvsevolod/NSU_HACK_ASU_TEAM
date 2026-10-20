from analyzer.engine import Engine
from analyzer.request import Request
from analyzer.state import ScenarioState,U
from builders import build


def test_basic_record_uses_its_component_creator_and_generated_accessor(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''record Input(String code,int count){}
      class Api{@PostMapping("/items") String entry(@RequestBody Input input){return input.code()+input.count();}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],Request.http('service','POST','/items',body={'code':'x','count':3}))=='x3'
    assert {target for _,relation,target in engine.edges if relation=='executes'}=={ids['Api.entry']}


def test_single_component_record_uses_object_properties(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''record Input(String code){}
      class Api{@PostMapping("/items") String entry(@RequestBody Input input){return input.code();}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],Request.http('service','POST','/items',body={'code':'x'}))=='x'


def test_record_custom_accessor_is_not_silently_replaced_with_a_field_read(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''record Input(String code){public String code(){return "changed";}}
      class Api{@PostMapping("/items") String entry(@RequestBody Input input){return input.code();}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],Request.http('service','POST','/items',body={'code':'x'})) == 'changed'
    assert ('','executes',ids['Input.code']) in engine.edges
    assert ('','executes',ids['Api.entry']) not in engine.confirmed_edges
    assert any('record custom component accessor' in warning for warning in engine.warnings)
