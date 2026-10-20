from analyzer.engine import Engine
from analyzer.state import ScenarioState
from builders import build


def test_non_field_json_behavior_is_visible_in_diagnostics(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Item {
        private String id="raw";public String getId(){return "formatted";}}
      class Api {@GetMapping("/item") Item item(){return new Item();}}'''})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.item'],{})
    assert engine.approximate
    assert any('JSON DTO field projection' in warning and 'visibility' in warning for warning in engine.warnings)
    assert any('JSON serialize field projection' in warning for warning in engine.warnings)


def test_annotation_string_does_not_drop_an_instance_field_as_static(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Item {
        @SuppressWarnings("private static") public String id="known";}
      class Api {@GetMapping("/item") Item item(){return new Item();}}
      class Caller {RestTemplate rest;String entry(){Item item=
        rest.getForObject("http://service/item",Item.class);return item.id;}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='known'
    assert not engine.warnings


def test_a_generated_builder_result_is_a_source_record_at_the_json_boundary(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      @Builder class Item {public String id;}
      class Api {@GetMapping("/item") Item item(){return Item.builder().id("known").build();}}
      class Caller {RestTemplate rest;String entry(){Map item=(Map)
        rest.getForObject("http://service/item",Object.class);return (String)item.get("id");}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='known'
    assert any('generated JavaBeans' in warning for warning in engine.warnings)


def test_an_ordinary_field_cannot_activate_a_framework_response_model(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Document {
        public String __type__="HttpServletResponse";public int status;
        void setStatus(int status){this.status=status;}int getStatus(){return 37;}}
      class Api {int entry(){Document document=new Document();document.setStatus(418);
        return document.getStatus();}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==37
