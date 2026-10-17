"""Framework boundaries on contracts unrelated to the public benchmark app."""
from datetime import datetime,timezone
import jwt
import pytest

from polygraph.analysis import analyze
from support import fixture,scenario,edge_set


@pytest.mark.parametrize('header,status', [(None,401),('Basic abc',401),('bEaReR value-17',200),('Bearer ',200)])
def test_native_bearer_header_and_auto_error_semantics(tmp_path,header,status):
    source='''from fastapi import FastAPI,Depends
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
app=FastAPI()
credential=OAuth2PasswordBearer(tokenUrl="/issue")
@app.get("/private")
def private(token:Annotated[str,Depends(credential)]):return token
'''
    p,store,ids=fixture(tmp_path,{'main.py':source})
    block,detail=analyze(p,store,{},scenario({'path':'/private','headers':{} if header is None else {'AUTHORIZATION':header}}))
    step=detail['paths'][0]['steps'][0]
    assert len(detail['paths'])==1 and step['response']['status']==status
    assert bool(edge_set(block,'executes'))==(status==200)
    if status==401:assert step['response']['headers']=={'WWW-Authenticate':'Bearer'}
    else:assert step['response']['body']==header.partition(' ')[2]


@pytest.mark.parametrize('form,status', [({'username':'delta','password':'valid','scope':'read write','grant_type':'password'},200),
                                       ({'username':'delta','password':'valid','grant_type':'client_credentials'},422),
                                       ({'username':'delta','grant_type':'password'},422)])
def test_native_oauth_form_uses_actual_signature_validation(tmp_path,form,status):
    source='''from fastapi import FastAPI,Depends
from fastapi.security import OAuth2PasswordRequestFormStrict as Credentials
from typing import Annotated
app=FastAPI()
@app.post("/issue")
def issue(value:Annotated[Credentials,Depends()]):return {"handle":value.username,"roles":value.scopes}
'''
    p,store,_=fixture(tmp_path,{'main.py':source})
    block,detail=analyze(p,store,{},scenario({'path':'/issue','method':'POST','form':form}))
    response=detail['paths'][0]['steps'][0]['response']
    assert response['status']==status
    assert bool(edge_set(block,'executes'))==(status==200)
    if status==200:assert response['body']=={'handle':'delta','roles':['read','write']}


def test_native_body_alias_constraints_response_alias_and_extra_filtering(tmp_path):
    source='''from fastapi import FastAPI
from pydantic import BaseModel,Field
app=FastAPI()
class Input(BaseModel):
    internal:str=Field(alias="wireName",min_length=2,max_length=5)
class Public(BaseModel):
    visible:str=Field(serialization_alias="display")
@app.post("/transform",response_model=Public)
def transform(value:Input):return {"visible":value.internal,"private":"must disappear"}
'''
    p,store,_=fixture(tmp_path,{'main.py':source})
    _,detail=analyze(p,store,{},scenario({'method':'POST','path':'/transform','body':{'wireName':'okay'}}))
    assert detail['paths'][0]['steps'][0]['response']['body']=={'display':'okay'}
    block,detail=analyze(p,store,{},scenario({'method':'POST','path':'/transform','body':{'wireName':'x'}}))
    assert not edge_set(block)
    assert detail['paths'][0]['steps'][0]['response']['status']==422


def test_schema_cache_does_not_reuse_other_initial_globals(tmp_path):
    source='''from fastapi import FastAPI
from pydantic import BaseModel,Field
MINIMUM=1
app=FastAPI()
class Input(BaseModel):text:str=Field(min_length=MINIMUM)
@app.post("/value")
def value(item:Input):return item.text
'''
    p,store,_=fixture(tmp_path,{'main.py':source})
    request=scenario({'path':'/value','method':'POST','body':{'text':'ab'}})
    _,a=analyze(p,store,{'globals':{'main.MINIMUM':1}},request)
    _,b=analyze(p,store,{'globals':{'main.MINIMUM':3}},request)
    assert a['paths'][0]['steps'][0]['response']['status']==200
    assert b['paths'][0]['steps'][0]['response']['status']==422


