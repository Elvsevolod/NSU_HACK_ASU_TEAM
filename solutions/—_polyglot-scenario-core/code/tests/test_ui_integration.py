"""Manual source-UI-to-core oracles, independent of the challenge project."""
from copy import deepcopy
import pytest

from polygraph.analysis import analyze
from polygraph.grounding import Grounder
from polygraph.ui import BoundSymbol, to_backend, to_browser
from polygraph.ui_extract.json_values import parse, stringify
from polygraph.ui_extract.state import JS_UNDEFINED, SymbolicValue, U
from polygraph.values import Symbol, Text
from polygraph.kernel import Kernel
from polygraph.state import State
from polygraph.project import Project
from support import edge_set, fixture


def test_source_ui_to_fastapi_binds_literal_field(tmp_path):
    sources={'main.py': '''from fastapi import FastAPI
from sqlmodel import SQLModel
app=FastAPI()
class Input(SQLModel):
    title:str
@app.post("/cards")
def create_card(value:Input):return value.title
''', 'page.html':'<input id="title" value="Before"><script src="client.js"></script>', 'client.js':'''function createCard(){
 $.ajax({url:"/cards",type:"POST",contentType:"application/json",data:JSON.stringify({title:$("#title").val()})});
}
'''}
    p,store,ids=fixture(tmp_path,sources)
    block,detail=analyze(p,store,{}, {'id':'ui','steps':[{'action':'Create card with title="After"'}]})
    assert edge_set(block)=={('scenario:ui','executes',ids['main.create_card'])}
    step=detail['paths'][0]['steps'][0]
    assert step['response']['body']=='After'
    assert step['grounding']['ui']['source']['file']=='client.js'
    assert step['request']['body']=={'title':'After'}


def test_ui_symbolic_uuid_roundtrip_through_json_storage_keeps_identity():
    symbol=Symbol('opaque-value','UUID',True)
    value=to_browser({'id':symbol},[])
    value['missing']=JS_UNDEFINED
    encoded=stringify(value)
    decoded=parse(encoded)
    assert isinstance(decoded['id'],BoundSymbol)
    assert to_backend(deepcopy(decoded['id']))==symbol
    assert 'missing' not in decoded
    ordinary={'__symbol__':value['id']['__symbol__'],'__type__':'String'}
    assert not isinstance(to_browser(ordinary,[]),SymbolicValue)
    assert to_backend(to_browser(ordinary,[]))==ordinary


def ui_chain_fixture(tmp_path):
    java='''import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.*;
import java.util.Map;
import java.util.UUID;
class Upload {String title;int quantity;}
@RestController class Portal {
 RestTemplate client=new RestTemplate();
 @PostMapping("/artifacts") Object create(@RequestBody Upload upload){return client.exchange("http://catalog/items",HttpMethod.POST,new HttpEntity<>(upload),Map.class).getBody();}
 @GetMapping("/artifacts/{id}") Object read(@PathVariable UUID id){return client.getForObject("http://catalog/items/"+id,Map.class);}
}'''
    python='''from fastapi import FastAPI,Depends
from sqlmodel import SQLModel,Field,Session,create_engine
from uuid import UUID,uuid4
app=FastAPI()
class Upload(SQLModel):
    title:str
    quantity:int
class Item(SQLModel,table=True):
    __tablename__="artifact_rows"
    id:UUID=Field(default_factory=uuid4,primary_key=True)
    title:str
    quantity:int
def database():return Session(create_engine("postgresql://worker:pass@db/inventory"))
@app.post("/items")
def add_item(upload:Upload,session:Session=Depends(database)):
    item=Item(title=upload.title,quantity=upload.quantity)
    session.add(item)
    session.commit()
    return item
def lookup(session,id):return session.get(Item,id)
@app.get("/items/{id}")
def read_item(id:UUID,session:Session=Depends(database)):return lookup(session,id)
'''
    script='''function createArtifact(){
 $.ajax({url:"/artifacts",type:"POST",contentType:"application/json",
  data:JSON.stringify({title:$("#title").val(),quantity:parseInt($("#quantity").val(),10)}),
  success:function(result){sessionStorage.setItem("created",JSON.stringify(result));}});
}
function readArtifact(){
 var saved=JSON.parse(sessionStorage.getItem("created"));
 $.ajax({url:"/artifacts/"+saved.id,type:"GET",success:function(item){$("#quantity_out").text(item.quantity);}});
}
'''
    html='<input id="title" value="Before"><input id="quantity" value="1"><span id="quantity_out"></span><script src="client.js"></script>'
    p,store,ids=fixture(tmp_path,{'portal/Portal.java':java,'catalog/main.py':python,'ui/page.html':html,'ui/client.js':script},['artifact_rows'],{'artifact_rows':[]},modules={'portal':'portal','catalog':'catalog'})
    scenario={'id':'ui-chain','steps':[{'action':'Create artifact through portal with title="Draft", quantity=6'},{'action':'Read artifact through portal'}]}
    return p,store,ids,scenario


