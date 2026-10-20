import pytest
from analyzer.absence_contracts import empty_equivalent
from analyzer.engine import Engine
from analyzer.state import ScenarioState
from builders import build


@pytest.mark.parametrize('tail',[
    'Credentials alias=input;return alias.getChallenge()==null;',
    'saved=input;return saved.getChallenge()==null;',
    'return inspect((Object)input);',
])
def test_absence_proof_declines_unproven_alias_or_escape(tmp_path,tail):
    p,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.util.StringUtils;import lombok.Data;
      @Data class Credentials{private String challenge;}
      class Api{Credentials saved;@PostMapping("/login")boolean login(@RequestBody Credentials input){
        if(!StringUtils.isEmpty(input.getChallenge())){return false;}'''+tail+'''}
        boolean inspect(Object escaped){return ((Credentials)escaped).getChallenge()==null;}}'''})
    e=Engine(p,ScenarioState(db));e.method=ids['Api.login']
    assert not empty_equivalent(e,ids['Api.login'],'challenge')
