import pytest
from analyzer.engine import Engine
from analyzer.java_collections import JavaRecord, JavaMap
from analyzer.paths import run_paths
from analyzer.state import ScenarioState, U
from builders import build


@pytest.mark.parametrize('name', ['mutate', 'debug', 'info', 'print'])
def test_unknown_calls_invalidate_dto_fields_and_explore_throw(tmp_path, name):
    project, db, ids = build(tmp_path, {'Api.java': '''class Dto {public boolean active;}
      class Api {External external;int entry(Dto dto){external.'''+name+'''(dto);if(dto.active){reserve();}return 7;}
      void reserve(){} }'''})
    dto = JavaRecord('Dto', {'__type__': 'Dto', 'active': False}, ['active'])
    outcomes = run_paths(project, ScenarioState(db), ids['Api.entry'], {'dto': dto}, limit=8)
    assert any(('', 'executes', ids['Api.reserve']) in item['engine'].edges for item in outcomes)
    assert any(item['engine'].outcome == 'uncaught application exception' for item in outcomes)
    assert dto['active'] is False
    assert all(item['engine'].effect_events[0]['completions'] == ('normal', 'throw') for item in outcomes)


def test_logger_requires_a_proven_native_type(tmp_path):
    project, db, ids = build(tmp_path, {'Api.java': '''import org.slf4j.Logger;
      class Dto {public boolean active;}
      class Api {Logger log;boolean entry(Dto dto){log.debug(dto);return dto.active;}}'''})
    dto = JavaRecord('Dto', {'__type__': 'Dto', 'active': False}, ['active'])
    engine = Engine(project, ScenarioState(db))
    assert engine.run(ids['Api.entry'], {'dto': dto}) is False
    assert not engine.effect_events


def test_unknown_map_mutation_does_not_keep_old_entries(tmp_path):
    project, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;
      class Api {External external;Object entry(Map<String,String> values){external.mutate(values);return values.get("k");}}'''})
    values = JavaMap({'k': 'before'})
    engine = Engine(project, ScenarioState(db))
    assert engine.run(ids['Api.entry'], {'values': values}) is U
    assert values.mapping is U


def test_unknown_list_mutation_does_not_keep_size_or_values(tmp_path):
    project, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;
      class Api {External external;Object entry(List<String> values){external.mutate(values);return values.size();}}'''})
    engine = Engine(project, ScenarioState(db))
    assert engine.run(ids['Api.entry'], {'values': ['before']}) is U


def test_source_dependency_footprint_preserves_an_independent_table(tmp_path):
    source = '''class External {MainStore store;} class Api {External external;void entry(){external.mutate();}}
      @Entity @Table(name="main") class Main {@Id String id;}
      @Entity @Table(name="other") class Other {@Id String id;}
      interface MainStore extends JpaRepository<Main,String>{}
      interface OtherStore extends JpaRepository<Other,String>{}'''
    project, db, ids = build(tmp_path, {'Api.java': source}, rows={'main': [{'id': 'a'}], 'other': [{'id': 'b'}]})
    engine = Engine(project, ScenarioState(db))
    engine.run(ids['Api.entry'], {})
    assert engine.effect_events[0]['resource_writes'] == ('res:table:service.main',)
    assert ('service', 'main') in engine.state.database.unknown_tables
    assert ('service', 'other') not in engine.state.database.unknown_tables
    assert not any(relation == 'data' for _, relation, _ in engine.edges)
