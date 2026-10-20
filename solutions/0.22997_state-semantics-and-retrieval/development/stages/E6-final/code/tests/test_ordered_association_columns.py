import json
import pytest
from analyzer.engine import Engine
from analyzer.project import Project
from analyzer.state import ScenarioState,U
from builders import build


def profile(tmp_path,column='codes_order',positions=(1,0),ordered=True):
    source='''import java.util.*;import jakarta.persistence.*;import org.springframework.data.jpa.repository.JpaRepository;
      @Entity @Table(name="items")class Item{@Id String id;
        @ElementCollection @CollectionTable(name="item_codes",joinColumns=@JoinColumn(name="item_id")) ORDER List<String> codes;}
      interface Store extends JpaRepository<Item,String>{Optional<Item> findById(String id);}
      class Api {Store store;Object entry(){List<String> codes=store.findById("box").orElseThrow().codes;codes.size();return codes;}}'''.replace('ORDER','@OrderColumn' if ordered else '')
    p,db,ids=build(tmp_path,{'Api.java':source},rows={'items':[{'id':'box'}],
      'item_codes':[{'item_id':'box','codes':'B',column:positions[0]},{'item_id':'box','codes':'A',column:positions[1]}]})
    skeleton=p.skeleton;skeleton['nodes']['res:table:service.item_codes']={'kind':'data_resource','name':'item_codes','module':'service','schema':'service','collection_of':'type:service:Item','origin':[{'file':'Api.java','line':4}]}
    (tmp_path/'skeleton.json').write_text(json.dumps(skeleton));p=Project(tmp_path/'skeleton.json',tmp_path)
    return p,db,ids


@pytest.mark.parametrize('column',['codes_order','codes_ORDER','CODES_ORDER'])
def test_default_jpa_order_column_uses_declared_sql_identifier_case_insensitively(tmp_path,column):
    p,db,ids=profile(tmp_path,column=column);e=Engine(p,ScenarioState(db));r=e.run(ids['Api.entry'],{})
    assert list(r)==['A','B'] and not r.opaque,(r,e.warnings)
    assert r.kinds==['String','String'] and r.order_known


@pytest.mark.parametrize('positions',[(0,0),(0,2),(-1,0)])
def test_invalid_positions_do_not_become_a_known_order(tmp_path,positions):
    p,db,ids=profile(tmp_path,positions=positions);e=Engine(p,ScenarioState(db));r=e.run(ids['Api.entry'],{})
    assert r is U or getattr(r,'opaque',False)


def test_unordered_association_retains_unknown_encounter_order(tmp_path):
    p,db,ids=profile(tmp_path,ordered=False);e=Engine(p,ScenarioState(db));r=e.run(ids['Api.entry'],{})
    assert len(r)==2 and r.order_known is False
