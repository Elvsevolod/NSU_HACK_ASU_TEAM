"""Source-derived C01 expectations, recorded before the short-circuit patch."""
import pytest
from analyzer.paths import run_paths
from analyzer.state import ScenarioState, U
from builders import build


@pytest.mark.parametrize('operation,callback_result', [('||', 'true'), ('&&', 'false')])
def test_unknown_left_has_a_real_skip_path_and_a_separate_callback_path(tmp_path, operation, callback_result):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{static int count=0;
      boolean touch(){count++;return RESULT;}
      Object entry(boolean left){boolean result=left OP touch();return Arrays.asList(result,count);}}'''
      .replace('RESULT',callback_result).replace('OP',operation)})
    rows=run_paths(p,ScenarioState(db),ids['Api.entry'],{'left':U},limit=4)
    assert {tuple(r['result']) for r in rows}=={(operation=='||',0),(operation=='||',1)}
    for row in rows:
        touched=('', 'executes', ids['Api.touch']) in row['engine'].edges
        assert touched == (row['result'][1]==1)
        assert row['engine'].outcome=='returned'


@pytest.mark.parametrize('operation', ['&&', '||'])
def test_unknown_left_does_not_lose_the_normal_path_when_rhs_throws(tmp_path, operation):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{
      boolean fail(){throw new IllegalStateException();}
      boolean entry(boolean left){return left OP fail();}}'''.replace('OP',operation)})
    rows=run_paths(p,ScenarioState(db),ids['Api.entry'],{'left':U},limit=4)
    assert {r['engine'].outcome for r in rows}=={'returned','uncaught application exception'}
    normal=next(r for r in rows if r['engine'].outcome=='returned')
    assert normal['result'] is (operation=='||')
    assert ('','executes',ids['Api.fail']) not in normal['engine'].edges


def test_unknown_string_null_guard_has_no_spurious_npe_or_completion_budget(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.Locale;class Api{
      String normalize(String value){if(value==null || value.isEmpty())return value;
        return value.replace(" ","").toLowerCase(Locale.ROOT);}
      String entry(String value){return normalize(value);}}'''})
    rows=run_paths(p,ScenarioState(db),ids['Api.entry'],{'value':U},limit=4)
    assert rows and all(r['engine'].outcome=='returned' for r in rows)
    assert any(r['result'] is None for r in rows)
    assert not any('NullPointerException' in w for r in rows for w in r['engine'].warnings)
    assert all(r['exploration']['completion_splits']==0 for r in rows)


@pytest.mark.parametrize('value', [None,'','A B'])
def test_known_string_values_keep_source_behavior(tmp_path, value):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.Locale;class Api{
      String entry(String value){if(value==null || value.isEmpty())return value;
        return value.replace(" ","").toLowerCase(Locale.ROOT);}}'''})
    rows=run_paths(p,ScenarioState(db),ids['Api.entry'],{'value':value},limit=4)
    assert len(rows)==1 and rows[0]['result']==(value if value is None else value.replace(' ','').lower())


def test_rhs_source_effect_is_not_replayed_when_selecting_the_short_circuit_path(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{static int leftCount=0;static int rightCount=0;
      boolean lhs(boolean value){leftCount++;return value;}boolean rhs(){rightCount++;return true;}
      Object entry(boolean value){boolean result=lhs(value)||rhs();return Arrays.asList(leftCount,rightCount,result);}}'''})
    rows=run_paths(p,ScenarioState(db),ids['Api.entry'],{'value':U},limit=4)
    assert {tuple(r['result']) for r in rows}=={(1,0,True),(1,1,True)}