def test_ui_java_python_stateful_chain_exact_all_four_relations(tmp_path):
    p,store,ids,scenario=ui_chain_fixture(tmp_path)
    block,detail=analyze(p,store,{},scenario)
    names=['Portal.create','Portal.read','main.database','main.add_item','main.read_item','main.lookup']
    expected={('scenario:ui-chain','executes',ids[name]) for name in names}
    expected|={(ids['Portal.create'],'remote',ids['main.add_item']),(ids['Portal.read'],'remote',ids['main.read_item']),
               (ids['main.read_item'],'calls',ids['main.lookup']),(ids['main.add_item'],'data','storage:artifact_rows'),(ids['main.lookup'],'data','storage:artifact_rows')}
    assert edge_set(block)==expected
    assert len(detail['paths'])==1
    steps=detail['paths'][0]['steps']
    assert len(steps)==2
    assert steps[0]['response']['body']==steps[1]['response']['body']
    assert steps[1]['response']['body']['quantity']==6
    assert isinstance(steps[1]['request']['url']['parts'][1],dict) and steps[1]['request']['url']['parts'][1]['kind']=='Symbol'
    assert all(step['grounding']['ui'] for step in steps)
    assert detail['paths'][0]['state']['storage:artifact_rows'][0]['title']=='Draft'


def card_ui(tmp_path, script):
    source='''from fastapi import FastAPI
app=FastAPI()
@app.post("/cards")
def create_card():return {"id":"server"}
@app.get("/cards/{id}")
def read_card(id:str):return id
'''
    return fixture(tmp_path, {'main.py':source, 'page.html':'<script src="client.js"></script>', 'client.js':script})


@pytest.mark.parametrize('prefix', ['var unused=JSON.parse("{");', 'JSON.parse("{");', 'var unused=null.missing;', 'return;'])
def test_request_prefix_must_reach_http_even_when_result_is_unused(tmp_path, prefix):
    p,store,_=card_ui(tmp_path, 'function createCard(){'+prefix+'$.ajax({url:"/cards",type:"POST"});}')
    block,detail=analyze(p,store,{}, {'id':'prefix','steps':[{'action':'Create card'}]})
    assert not edge_set(block)
    assert not detail['paths'][0]['steps']
    assert any(d['code'] in {'ui-preparation-exception','ui-prelude-stops'} for d in detail['paths'][0]['diagnostics'])


@pytest.mark.parametrize('prefix', ['var unused=JSON.parse("{");', 'JSON.parse("{");', 'var unused=result.missing.id;', 'throw "stop";'])
def test_known_callback_exception_stops_before_storage_and_next_request(tmp_path, prefix):
    script='''function createCard(){$.ajax({url:"/cards",type:"POST",success:function(result){PREFIX sessionStorage.setItem("id","invented");}});}
function readCard(){$.ajax({url:"/cards/"+sessionStorage.getItem("id"),type:"GET"});}'''.replace('PREFIX',prefix)
    p,store,ids=card_ui(tmp_path,script)
    block,detail=analyze(p,store,{}, {'id':'callback','steps':[{'action':'Create card'},{'action':'Read card'}]})
    assert edge_set(block)=={('scenario:callback','executes',ids['main.create_card'])}
    assert len(detail['paths'][0]['steps'])==1
    assert any(d['code']=='ui-callback-exception' for d in detail['paths'][0]['diagnostics'])


