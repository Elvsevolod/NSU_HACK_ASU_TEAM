"""Bounded Spring Security contracts; no fabricated authenticated principal."""
from copy import deepcopy
import re

from .state import U
from .project import text
from .java_collections import JavaRecord
from .java_exceptions import JavaThrow
from .models import key_equal
from .request import thaw

TOKEN='org.springframework.security.authentication.UsernamePasswordAuthenticationToken'
ENCODERS=('org.springframework.security.crypto.password.PasswordEncoder',
          'org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder')


def decision(engine,value,reason):
    if type(value) is bool:return value
    chosen=engine.choose(reason,[True,False])
    if chosen is None:
        from .engine import AnalysisBoundary
        raise AnalysisBoundary('security outcome needs isolated success/failure continuations: '+reason,category='unsupported_semantics')
    return chosen


def password_matches(engine,raw,encoded,reason):
    if isinstance(encoded,dict) and '__encoded_from__' in encoded:
        return key_equal(raw,encoded['__encoded_from__'])
    if not isinstance(raw,str) or not isinstance(encoded,str):return U
    if encoded.startswith('{noop}'):return raw==encoded[6:]
    if encoded.startswith(('$2a$','$2b$','$2y$')):
        try:
            import bcrypt
        except ImportError:
            engine.warnings.add('BCrypt verification backend unavailable; password match remains unknown: '+reason)
            return U
        try:return bcrypt.checkpw(raw.encode(),encoded.encode())
        except ValueError:return False
    # Plain strings do not prove use of NoOpPasswordEncoder.
    return U


def source_get(engine,principal,name,reason):
    if not isinstance(principal,JavaRecord):return U
    meta=engine.p.methods[engine.method]
    owner=engine.p.resolve_type(principal.declared_type,meta['module'],meta['file'])
    targets=[target for target in engine.p.inherited_methods(owner,name,0) if not engine.p.methods[target].get('abstract')]
    if len(targets)==1:return engine.invoke(targets[0],[],principal,reason='UserDetails '+name+' callback at '+reason)
    from .bean_properties import generated_accessor
    accessor=generated_accessor(engine.p,owner,name,0,engine.standard_type)
    if accessor:return principal.get(accessor['member'],U)
    engine.warnings.add('UserDetails callback receiver or target is unresolved: '+name+' at '+reason)
    return U


def authenticate(engine,token,reason):
    if not isinstance(token,dict) or token.get('__type__')!=TOKEN:
        from .engine import AnalysisBoundary
        raise AnalysisBoundary('unsupported AuthenticationManager token type: '+reason,category='unsupported_semantics')
    unit=engine.p.ix.unit_of(engine.method)
    candidates=[target for target in engine.p.by_name.get('loadUserByUsername',[])
        if engine.p.ix.unit_of(target)==unit and not engine.p.methods[target].get('abstract')
        and any(parent.rsplit('.',1)[-1]=='UserDetailsService' for parent in engine.p.framework_types.get(engine.p.methods[target]['owner'],()))
        and engine.p.enabled_type(engine.p.methods[target]['owner'])]
    configured=any(re.search(r'\.(?:userDetailsService|setUserDetailsService)\s*\(',source.decode())
        for path,source in engine.p.sources.items() if any(meta['file']==path and engine.p.ix.unit_of(mid)==unit for mid,meta in engine.p.methods.items()))
    if not candidates or not configured:
        from .engine import AnalysisBoundary
        raise AnalysisBoundary('AuthenticationManager provider wiring is not proven by source: '+reason,category='unknown_target')
    if len(candidates)>1:
        selected=engine.choose(reason+':UserDetailsService target',candidates)
        if selected is None:
            from .engine import AnalysisBoundary
            raise AnalysisBoundary('ambiguous UserDetailsService provider: '+reason,category='unknown_target')
    else:selected=candidates[0]
    principal=engine.invoke(selected,[token.get('principal',U)],reason='Spring authentication callback at '+reason)
    if principal is None:raise JavaThrow({'__type__':'UsernameNotFoundException'})
    for method,failure in [('isAccountNonLocked','LockedException'),('isEnabled','DisabledException'),('isAccountNonExpired','AccountExpiredException')]:
        if not decision(engine,source_get(engine,principal,method,reason),reason+':'+method):raise JavaThrow({'__type__':failure})
    stored=source_get(engine,principal,'getPassword',reason)
    raw=token.get('credentials',U)
    if raw is None or not decision(engine,password_matches(engine,raw,stored,reason),reason+':password match'):
        raise JavaThrow({'__type__':'BadCredentialsException'})
    if not decision(engine,source_get(engine,principal,'isCredentialsNonExpired',reason),reason+':credentials expiry'):
        raise JavaThrow({'__type__':'CredentialsExpiredException'})
    authorities=source_get(engine,principal,'getAuthorities',reason)
    return {'__type__':TOKEN,'principal':principal,'credentials':None,'authorities':authorities,'authenticated':True}


