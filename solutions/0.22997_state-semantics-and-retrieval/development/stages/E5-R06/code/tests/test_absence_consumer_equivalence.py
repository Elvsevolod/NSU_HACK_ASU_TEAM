import pytest
from analyzer.contracts import ContractGrounder,ContractIndex,read_static_context
from analyzer.frontend import Frontend
from analyzer.engine import Engine
from analyzer.request import grounded_request
from analyzer.state import ScenarioState
from builders import build


@pytest.mark.parametrize('consumer,equivalent',[
 ('if(!StringUtils.isEmpty(input.getChallenge())){return "challenge";}return "approved";',True),
 ('String code=input.getChallenge();if(!StringUtils.isEmpty(code)){return code;}return "approved";',True),
 ('if(input.getChallenge()==null){return "null";}return "empty";',False),
])
def test_context_absence_respects_the_actual_consumer(tmp_path,consumer,equivalent):
    p,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.util.StringUtils;import lombok.Data;
      @Data class Credentials{private String username;private String password;private String challenge;}
      class Api{@PostMapping("/login") String login(@RequestBody Credentials input){'''+consumer+'}}'})
    (tmp_path/'ui.js').write_text('''function login(){$.ajax({url:"/login",type:"POST",contentType:"application/json",
      data:JSON.stringify({username:$("#username").val(),password:$("#password").val()})});}''')
    f=Frontend(p);context=read_static_context({'account':'User alice / secret, no challenge at login'})
    grounder=ContractGrounder(p,f,ContractIndex(p,f),None,context)
    proposals,_=grounder.step('Log in with username and password',ScenarioState(db))
    assert len(proposals)==1
    proposal=proposals[0]
    assert (proposal['site'] is not None) is equivalent
    request=grounded_request(p,proposal['entry'],proposal['params'])
    e=Engine(p,proposal['state']);result=e.run(proposal['entry'],request)
    if equivalent:
        assert 'challenge' not in request.body and result=='approved'
        assert proposal['bindings']['challenge']['consumer_equivalence']
    else:assert request.body['challenge']=='' and result=='empty'
