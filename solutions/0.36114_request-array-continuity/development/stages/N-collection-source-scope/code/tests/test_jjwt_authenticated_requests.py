"""Login -> signed result -> real Authorization header -> source filter.

There is no pre-supplied successful token or authenticated session.
"""
from datetime import datetime, timedelta
import json
import base64
import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.request import Request, MISSING
from analyzer.state import ScenarioState, U
from builders import build
from test_regression_authentication import SOURCE


JWT_SOURCE = '''import io.jsonwebtoken.*;import java.util.*;
 import org.springframework.http.*;import org.springframework.web.bind.annotation.*;
 import org.springframework.security.authentication.*;import org.springframework.security.core.*;
 import org.springframework.web.filter.OncePerRequestFilter;import javax.servlet.*;import javax.servlet.http.*;
 class Credentials{public String name;public String password;}
 class SessionToken{public String token;public String name;}
 class Login {AuthenticationManager manager;
  @PostMapping("/login") ResponseEntity<SessionToken> login(@RequestBody Credentials input){
   try{Authentication authenticated=manager.authenticate(new UsernamePasswordAuthenticationToken(input.name,input.password));
    Claims claims=Jwts.claims().setSubject(authenticated.getName());claims.put("roles",Arrays.asList("reader"));
    String token=Jwts.builder().setClaims(claims).setIssuedAt(new Date()).setExpiration(new Date(new Date().getTime()+60000L))
       .signWith(SignatureAlgorithm.HS256,"c2VjcmV0").compact();
    SessionToken result=new SessionToken();result.token=token;result.name=authenticated.getName();return ResponseEntity.ok(result);
   }catch(AuthenticationException failure){return new ResponseEntity<SessionToken>(null,HttpStatus.UNAUTHORIZED);}}
  @GetMapping("/protected") String read(){return "protected-data";}
 }
 class Gate extends OncePerRequestFilter {
  void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain){
   if(req.getRequestURI().equals("/protected")){
    String header=req.getHeader("Authorization");if(header==null){res.setStatus(401);return;}
    try{Claims claims=Jwts.parser().setSigningKey("c2VjcmV0").parseClaimsJws(header.substring(7)).getBody();
     if(!claims.getSubject().equals("alice")){res.setStatus(403);return;}}
    catch(JwtException failure){res.setStatus(401);return;}
   }chain.doFilter(req,res);
  }
 }'''


def fixture(root, version='0.8.0'):
    root.mkdir(parents=True,exist_ok=True)
    (root/'pom.xml').write_text('<project><dependencies><dependency><groupId>io.jsonwebtoken</groupId>'
        '<artifactId>jjwt</artifactId><version>'+version+'</version></dependency></dependencies></project>')
    return build(root,{'Security.java':SOURCE,'Web.java':JWT_SOURCE})


@pytest.mark.parametrize('name,password,status',[('alice','secret',True),('alice','wrong',False),('disabled','secret',False)])
def test_password_status_and_first_request_result(tmp_path,name,password,status):
    project,db,ids=fixture(tmp_path)
    state=ScenarioState(db,{'clock':datetime(2026,10,18)})
    request=Request.http('service','POST','/login',{'Content-Type':'application/json'},{'name':name,'password':password})
    paths=run_paths(project,state,ids['Login.login'],request,limit=1)
    assert len(paths)==1
    result=paths[0]['result'];engine=paths[0]['engine']
    if status:
        assert result['name']==name and isinstance(result['token'],str)
        claims=json.loads(base64.urlsafe_b64decode(result['token'].split('.')[1]+'=='))
        assert claims['sub']==name and claims['roles']==['reader']
        assert sorted(engine.warnings)==['request filter registration is assumed from source classes; full bean registration is not modeled']
    else:
        assert result is None and engine.outcome=='HTTP error response'
        assert not any('opaque call' in warning for warning in engine.warnings)


@pytest.mark.parametrize('actor,alter,elapsed,expected', [
    ('alice',False,0,'protected-data'),('bob',False,0,None),
    ('alice',True,0,None),('alice',False,61,None),
])
def test_actual_login_token_controls_next_protected_request(tmp_path,actor,alter,elapsed,expected):
    project,db,ids=fixture(tmp_path)
    clock=datetime(2026,10,18);state=ScenarioState(db,{'clock':clock})
    login=Request.http('service','POST','/login',{'Content-Type':'application/json'},{'name':actor,'password':'secret'})
    first=Engine(project,state);result=first.run(ids['Login.login'],login)
    assert isinstance(result,dict) and result['name']==actor
    token=result['token']
    if alter:token=token.rsplit('.',1)[0]+'.invalid'
    first.state.now=clock+timedelta(seconds=elapsed)
    protected=Request.http('service','GET','/protected',{'Authorization':'Bearer '+token},MISSING)
    second=Engine(project,first.state)
    observed=second.run(ids['Login.read'],protected)
    if expected is not None:assert observed==expected
    else:
        assert observed is U and second.outcome=='request stopped by filter'
        assert second.http_responses[-1]['status']==(403 if actor=='bob' else 401)
    entered=ids['Login.read'] in {target for _,kind,target in second.edges if kind=='executes'}
    assert entered is (expected is not None)
    assert sorted(second.warnings)==['request filter registration is assumed from source classes; full bean registration is not modeled']


def test_unknown_library_version_is_explicitly_unsupported(tmp_path):
    project,db,ids=fixture(tmp_path,'0.12.0')
    state=ScenarioState(db,{'clock':datetime(2026,10,18)})
    request=Request.http('service','POST','/login',{'Content-Type':'application/json'},{'name':'alice','password':'secret'})
    engine=Engine(project,state);engine.run(ids['Login.login'],request)
    assert engine.outcome=='unsupported_semantics boundary'
    assert any('version 0.8.0' in warning for warning in engine.warnings)
