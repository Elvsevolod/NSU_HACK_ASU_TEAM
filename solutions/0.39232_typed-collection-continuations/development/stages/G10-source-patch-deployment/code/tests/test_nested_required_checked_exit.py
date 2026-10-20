from analyzer.engine import Engine
from analyzer.state import ScenarioState
from builders import build


def test_checked_outer_exit_cannot_clear_an_existing_rollback_only(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.io.IOException;
      class Api{Inner inner;Store store;@Transactional void entry()throws IOException{
        Row a=new Row();a.id="a";store.save(a);try{inner.fail();}catch(RuntimeException ignored){}
        throw new IOException();}}
      class Inner{Store store;@Transactional void fail(){Row b=new Row();b.id="b";store.save(b);throw new IllegalStateException();}}
      @Entity @Table(name="rows")class Row{@Id String id;}interface Store extends JpaRepository<Row,String>{Row save(Row value);}'''},rows={'rows':[]})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert engine.state.database.tables[('service','rows')]==[]
    assert engine.persistence_events[-1]['outcome']=='rollback'
