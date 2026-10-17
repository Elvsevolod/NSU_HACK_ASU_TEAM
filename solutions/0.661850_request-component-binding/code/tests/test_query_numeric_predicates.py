import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


@pytest.mark.parametrize('op,expected',[
    ('>',{'two'}),('>=',{'one','two'}),('<',{'zero'}),('<=',{'zero','one'}),
    ('!=',{'zero','two'}),('<>',{'zero','two'}),('=',{'one'}),
])
def test_source_query_numeric_comparisons_choose_only_matching_rows(tmp_path,op,expected):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {@Autowired Store store;
      List<Row> entry(){return store.visible(1);}}
      @Entity @Table(name="rows") class Row {@Id String id;Integer amount;}
      interface Store extends JpaRepository<Row,String>{
        @Query(value="SELECT * FROM rows WHERE amount '''+op+''' ?1",nativeQuery=true)
        List<Row> visible(int cutoff);}'''},rows={'rows':[{'id':'zero','amount':0},
          {'id':'one','amount':1},{'id':'two','amount':2},{'id':'missing','amount':None}]})
    engine=Engine(project,ScenarioState(db));result=engine.run(ids['Api.entry'],{})
    assert {row['id'] for row in result}==expected
    assert not engine.warnings


def test_text_ordering_is_not_guessed_without_database_collation(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {@Autowired Store store;
      List<Row> entry(){return store.visible("B");}}
      @Entity @Table(name="rows") class Row {@Id String id;String amount;}
      interface Store extends JpaRepository<Row,String>{
        @Query(value="SELECT * FROM rows WHERE amount > ?1",nativeQuery=true)
        List<Row> visible(String cutoff);}'''},rows={'rows':[{'id':'text','amount':'a'}]})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{}) is U
    assert any('predicate' in warning for warning in engine.warnings)


@pytest.mark.parametrize('predicate',['amount = ?1','amount in (?1)'])
def test_explicit_query_null_comparison_does_not_behave_like_is_null(tmp_path,predicate):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {@Autowired Store store;
      List<Row> entry(){return store.visible(null);}}
      @Entity @Table(name="rows") class Row {@Id String id;Integer amount;}
      interface Store extends JpaRepository<Row,String>{
        @Query(value="SELECT * FROM rows WHERE '''+predicate+'''",nativeQuery=true)
        List<Row> visible(Integer cutoff);}'''},rows={'rows':[{'id':'missing','amount':None}]})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==[]


def test_multiple_numeric_predicates_keep_their_parameter_indexes(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {@Autowired Store store;
      List<Row> entry(){return store.visible(0,2);}}
      @Entity @Table(name="rows") class Row {@Id String id;Integer amount;}
      interface Store extends JpaRepository<Row,String>{
        @Query(value="SELECT * FROM rows WHERE amount > (?1) AND amount < ?2",nativeQuery=true)
        List<Row> visible(int low,int high);}'''},rows={'rows':[{'id':'zero','amount':0},
           {'id':'one','amount':1},{'id':'two','amount':2},{'id':'missing','amount':None}]})
    engine=Engine(project,ScenarioState(db))
    assert [row['id'] for row in engine.run(ids['Api.entry'],{})]==['one']
    assert not engine.warnings
