from datetime import datetime
import pytest
from analyzer.__main__ import analyze
from analyzer.actors import actor_role
from analyzer.contracts import ContractGrounder,ContractIndex,read_static_context
from analyzer.frontend import Frontend
from analyzer.state import ScenarioState,U
from builders import build
from test_angular_legacy_session import UI,attach
from test_jjwt_authenticated_requests import JWT_SOURCE
from test_regression_authentication import SOURCE


def fixture(root):
    (root/'pom.xml').write_text('<project><dependencies><dependency><groupId>io.jsonwebtoken</groupId><artifactId>jjwt</artifactId><version>0.8.0</version></dependency></dependencies></project>')
    security=SOURCE.replace('new Profile(name,"{noop}secret",','new Profile(name,name.equals("bob")?"{noop}bravo":"{noop}secret",')
    api=JWT_SOURCE.replace('Credentials{public String name;','Credentials{public String username;').replace('input.name,','input.username,')
    p,db,ids=build(root,{'Security.java':security,'Web.java':api})
    attach(root,UI.replace('data:{name:$("#name").val()','data:{username:$("#username").val()'))
    return p,db,ids


def test_two_actor_credentials_login_callbacks_headers_and_return_keep_ownership(tmp_path):
    project,db,_=fixture(tmp_path);frontend=Frontend(project)
    context=read_static_context({'accounts':{'alice':{'username':'alice','password':'secret'},
        'bob':{'username':'bob','password':'bravo'}},'date':'System clock 18 October 2026'})
    scenario={'id':'two-actors','steps':[{'n':i+1,'action':action} for i,action in enumerate([
        'Log in as alice with username and password','As alice, read protected',
        'Log in as bob with username and password','As bob, read protected','As alice, read protected'])]}
    _,report=analyze(project,frontend,ContractIndex(project,frontend),None,db,context,scenario,path_limit=4,grounder_type=ContractGrounder)
    rows=[step['alternatives'][0] for step in report['steps']]
    assert rows[0]['parameters']['username']=='alice' and rows[0]['parameters']['password']=='secret'
    assert rows[2]['parameters']['username']=='bob' and rows[2]['parameters']['password']=='bravo'
    first=rows[0]['result']['token'];second=rows[2]['result']['token']
    assert first!=second
    assert rows[1]['request']['headers']['authorization']==['Bearer '+first]
    assert rows[3]['request']['headers']['authorization']==['Bearer '+second]
    assert rows[3]['responses'][-1]['status']==403
    assert rows[4]['request']['headers']['authorization']==['Bearer '+first] and rows[4]['result']=='protected-data'
    assert [row['request']['actor'] for row in rows]==['alice','alice','bob','bob','alice']
    assert rows[0]['bindings']['username']['reference']=='actor[alice].username'


def test_missing_admin_context_never_borrows_passenger_defaults_or_init_password(tmp_path):
    p,db,ids=fixture(tmp_path);frontend=Frontend(p)
    context=read_static_context({'account':'The passenger is the pre-registered user alice / secret'})
    grounder=ContractGrounder(p,frontend,ContractIndex(p,frontend),None,context)
    proposals,_=grounder.step("Log in to the admin console with the administrator's username and password",ScenarioState(db))
    assert proposals
    for proposal in proposals:
        assert proposal['actor']=='admin'
        assert proposal['params'].get('username',U) is U
        assert proposal['params'].get('password',U) is U
        assert any('No established credentials for actor admin' in message for message in proposal['unresolved'])


def test_role_aliases_share_one_browser_namespace_and_preserve_other_actor(tmp_path):
    _,db,_=build(tmp_path,{'Api.java':'class Api{void entry(){}}'})
    state=ScenarioState(db);state.select_actor('administrator');state.browser['storage']['staff']='one'
    state.select_actor('passenger');state.browser['storage']['visitor']='two'
    state.select_actor('admin')
    assert state.browser['actor']=='admin' and state.browser['storage']=={'staff':'one'}
    state.select_actor('passenger');assert state.browser['storage']=={'visitor':'two'}


@pytest.mark.parametrize('text,actor',[
    ("Log in to the admin console with the administrator's username and password",'admin'),
    ('Log in as a passenger with username and password','passenger'),
    ('Sign in with the administrator account','admin'),
    ('As administrator, list documents','admin'),('Return to alice','alice'),
])
def test_explicit_actor_paraphrases(text,actor):
    assert actor_role(text)==actor