def test_callback_return_keeps_previous_storage_and_both_storage_kinds_are_separate(tmp_path):
    script='''function createCard(){$.ajax({url:"/cards",type:"POST",success:function(result){
sessionStorage.setItem("id","session");localStorage.setItem("id","local");return;localStorage.setItem("id","wrong");}});}
function readCard(){$.ajax({url:"/cards/"+sessionStorage.getItem("id")+"-"+localStorage.getItem("id"),type:"GET"});}'''
    p,store,_=card_ui(tmp_path,script)
    _,detail=analyze(p,store,{}, {'id':'storage','steps':[{'action':'Create card'},{'action':'Read card'}]})
    assert len(detail['paths'])==1
    assert detail['paths'][0]['steps'][1]['response']['body']=='session-local'


def test_explicitly_empty_storage_is_null_and_cannot_fabricate_a_request_id(tmp_path):
    script='''function readCard(){var saved=JSON.parse(sessionStorage.getItem("id"));$.ajax({url:"/cards/"+saved.id,type:"GET"});}'''
    p,store,_=card_ui(tmp_path,script)
    block,detail=analyze(p,store,{'browser':{'storage':{'sessionStorage':{}}}}, {'id':'empty','steps':[{'action':'Read card'}]})
    assert not edge_set(block)
    assert any(d['code']=='ui-preparation-exception' for d in detail['paths'][0]['diagnostics'])


def test_source_transform_is_validated_instead_of_overwriting_computed_wire_value(tmp_path):
    source='''from fastapi import FastAPI
from sqlmodel import SQLModel
app=FastAPI()
class Upload(SQLModel):quantity:int
@app.post("/cards")
def create_card(value:Upload):return value.quantity
'''
    script='''function createCard(){$.ajax({url:"/cards",type:"POST",contentType:"application/json",data:JSON.stringify({quantity:parseInt($("#quantity").val(),10)*2})});}'''
    p,store,_=fixture(tmp_path,{'main.py':source,'page.html':'<input id="quantity" value="1"><script src="client.js"></script>','client.js':script})
    step={'action':'Create card with quantity=4'}
    block,detail=analyze(p,store,{}, {'id':'transform','steps':[step]})
    assert not edge_set(block)
    assert any(d['code']=='ui-input-conflict' for d in detail['paths'][0]['diagnostics'])
    _,detail=analyze(p,store,{}, {'id':'transform','steps':[{**step,'ui_inputs':{'dom':{'#quantity':'2'}}}]})
    assert detail['paths'][0]['steps'][0]['response']['body']==4


def test_symbolic_query_and_embedded_path_parts_keep_identity_without_token_collisions(tmp_path):
    source='''from fastapi import FastAPI
app=FastAPI()
@app.get("/cards/{path}")
def read_card(path:str,id:str,literal:str):return {"path":path,"id":id,"literal":literal}
'''
    p,store,_=fixture(tmp_path,{'main.py':source})
    engine=Kernel(p,State(store));engine.scenario_id='query'
    symbol=Symbol('opaque','UUID',True)
    response=engine.request({'url':Text(('/cards/key-',symbol,'?id=',symbol,'&literal=%5f%5fpolygraph_0_0%5f%5f'))})
    assert response.body['id']==symbol
    assert response.body['path']==Text(('key-',symbol))
    assert response.body['literal']=='__polygraph_0_0__'


@pytest.mark.parametrize('language', ['java','python-default','python-annotated'])
def test_flat_ui_form_reaches_correct_framework_parameter_location(tmp_path, language):
    java='''import org.springframework.web.bind.annotation.*;
@RestController class Cards {@PostMapping("/cards") String createCard(@RequestParam("card-title") String title,@RequestParam int quantity){return title+":"+quantity;}}
'''
    python='''from fastapi import FastAPI,Form as F
from typing import Annotated
app=FastAPI()
@app.post("/cards")
def create_card(SIGNATURE):return title+":"+str(quantity)
'''
    signature='title:str=F(alias="card-title"),quantity:int=F()' if language=='python-default' else 'title:Annotated[str,F(alias="card-title")],quantity:Annotated[int,F()]'
    sources={'Cards.java':java} if language=='java' else {'main.py':python.replace('SIGNATURE',signature)}
    sources.update({'page.html':'<input id="title" value="Before"><input id="quantity" value="1"><script src="client.js"></script>',
                    'client.js':'''function createCard(){$.ajax({url:"/cards",type:"POST",data:{"card-title":$("#title").val(),quantity:parseInt($("#quantity").val(),10)}});}'''})
    p,store,_=fixture(tmp_path,sources)
    _,detail=analyze(p,store,{}, {'id':'form','steps':[{'action':'Create card with title="Draft", quantity=6'}]})
    steps=detail['paths'][0]['steps']
    assert len(steps)==1
    assert steps[0]['request']['form']=={'card-title':'Draft','quantity':'6'}
    assert steps[0]['response']['body']=='Draft:6'


