from analyzer.__main__ import analyze
from analyzer.contracts import ContractGrounder,ContractIndex
from analyzer.frontend import Frontend
from analyzer.request import grounded_request,Request
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build
from test_regression_authentication import SOURCE as SECURITY_SOURCE


SECURITY_PREFIX=SECURITY_SOURCE[:SECURITY_SOURCE.index('class Api {')]
SOURCE=SECURITY_PREFIX+'''class Credentials {public String username;public String password;}
class Session {public boolean success;public String token;
 Session(boolean ok,String value){success=ok;token=value;}}
class Api {AuthenticationManager manager;
 @PostMapping("/login") Session login(@RequestBody Credentials input){
  try{if(manager.authenticate(new UsernamePasswordAuthenticationToken(input.username,input.password)).isAuthenticated()){
      return new Session(true,input.username+"-token");}}
  catch(AuthenticationException failure){return new Session(false,null);}
  return new Session(false,null);}
 @GetMapping("/secure") String secure(@RequestHeader("Authorization") String bearer,@RequestHeader HttpHeaders headers){return bearer;}
}'''
UI='''function login(){$.ajax({url:"/login",type:"POST",contentType:"application/json",
 data:JSON.stringify({username:$("#username").val(),password:$("#password").val()}),
 success:function(r){if(r.success){sessionStorage.setItem("token",r.token);}else{sessionStorage.removeItem("token");}},
 error:function(){sessionStorage.removeItem("token");}});}
function secure(){$.ajax({url:"/secure",type:"GET",headers:{Authorization:sessionStorage.getItem("token")}});}'''


def test_login_storage_headers_binding_and_failed_clear_are_one_chain(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':SOURCE})
    (tmp_path/'ui.js').write_text(UI)
    ui=Frontend(project);index=ContractIndex(project,ui)
    scenario={'id':'browser-chain','steps':[
        {'n':1,'action':'As alice, login username "alice" password "secret"'},
        {'n':2,'action':'As alice, secure'},
        {'n':3,'action':'As bob, secure'},
        {'n':4,'action':'As alice, login username "alice" password "wrong"'},
        {'n':5,'action':'As alice, secure'},
    ]}
    _,report=analyze(project,ui,index,None,db,{'facts':{},'unresolved':[]},scenario,grounder_type=ContractGrounder)
    rows=[step['alternatives'][0] for step in report['steps']]
    assert rows[0]['result']=={'success':True,'token':'alice-token'}
    assert rows[1]['result']=='alice-token'
    assert rows[1]['request']['headers']['authorization']==['alice-token']
    assert 'headers' not in rows[1]['request']['headers']
    assert rows[2]['result']!='alice-token'
    assert rows[3]['result']=={'success':False,'token':None}
    assert 'token' not in rows[3]['state_after']['browser']['storage']
    assert rows[4]['result']!='alice-token'


def test_ui_and_explicit_header_requests_have_identical_wire_arguments_and_events(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':SOURCE})
    (tmp_path/'ui.js').write_text(UI)
    ui=Frontend(project);site=next(site for site in ui.sites.values() if ids['Api.secure'] in site['handlers'])
    state=ScenarioState(db);state.browser['storage']['token']='shared-value'
    request=grounded_request(project,ids['Api.secure'],{},source_headers=ui.request_headers(site,state))
    explicit=Request.http('service','GET','/secure',{'Authorization':'shared-value','__rest_unknown__':True})
    engines=[Engine(project,ScenarioState(db)) for _ in range(2)]
    assert [engine.run(ids['Api.secure'],value) for engine,value in zip(engines,[request,explicit])]==['shared-value']*2
    assert engines[0].edges==engines[1].edges
    assert engines[0].bind_request(ids['Api.secure'],request,'check')==engines[1].bind_request(ids['Api.secure'],explicit,'check')


def test_failed_http_callback_clears_source_storage(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':SOURCE})
    (tmp_path/'ui.js').write_text(UI)
    ui=Frontend(project);site=next(site for site in ui.sites.values() if ids['Api.login'] in site['handlers'])
    state=ScenarioState(db);state.browser['storage']['token']='stale'
    ui.apply_response(site,U,state,status=401)
    assert 'token' not in state.browser['storage']