def test_cached_native_factory_uses_current_engine_and_runs_once_before_handler(tmp_path):
    source='''from fastapi import FastAPI
from pydantic import BaseModel,Field
from sqlmodel import SQLModel,Session,create_engine
from sqlmodel import Field as Column
app=FastAPI()
class Row(SQLModel,table=True):
    id:int=Column(primary_key=True)
    text:str
def choose():
    with Session(create_engine("postgresql://u:p@db/example")) as session:return session.get(Row,1).text
class Input(BaseModel):text:str=Field(default_factory=choose)
@app.post("/value")
def value(item:Input):return item.text
'''
    p,store,ids=fixture(tmp_path,{'main.py':source},['row'],{'row':[{'id':1,'text':'before'}]})
    request=scenario({'path':'/value','method':'POST','body':{}})
    first,one=analyze(p,store,{},request)
    store.replace('storage:row',[{'id':1,'text':'after'}])
    second,two=analyze(p,store,{},request)
    assert one['paths'][0]['steps'][0]['response']['body']=='before'
    assert two['paths'][0]['steps'][0]['response']['body']=='after'
    assert len([event for event in two['paths'][0]['events'] if event.get('kind')=='http'])==1
    assert edge_set(first)==edge_set(second)=={('scenario:arbitrary','executes',ids['main.choose']),('scenario:arbitrary','executes',ids['main.value']),(ids['main.choose'],'data','storage:row')}


def test_native_uuid_import_is_not_confused_with_unrelated_source_class(tmp_path):
    source='''from fastapi import FastAPI
from uuid import UUID
app=FastAPI()
@app.get("/value")
def value(id:UUID):return id
'''
    other='''from pydantic import BaseModel
class UUID(BaseModel):fake:str
'''
    p,store,_=fixture(tmp_path,{'main.py':source,'other.py':other})
    _,detail=analyze(p,store,{},scenario({'path':'/value','query':{'id':'10000000-0000-4000-8000-000000000001'}}))
    assert detail['paths'][0]['steps'][0]['response']['body']=='10000000-0000-4000-8000-000000000001'


def test_declared_module_function_with_library_name_is_not_replayed_as_factory(tmp_path):
    source='''from fastapi import FastAPI
from pwdlib import PasswordHash
app=FastAPI()
policy=PasswordHash.recommended()
@app.get("/value")
def value():return policy
'''
    custom='''class PasswordHash:
    @classmethod
    def recommended(cls):return {"source":"initialized before scenario"}
'''
    p,store,ids=fixture(tmp_path,{'main.py':source,'pwdlib/__init__.py':custom})
    block,detail=analyze(p,store,{},scenario({'path':'/value'}))
    assert ids['__init__.recommended'] not in {e[2] for e in edge_set(block,'executes')}
    assert any(d['code']=='definition-time-value' for d in detail['paths'][0]['diagnostics'])


def test_jwt_missing_clock_does_not_confirm_code_after_temporal_validation(tmp_path):
    secret='fixture-key-'+ 'm'*48
    source='''from fastapi import FastAPI
import jwt
app=FastAPI()
def accepted():return "accepted"
@app.get("/value")
def value(token:str):
    jwt.decode(token,SECRET,algorithms=["HS256"])
    return accepted()
'''.replace('SECRET',repr(secret))
    p,store,ids=fixture(tmp_path,{'main.py':source})
    token=jwt.encode({'sub':'person','exp':datetime(2026,1,3,tzinfo=timezone.utc)},secret,algorithm='HS256')
    block,detail=analyze(p,store,{},scenario({'path':'/value','query':{'token':token}}))
    assert ids['main.accepted'] not in {e[2] for e in edge_set(block,'executes')}
    assert detail['status']=='partial'


