import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState
from builders import build


@pytest.mark.parametrize('formatting',[False,True])
def test_native_formatter_keeps_owner_id_and_source_getter(tmp_path,formatting):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.core.style.ToStringCreator;
      import org.slf4j.Logger;
      class Owner {int id=7;int getId(){return id;}
        public String toString(){return new ToStringCreator(this).append("id",getId()).toString();}}
      class Api {Logger log;int entry(){Owner owner=new Owner();'''+
      ('log.info("{}",owner);' if formatting else '')+'''return owner.id;}}'''})
    state=ScenarioState(db);state.context['logging']={'enabled':True}
    outcomes=run_paths(project,state,ids['Api.entry'],{},limit=1)
    assert {row['result'] for row in outcomes}=={7}
    assert all((('', 'executes',ids['Owner.getId']) in row['engine'].edges) is formatting for row in outcomes)
    assert not any(event['operation']=='append' and event['model_version']=='opaque-java-call/1'
                   for row in outcomes for event in row['engine'].effect_events)


@pytest.mark.parametrize('throws',[False,True])
def test_appended_source_to_string_keeps_mutation_and_throw(tmp_path,throws):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.core.style.ToStringCreator;
      class Value {int count;public String toString(){count++;'''+
      ('throw new IllegalStateException();' if throws else 'return "value";')+'''}}
      class Api {int entry(){Value value=new Value();try{new ToStringCreator(this).append("v",value);}
        catch(IllegalStateException failure){return value.count+10;}return value.count;}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})==(11 if throws else 1)
    assert ('', 'executes',ids['Value.toString']) in engine.edges
    assert (ids['Api.entry'],'calls',ids['Value.toString']) in engine.edges


def test_source_formatter_name_is_not_native(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class ToStringCreator {int n;
      ToStringCreator append(String key,int value){n=value;return this;}}
      class Api {int entry(){ToStringCreator creator=new ToStringCreator();creator.append("x",19);return creator.n;}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==19
