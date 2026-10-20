import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build

SOURCE='''class Api {@Autowired Store store;
      List<Row> entry(){return store.visible(1);}}
      @Entity @Table(name="rows") class Row {@Id String id;Integer amount;}
      interface Store extends JpaRepository<Row,String>{
        @Query(value="SELECT * FROM rows WHERE %s",nativeQuery=true)
        List<Row> visible(int cutoff);}'''

ROWS={'rows':[{'id':'zero','amount':0},{'id':'one','amount':1},{'id':'two','amount':2}]}


@pytest.mark.parametrize('where,expected',[
    ('amount > ?1',{'two'}),('amount > (?1)',{'two'}),('amount > ( ?1 )',{'two'}),
    ('amount in ?1',{'one'}),('amount in (?1)',{'one'}),
])
def test_positional_rhs_accepts_bare_or_balanced_parentheses(tmp_path,where,expected):
    project,db,ids=build(tmp_path,{'Api.java':SOURCE%where},rows=ROWS)
    engine=Engine(project,ScenarioState(db));result=engine.run(ids['Api.entry'],{})
    assert {row['id'] for row in result}==expected
    assert not engine.warnings


@pytest.mark.parametrize('where',['amount > (?1','amount > ?1)'])
def test_unbalanced_rhs_parentheses_leave_the_query_unknown(tmp_path,where):
    project,db,ids=build(tmp_path,{'Api.java':SOURCE%where},rows=ROWS)
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{}) is U
    assert any('predicate' in warning for warning in engine.warnings)
