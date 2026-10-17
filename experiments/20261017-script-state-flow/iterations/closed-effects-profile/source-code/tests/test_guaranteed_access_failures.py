import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState
from builders import build


@pytest.mark.parametrize('code',[
 'Item row=null;String unused=row.id;',
 'Item row=null;row.id="new";',
 'int[] rows=null;int unused=rows[0];',
 'int[] rows={1};int unused=rows[2];',
 'List<String> rows=new ArrayList<>();rows.get(0);',
 'List<String> rows=new ArrayList<>();rows.iterator().next();',
 '"a".charAt(2);',
 '"a".substring(-1);'])
def test_guaranteed_null_and_bounds_failures_stop_following_source_calls(tmp_path,code):
    project,db,ids=build(tmp_path,{'Api.java':'''class Item {String id;}
      class Api {void entry(){'''+code+'''after();}void after(){}}'''})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert engine.outcome=='uncaught application exception'
    assert ids['Api.after'] not in {t for _,r,t in engine.edges if r=='calls'}


def test_static_constant_access_through_a_null_reference_does_not_throw(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Item {static final String LABEL="static";}
      class Api {String entry(){Item row=null;return row.LABEL;}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='static'


def test_java_string_length_counts_utf16_code_units(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'class Api {int entry(){return "😀".length();}}'})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==2
