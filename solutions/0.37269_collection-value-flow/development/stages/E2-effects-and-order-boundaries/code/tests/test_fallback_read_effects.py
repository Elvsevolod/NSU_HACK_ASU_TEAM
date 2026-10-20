import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState
from builders import build


@pytest.mark.parametrize('operation,annotation,unknown', [
    ('store.findById("p1");','',False),
    ('store.save(new Parcel());','',True),
    ('store.findById("p1");','@Transactional',True),
])
def test_fallback_preserves_proven_reads_and_invalidates_possible_writes(tmp_path,operation,annotation,unknown):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.data.jpa.repository.JpaRepository;
      class Api{Store store;'''+annotation+''' void entry(){'''+operation+'''}}
      @Entity @Table(name="parcels") class Parcel{@Id String id;}
      interface Store extends JpaRepository<Parcel,String>{Parcel findById(String id);Parcel save(Parcel value);}'''},
      rows={'parcels':[{'id':'p1'}]})
    engine=Engine(project,ScenarioState(db));engine.method=ids['Api.entry']
    engine.fallback(ids['Api.entry'])
    assert (('service','parcels') in engine.state.database.unknown_tables) is unknown
    assert (ids['Api.entry'],'data','res:table:service.parcels') in engine.candidate_edges


@pytest.mark.parametrize('signature',[
    '@Procedure int getNextNumber();',
    '@Modifying @Query("update Parcel p set p.id = ?1") int getById(String id);',
    'default Parcel getById(String id){return save(new Parcel());}',
])
def test_read_prefix_does_not_prove_repository_read_effects(tmp_path,signature):
    method='getNextNumber()' if 'getNextNumber' in signature else 'getById("p1")'
    p,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.data.jpa.repository.JpaRepository;
      class Api{Store store;void entry(){store.'''+method+''';}}
      @Entity @Table(name="parcels")class Parcel{@Id String id;}
      interface Store extends JpaRepository<Parcel,String>{'''+signature+''' Parcel save(Parcel value);}'''},
      rows={'parcels':[{'id':'p1'}]})
    e=Engine(p,ScenarioState(db));e.method=ids['Api.entry'];e.fallback(ids['Api.entry'])
    assert ('service','parcels') in e.state.database.unknown_tables


def test_missing_call_receiver_metadata_is_unknown_write_not_a_crash(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.data.jpa.repository.JpaRepository;
      class Api{Store store;void entry(){store.findById("p1");}}
      @Entity @Table(name="parcels")class Parcel{@Id String id;}
      interface Store extends JpaRepository<Parcel,String>{Parcel findById(String id);}'''},rows={'parcels':[{'id':'p1'}]})
    for site in p.sites[ids['Api.entry']]:p.nodes[site]['receiver_type']=None
    e=Engine(p,ScenarioState(db));e.method=ids['Api.entry'];e.fallback(ids['Api.entry'])
    assert ('service','parcels') in e.state.database.unknown_tables
