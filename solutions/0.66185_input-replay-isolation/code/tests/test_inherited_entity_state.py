from analyzer.engine import Engine
from analyzer.state import ScenarioState, U
from builders import build


def test_inherited_id_column_and_explicit_source_accessors_remain_connected(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Base {
      @Id @Column(name="record_key") protected Integer id;
      Integer getId(){return id;}}
      class Named extends Base {String name;String getName(){return name;}
        void setName(String name){this.name=name;}}
      @Entity @Table(name="categories") class Category extends Named {}
      interface Store extends JpaRepository<Category,Integer>{Category findById(Integer id);Category save(Category row);}
      class Api {@Autowired Store store;String entry(){Category row=store.findById(7);
        row.setName("updated");store.save(row);return row.getName();}}'''},rows={'categories':[{'record_key':7,'name':'old'}]})
    engine=Engine(project,ScenarioState(db));result=engine.run(ids['Api.entry'],{})
    assert result=='updated'
    assert project.id_fields['res:table:service.categories']==['id']
    assert {ids['Named.setName'],ids['Named.getName']}<={t for _,r,t in engine.edges if r=='calls'}
    assert len(engine.state.database.rows(project.nodes['res:table:service.categories']))==1


def test_inherited_generated_identifier_initializes_and_updates_one_record(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Base {@Id @GeneratedValue Integer id;}
      @Entity @Table(name="categories") class Category extends Base {String name;}
      interface Store extends JpaRepository<Category,Integer>{Category save(Category row);}
      class Api {@Autowired Store store;Category entry(){Category c=new Category();
        c.name="first";store.save(c);c.name="second";store.save(c);return c;}}'''},rows={'categories':[]})
    engine=Engine(project,ScenarioState(db));result=engine.run(ids['Api.entry'],{})
    assert result['id'] is not U and isinstance(result['id'],dict)
    rows=engine.state.database.rows(project.nodes['res:table:service.categories'])
    assert len(rows)==1 and rows[0]['name']=='second'


def test_source_method_override_wins_over_inherited_accessor(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Base {String getName(){return "base";}}
      class Child extends Base {String getName(){return "child";}}
      class Api {String entry(){Child c=new Child();return c.getName();}}'''})
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Api.entry'],{})=='child'
    assert ids['Base.getName'] not in {t for _,r,t in engine.edges if r=='calls'}
