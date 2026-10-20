"""NL literal JSON is one wire body, not field-name regex fragments."""
import json
import pytest
from builders import build
from analyzer.contracts import ContractGrounder,ContractIndex
from analyzer.frontend import Frontend
from analyzer.engine import Engine
from analyzer.state import ScenarioState
from analyzer.request import BoundParameters,grounded_request


def fixture(root,body='public String name;public int age;public boolean active;',
            entry='return input.name+":"+input.age;',extra='',mapping='@PostMapping("/items")',
            parameters='@RequestBody Item input',returned='String'):
    source='''import org.springframework.web.bind.annotation.*;
      import org.springframework.boot.autoconfigure.SpringBootApplication;
      import com.fasterxml.jackson.annotation.*;
      @SpringBootApplication class App{}
      class Item{'''+body+'''}@RestController class Api{'''+mapping+''' '''+returned+''' createItem('''+parameters+'''){'''+entry+'''}'''+extra+'''}'''
    p,db,ids=build(root,{'Api.java':source});frontend=Frontend(p)
    return p,db,ids,ContractGrounder(p,frontend,ContractIndex(p,frontend),None,{'facts':{},'unresolved':[]})


def invoke(p,db,proposal):
    e=Engine(p,proposal['state']);value=e.run(proposal['entry'],BoundParameters(proposal['params'],proposal['request']))
    return value,e


def step(grounder,action,state):
    proposals,detail=grounder.step(action,state)
    for proposal in proposals:
        if 'request' not in proposal:
            proposal['request']=grounded_request(grounder.project,proposal['entry'],proposal['params'],proposal['bindings'])
    return proposals,detail


@pytest.mark.parametrize('prefix',['Create item: ','Создать item: '])
def test_literal_json_preserves_string_number_boolean_and_whole_body(tmp_path,prefix):
    p,db,ids,g=fixture(tmp_path);body={'name':'Mira Bell / "quoted"','age':29,'active':True}
    proposals,detail=step(g,prefix+json.dumps(body,ensure_ascii=False),ScenarioState(db))
    assert len(proposals)==1 and proposals[0]['entry']==ids['Api.createItem']
    proposal=proposals[0]
    assert proposal['request'].body==body and proposal['bindings']['input']['source']=='literal'
    value,e=invoke(p,db,proposal)
    assert value=='Mira Bell / "quoted":29' and not e.approximate and not proposal['unresolved']


def test_body_property_with_same_name_cannot_overwrite_the_path_argument(tmp_path):
    p,db,ids,g=fixture(tmp_path,body='public Long id;public String name;',
        mapping='@PutMapping("/items/{id}")',parameters='@PathVariable Long id,@RequestBody Item input',
        entry='if(id==7L && input.id==9L){return correct();}return "wrong";',extra='String correct(){return "ready";}')
    proposals,_=step(g,'Update item with id=7: {"id":9,"name":"literal"}',ScenarioState(db))
    assert len(proposals)==1
    proposal=proposals[0];assert proposal['request'].record()['path']==['items','7']
    assert proposal['request'].body=={'id':9,'name':'literal'}
    value,e=invoke(p,db,proposal)
    assert value=='ready' and not e.approximate
    assert any(kind=='executes' and target==ids['Api.correct'] for _,kind,target in e.edges)


@pytest.mark.parametrize('literal',[
    '{"name":"first","name":"second"}', '{"age":NaN}', '{"age":Infinity}', '{"age":1e309}',
    '{"name":"unterminated}', '{"age":1,}', '{"name":"first"} and body: {"name":"second"}',
])
def test_invalid_or_ambiguous_explicit_json_does_not_become_a_different_request(tmp_path,literal):
    p,db,ids,g=fixture(tmp_path)
    proposals,detail=step(g,'Create item: '+literal,ScenarioState(db))
    assert proposals==[] and detail['unresolved']