@pytest.mark.parametrize('language,expected', [('java',415),('python',422)])
def test_json_stringification_does_not_change_default_form_media_type(tmp_path, language, expected):
    source='''import org.springframework.web.bind.annotation.*;
class Input {String title;}
@RestController class Cards {@PostMapping("/cards") String createCard(@RequestBody Input value){return value.title;}}
''' if language=='java' else '''from fastapi import FastAPI
from sqlmodel import SQLModel
app=FastAPI()
class Input(SQLModel):title:str
@app.post("/cards")
def create_card(value:Input):return value.title
'''
    p,store,_=fixture(tmp_path,{'Cards.java' if language=='java' else 'main.py':source,'page.html':'<script src="client.js"></script>',
        'client.js':'''function createCard(){$.ajax({url:"/cards",type:"POST",data:JSON.stringify({title:"Draft"})});}'''})
    block,detail=analyze(p,store,{}, {'id':'media','steps':[{'action':'Create card'}]})
    assert not edge_set(block)
    assert detail['paths'][0]['steps'][0]['response']['status']==expected


def test_json_content_type_does_not_implicitly_stringify_a_source_object(tmp_path):
    source='''from fastapi import FastAPI
from sqlmodel import SQLModel
app=FastAPI()
class Input(SQLModel):title:str
@app.post("/cards")
def create_card(value:Input):return value.title
'''
    p,store,_=fixture(tmp_path,{'main.py':source,'page.html':'<script src="client.js"></script>',
        'client.js':'''function createCard(){$.ajax({url:"/cards",type:"POST",contentType:"application/json",data:{title:"Draft"}});}'''})
    block,detail=analyze(p,store,{}, {'id':'media','steps':[{'action':'Create card'}]})
    assert not edge_set(block)
    assert detail['paths'][0]['steps'][0]['response']['status']==422


def test_metadata_shaped_response_is_ordinary_application_data_in_callback(tmp_path):
    source='''from fastapi import FastAPI
app=FastAPI()
@app.post("/cards")
def create_card():return {"__symbol__":"ordinary","__type__":"String"}
@app.get("/cards/{id}")
def read_card(id:str):return id
'''
    script='''function createCard(){$.ajax({url:"/cards",type:"POST",success:function(result){sessionStorage.setItem("id",result.__symbol__);}});}
function readCard(){$.ajax({url:"/cards/"+sessionStorage.getItem("id"),type:"GET"});}'''
    p,store,_=fixture(tmp_path,{'main.py':source,'page.html':'<script src="client.js"></script>','client.js':script})
    _,detail=analyze(p,store,{}, {'id':'metadata','steps':[{'action':'Create card'},{'action':'Read card'}]})
    assert detail['paths'][0]['steps'][1]['response']['body']=='ordinary'


@pytest.mark.parametrize('options,prefix', [('beforeSend:function(){return false;},',''),('', '$.ajaxSetup({type:"DELETE"});')])
def test_unmodeled_ajax_hooks_do_not_silently_claim_backend_execution(tmp_path, options, prefix):
    p,store,_=card_ui(tmp_path,prefix+'function createCard(){$.ajax({'+options+'url:"/cards",type:"POST"});}')
    block,detail=analyze(p,store,{}, {'id':'hook','steps':[{'action':'Create card'}]})
    assert not edge_set(block)
    assert any(d['code']=='ui-transport-unknown' for d in detail['paths'][0]['diagnostics'])


