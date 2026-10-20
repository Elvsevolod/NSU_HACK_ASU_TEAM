import pytest
from analyzer.engine import Engine
from analyzer.native_storage import JavaList
from analyzer.state import ScenarioState, U
from builders import build


SOURCE = '''import java.util.*;
class Row {public String id;public String name;}
class Api {Map<String,String> cache=new HashMap<>();
 boolean local(List<Row> rows){Map<String,String> names=new HashMap<>();
   for(Row row:rows){names.put(row.id,row.name);}return names.get("A")==null;}
 void write(List<Row> rows){for(Row row:rows){cache.put(row.id,row.name);}}
 boolean read(){return cache.get("A")==null;}
}'''


def opaque_rows():
    rows = JavaList()
    rows.opaque = True
    return rows


@pytest.mark.parametrize('opaque', [False, True])
def test_unknown_membership_does_not_prove_local_map_empty(tmp_path, opaque):
    p, db, ids = build(tmp_path, {'Api.java': SOURCE})
    engine = Engine(p, ScenarioState(db))
    assert engine.run(ids['Api.local'], {'rows': opaque_rows() if opaque else U}) is U
    assert engine.outcome == 'unsupported_semantics boundary'
    assert any('unknown collection' in warning for warning in engine.warnings)


def test_skipped_effect_does_not_leave_shared_cache_known_empty(tmp_path):
    p, db, ids = build(tmp_path, {'Api.java': SOURCE})
    first = Engine(p, ScenarioState(db))
    first.run(ids['Api.write'], {'rows': opaque_rows()})
    second = Engine(p, first.state)
    assert second.run(ids['Api.read'], {}) is U


@pytest.mark.parametrize('source, expected', [
    ('new ArrayList<Row>()', True),
    ('Arrays.asList(row("A","one"))', False),
    ('Arrays.asList(row("A","one"),row("B","two"))', False),
])
def test_known_empty_and_known_members_remain_exact(tmp_path, source, expected):
    p, db, ids = build(tmp_path, {'Api.java': SOURCE.replace(
        ' boolean local(', ' Row row(String id,String name){Row r=new Row();r.id=id;r.name=name;return r;}\n'
        ' boolean entry(){return local(' + source + ');}\n boolean local(')})
    engine = Engine(p, ScenarioState(db))
    assert engine.run(ids['Api.entry'], {}) is expected


def test_null_foreach_throws_before_body(tmp_path):
    p, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;class Api{
      String entry(){try{for(String value:(List<String>)null){return value;}}
       catch(NullPointerException failure){return "null";}return "after";}}'''})
    assert Engine(p, ScenarioState(db)).run(ids['Api.entry'], {}) == 'null'


def test_unknown_repository_rows_do_not_prove_missing_key(tmp_path):
    p, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;
      import org.springframework.data.jpa.repository.JpaRepository;
      @Entity @Table(name="rows") class Row {public String id;public String name;}
      interface Rows extends JpaRepository<Row,String>{List<Row> findAll();}
      class Api {Rows repository;boolean entry(){Map<String,String> names=new HashMap<>();
        for(Row row:repository.findAll()){names.put(row.id,row.name);}
        return names.get("A")==null;}}'''}, rows={'rows': [{'id': 'A', 'name': 'one'}]})
    db.unknown_tables.add(('service', 'rows'))
    engine = Engine(p, ScenarioState(db))
    assert engine.run(ids['Api.entry'], {}) is U
    assert engine.outcome == 'unsupported_semantics boundary'


@pytest.mark.parametrize('body', ['return value;', 'throw new IllegalStateException();',
                                  'break;', 'continue;'])
def test_unknown_iteration_does_not_invent_body_completion(tmp_path, body):
    p, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;class Api{
      String entry(List<String> rows){for(String value:rows){''' + body + '''}return "after";}}'''})
    rows = JavaList(['old'], ['String'])
    rows.opaque = True
    engine = Engine(p, ScenarioState(db))
    assert engine.run(ids['Api.entry'], {'rows': rows}) is U
    assert engine.outcome == 'unsupported_semantics boundary'
