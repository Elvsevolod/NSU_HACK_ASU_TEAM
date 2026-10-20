"""Independent source examples frozen before review-32 implementation.

Expected values follow the Java API/source, not analyzer predictions or gold.
Only our Python interpreter is run; these snippets are never compiled/launched.
"""
import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState, U
from builders import build


def run(tmp_path, body, extra='', result_type='Object', arguments=None, params=''):
    p, db, ids = build(tmp_path, {'Api.java': 'import java.util.*;'+extra+
        'class Api{'+result_type+' entry('+params+'){'+body+'}int after(){return 99;}}'})
    engine = Engine(p, ScenarioState(db))
    return engine.run(ids['Api.entry'], arguments or {}), engine, ids


def test_computed_static_initializer_and_scenario_reset(tmp_path):
    p, db, ids = build(tmp_path, {'Material.java': '''class Material{
      private static String encoded=java.util.Base64.getEncoder().encodeToString("ab".getBytes());
      static String read(){return encoded;}static void change(String v){encoded=v;}}'''},
      context={'charset':'UTF-8'})
    state = ScenarioState(db, {'charset':'UTF-8'})
    assert Engine(p,state).run(ids['Material.read'],{}) == 'YWI='
    Engine(p,state).run(ids['Material.change'],{'v':'next'})
    assert Engine(p,state).run(ids['Material.read'],{}) == 'next'
    assert Engine(p,ScenarioState(db, {'charset':'UTF-8'})).run(ids['Material.read'],{}) == 'YWI='


@pytest.mark.parametrize('expression', ['offsets.get(names.indexOf("South"))', 'offsets.get(pos)'])
def test_index_of_primitive_consumer(tmp_path, expression):
    value, engine, _ = run(tmp_path, '''List<String> names=Arrays.asList("North","South");
      List<Integer> offsets=Arrays.asList(0,12);int pos=names.indexOf("South");return '''+expression+';', result_type='int')
    assert value == 12
    assert not engine.approximate


@pytest.mark.parametrize('items,needle,wanted', [
    ('"A","A","B"','"A"',0), ('"A","B"','"X"',-1),
    ('null,"B"','null',0), ('1,1L,true','1L',1), ('1,1L,true','true',2)])
def test_index_of_value_and_wrapper_identity(tmp_path, items, needle, wanted):
    value, engine, _ = run(tmp_path, 'List<Object> items=Arrays.asList('+items+');int pos=items.indexOf('+needle+');return pos;', result_type='int')
    assert value == wanted
    assert not engine.approximate


def test_missing_index_throws_at_get_and_skips_suffix(tmp_path):
    value,engine,ids = run(tmp_path, '''List<String> names=Arrays.asList("A");
      try{int pos=names.indexOf("B");names.get(pos);return after();}
      catch(IndexOutOfBoundsException failure){return -1;}''', result_type='int')
    assert value == -1
    assert ('','executes',ids['Api.after']) not in engine.edges


def test_source_index_of_is_not_a_native_signature(tmp_path):
    value, engine, _ = run(tmp_path, 'return new Lookup().indexOf("A");',
        extra='class Lookup{String indexOf(String key){return "source";}}', result_type='String')
    assert value == 'source'
    assert not engine.approximate


def test_finite_foreach_runs_captured_effect(tmp_path):
    value,engine,_ = run(tmp_path, '''List<Integer> touched=new ArrayList<>();
      Arrays.asList(1).stream().forEach(x->touched.add(x));return touched.size();''', result_type='int')
    assert value == 1
    assert not engine.approximate


def test_reused_standard_stream_cannot_run_suffix(tmp_path):
    value,engine,ids = run(tmp_path, '''java.util.stream.Stream<Integer> stream=Arrays.asList(1).stream();
      stream.toList();stream.toList();return after();''', result_type='int')
    assert value is U and engine.outcome == 'uncaught application exception'
    assert ('','executes',ids['Api.after']) not in engine.edges


def test_empty_optional_map_presence(tmp_path):
    value,engine,_ = run(tmp_path, 'return Optional.empty().map(x->x).isEmpty();', result_type='boolean')
    assert value is True
    assert not engine.approximate
