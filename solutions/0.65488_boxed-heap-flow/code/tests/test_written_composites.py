from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from analyzer.symbolic_text import concat_text
from builders import build


def test_empty_string_concatenation_preserves_the_symbolic_string_value():
    value={'__symbol__':'opaque-uuid','__type__':'String','__length__':36,'__uuid_text__':True}
    assert concat_text(value,'')==value
    assert concat_text('',value)==value
    assert concat_text(concat_text('',value),'')==value
    assert concat_text(value,'') is not value


def test_symbolic_string_length_counts_utf16_literal_units():
    value={'__symbol__':'opaque-uuid','__type__':'String','__length__':36,'__uuid_text__':True}
    assert concat_text('😀',value)['__length__']==38


def test_written_embedded_value_survives_later_repository_materialization(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''@Embeddable class Code {String prefix;int serial;}
      @Entity @Table(name="items") class Item {@Id String id;@Embedded Code code;}
      interface Store extends JpaRepository<Item,String>{Item save(Item row);Item findByCode(Code code);}
      class Api {@Autowired Store store;Item entry(){Code code=new Code();code.prefix="A";code.serial=7;
        Item row=new Item();row.id="one";row.code=code;store.save(row);return store.findByCode(code);}}'''
      },rows={'items':[]})
    result=Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})
    assert result is not U and result['code']['prefix']=='A' and result['code']['serial']==7


def test_written_element_collection_is_not_replaced_by_old_empty_join_table(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;@Entity @Table(name="items") class Item {@Id String id;
      @ElementCollection @CollectionTable(name="tags",joinColumns=@JoinColumn(name="item_id")) List<String> tags;}
      interface Store extends JpaRepository<Item,String>{Item save(Item row);Item findById(String id);}
      class Api {@Autowired Store store;Item entry(){Item row=new Item();row.id="one";
        row.tags=new ArrayList<>();row.tags.add("new");store.save(row);return store.findById("one");}}'''
      },rows={'items':[],'tags':[]})
    result=Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})
    assert result is not U and result['tags']==['new']
