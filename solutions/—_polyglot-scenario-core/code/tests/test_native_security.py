"""Native library behavior and abstract execution completion are both checked."""
from datetime import datetime,timezone

import jwt
import pytest
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from polygraph.analysis import analyze
from polygraph.ir import Span
from polygraph.kernel import Incomplete,Kernel
from polygraph.security_models import call,decode
from polygraph.values import OpaqueString,TypeRef
from support import edge_set,fixture,scenario

SECRET='native-component-fixture-'+'z'*48
CLOCK='2026-01-02T10:00:00Z'
PAST=int(datetime(2026,1,2,9,tzinfo=timezone.utc).timestamp())
FUTURE=int(datetime(2026,1,2,11,tzinfo=timezone.utc).timestamp())


@pytest.mark.parametrize('claims,options,expected',[
    ({'exp':PAST},{},'ExpiredSignatureError'),
    ({'exp':FUTURE,'nbf':FUTURE},{},'ImmatureSignatureError'),
    ({'exp':PAST,'aud':'wrong'},{},'ExpiredSignatureError'),
    ({'exp':FUTURE,'aud':'wrong'},{},'InvalidAudienceError'),
    ({'sub':17},{},'InvalidSubjectError'),
    ({'exp':PAST},{'verify_exp':False},None),
    ({},{'require':['exp']},'MissingRequiredClaimError'),
])
def test_actual_jwt_claim_order_options_and_explicit_clock(tmp_path,claims,options,expected):
    p,_,_=fixture(tmp_path,{'main.py':'def unused():pass\n'})
    engine=Kernel(p,context={'clock':CLOCK})
    encoded=jwt.encode(claims,SECRET,algorithm='HS256')
    args=(encoded,SECRET,['HS256'],options)  # Positional options are an upstream contract too.
    if expected:
        with pytest.raises(getattr(jwt.exceptions,expected)):decode(engine,args,{},Span())
    else:assert decode(engine,args,{},Span())==claims


def test_unknown_temporal_validation_is_not_a_fabricated_expiration(tmp_path):
    p,_,_=fixture(tmp_path,{'main.py':'def unused():pass\n'})
    token=jwt.encode({'exp':FUTURE},SECRET,algorithm='HS256')
    with pytest.raises(Incomplete):decode(Kernel(p),(token,SECRET),{'algorithms':['HS256']},Span())
    # With the upstream check disabled no clock is required.
    assert decode(Kernel(p),(token,SECRET),{'algorithms':['HS256'],'options':{'verify_exp':False}},Span())=={'exp':FUTURE}


def test_native_password_verification_upgrade_and_opaque_new_hash(tmp_path):
    p,_,_=fixture(tmp_path,{'main.py':'def unused():pass\n'})
    engine=Kernel(p)
    hasher=engine.state.new('pwdlib.hashers.argon2.Argon2Hasher',{'memory_cost':1024,'time_cost':1,'parallelism':1})
    policy=engine.state.new('pwdlib.PasswordHash',{'hashers':[hasher]})
    old_hash=PasswordHash((Argon2Hasher(memory_cost=512,time_cost=1,parallelism=1),)).hash('delta')
    okay,upgraded=call(engine,policy,'verify_and_update',(),{'password':'delta','hash':old_hash},Span())
    assert okay is True and isinstance(upgraded,OpaqueString)
    assert call(engine,policy,'verify',(),{'password':'delta','hash':upgraded},Span()) is True
    assert call(engine,policy,'verify',('wrong',upgraded),{},Span()) is False
    assert upgraded.identity in engine.state.opaque_values and upgraded.nonempty
    assert call(engine,policy,'verify_and_update',('delta',upgraded),{},Span())==(True,None)


@pytest.mark.parametrize('encoded', ['$argon2id$v=19$m=999999,t=3,p=4$MTIzNDU2Nzg$MTIzNDU2Nzg5MDEyMzQ1Ng',
                                     '$2b$31$abcdefghijklmnopqrstuuabcdefghijklmnopqrstuvwxabcdefghi'])
def test_hash_budget_cannot_be_bypassed_by_keyword_argument(tmp_path,encoded):
    p,_,_=fixture(tmp_path,{'main.py':'def unused():pass\n'})
    engine=Kernel(p);policy=engine.state.new('pwdlib.PasswordHash',{'recommended':True})
    with pytest.raises(Incomplete):call(engine,policy,'verify',(),{'password':'value','hash':encoded},Span())


def test_source_exception_with_native_name_does_not_catch_upstream_exception(tmp_path):
    source='''from fastapi import FastAPI
import jwt
app=FastAPI()
class InvalidTokenError(Exception):pass
def mistaken():return "wrong catch"
@app.get("/check")
def check(token:str):
    try:jwt.decode(token,"unused",algorithms=["HS256"])
    except InvalidTokenError:return mistaken()
'''
    p,store,ids=fixture(tmp_path,{'main.py':source})
    block,detail=analyze(p,store,{},scenario({'path':'/check','query':{'token':'malformed'}}))
    assert ids['main.mistaken'] not in {e[2] for e in edge_set(block,'executes')}
    assert detail['paths'][0]['steps'][0]['response']['status']==500


def test_builtin_exception_catch_ignores_unrelated_class_in_another_module(tmp_path):
    source='''from fastapi import FastAPI
import jwt
app=FastAPI()
def caught():return "caught"
@app.get("/check")
def check(token:str):
    try:jwt.decode(token,"unused",algorithms=["HS256"])
    except Exception:return caught()
'''
    p,store,ids=fixture(tmp_path,{'main.py':source,'other.py':'class Exception:pass\n'})
    block,detail=analyze(p,store,{},scenario({'path':'/check','query':{'token':'malformed'}}))
    assert ids['main.caught'] in {e[2] for e in edge_set(block,'executes')}
    assert detail['paths'][0]['steps'][0]['response']['body']=='caught'


def test_conflicting_supplied_native_version_does_not_use_current_library(tmp_path):
    p,_,_=fixture(tmp_path,{'main.py':'def unused():pass\n'})
    engine=Kernel(p,context={'framework_versions':{'app':{'PyJWT':'1.7.1'}}})
    token=jwt.encode({'sub':'person'},SECRET,algorithm='HS256')
    with pytest.raises(Incomplete):decode(engine,(token,SECRET),{'algorithms':['HS256']},Span('main.py',1))


def test_unavailable_native_algorithm_in_positional_argument_cuts_prefix(tmp_path):
    p,_,_=fixture(tmp_path,{'main.py':'def unused():pass\n'})
    engine=Kernel(p)
    with pytest.raises(Incomplete):call(engine,TypeRef('jwt'),'encode',({'sub':'person'},SECRET,'unknown-algorithm'),{},Span())


def test_cyclic_native_argument_does_not_crash_host_recursion(tmp_path):
    p,_,_=fixture(tmp_path,{'main.py':'def unused():pass\n'})
    engine=Kernel(p);cycle=[];cycle.append(cycle)
    with pytest.raises(Incomplete):call(engine,TypeRef('jwt'),'encode',({'payload':cycle},SECRET),{},Span())