def test_missing_ajax_type_uses_get_even_if_action_and_retrieved_handler_say_create(tmp_path):
    source='''from fastapi import FastAPI
app=FastAPI()
@app.post("/cards")
def create_card():return 7
'''
    p,store,_=fixture(tmp_path,{'main.py':source,'page.html':'<script src="client.js"></script>',
        'client.js':'''function createCard(){$.ajax({url:"/cards"});}'''})
    block,detail=analyze(p,store,{}, {'id':'verb','steps':[{'action':'Create card'}]})
    assert not edge_set(block)
    assert detail['paths'][0]['steps'][0]['request']['method']=='GET'
    assert any(d['code']=='unresolved-request' for d in detail['paths'][0]['diagnostics'])


def test_multiple_requests_in_one_action_are_explicitly_outside_current_ui_ordering(tmp_path):
    p,store,_=card_ui(tmp_path,'''function createCard(){$.ajax({url:"/cards",type:"POST"});$.ajax({url:"/cards/server",type:"GET"});}''')
    block,detail=analyze(p,store,{}, {'id':'compound','steps':[{'action':'Create card'}]})
    assert not edge_set(block)
    assert any(d['code']=='ui-compound-unsupported' for d in detail['paths'][0]['diagnostics'])


def test_query_numbers_are_transferred_as_strings_to_string_parameters(tmp_path):
    source='''from fastapi import FastAPI
app=FastAPI()
@app.get("/cards")
def read_card(quantity:str):return quantity
'''
    p,store,_=fixture(tmp_path,{'main.py':source,'page.html':'<script src="client.js"></script>',
        'client.js':'''function readCard(){$.ajax({url:"/cards",data:{quantity:6}});}'''})
    _,detail=analyze(p,store,{}, {'id':'query','steps':[{'action':'Read card'}]})
    step=detail['paths'][0]['steps'][0]
    assert step['request']['query']['quantity']=='6'
    assert step['response']['body']=='6'


def test_case_insensitive_source_header_overrides_default_ajax_media_type(tmp_path):
    source='''from fastapi import FastAPI
from sqlmodel import SQLModel
app=FastAPI()
class Input(SQLModel):title:str
@app.post("/cards")
def create_card(value:Input):return value.title
'''
    script='''function createCard(){$.ajax({url:"/cards",type:"POST",headers:{"CONTENT-type":"application/json"},data:JSON.stringify({title:"Draft"})});}'''
    p,store,_=fixture(tmp_path,{'main.py':source,'page.html':'<script src="client.js"></script>','client.js':script})
    _,detail=analyze(p,store,{}, {'id':'header','steps':[{'action':'Create card'}]})
    step=detail['paths'][0]['steps'][0]
    assert step['response']['body']=='Draft'
    assert step['request']['headers']=={'content-type':'application/json'}


def test_html_change_invalidates_fingerprint_and_old_control_default(tmp_path):
    source='''from fastapi import FastAPI
from sqlmodel import SQLModel
app=FastAPI()
class Input(SQLModel):title:str
@app.post("/cards")
def create_card(value:Input):return value.title
'''
    script='''function createCard(){$.ajax({url:"/cards",type:"POST",contentType:"application/json",data:JSON.stringify({title:$("#title").val()})});}'''
    html='<input id="title" value="Before"><script src="client.js"></script>'
    cache=tmp_path/'cache.json'
    p,store,_=fixture(tmp_path,{'main.py':source,'page.html':html,'client.js':script},cache=cache)
    scenario={'id':'default','steps':[{'action':'Create card'}]}
    _,before=analyze(p,store,{},scenario);p.save_cache()
    assert before['paths'][0]['steps'][0]['response']['body']=='Before'
    (p.root/'page.html').write_text(html.replace('Before','After'))
    changed=Project(p.root,tmp_path/'skeleton.json',cache)
    _,after=analyze(changed,store,{},scenario)
    assert after['paths'][0]['steps'][0]['response']['body']=='After'
    assert changed.fingerprint!=p.fingerprint
    assert changed.cache_hits==0


