from analyzer.contracts import ContractGrounder,ContractIndex
from analyzer.frontend import Frontend
from analyzer.nl_inputs import language_roles
from analyzer.state import ScenarioState,U
from builders import build


def test_comparative_qualifier_does_not_reverse_from_to_roles():
    assert language_roles('Search route with fewest stops from North to South')=={'origin':'North','destination':'South'}


def test_known_empty_date_return_blocks_ajax_even_outside_an_if(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Input{public String date;}class Api{
      @PostMapping("/changes") String change(@RequestBody Input input){return input.date;}}'''})
    (tmp_path/'page.html').write_text('<input id="date" value=""><script src="ui.js"></script>')
    (tmp_path/'ui.js').write_text('''function change(){if($("#date").val()==""){return;}
      $.ajax({url:"/changes",type:"POST",data:JSON.stringify({date:$("#date").val()})});}''')
    ui=Frontend(project);grounder=ContractGrounder(project,ui,ContractIndex(project,ui),None,{'facts':{}})
    proposals,detail=grounder.step('Change',ScenarioState(db))
    assert proposals==[] and detail.get('blocked_by_known_ui_guard')


def test_new_credentials_reuse_user_input_when_registration_result_is_unknown(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Credentials{public String username;public String password;}
      class Api{@PostMapping("/register") Object register(@RequestBody Credentials input){return null;}
      @PostMapping("/login") Object login(@RequestBody Credentials input){return null;}}'''})
    (tmp_path/'page.html').write_text('<input id="username" value="old-user"><input id="password" value="old-password"><script src="ui.js"></script>')
    (tmp_path/'ui.js').write_text('''function login(){$.ajax({url:"/login",type:"POST",data:JSON.stringify({username:$("#username").val(),password:$("#password").val()})});}''')
    ui=Frontend(project);grounder=ContractGrounder(project,ui,ContractIndex(project,ui),None,{'facts':{}})
    state=ScenarioState(db)
    username=state.fresh_input('username');password=state.fresh_input('password')
    state.input_journal=[{'entry':ids['Api.register'],'action':'Register new account','actor':U,'parameters':{'username':username,'password':password}}]
    state.history=[{'entry':ids['Api.register'],'result':U}]
    proposals,_=grounder.step('Login with new username and password',state)
    assert len(proposals)==1
    proposal=proposals[0]
    assert proposal['params']['username']==username and proposal['params']['password']==password
    assert all(proposal['bindings'][key]['source']=='user_input' for key in ('username','password'))
