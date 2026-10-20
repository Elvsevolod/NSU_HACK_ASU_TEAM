import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.heap_join import clone_execution,mutable_ids
from analyzer.request import grounded_request
from analyzer.java_collections import JavaRecord
from analyzer.state import ScenarioState,U
from builders import build


def test_unknown_loop_events_are_possible_and_return_keeps_its_completion(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api{int entry(boolean flag){while(flag){conditional();return 7;}return after();}
      void conditional(){}int after(){return 9;}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{'flag':U},limit=1)
    assert {row['result'] for row in outcomes}=={7,9}
    for row in outcomes:
        assert ('','executes',ids['Api.conditional']) not in row['engine'].confirmed_edges


def test_uncertain_save_has_no_uninitialized_python_local(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api{Store store;void entry(boolean flag){while(flag){Row row=new Row();row.id="x";store.save(row);break;}}}
      @Entity @Table(name="rows")class Row{@Id String id;}interface Store extends JpaRepository<Row,String>{Row save(Row value);}'''},rows={'rows':[]})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{'flag':U},limit=1)
    assert outcomes


def test_nested_required_marks_outer_transaction_rollback_only(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api{Inner inner;Store store;
      @Transactional void entry(){Row a=new Row();a.id="a";store.save(a);try{inner.fail();}catch(RuntimeException ignored){}
        Row b=new Row();b.id="b";store.save(b);}}
      class Inner{Store store;@Transactional void fail(){Row c=new Row();c.id="c";store.save(c);throw new IllegalStateException();}}
      @Entity @Table(name="rows")class Row{@Id String id;}interface Store extends JpaRepository<Row,String>{Row save(Row value);}'''},rows={'rows':[]})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert engine.state.database.tables[('service','rows')]==[]
    assert engine.persistence_events[-1]['outcome']=='rollback'
    assert engine.outcome=='uncaught application exception'


def test_cached_table_identities_include_an_appended_live_alias(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'class Api{void entry(){}}'},rows={'rows':[{'id':'old'}]})
    state=ScenarioState(db);key=('service','rows')
    rows=state.database.tables[key]
    state.database.tables.shared_identities(key,mutable_ids)
    row=JavaRecord('Row',{'id':'new'},['id']);rows.append(row)
    (owned,params),_=clone_execution(state,{'row':row})
    params['row']['id']='changed'
    assert owned.database.tables[key][-1] is params['row']
    assert owned.database.tables[key][-1]['id']=='changed' and row['id']=='new'


def test_dirty_checking_uses_the_same_column_mapping_as_read(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api{Store store;
      @Transactional String entry(){Row row=store.findById("x");row.label="after";store.flush();return store.findById("x").label;}}
      @Entity @Table(name="rows")class Row{@Id @Column(name="row_key") String id;@Column(name="display_text") String label;}
      interface Store extends JpaRepository<Row,String>{Row findById(String key);void flush();}'''},rows={'rows':[{'row_key':'x','display_text':'before'}]})
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Api.entry'],{})=='after'
    row=engine.state.database.tables[('service','rows')][0]
    assert row['displayText']=='after' and row['rowKey']=='x'
    assert project.materialize(engine.state.database,'res:table:service.rows',row)['label']=='after'


def test_lazy_materialization_runs_the_same_constructor_helpers_as_normal_load(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api{Store store;String entry(){return store.getReferenceById("x").label;}}
      @Entity @Table(name="rows")class Row{@Id String id;String label;Row(){helper();}void helper(){nested();}void nested(){}}
      interface Store extends JpaRepository<Row,String>{Row getReferenceById(String key);}'''},rows={'rows':[{'id':'x','label':'persisted'}]})
    engine=Engine(project,ScenarioState(db));assert engine.run(ids['Api.entry'],{})=='persisted'
    assert ('','executes',ids['Row.helper']) in engine.edges
    assert ('','executes',ids['Row.nested']) in engine.edges


def test_multiple_url_aliases_keep_the_shared_http_binder(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api{@GetMapping({"/items/{id}","/v2/items/{id}"}) String read(@PathVariable int id){return "entered";}}'''})
    request=grounded_request(project,ids['Api.read'],{'id':'invalid'})
    assert request is not None
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.read'],request)
    assert engine.outcome=='HTTP binding failure' and not engine.edges
