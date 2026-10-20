import pytest

from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from builders import build


SOURCE='''import java.util.*;import java.util.stream.Collectors;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
class Profile implements UserDetails {
 String username;String password;boolean enabled;
 Profile(String name,String secret,boolean flag){username=name;password=secret;enabled=flag;}
 public String getUsername(){return username;}
 public String getPassword(){return password;}
 public boolean isAccountNonExpired(){return true;}
 public boolean isAccountNonLocked(){return true;}
 public boolean isCredentialsNonExpired(){return true;}
 public boolean isEnabled(){return enabled;}
 public List<SimpleGrantedAuthority> getAuthorities(){return Arrays.asList("ROLE_READER").stream().map(SimpleGrantedAuthority::new).collect(Collectors.toList());}
}
class Provider implements UserDetailsService {
 public UserDetails loadUserByUsername(String name){return new Profile(name,"{noop}secret",!name.equals("disabled"));}
}
class Config {UserDetailsService service;void configure(AuthenticationManagerBuilder builder){builder.userDetailsService(service);}}
class Api {AuthenticationManager manager;
 boolean entry(String name,String password){try{return manager.authenticate(new UsernamePasswordAuthenticationToken(name,password)).isAuthenticated();}
 catch(AuthenticationException failure){return false;}}
}'''


@pytest.mark.parametrize('name,password,expected',[('alice','secret',True),('alice','wrong',False),('disabled','secret',False)])
def test_authentication_uses_loaded_principal_and_actual_password_status(tmp_path,name,password,expected):
    project,db,ids=build(tmp_path,{'Api.java':SOURCE})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{'name':name,'password':password},limit=1)
    assert {row['result'] for row in outcomes}=={expected}
    for row in outcomes:
        engine=row['engine']
        assert not any(event['operation']=='authenticate' for event in engine.effect_events)
        executed={target for _,relation,target in engine.edges if relation=='executes'}
        assert ids['Provider.loadUserByUsername'] in executed
        assert (ids['Profile.getAuthorities'] in executed) is expected


def test_password_and_authority_callbacks_share_the_loaded_receiver(tmp_path,monkeypatch):
    project,db,ids=build(tmp_path,{'Api.java':SOURCE})
    invoke=Engine.invoke;loaded=[];receivers=[]
    def observe(self,mid,args,receiver=None,*extra,**kwargs):
        if mid.startswith('method:service:Profile#') and not '#<init>' in mid:receivers.append(receiver)
        result=invoke(self,mid,args,receiver,*extra,**kwargs)
        if mid==ids['Provider.loadUserByUsername']:loaded.append(result)
        return result
    monkeypatch.setattr(Engine,'invoke',observe)
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{'name':'alice','password':'secret'}) is True
    assert len(loaded)==1 and receivers and all(receiver is loaded[0] for receiver in receivers)


def test_constructor_reference_is_a_lazy_stream_callback(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import java.util.stream.Collectors;
      class Value {String text;Value(String input){text=input;}}
      class Api {String entry(){return Arrays.asList("first","second").stream().map(Value::new).collect(Collectors.toList()).get(1).text;}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{},limit=1)
    assert {row['result'] for row in outcomes}=={'second'}
    assert all(('', 'executes',ids['Value.<init>']) in row['engine'].edges for row in outcomes)
