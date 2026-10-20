"""Bounded JJWT 0.8.0: explicit claims, HS256, standard compact JWS.

No assumed identity/session, provider, key, clock or successful verification.
Other versions, algorithms, serializers and unknown claims stop explicitly.
"""
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from copy import deepcopy
from .java_collections import JavaMap
from .native_arrays import JavaArray
from .java_exceptions import JavaThrow
from .library_versions import declared_version
from .project import text
from .state import U


class Algorithm(str): pass
class Claims(JavaMap): pass
class Builder(dict): pass
class Parser(dict): pass
class Jws(dict): pass


def boundary(reason):
    from .engine import AnalysisBoundary
    raise AnalysisBoundary('JJWT 0.8.0 contract boundary: '+reason,category='unsupported_semantics')


def key(value):
    if isinstance(value,str):
        try:return base64.b64decode(value,validate=True)
        except ValueError:raise JavaThrow({'__type__':'IllegalArgumentException'}) from None
    if isinstance(value,JavaArray) and value.component=='byte' and all(type(item) is int for item in value):
        return bytes(item%256 for item in value)
    boundary('signing key representation is unresolved')


def encoded(value):
    return base64.urlsafe_b64encode(json.dumps(value,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).rstrip(b'=').decode()


def decoded(value):
    return json.loads(base64.urlsafe_b64decode(value+'='*((-len(value))%4)))


def seconds(value):
    if not isinstance(value,datetime):boundary('claim date or analysis clock is unknown')
    return int((value-datetime(1970,1,1)).total_seconds())


def native_call(engine,node,name,receiver,args,reason):
    qualifier=node.child_by_field_name('object')
    static=engine.standard_type(text(qualifier),'io.jsonwebtoken.Jwts')
    if not static and not isinstance(receiver,(Claims,Builder,Parser,Jws)):return False,U
    if declared_version(engine.p,engine.p.methods[engine.method],'io.jsonwebtoken','jjwt')!='0.8.0':
        boundary('source dependency must explicitly select supported version 0.8.0')
    if static:
        if name=='claims' and not args:return True,Claims({},flavor='LinkedHashMap')
        if name=='builder' and not args:return True,Builder(claims=Claims({},flavor='LinkedHashMap'))
        if name=='parser' and not args:return True,Parser()
        boundary('unsupported Jwts factory overload: '+name)
    claim_names={'Subject':'sub','Expiration':'exp','IssuedAt':'iat','NotBefore':'nbf','Issuer':'iss','Audience':'aud','Id':'jti'}
    if isinstance(receiver,(Claims,Builder)):
        claims=receiver['claims'] if isinstance(receiver,Builder) else receiver
        if name.startswith('set') and name[3:] in claim_names and len(args)==1:
            value=args[0];field=claim_names[name[3:]]
            if value is None:claims.remove({'kind':'String','key':field})
            else:claims.put({'kind':'String','key':field},seconds(value) if field in ('exp','iat','nbf') else value,None)
            return True,receiver
        if isinstance(receiver,Claims):
            if name.startswith('get') and name[3:] in claim_names and not args:
                field=claim_names[name[3:]];value=claims.mapping.get(field)
                return True,datetime(1970,1,1)+timedelta(seconds=value) if field in ('exp','iat','nbf') and type(value) is int else value
            # Map methods retain their ordinary Java Map contracts.
            if name in ('put','get','remove','size','isEmpty','containsKey','entrySet','keySet','values'):return False,U
        if isinstance(receiver,Builder):
            if name=='setClaims' and len(args)==1 and isinstance(args[0],JavaMap):
                receiver['claims']=deepcopy(args[0]);return True,receiver
            if name=='signWith' and len(args)==2:
                if not isinstance(args[0],Algorithm) or args[0]!='HS256':boundary('only observed HS256 is supported')
                receiver['key']=key(args[1]);return True,receiver
            if name=='compact' and not args:
                if not receiver.get('key'):boundary('nonempty signing key is not proven')
                payload=engine.json_wire(claims,reason)
                try:message=encoded({'alg':'HS256'})+'.'+encoded(payload)
                except (TypeError,ValueError):boundary('claims contain unresolved or unsupported JSON values')
                signature=base64.urlsafe_b64encode(hmac.new(receiver['key'],message.encode(),hashlib.sha256).digest()).rstrip(b'=').decode()
                engine.remember_reference_kind('String')
                return True,message+'.'+signature
    if isinstance(receiver,Parser):
        if name=='setSigningKey' and len(args)==1:receiver['key']=key(args[0]);return True,receiver
        if name=='parseClaimsJws' and len(args)==1:
            token=args[0]
            if not isinstance(token,str) or not token:raise JavaThrow({'__type__':'IllegalArgumentException'})
            try:
                header,payload,signature=token.split('.')
                metadata=decoded(header);claims=decoded(payload)
                if not isinstance(metadata,dict):raise ValueError('non-object header')
            except (ValueError,TypeError,UnicodeError):raise JavaThrow({'__type__':'io.jsonwebtoken.MalformedJwtException'}) from None
            if metadata.get('alg')!='HS256':raise JavaThrow({'__type__':'io.jsonwebtoken.UnsupportedJwtException'})
            if not receiver.get('key'):boundary('parser signing key is unknown')
            expected=base64.urlsafe_b64encode(hmac.new(receiver['key'],(header+'.'+payload).encode(),hashlib.sha256).digest()).rstrip(b'=').decode()
            if not hmac.compare_digest(expected,signature):raise JavaThrow({'__type__':'io.jsonwebtoken.SignatureException'})
            if not isinstance(claims,dict):raise JavaThrow({'__type__':'io.jsonwebtoken.MalformedJwtException'})
            if any(field in claims for field in ('exp','nbf')):
                seconds(engine.state.now)
                now=(engine.state.now-datetime(1970,1,1)).total_seconds()
                if any(type(claims[field]) not in (int,float) for field in ('exp','nbf') if field in claims):boundary('non-numeric temporal claims')
                if 'exp' in claims and now>claims['exp']:raise JavaThrow({'__type__':'io.jsonwebtoken.ExpiredJwtException'})
                if 'nbf' in claims and now<claims['nbf']:raise JavaThrow({'__type__':'io.jsonwebtoken.PrematureJwtException'})
            return True,Jws(body=Claims(claims,flavor='LinkedHashMap'))
    if isinstance(receiver,Jws) and name=='getBody' and not args:return True,receiver['body']
    boundary('unsupported fluent operation: '+name)
