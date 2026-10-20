import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState, U
from builders import build


SOURCE = '''import java.util.*; class Api {Store store;
  @Transactional Object entry(){BODY}
  String prefix(){return "prefix";}}
  @Entity @Table(name="items") class Item {@Id String id;public String name;String getId(){return id;}String getName(){return name;}}
  interface Store extends JpaRepository<Item,String>{Item save(Item input);Item saveAndFlush(Item input);void flush();Optional<Item> findById(String id);Item getReferenceById(String id);}'''
RID = 'res:table:service.items'


def execute(tmp_path, body, rows=None):
    project, db, ids = build(tmp_path, {'Api.java': SOURCE.replace('BODY', body)}, rows={'items': rows or []})
    engine = Engine(project, ScenarioState(db))
    result = engine.run(ids['Api.entry'], {})
    return result, engine, ids, project


@pytest.mark.parametrize('flush,events', [('', 0), ('store.flush();', 1)])
def test_sql_event_survives_rollback_only_if_it_was_flushed(tmp_path, flush, events):
    result, engine, ids, project = execute(tmp_path, 'prefix();Item i=new Item();i.id="new";i.name="N";store.save(i);'+flush+'throw new RuntimeException();')
    assert result is U and engine.outcome == 'uncaught application exception'
    assert len(engine.data_operations) == events
    assert engine.state.database.rows(project.nodes[RID]) == []
    assert ('', 'executes', ids['Api.prefix']) in engine.edges
    assert bool((ids['Api.entry'], 'data', RID) in engine.edges) is bool(events)


def test_save_flushes_at_commit_and_retains_new_entity_mutation(tmp_path):
    _, engine, _, project = execute(tmp_path, 'Item i=new Item();i.id="new";i.name="before";store.save(i);i.name="after";return i;')
    assert engine.state.database.rows(project.nodes[RID])[0]['name'] == 'after'
    assert len(engine.data_operations) == 1
    assert engine.data_operations[0]['emitted_by'].startswith('transaction commit')


def test_repeated_findbyid_uses_the_managed_instance(tmp_path):
    value, engine, _, _ = execute(tmp_path, 'Item a=store.findById("x").get();Item b=store.findById("x").get();a.name="changed";return b.name;', [{'id': 'x', 'name': 'before'}])
    assert value == 'changed'
    assert [event['operation'] for event in engine.data_operations] == ['findById', 'dirty_update']


@pytest.mark.parametrize('access,expected,operations', [('id', 'x', []), ('name', 'N', ['lazy_load']), ('getId()', 'x', []), ('getName()', 'N', ['lazy_load'])])
def test_lazy_reference_identifier_does_not_issue_a_select(tmp_path, access, expected, operations):
    value, engine, _, _ = execute(tmp_path, 'Item item=store.getReferenceById("x");return item.'+access+';', [{'id': 'x', 'name': 'N'}])
    assert value == expected
    assert [event['operation'] for event in engine.data_operations] == operations


def test_checked_exception_commits_under_the_default_spring_policy(tmp_path):
    _, engine, _, project = execute(tmp_path, 'Item i=new Item();i.id="new";store.save(i);throw new java.io.IOException();')
    assert engine.state.database.rows(project.nodes[RID])[0]['id'] == 'new'
    assert engine.persistence_events[-1]['outcome'] == 'commit'


def test_identity_insert_timing_is_explicitly_provider_scoped(tmp_path):
    source=SOURCE.replace('@Id String id;','@Id @GeneratedValue(strategy=GenerationType.IDENTITY) Integer id;').replace('BODY',
        'Item item=new Item();store.save(item);throw new RuntimeException();')
    project,db,ids=build(tmp_path,{'Api.java':source},rows={'items':[]})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert len(engine.data_operations)==1
    assert engine.state.database.rows(project.nodes[RID])==[]
    assert (ids['Api.entry'],'data',RID) not in engine.confirmed_edges
    assert any('Hibernate-compatible' in reason for reason in engine.execution_assumptions)


def test_nondefault_propagation_keeps_touched_state_unknown_and_candidate_sql(tmp_path):
    source=SOURCE.replace('@Transactional','@Transactional(propagation=Propagation.REQUIRES_NEW)').replace('BODY',
        'Item item=new Item();item.id="new";store.save(item);return item;')
    project,db,ids=build(tmp_path,{'Api.java':source},rows={'items':[]})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert engine.persistence_events[-1]['outcome']=='unknown'
    assert engine.state.database.rows(project.nodes[RID]) is None
    assert (ids['Api.entry'],'data',RID) in engine.candidate_edges
