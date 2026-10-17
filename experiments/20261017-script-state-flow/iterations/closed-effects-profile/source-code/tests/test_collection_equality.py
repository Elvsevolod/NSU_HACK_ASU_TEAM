from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState
from builders import build


def test_collection_uses_source_equals_instead_of_an_assumed_id_key(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Item {String id;String name;
      boolean equals(Object obj){if(this==obj){return true;}if(obj==null){return false;}
        if(getClass()!=obj.getClass()){return false;}Item other=(Item)obj;return name.equals(other.name);}}
      class Api {boolean entry(){Item a=new Item();a.id="one";a.name="same";
        Item b=new Item();b.id="two";b.name="same";
        List<Item> rows=new ArrayList<>();rows.add(a);return rows.contains(b);}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert {o['result'] for o in outcomes}=={True}
    assert all(('', 'executes',ids['Item.equals']) in o['engine'].edges for o in outcomes)
    assert all((ids['Api.entry'],'calls',ids['Item.equals']) not in o['engine'].edges for o in outcomes)


def test_source_equals_callback_can_throw_and_stop_the_caller(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Item {boolean equals(Object obj){throw new IllegalStateException();}}
      class Api {void entry(){List<Item> rows=new ArrayList<>();rows.add(new Item());
        rows.contains(new Item());after();}void after(){}}'''})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert engine.outcome=='uncaught application exception'
    assert ids['Api.after'] not in {t for _,r,t in engine.edges if r=='calls'}


def test_empty_collection_membership_is_false_even_for_an_opaque_uuid(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {boolean entry(){
      List<String> rows=new ArrayList<>();return rows.contains(UUID.randomUUID().toString());}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{}) is False