def native_call(engine,node,name,receiver,arguments,env,reason):
    objnode=node.child_by_field_name('object')
    declared=engine.source_type(objnode)
    if name=='authenticate' and engine.standard_type(declared,'org.springframework.security.authentication.AuthenticationManager') and len(arguments)==1:
        return True,authenticate(engine,arguments[0],reason)
    if name in ('encode','matches') and any(engine.standard_type(declared,typ) for typ in ENCODERS):
        if name=='matches' and len(arguments)==2:return True,password_matches(engine,*arguments,reason)
        if name=='encode' and len(arguments)==1:
            engine.remember_reference_kind('String')
            if arguments[0] is None:raise JavaThrow({'__type__':'IllegalArgumentException'})
            value=engine.state.generated_value('String','PasswordEncoder.encode')
            value['__encoded_from__']=deepcopy(arguments[0]);value['__encoding_contract__']=declared
            return True,value
    if isinstance(receiver,dict) and receiver.get('__type__')==TOKEN and not arguments:
        fields={'getPrincipal':'principal','getCredentials':'credentials','getAuthorities':'authorities','isAuthenticated':'authenticated'}
        if name in fields:return True,receiver.get(fields[name],U)
        if name=='getName':
            value=receiver.get('principal',U)
            engine.remember_reference_kind('String')
            return True,source_get(engine,value,'getUsername',reason) if isinstance(value,JavaRecord) else value
    if name=='<init>':
        written=text(node.child_by_field_name('type'))
        if engine.standard_type(written,TOKEN) and len(arguments) in (2,3):
            return True,{'__type__':TOKEN,'principal':arguments[0],'credentials':arguments[1],
                'authorities':arguments[2] if len(arguments)==3 else [],'authenticated':len(arguments)==3}
        if engine.standard_type(written,'org.springframework.security.core.authority.SimpleGrantedAuthority') and len(arguments)==1:
            if not isinstance(arguments[0],str):return True,U
            if not arguments[0].strip():raise JavaThrow({'__type__':'IllegalArgumentException'})
            return True,{'__type__':'org.springframework.security.core.authority.SimpleGrantedAuthority','authority':arguments[0]}
    if name=='getAuthority' and isinstance(receiver,dict) and receiver.get('__type__')=='org.springframework.security.core.authority.SimpleGrantedAuthority' and not arguments:
        engine.remember_reference_kind('String');return True,receiver.get('authority',U)
    return False,U


def authorize_request(engine,target,args,request):
    """Evaluate the supported method guard against supplied post-auth facts."""
    if request is None:return None
    context=thaw(request.session)
    if not isinstance(context,dict) or 'authenticated' not in context:return None
    meta=engine.p.methods[target]
    annotations=[*engine.p.nodes[meta['owner']].get('annotations',[]),*meta.get('annotations',[])]
    annotation=next((item for item in annotations if item['name'].rsplit('.',1)[-1]=='PreAuthorize'),None)
    if annotation is None:return True
    raw=annotation.get('args','').strip()
    if not raw.startswith('("') or not raw.endswith('")'):return None
    expression=raw[2:-2]
    parameters=dict(zip((name for name,_ in engine.p.parameters(target)),args))
    def atom(value):
        value=value.strip()
        scope=re.fullmatch(r"#oauth2\.hasScope\('([^']+)'\)",value)
        if scope:
            oauth=context.get('oauth2_request')
            return bool(context.get('authenticated')) and isinstance(oauth,dict) and scope[1] in oauth.get('scope',[])
        equal=re.fullmatch(r"#(\w+)\.equals\('([^']*)'\)",value)
        if equal:return key_equal(parameters.get(equal[1],U),equal[2])
        role=re.fullmatch(r"hasRole\('([^']+)'\)",value)
        if role:return 'ROLE_'+role[1] in context.get('authorities',[])
        return U
    alternatives=[]
    for group in re.split(r'\s+or\s+',expression):
        values=[atom(value) for value in re.split(r'\s+and\s+',group)]
        alternatives.append(False if False in values else U if U in values else True)
    result=True if True in alternatives else U if U in alternatives else False
    if result is U:
        engine.assume('method authorization expression is outside the supported supplied-context contract: '+target)
        return None
    return result
