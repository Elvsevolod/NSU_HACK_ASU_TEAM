"""Null aggregate fields cannot remove existing children or invent cascade writes."""
import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


@pytest.mark.parametrize('identifier,completed',[(2,True),(1,False)])
def test_null_children_save_preserves_other_membership(tmp_path,identifier,completed):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import jakarta.persistence.*;
      import org.springframework.data.jpa.repository.JpaRepository;
      @Entity @Table(name="parents")class Parent{@Id Long id;String name;
        @OneToMany(mappedBy="parent",cascade=CascadeType.ALL)List<Child> children;}
      @Entity @Table(name="children")class Child{@Id Long id;
        @ManyToOne @JoinColumn(name="parent_id")Parent parent;}
      interface Store extends JpaRepository<Parent,Long>{Parent save(Parent item);}
      class Api{Store store;Object entry(Long id){Parent p=new Parent();p.id=id;p.name="new";
        store.save(p);return p.children;}}'''},
      rows={'parents':[{'id':1,'name':'existing'}],'children':[{'id':9,'parent_id':1}]})
    e=Engine(p,ScenarioState(db));value=e.run(ids['Api.entry'],{'id':identifier})
    if completed:
        assert value is None and e.outcome=='returned',(value,e.warnings)
        assert db.rows(p.nodes['res:table:service.children'])==[{'id':9,'parentId':1}]
        assert not any(o.get('resource')=='res:table:service.children' and o.get('datastore_event') for o in e.data_operations)
    else:
        assert value is U and e.outcome=='unsupported_semantics boundary'
        assert any('aggregate membership changed' in warning for warning in e.warnings)
