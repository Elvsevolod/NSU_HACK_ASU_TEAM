import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build
from analyzer.models import construct,library,wire


@pytest.mark.parametrize('lookup,expected',[
    ('1','integer'),('1L','long'),('"1"','string'),('true','boolean'),("'x'",'character'),('"x"','text'),
])
def test_boxed_key_types_do_not_collapse_to_one_python_or_string_key(tmp_path,lookup,expected):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api {
      String entry(){Map values=new HashMap();values.put(1,"integer");values.put(1L,"long");
        values.put("1","string");values.put(true,"boolean");values.put('x',"character");
        values.put("x","text");return (String)values.get('''+lookup+''');}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==expected


def test_copy_constructor_copies_typed_mappings_without_sharing_entry_mutation(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api {
      String entry(){Map first=new HashMap();first.put(7,"original");Map second=new HashMap(first);
        second.put(7,"changed");return (String)first.get(7);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='original'


def test_generated_opaque_string_key_is_reused_without_a_fabricated_literal(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api {
      String entry(){String key=UUID.randomUUID().toString();Map values=new HashMap();
        values.put(key,"found");return (String)values.get(key);}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='found'


def test_json_key_text_is_converted_at_the_boundary_and_not_inside_the_map():
    _,value=construct('java.util.HashMap',[],U)
    library('put',value,[7,'seven'],'map',U,key_type='int')
    assert library('get',value,['7'],'map',U)==(True,None)
    assert wire(value)=={'7':'seven'}
    library('put',value,['7','string'],'map',U)
    warnings=[]
    assert wire(value,warnings.append) is U
    assert any('duplicate-field order' in message for message in warnings)
    assert library('get',value,[7],'map',U,key_type='int')==(True,'seven')


def test_a_raw_map_http_response_uses_json_string_keys_even_if_the_server_used_integers(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {@GetMapping("/labels") Map labels(){Map data=new HashMap();data.put(7,"seven");return data;}}
      class Caller {RestTemplate rest;String entry(){Map response=
        rest.getForObject("http://service/labels",Map.class);
        if(response.get(7)!=null){return "wrong";}return (String)response.get("7");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='seven'