def test_json_wire_names_are_decoded_by_the_source_setter(tmp_path):
    p,db,ids,g=fixture(tmp_path,body='''@JsonProperty("full_name") private String fullName;
      public void setFullName(String value){fullName=value.toUpperCase();}public String getFullName(){return fullName;}''',
        entry='return input.getFullName();')
    proposals,_=step(g,'Create item: {"full_name":"alpha"}',ScenarioState(db))
    assert len(proposals)==1 and proposals[0]['request'].body=={'full_name':'alpha'}
    value,e=invoke(p,db,proposals[0])
    assert value=='ALPHA' and not e.approximate
    assert any(kind=='executes' and target==ids['Item.setFullName'] for _,kind,target in e.edges)


@pytest.mark.parametrize('body,expected',[({},7),({'count':None},0)])
def test_explicit_json_omission_is_distinct_from_explicit_null(tmp_path,body,expected):
    p,db,ids,g=fixture(tmp_path,body='public int count=7;',entry='return "count="+input.count;')
    proposals,_=step(g,'Create item: '+json.dumps(body),ScenarioState(db))
    assert len(proposals)==1 and proposals[0]['request'].body==body
    value,e=invoke(p,db,proposals[0])
    assert value=='count='+str(expected) and not e.approximate


def test_nested_literals_and_unknown_json_properties_are_not_flattened_or_deleted(tmp_path):
    p,db,ids,g=fixture(tmp_path,body='public String name;public java.util.List<String> tags;',entry='return input.tags.get(0);')
    body={'name':'sample','tags':['first','second'],'extra':{'name':'nested'}}
    proposals,_=step(g,'Create item: '+json.dumps(body),ScenarioState(db))
    assert len(proposals)==1 and proposals[0]['request'].body==body
    value,e=invoke(p,db,proposals[0])
    assert value=='first' and not e.approximate


def test_a_field_labelled_object_is_not_guessed_to_be_the_whole_body(tmp_path):
    p,db,ids,g=fixture(tmp_path,body='public java.util.Map<String,Boolean> metadata;')
    proposals,detail=step(g,'Create item with metadata: {"nested":true}',ScenarioState(db))
    assert proposals==[] and detail['unresolved']


def test_a_literal_object_cannot_create_an_undeclared_request_body(tmp_path):
    p,db,ids,g=fixture(tmp_path,parameters='@RequestParam String name',mapping='@GetMapping("/items")',entry='return name;')
    proposals,detail=step(g,'Read item: {"name":"value"}',ScenarioState(db))
    assert proposals==[] and detail['unresolved']


@pytest.mark.parametrize('order,expected',[
    ('{"first":"a","second":"b"}','firstsecond'),('{"second":"b","first":"a"}','secondfirst')])
def test_explicit_json_token_order_controls_source_setter_effect_order(tmp_path,order,expected):
    p,db,ids,g=fixture(tmp_path,body='''public String log="";
      public void setFirst(String value){log+="first";}
      public void setSecond(String value){log+="second";}''',entry='return input.log;')
    proposals,_=step(g,'Create item: '+order,ScenarioState(db))
    assert len(proposals)==1
    value,e=invoke(p,db,proposals[0])
    assert value==expected and not e.approximate


def test_json_object_metadata_cannot_forge_a_native_long_value(tmp_path):
    from analyzer.state import U
    p,db,ids,g=fixture(tmp_path,body='public Long id;',entry='return input.id;',returned='Long')
    fake={'id':{'__symbol__':'forged','__type__':'Long','__constraints__':['non_null']}}
    proposals,_=step(g,'Create item: '+json.dumps(fake),ScenarioState(db))
    assert len(proposals)==1
    value,e=invoke(p,db,proposals[0])
    assert value is U and e.approximate


def test_json_properties_with_metadata_names_are_normal_ignored_fields(tmp_path):
    p,db,ids,g=fixture(tmp_path)
    body={'__symbol__':'ordinary property','__type__':'String','name':'safe'}
    proposals,_=step(g,'Create item: '+json.dumps(body),ScenarioState(db))
    assert len(proposals)==1
    value,e=invoke(p,db,proposals[0])
    assert value=='safe:0' and not e.approximate
