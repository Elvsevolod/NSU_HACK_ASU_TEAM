from datetime import datetime
import pytest
from analyzer.__main__ import analyze
from analyzer.contracts import ContractGrounder,ContractIndex
from analyzer.frontend import Frontend
from analyzer.state import ScenarioState,U
from builders import build
from test_jjwt_authenticated_requests import fixture


UI='''angular.module("app",[]).controller("Session",function($scope,$http){
 $scope.login=function(){$http({method:"POST",url:"/login",data:{name:$("#name").val(),password:$("#password").val()}})
 .success(function(data,status){if(status==200 && data.name){sessionStorage.setItem("login_token",data.token);}})
 .error(function(failure){sessionStorage.removeItem("login_token");});};
 $scope.read=function(){$http({method:"GET",url:"/protected",headers:{Authorization:"Bearer "+sessionStorage.getItem("login_token")}});};
});'''


def attach(root,ui=UI,version='1.5.8'):
    (root/'ui.js').write_text(ui)
    (root/'page.html').write_text('<html ng-app="app"><script src="https://code.angularjs.org/'+version+'/angular.js"></script><script src="ui.js"></script></html>')


def test_source_login_token_passes_angular_storage_into_protected_http_without_insertion(tmp_path):
    project,db,ids=fixture(tmp_path);attach(tmp_path)
    frontend=Frontend(project)
    scenario={'id':'angular-session','steps':[{'n':1,'action':'As alice, login name "alice" password "secret"'},
        {'n':2,'action':'As alice, read protected'}]}
    _,trace=analyze(project,frontend,ContractIndex(project,frontend),None,db,
        {'facts':{},'unresolved':[],'clock':datetime(2026,10,18)},scenario,path_limit=4,grounder_type=ContractGrounder)
    login=trace['steps'][0]['alternatives'][0];read=trace['steps'][1]['alternatives'][0]
    assert isinstance(login['result']['token'],str)
    assert login['state_after']['browser']['storage']['login_token']==login['result']['token']
    assert read['request']['headers']['authorization']==['Bearer '+login['result']['token']]
    assert read['result']=='protected-data'


def test_adjacent_http_calls_keep_their_own_success_callback_and_error_guard(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{@GetMapping("/first")String first(){return "one";}
      @GetMapping("/second")String second(){return "two";}}'''})
    attach(tmp_path,'''var app=angular.module("app",[]);app.controller("Session",function($http){
      $http({url:"/first",method:"GET"}).success(function(data){sessionStorage.setItem("first",data);});
      $http({url:"/second",method:"GET"}).success(function(data){sessionStorage.setItem("second",data);})
        .error(function(){sessionStorage.removeItem("second");});});''')
    frontend=Frontend(p);state=ScenarioState(db)
    first=next(s for s in frontend.sites.values() if ids['Api.first'] in s['handlers'])
    second=next(s for s in frontend.sites.values() if ids['Api.second'] in s['handlers'])
    frontend.apply_response(first,'one',state,200)
    assert state.browser['storage']=={'first':'one'}
    frontend.apply_response(second,'two',state,200)
    assert state.browser['storage']=={'first':'one','second':'two'}
    frontend.apply_response(second,U,state,401)
    assert state.browser['storage']=={'first':'one'}


@pytest.mark.parametrize('source,version',[
    ('function inner($http){$http({url:"/first",method:"GET"}).success(function(data){sessionStorage.setItem("unsafe",data);});}inner(fake);','1.5.8'),
    ('$http({url:"/first",method:"GET"}).then(function(response){sessionStorage.setItem("unsafe",response);});','1.5.8'),
    ('$http({url:"/first",method:"GET"}).success(function(data){sessionStorage.setItem("unsafe",data);});','1.8.2'),
])
def test_shadowed_injection_then_envelope_and_removed_api_are_not_legacy_success(tmp_path,source,version):
    p,db,_=build(tmp_path,{'Api.java':'class Api{@GetMapping("/first")String first(){return "value";}}'})
    attach(tmp_path,'angular.module("app",[]).controller("Session",function($http){'+source+'});',version)
    frontend=Frontend(p);state=ScenarioState(db)
    for site in frontend.sites.values():frontend.apply_response(site,'value',state,200)
    assert state.browser['storage']=={}
