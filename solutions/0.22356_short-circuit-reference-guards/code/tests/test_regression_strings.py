import pytest

from analyzer.paths import run_paths
from analyzer.state import ScenarioState, U
from builders import build


@pytest.mark.parametrize('expression,expected', [
    ('"ＡB-C".replace("-", " ").toLowerCase(Locale.ROOT)', 'ａb c'),
    ('"A-B".replace("-", "").toLowerCase(Locale.ROOT)', 'ab'),
    ('"İ".toLowerCase(Locale.ROOT)', 'i\u0307'),
    ('"I".toLowerCase(new Locale("tr"))', 'ı'),
    ('"I".toLowerCase(Locale.ROOT)', 'i'),
])
def test_native_string_chain_keeps_signature_type_and_value(tmp_path, expression, expected):
    project,db,ids=build(tmp_path, {'Api.java': """import java.util.Locale; class Api {
      String entry(){return """+expression+""";} }"""})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{},limit=1)
    assert {row['result'] for row in outcomes}=={expected}
    assert all(not row['engine'].effect_events for row in outcomes)


def test_unknown_string_transformation_retains_type_not_invented_text(tmp_path):
    project,db,ids=build(tmp_path, {'Api.java': """import java.util.Locale; class Api {
      String entry(String input){return input.replace('x','y').toLowerCase(Locale.ROOT);} }"""})
    value={'__symbol__':'user-text','__type__':'String','__length__':12,'__constraints__':['non_null']}
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{'input':value},limit=1)
    assert outcomes
    for row in outcomes:
        result=row['result']
        assert isinstance(result,dict) and result.get('__type__')=='String'
        assert result.get('__symbol__')!='user-text'
        assert 'non_null' in result.get('__constraints__',[])
        assert not row['engine'].effect_events


def test_default_locale_is_not_silently_assumed_root(tmp_path):
    project,db,ids=build(tmp_path, {'Api.java':'class Api {String entry(){return "I".toLowerCase();}}'})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{},limit=1)
    assert outcomes and all(isinstance(row['result'],dict) and row['result'].get('__type__')=='String' for row in outcomes)
    assert any('locale' in message.lower() for row in outcomes for message in row['engine'].warnings)
