"""Trusted PyJWT/pwdlib primitives and explicit analysis time; no app imports."""
from datetime import datetime, timedelta, timezone
from copy import deepcopy
import time
import inspect

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher
from argon2 import extract_parameters

from .values import Object, OpaqueString, Raised, TypeRef, Unknown, unknown
from .models import NOT_HANDLED
from .native_contracts import check
import builtins

HASHERS={'pwdlib.hashers.argon2.Argon2Hasher':Argon2Hasher,'pwdlib.hashers.bcrypt.BcryptHasher':BcryptHasher}
PURE_FACTORIES={*HASHERS,'pwdlib.PasswordHash','pwdlib.PasswordHash.recommended',
                'sqlmodel.create_engine','sqlalchemy.create_engine','fastapi.security.OAuth2PasswordBearer',
                'datetime.timedelta','builtins.str','str'}
CALLS={'count':0,'seconds':0.}


def concrete(value,active=frozenset()):
    if unknown(value):return False
    if isinstance(value,(dict,tuple,list)):
        if id(value) in active or len(active)>=128:return False
        active=active|{id(value)}
    if isinstance(value,dict):return all(isinstance(k,str) and concrete(v,active) for k,v in value.items())
    if isinstance(value,(tuple,list)):return all(concrete(v,active) for v in value)
    return value is None or type(value) in {str,bytes,bool,int,float,datetime,timedelta}


def clock(engine):
    value=engine.context.get('clock')
    if isinstance(value,str) and 'T' in value:
        try:
            parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
            if parsed.tzinfo is not None:return parsed
        except ValueError:pass
    engine.note('clock-unknown','A timezone-aware analysis instant was not supplied')
    return Unknown('analysis clock is unspecified','datetime')


def native_type(name):
    if not name.startswith(('jwt.','pwdlib.','argon2.')):return None
    from pwdlib import exceptions as password_errors
    from argon2 import exceptions as argon_errors
    modules={'jwt':jwt,'jwt.exceptions':jwt.exceptions,'pwdlib.exceptions':password_errors,'argon2.exceptions':argon_errors}
    prefix,_,short=name.rpartition('.')
    value=getattr(modules.get(prefix),short,None)
    return value if isinstance(value,type) and issubclass(value,Exception) else None


def exception_matches(actual,expected):
    source=native_type(actual)
    if source is None:return False
    target=native_type(expected)
    if target is None and ('.' not in expected or expected.startswith('builtins.')):
        target=getattr(builtins,expected.removeprefix('builtins.'),None)
    return isinstance(target,type) and issubclass(target,Exception) and issubclass(source,target) or expected in {'BaseException','builtins.BaseException'}


def decode(engine,args,kwargs,span):
    check(engine,'PyJWT',span)
    def instant():
        now=clock(engine)
        if isinstance(now,Unknown):engine.unsupported('JWT temporal validation requires an explicit analysis instant',span)
        return now.timestamp()
    # Preserve upstream ordering, option merging, argument binding and errors.
    # The host-clock argument in these three hooks is deliberately discarded.
    # No global monkeypatch or target Python callable is involved.
    class ScenarioJWT(jwt.PyJWT):
        def _validate_iat(self,payload,now,leeway):return super()._validate_iat(payload,instant(),leeway)
        def _validate_nbf(self,payload,now,leeway):return super()._validate_nbf(payload,instant(),leeway)
        def _validate_exp(self,payload,now,leeway):return super()._validate_exp(payload,instant(),leeway)
    return ScenarioJWT().decode(*args,**kwargs)


def password_policy(value):
    if value.fields.get('recommended'):return PasswordHash.recommended()
    hashers=[]
    if not isinstance(value.fields.get('hashers',[]),(tuple,list)):return None
    for hasher in value.fields.get('hashers',[]):
        if not isinstance(hasher,Object) or hasher.typ not in HASHERS:return None
        parameters=hasher.fields
        if not concrete(parameters):return None
        if hasher.typ.endswith('Argon2Hasher') and (parameters.get('memory_cost',65536)>131072 or parameters.get('time_cost',3)>6 or parameters.get('parallelism',4)>8):return None
        if hasher.typ.endswith('BcryptHasher') and parameters.get('rounds',12)>14:return None
        hashers.append(HASHERS[hasher.typ](**parameters))
    return PasswordHash(tuple(hashers)) if hashers else None


