import pytest
from analyzer.paths import run_paths
from analyzer.engine import Engine
from analyzer.state import ScenarioState, U
from builders import build


SOURCE = '''import java.util.*;import org.springframework.data.jpa.repository.JpaRepository;
 @Entity @Table(name="parcels") class Parcel{@Id public String id;public String label;}
 interface Store extends JpaRepository<Parcel,String>{
  Optional<Parcel> findById(String id);List<Parcel> findByLabel(String label);}
 class Api{Store store;
  String entry(String id){Optional<Parcel> value=store.findById(id);
   try{if(value.isPresent()){value.get();if(!value.isPresent()){return wrong();}return present();}return absent();}
   catch(NullPointerException failure){return wrong();}catch(NoSuchElementException failure){return wrong();}}
  String list(String label){List<Parcel> values=store.findByLabel(label);
   try{values.size();return after();}catch(NullPointerException failure){return wrong();}}
  String wrong(){return "wrong";}String present(){return "present";}
  String absent(){return "absent";}String after(){return "after";}}'''


@pytest.mark.parametrize('limit', [1,4,8])
@pytest.mark.parametrize('unknown_database', [False,True])
def test_unknown_contents_keep_nonnull_optional_and_correlated_presence(tmp_path,limit,unknown_database):
    project,db,ids=build(tmp_path,{'Api.java':SOURCE},rows={'parcels':[{'id':'p1','label':'one'}]})
    if unknown_database:db.unknown_tables.add(('service','parcels'))
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{'id':U},limit=limit)
    assert {row['result'] for row in outcomes} == {'present','absent'}
    assert all(ids['Api.wrong'] not in {t for _,k,t in row['engine'].edges if k=='executes'} for row in outcomes)


@pytest.mark.parametrize('limit',[1,4,8])
def test_unknown_list_is_not_a_nullable_receiver(tmp_path,limit):
    project,db,ids=build(tmp_path,{'Api.java':SOURCE},rows={'parcels':[{'id':'p1','label':'one'}]})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.list'],{'label':U},limit=limit)
    assert {row['result'] for row in outcomes} == {'after'}


def test_custom_repository_default_method_can_return_null(tmp_path):
    source=SOURCE.replace('List<Parcel> findByLabel(String label);',
        'default List<Parcel> findByLabel(String label){return null;}')
    project,db,ids=build(tmp_path,{'Api.java':source},rows={'parcels':[{'id':'p1','label':'one'}]})
    assert Engine(project,ScenarioState(db)).run(ids['Api.list'],{'label':'one'}) == 'wrong'