@pytest.mark.parametrize('script', ['''function createCard(){
var draft=new Object();draft.title=$("#title").val();
var encoded=JSON.stringify(draft);draft.title="Later";
$.ajax({url:"/cards",type:"POST",contentType:"application/json",data:encoded,xhrFields:{withCredentials:true}});}
''','''var module=angular.module("board",[]);
module.controller("Board",function($scope,$http){$scope.createCard=function(){
var title=$scope.title;
$http({url:"/cards",method:"POST",data:{title:title},withCredentials:true});
};});'''])
def test_source_object_snapshot_and_angular_json_default_on_independent_contract(tmp_path, script):
    source='''from fastapi import FastAPI
from sqlmodel import SQLModel
app=FastAPI()
class Input(SQLModel):title:str
@app.post("/cards")
def create_card(value:Input):return value.title
'''
    p,store,_=fixture(tmp_path,{'main.py':source,'page.html':'<input id="title" value="Before"><script src="client.js"></script>','client.js':script})
    _,detail=analyze(p,store,{}, {'id':'object','steps':[{'action':'Create card with title="Draft"'}]})
    assert len(detail['paths'])==1
    assert detail['paths'][0]['steps'][0]['response']['body']=='Draft'
    assert any(d['code']=='ui-cookie-context' for d in detail['paths'][0]['diagnostics'])


def test_null_property_assignment_in_prefix_throws_before_request(tmp_path):
    p,store,_=card_ui(tmp_path,'''function createCard(){var value=null;value.title="unreachable";$.ajax({url:"/cards",type:"POST"});}''')
    block,detail=analyze(p,store,{}, {'id':'assignment','steps':[{'action':'Create card'}]})
    assert not edge_set(block)
    assert any(d['code']=='ui-preparation-exception' for d in detail['paths'][0]['diagnostics'])


def test_source_object_constructor_shadowing_cannot_bypass_native_guard(tmp_path):
    p,store,_=card_ui(tmp_path,'''function createCard(){function Object(){throw "custom";}var value=new Object();$.ajax({url:"/cards",type:"POST",data:JSON.stringify(value)});}''')
    block,detail=analyze(p,store,{}, {'id':'shadow','steps':[{'action':'Create card'}]})
    assert not edge_set(block)
    assert any(d['code']=='ui-native-shadowed' for d in detail['paths'][0]['diagnostics'])


def test_angular_callback_chain_is_visible_as_an_unmodeled_tail_after_http(tmp_path):
    p,store,ids=card_ui(tmp_path,'''function createCard(){$http({url:"/cards",method:"POST"}).success(function(result){sessionStorage.setItem("id",result.id);});}
function readCard(){$.ajax({url:"/cards/"+sessionStorage.getItem("id"),type:"GET"});}''')
    block,detail=analyze(p,store,{}, {'id':'chain','steps':[{'action':'Create card'},{'action':'Read card'}]})
    assert edge_set(block)=={('scenario:chain','executes',ids['main.create_card'])}
    assert len(detail['paths'][0]['steps'])==1
    assert any(d['code']=='ui-callback-chain-unsupported' for d in detail['paths'][0]['diagnostics'])


def test_repeated_query_field_is_not_silently_reduced_to_one_scalar(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
@RestController class Cards {@GetMapping("/cards") String readCard(@RequestParam String tag){return tag;}}
'''
    p,store,_=fixture(tmp_path,{'Cards.java':source,'page.html':'<script src="client.js"></script>',
        'client.js':'''function readCard(){$.ajax({url:"/cards",data:"tag=first&tag=second"});}'''})
    block,detail=analyze(p,store,{}, {'id':'repeated','steps':[{'action':'Read card'}]})
    assert not edge_set(block)
    assert any(d['code']=='ui-repeated-query-unsupported' for d in detail['paths'][0]['diagnostics'])


def test_json_object_prototype_property_does_not_become_known_undefined_and_throw(tmp_path):
    p,store,ids=card_ui(tmp_path,'''function createCard(){$.ajax({url:"/cards",type:"POST",success:function(result){
var className=result.constructor.name;sessionStorage.setItem("class",className);}});}''')
    block,detail=analyze(p,store,{}, {'id':'prototype','steps':[{'action':'Create card'}]})
    assert edge_set(block)=={('scenario:prototype','executes',ids['main.create_card'])}
    codes=[item['code'] for item in detail['paths'][0]['diagnostics']]
    assert 'ui-callback-exception' not in codes
    assert 'browser-limitations' in codes