def test_source_default_factory_receives_native_validated_data_once(tmp_path):
    source='''from fastapi import FastAPI
from pydantic import BaseModel,Field
app=FastAPI()
COUNT=0
def calculate(data):
    global COUNT
    COUNT+=1
    return data["quantity"]+7
class Input(BaseModel):
    quantity:int
    total:int=Field(default_factory=calculate)
@app.post("/value")
def value(item:Input):return {"quantity":item.quantity,"total":item.total,"count":COUNT}
'''
    p,store,ids=fixture(tmp_path,{'main.py':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':{'quantity':'2'}}))
    assert detail['paths'][0]['steps'][0]['response']['body']=={'quantity':2,'total':9,'count':1}
    assert edge_set(block)=={('scenario:arbitrary','executes',ids['main.calculate']),('scenario:arbitrary','executes',ids['main.value'])}


def test_unbuilt_schema_keeps_initial_metadata_after_runtime_global_write(tmp_path):
    source='''from fastapi import FastAPI
from pydantic import BaseModel,Field
MINIMUM=1
app=FastAPI()
class Input(BaseModel):text:str=Field(min_length=MINIMUM)
@app.post("/change")
def change():
    global MINIMUM
    MINIMUM=20
@app.post("/value")
def value(item:Input):return item.text
'''
    p,store,_=fixture(tmp_path,{'main.py':source})
    _,detail=analyze(p,store,{},scenario({'path':'/change','method':'POST'}, {'path':'/value','method':'POST','body':{'text':'abc'}}))
    assert [step['response']['status'] for step in detail['paths'][0]['steps']]==[200,200]
    assert detail['paths'][0]['steps'][1]['response']['body']=='abc'


def test_source_validator_is_reported_before_confirming_handler(tmp_path):
    source='''from fastapi import FastAPI
from pydantic import BaseModel,field_validator
app=FastAPI()
class Input(BaseModel):
    text:str
    @field_validator("text")
    @classmethod
    def check(cls,value):raise ValueError("reject")
@app.post("/value")
def value(item:Input):return item.text
'''
    p,store,_=fixture(tmp_path,{'main.py':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':{'text':'abc'}}))
    assert not edge_set(block) and detail['status']=='partial'
    assert any('validators' in d['message'] for d in detail['paths'][0]['diagnostics'])


def test_nested_response_aliases_and_allowed_extras_use_native_serializer(tmp_path):
    source='''from fastapi import FastAPI
from pydantic import BaseModel,Field,ConfigDict
app=FastAPI()
class Nested(BaseModel):value:str=Field(serialization_alias="shown")
class Output(BaseModel):
    model_config=ConfigDict(extra="allow")
    nested:Nested
    optional:str|None=None
@app.get("/value",response_model=Output,response_model_exclude_none=True)
def value():return {"nested":{"value":"nested","hidden":"drop"},"extra":3,"other":None}
'''
    p,store,_=fixture(tmp_path,{'main.py':source})
    _,detail=analyze(p,store,{},scenario({'path':'/value'}))
    assert detail['paths'][0]['steps'][0]['response']['body']=={'nested':{'shown':'nested'},'extra':3}


def test_response_exclude_unset_preserves_source_model_provided_fields(tmp_path):
    source='''from fastapi import FastAPI
from pydantic import BaseModel
app=FastAPI()
class Input(BaseModel):
    title:str
    description:str="default"
@app.post("/value",response_model=Input,response_model_exclude_unset=True)
def value(item:Input):return item
'''
    p,store,_=fixture(tmp_path,{'main.py':source})
    _,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':{'title':'hello'}}))
    assert detail['paths'][0]['steps'][0]['response']['body']=={'title':'hello'}


def test_same_source_response_model_uses_field_alias_without_rejecting_input(tmp_path):
    source='''from fastapi import FastAPI
from pydantic import BaseModel,Field
app=FastAPI()
class Input(BaseModel):text:str=Field(alias="wire",serialization_alias="output")
@app.post("/value",response_model=Input)
def value(item:Input):return item
'''
    p,store,_=fixture(tmp_path,{'main.py':source})
    _,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':{'wire':'hello'}}))
    assert detail['paths'][0]['steps'][0]['response']['body']=={'output':'hello'}


@pytest.mark.parametrize('declaration', ['text:str=Field(frozen=True)', 'text:str\n    def model_post_init(self,context):raise ValueError("reject")'])
def test_unmodeled_field_or_lifecycle_hook_does_not_confirm_handler(tmp_path,declaration):
    source='''from fastapi import FastAPI
from pydantic import BaseModel,Field
app=FastAPI()
class Input(BaseModel):
    DECLARATION
@app.post("/value")
def value(item:Input):return item.text
'''.replace('DECLARATION',declaration)
    p,store,_=fixture(tmp_path,{'main.py':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':{'text':'hello'}}))
    assert not edge_set(block) and detail['status']=='partial'


def test_source_factory_with_uuid_suffix_is_called_and_not_invented_as_uuid(tmp_path):
    source='''from fastapi import FastAPI
from pydantic import BaseModel,Field
app=FastAPI()
def custom_uuid4():return 17
class Input(BaseModel):number:int=Field(default_factory=custom_uuid4)
@app.post("/value")
def value(item:Input):return item.number
'''
    p,store,ids=fixture(tmp_path,{'main.py':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':{}}))
    assert detail['paths'][0]['steps'][0]['response']['body']==17
    assert ids['main.custom_uuid4'] in {e[2] for e in edge_set(block,'executes')}


def test_module_alias_factory_receives_validated_data_despite_duplicate_short_names(tmp_path):
    source='''from fastapi import FastAPI
from pydantic import BaseModel,Field
import chosen as helpers
app=FastAPI()
class Input(BaseModel):
    number:int
    total:int=Field(default_factory=helpers.compute)
@app.post("/value")
def value(item:Input):return item.total
'''
    p,store,ids=fixture(tmp_path,{'main.py':source,'chosen.py':'def compute(data):return data["number"]+7\n','other.py':'def compute(data):return 99\n'})
    block,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':{'number':3}}))
    assert detail['paths'][0]['steps'][0]['response']['body']==10
    assert ids['chosen.compute'] in {e[2] for e in edge_set(block,'executes')}
    assert ids['other.compute'] not in {e[2] for e in edge_set(block,'executes')}


def test_lambda_factory_is_explicitly_unsupported_instead_of_missing_required_input(tmp_path):
    source='''from fastapi import FastAPI
from pydantic import BaseModel,Field
app=FastAPI()
class Input(BaseModel):number:int=Field(default_factory=lambda:7)
@app.post("/value")
def value(item:Input):return item.number
'''
    p,store,_=fixture(tmp_path,{'main.py':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':{}}))
    assert not edge_set(block) and detail['status']=='partial'
    assert not detail['paths'][0]['steps'] and detail['paths'][0]['coverage']=='cutoff'


def test_native_uuid_factory_does_not_resolve_unrelated_source_short_name(tmp_path):
    source='''from fastapi import FastAPI
from pydantic import BaseModel,Field
from uuid import UUID,uuid4
app=FastAPI()
class Input(BaseModel):id:UUID=Field(default_factory=uuid4)
@app.post("/value")
def value(item:Input):return item.id
'''
    p,store,ids=fixture(tmp_path,{'main.py':source,'unrelated.py':'def uuid4(data):return "incorrect"\n'})
    block,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':{}}))
    assert ids['unrelated.uuid4'] not in {e[2] for e in edge_set(block,'executes')}
    assert detail['paths'][0]['steps'][0]['response']['body']['typ']=='UUID'
