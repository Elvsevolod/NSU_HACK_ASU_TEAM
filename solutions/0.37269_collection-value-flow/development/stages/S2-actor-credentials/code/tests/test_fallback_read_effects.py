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
    project,db,ids=build(tmp_path,{'Api.java':'''class Api{Store store;'''+annotation+''' void entry(){'''+operation+'''}}
      @Entity @Table(name="parcels") class Parcel{@Id String id;}
      interface Store extends JpaRepository<Parcel,String>{Parcel findById(String id);Parcel save(Parcel value);}'''},
      rows={'parcels':[{'id':'p1'}]})
    engine=Engine(project,ScenarioState(db));engine.method=ids['Api.entry']
    engine.fallback(ids['Api.entry'])
    assert (('service','parcels') in engine.state.database.unknown_tables) is unknown
    assert (ids['Api.entry'],'data','res:table:service.parcels') in engine.candidate_edges