def invoke(engine,receiver,name,args,kwargs,span):
    qualified=receiver.name+'.'+name if isinstance(receiver,TypeRef) else name
    if isinstance(receiver,Object) and receiver.typ=='pwdlib.PasswordHash':
        if name not in {'hash','verify','verify_and_update'}:return NOT_HANDLED
        check(engine,'pwdlib',span)
        args=tuple(engine.state.opaque_values.get(v.identity,Unknown('opaque digest unavailable')) if isinstance(v,OpaqueString) else v for v in args)
        kwargs={k:engine.state.opaque_values.get(v.identity,Unknown('opaque digest unavailable')) if isinstance(v,OpaqueString) else v for k,v in kwargs.items()}
        if not concrete((args,kwargs)):
            engine.unsupported('Password operation has an unresolved input and completion',span)
        policy=password_policy(receiver)
        if policy is None:
            engine.unsupported('Password policy is unsupported or exceeds native resource bounds',span)
        bound=inspect.signature(getattr(policy,name)).bind(*args,**kwargs).arguments
        encoded=bound.get('hash')
        if isinstance(encoded,bytes):encoded=encoded.decode('ascii',errors='replace')
        if isinstance(encoded,str):
            if encoded.startswith('$argon2'):
                parameters=extract_parameters(encoded)
                if parameters.memory_cost>131072 or parameters.time_cost>6 or parameters.parallelism>8:
                    engine.unsupported('Encoded password hash exceeds native resource bounds',span)
            elif encoded.startswith(('$2a$','$2b$','$2y$')) and int(encoded.split('$')[2])>14:
                engine.unsupported('Encoded BCrypt work factor exceeds native resource bounds',span)
        result=getattr(policy,name)(*args,**kwargs)
        if name=='hash':return engine.state.opaque_string(result)
        if name=='verify_and_update':return result[0],engine.state.opaque_string(result[1]) if result[1] is not None else None
        return result
    if qualified in HASHERS:
        if args:engine.unsupported('Positional hasher configuration not modeled',span)
        return engine.state.new(qualified,deepcopy(kwargs))
    if qualified=='pwdlib.PasswordHash':
        return engine.state.new(qualified,{'hashers':args[0] if args else kwargs.get('hashers',[])})
    if qualified=='pwdlib.PasswordHash.recommended':
        return engine.state.new('pwdlib.PasswordHash',{'recommended':True})
    if qualified=='datetime.timedelta':
        return timedelta(*args,**kwargs) if concrete((args,kwargs)) else Unknown('duration input unknown','timedelta')
    if qualified in {'datetime.datetime.now','datetime.datetime.utcnow','datetime.datetime.today'}:
        now=clock(engine)
        if isinstance(now,Unknown):return now
        if name=='utcnow':return now.astimezone(timezone.utc).replace(tzinfo=None)
        zone=args[0] if args else kwargs.get('tz')
        if isinstance(zone,TypeRef) and zone.name in {'datetime.UTC','datetime.timezone.utc'}:return now.astimezone(timezone.utc)
        if zone is not None:return Unknown('unsupported timezone','datetime')
        if engine.context.get('timezone')=='UTC':return now.astimezone(timezone.utc).replace(tzinfo=None)
        engine.note('clock-zone-unknown','A local wall-clock operation needs a supplied timezone',span)
        return Unknown('local timezone unspecified','datetime')
    if qualified in {'jwt.encode','jwt.decode'}:
        check(engine,'PyJWT',span)
        if not concrete((args,kwargs)):
            engine.unsupported('JWT operation has unresolved inputs and completion',span)
        available=jwt.algorithms.get_default_algorithms()
        algorithms=[kwargs.get('algorithm','HS256')] if qualified=='jwt.encode' else kwargs.get('algorithms',[])
        if isinstance(algorithms,list) and any(algorithm not in available for algorithm in algorithms):
            engine.unsupported('Requested JWT algorithm is not available in the pinned native build',span)
        return jwt.encode(*args,**kwargs) if qualified=='jwt.encode' else decode(engine,args,kwargs,span)
    return NOT_HANDLED


def call(engine,receiver,name,args,kwargs,span):
    qualified=receiver.name+'.'+name if isinstance(receiver,TypeRef) else name
    if not (isinstance(receiver,Object) and receiver.typ=='pwdlib.PasswordHash' and name in {'hash','verify','verify_and_update'} or qualified in PURE_FACTORIES or qualified in {'datetime.datetime.now','datetime.datetime.utcnow','datetime.datetime.today','jwt.encode','jwt.decode'}):return NOT_HANDLED
    started=time.perf_counter()
    try:return invoke(engine,receiver,name,args,kwargs,span)
    except (jwt.PyJWTError,ValueError,TypeError,OverflowError) as exc:
        raise Raised(type(exc).__module__+'.'+type(exc).__name__,str(exc)) from None
    except NotImplementedError:
        engine.unsupported('Native primitive is unavailable in the pinned build',span)
    except Exception as exc:
        if type(exc).__module__.startswith(('pwdlib.','argon2.')):
            raise Raised(type(exc).__module__+'.'+type(exc).__name__,str(exc)) from None
        raise
    finally:
        CALLS['count']+=1;CALLS['seconds']+=time.perf_counter()-started
