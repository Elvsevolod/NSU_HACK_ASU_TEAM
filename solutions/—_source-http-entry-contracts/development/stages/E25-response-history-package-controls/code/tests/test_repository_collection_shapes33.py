import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from analyzer.native_storage import JavaList
from builders import build


def source(shape,custom=False):
    declaration=(f'default {shape}<Parcel> findByLabel(String label){{return null;}}' if custom
                 else f'{shape}<Parcel> findByLabel(String label);')
    return '''import java.util.*;import org.springframework.data.jpa.repository.JpaRepository;
      @Entity @Table(name="parcels") class Parcel{@Id public String id;public String label;}
      interface Store extends JpaRepository<Parcel,String>{DECLARATION}
      class Api{Store store;SHAPE<Parcel> field;
        SHAPE<Parcel> returned(String label){return store.findByLabel(label);}
        String consume(SHAPE<Parcel> value){try{value.size();return "after";}
          catch(NullPointerException failure){return "spurious-null";}}
        String entry(String label){SHAPE<Parcel> local=returned(label);field=local;
          SHAPE<Parcel> alias=field;return consume(alias);}
        Object expose(String label){return returned(label);}
        String cast(String label){Object value=returned(label);try{List<Parcel> list=(List<Parcel>)value;
          return "list";}catch(ClassCastException failure){return "set";}}}
    '''.replace('DECLARATION',declaration).replace('SHAPE',shape)


@pytest.mark.parametrize('shape',['List','ArrayList','LinkedList','Collection','Set','HashSet'])
@pytest.mark.parametrize('unknown_database',[False,True])
def test_unknown_query_keeps_nonnull_shape_through_return_field_parameter(tmp_path,shape,unknown_database):
    project,db,ids=build(tmp_path,{'Api.java':source(shape)},rows={'parcels':[{'id':'p1','label':'one'}]})
    if unknown_database:db.unknown_tables.add(('service','parcels'))
    paths=run_paths(project,ScenarioState(db),ids['Api.entry'],{'label':U},limit=4)
    assert {row['result'] for row in paths}=={'after'}
    value=Engine(project,ScenarioState(db)).run(ids['Api.expose'],{'label':U})
    assert isinstance(value,JavaList) and value.opaque
    assert value.flavor==shape
    if shape in ('Set','HashSet'):
        assert not value.order_known
        assert Engine(project,ScenarioState(db)).run(ids['Api.cast'],{'label':U})==('set' if shape=='HashSet' else U)


@pytest.mark.parametrize('shape',['List','ArrayList','Set'])
def test_source_default_query_is_allowed_to_return_null(tmp_path,shape):
    project,db,ids=build(tmp_path,{'Api.java':source(shape,custom=True)},rows={'parcels':[{'id':'p1','label':'one'}]})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{'label':'one'})=='spurious-null'


def test_source_named_collection_is_not_a_standard_nonnull_wrapper(tmp_path):
    java=source('ArrayList').replace('import java.util.*;','class ArrayList<T>{int size(){return 0;}}')
    project,db,ids=build(tmp_path,{'Api.java':java},rows={'parcels':[{'id':'p1','label':'one'}]})
    assert Engine(project,ScenarioState(db)).run(ids['Api.expose'],{'label':U}) is U
