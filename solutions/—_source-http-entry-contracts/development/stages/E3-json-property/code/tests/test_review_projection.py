from analyzer.engine import Engine
from analyzer.request import Request
from analyzer.state import ScenarioState,U
from builders import build


def test_direct_field_only_source_constructor_is_an_execution(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Visit{String code;Visit(String code){this.code=code;}}
      class Api{String entry(){return new Visit("v1").code;}}'''})
    e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{})=='v1'
    assert ('','executes',ids['Visit.<init>']) in e.edges
    assert (ids['Api.entry'],'calls',ids['Visit.<init>']) in e.edges


def test_orm_reflection_root_is_suppressed_but_its_nested_helper_runs(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{Store store;String entry(){return store.findById("x").name;}}
      @Entity @Table(name="items") class Item{@Id String id;String name;Item(){helper();name="constructor";}void helper(){nested();}void nested(){}}
      interface Store extends JpaRepository<Item,String>{Item findById(String id);}'''},rows={'items':[{'id':'x','name':'persisted'}]})
    e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{})=='persisted'
    assert ('','executes',ids['Item.<init>']) not in e.edges
    assert ('','executes',ids['Item.helper']) in e.edges
    assert (ids['Item.<init>'],'calls',ids['Item.helper']) not in e.edges
    assert (ids['Item.helper'],'calls',ids['Item.nested']) in e.edges
    assert (ids['Api.entry'],'calls',ids['Item.<init>']) not in e.edges


def test_orm_constructor_failure_preserves_select_and_stops_source_continuation(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{Store store;String entry(){store.findById("x");return after();}String after(){return "wrong";}}
      @Entity @Table(name="items") class Item{@Id String id;Item(){throw new RuntimeException();}}
      interface Store extends JpaRepository<Item,String>{Item findById(String id);}'''},rows={'items':[{'id':'x'}]})
    e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{}) is U
    assert (ids['Api.entry'],'data','res:table:service.items') in e.edges
    assert ('','executes',ids['Api.after']) not in e.edges
    assert ('','executes',ids['Item.<init>']) not in e.edges


def test_json_and_orm_use_the_same_reflection_root_rule(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{@PostMapping("/items") String entry(@RequestBody Item input){return input.name;}}
      class Item{public String name;public Item(){helper();}void helper(){nested();}void nested(){}}'''})
    e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],Request.http('service','POST','/items',body={'name':'wire'}))=='wire'
    assert ('','executes',ids['Item.<init>']) not in e.edges
    assert ('','executes',ids['Item.helper']) in e.edges
    assert (ids['Item.<init>'],'calls',ids['Item.helper']) not in e.edges
    assert (ids['Item.helper'],'calls',ids['Item.nested']) in e.edges


def test_json_source_constructor_initializes_fields_in_java_order(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{@PostMapping("/items") int entry(@RequestBody Item input){return input.first;}}
      class Item{public int first=readLater();public int later=9;public Item(){}int readLater(){return later;}}'''})
    e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],Request.http('service','POST','/items',body={}))==0
    assert ('','executes',ids['Item.<init>']) not in e.edges
    assert ('','executes',ids['Item.readLater']) in e.edges
