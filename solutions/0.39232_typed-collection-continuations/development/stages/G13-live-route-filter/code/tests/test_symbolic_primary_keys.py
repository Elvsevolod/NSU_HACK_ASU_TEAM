from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def test_exact_opaque_primary_key_is_not_lost_among_other_distinct_rows(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''@Entity @Table(name="items") class Item {@Id String id;String name;}
      interface Store extends JpaRepository<Item,String>{Item findById(String id);}
      class Api {@Autowired Store store;Item entry(String id){return store.findById(id);}}'''
      },rows={'items':[{'id':'existing','name':'old'}]})
    state=ScenarioState(db)
    key={'__symbol__':'opaque-id','__type__':'String','__constraints__':['non_null']}
    state.database.tables[('service','items')].append({'id':key,'name':'new'})
    result=Engine(project,state).run(ids['Api.entry'],{'id':key})
    assert result is not U and result['name']=='new'


def test_nonunique_field_does_not_inherit_primary_key_uniqueness(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''@Entity @Table(name="items") class Item {@Id String id;String category;}
      interface Store extends JpaRepository<Item,String>{List<Item> findByCategory(String category);}
      class Api {@Autowired Store store;List<Item> entry(String category){return store.findByCategory(category);}}'''
      },rows={'items':[{'id':'existing','category':'old'}]})
    state=ScenarioState(db);key={'__symbol__':'category','__type__':'String'}
    state.database.tables[('service','items')].append({'id':'new','category':key})
    assert Engine(project,state).run(ids['Api.entry'],{'category':key}) is U


def test_false_conjunct_proves_an_empty_query_even_with_another_unknown_input(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''@Entity @Table(name="items") class Item {@Id String id;String owner;String category;}
      interface Store extends JpaRepository<Item,String>{List<Item> findByOwnerAndCategory(String owner,String category);}
      class Api {@Autowired Store store;List<Item> entry(String category){return store.findByOwnerAndCategory("missing",category);}}'''
      },rows={'items':[{'id':'existing','owner':'someone','category':'old'}]})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==[]
