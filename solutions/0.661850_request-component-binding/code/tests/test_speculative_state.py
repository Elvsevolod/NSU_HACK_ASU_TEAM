from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from builders import build


def test_an_agreed_write_in_both_budgeted_branches_is_preserved(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {Store store;
      String entry(boolean choice){Row value=new Row();value.id="created";
        if(choice){store.save(value);}else{store.save(value);}
        return store.findById("created").get().id;}}
      @Entity @Table(name="rows") class Row {@Id String id;}
      interface Store extends JpaRepository<Row,String>{}'''},rows={'rows':[]})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{'choice':U},limit=1)
    assert len(outcomes)==1 and outcomes[0]['result']=='created'
    assert [row['id'] for row in outcomes[0]['state'].database.tables[('service','rows')]]==['created']
    assert not outcomes[0]['state'].database.unknown_tables
    assert outcomes[0]['engine'].approximate


def test_speculative_forks_copy_mutable_state_but_share_completed_observations(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'class Api {String entry(){return "ok";}}'},rows={'rows':[{'id':'original'}]})
    original=ScenarioState(db)
    original.history=[{'result':{'stable':['observed']}}]
    engine=Engine(project,original)
    fork=engine.execution_fork(original)
    assert fork.history is not original.history and fork.history[0] is original.history[0]
    fork.history.append({'result':'following request'})
    fork.browser['storage']['key']='changed'
    fork.database.tables[('service','rows')][0]['id']='changed'
    assert len(original.history)==1 and original.browser['storage']=={}
    assert original.database.tables[('service','rows')][0]['id']=='original'


def test_conflicting_speculative_writes_remain_unknown(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {Store store;
      Object entry(boolean choice){Row value=new Row();
        if(choice){value.id="left";store.save(value);}
        else{value.id="right";store.save(value);}
        return store.findAll();}}
      @Entity @Table(name="rows") class Row {@Id String id;}
      interface Store extends JpaRepository<Row,String>{}'''},rows={'rows':[]})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{'choice':U},limit=1)
    assert outcomes[0]['result'] is U
    assert ('service','rows') in outcomes[0]['state'].database.unknown_tables
