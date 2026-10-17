from analyzer.engine import Engine
from analyzer.state import ScenarioState
from builders import build


def test_hibernate_uuid_generator_format_is_derived_from_source_declaration(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''@Entity @Table(name="items")
      @GenericGenerator(name="parcel-identities",strategy="org.hibernate.id.UUIDGenerator")
      class Item {@Id @GeneratedValue(generator="parcel-identities") String id;}
      interface Store extends JpaRepository<Item,String>{Item save(Item row);}
      class Api {@Autowired Store store;Item entry(){Item row=new Item();store.save(row);return row;}}'''
      },rows={'items':[]})
    result=Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})
    assert result['id']['__type__']=='String'
    assert result['id']['__uuid_text__'] is True and result['id']['__length__']==36


def test_arbitrary_string_generator_is_not_assumed_to_make_uuids(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''@Entity @Table(name="items")
      @GenericGenerator(name="sequence",strategy="example.CustomGenerator")
      class Item {@Id @GeneratedValue(generator="sequence") String id;}
      interface Store extends JpaRepository<Item,String>{Item save(Item row);}
      class Api {@Autowired Store store;Item entry(){Item row=new Item();store.save(row);return row;}}'''
      },rows={'items':[]})
    result=Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})
    assert '__uuid_text__' not in result['id'] and '__length__' not in result['id']
