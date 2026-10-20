"""Class<T> array conversion through source methods and downstream consumers."""
import pytest
import json
from analyzer.project import Project
from analyzer.paths import run_paths
from analyzer.engine import Engine
from analyzer.state import ScenarioState, U
from analyzer.native_arrays import JavaArray
from builders import build


def run(tmp_path, body, schema='class Parcel {public String id;String getId(){return id;}}'):
    project, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;
      import com.fasterxml.jackson.databind.*;''' + schema + '''class Api {
      <T> T decode(String text,Class<T> cls){return new ObjectMapper().readValue(text,cls);}
      Object entry(){''' + body + '''}
      String after(){return "wrong";} String rejected(){return "rejected";}
    }'''})
    engine = Engine(project, ScenarioState(db))
    value = engine.run(ids['Api.entry'], {})
    return value, engine, ids


def test_class_array_survives_generic_decode_and_foreach_selection(tmp_path):
    result, engine, ids = run(tmp_path, '''Parcel[] values=decode("[{\\"id\\":\\"P7\\"},{\\"id\\":\\"P9\\"}]",Parcel[].class);
      List<Parcel> items=Arrays.asList(values);
      for(Parcel item:items){if(item.getId().equals("P9")){return item.getId();}}return "missing";''')
    assert result == 'P9'
    assert ids['Parcel.getId'] in {target for _, kind, target in engine.edges if kind == 'executes'}


@pytest.mark.parametrize('text,expected', [('[]', []), ('[null]', [None])])
def test_empty_and_null_elements_keep_array_shape(tmp_path, text, expected):
    result, engine, _ = run(tmp_path, 'return decode("' + text + '",Parcel[].class);')
    assert isinstance(result, JavaArray) and result.component == 'Parcel'
    assert list(result) == expected and not engine.approximate


def test_null_array_stays_null(tmp_path):
    result, engine, _ = run(tmp_path, 'return decode("null",Parcel[].class);')
    assert result is None and not engine.approximate


def test_nested_arrays_keep_each_runtime_component(tmp_path):
    result, engine, _ = run(tmp_path, 'return decode("[[null],[]]",Parcel[][].class);')
    assert isinstance(result, JavaArray) and result.component == 'Parcel[]'
    assert all(isinstance(item, JavaArray) and item.component == 'Parcel' for item in result)
    assert list(result[0]) == [None] and list(result[1]) == [] and not engine.approximate


@pytest.mark.parametrize('typ,text,expected', [('int', '[1,null,3]', [1,0,3]),
    ('boolean', '[true,false,null]', [True,False,False]), ('long', '[2147483648]', [2147483648]),
    ('String', '["a",null]', ['a',None])])
def test_primitive_and_reference_elements_use_declared_conversion(tmp_path, typ, text, expected):
    escaped = text.replace('"', '\\"')
    result, engine, _ = run(tmp_path, 'return decode("' + escaped + '",' + typ + '[].class);')
    assert isinstance(result, JavaArray) and list(result) == expected and not engine.approximate


def test_wrong_object_shape_uses_owned_codec_failure_before_following_code(tmp_path):
    result, engine, ids = run(tmp_path, '''try{decode("{}",Parcel[].class);return after();}
      catch(JsonMappingException failure){return rejected();}''')
    assert result == 'rejected'
    assert ids['Api.after'] not in {target for _, kind, target in engine.edges if kind == 'executes'}


def test_null_primitive_element_obeys_observed_policy(tmp_path):
    result, _, _ = run(tmp_path, '''ObjectMapper mapper=new ObjectMapper();
      mapper.enable(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES);
      try{mapper.readValue("[null]",int[].class);return after();}catch(JsonMappingException failure){return rejected();}''')
    assert result == 'rejected'


def test_convert_scalar_dto_to_array_cannot_alias_or_erase_the_input(tmp_path):
    result, engine, _ = run(tmp_path, '''Parcel parcel=new Parcel();parcel.id="kept";
      try{new ObjectMapper().convertValue(parcel,Parcel[].class);return after();}
      catch(IllegalArgumentException failure){return parcel.id;}''')
    assert result == 'kept' and not engine.approximate


def test_array_list_is_backed_in_both_directions_and_has_fixed_size(tmp_path):
    result,engine,_=run(tmp_path,'''String[] values=decode("[\\"a\\",\\"b\\"]",String[].class);
      List<String> view=Arrays.asList(values);view.set(0,"c");values[1]="d";
      try{view.add("wrong");return after();}catch(UnsupportedOperationException failure){return values[0]+view.get(1);}''')
    assert result=='cd' and not engine.approximate


def test_array_view_keeps_runtime_store_check_after_erasure(tmp_path):
    result,engine,_=run(tmp_path,'''String[] values=decode("[\\"a\\"]",String[].class);
      List view=Arrays.asList(values);try{view.set(0,7);return after();}
      catch(ArrayStoreException failure){return values[0];}''')
    assert result=='a' and not engine.approximate


def test_primitive_array_is_a_single_as_list_element(tmp_path):
    result,engine,_=run(tmp_path,'''int[] values=decode("[1,2]",int[].class);
      return Arrays.asList(values).size();''')
    assert result==1 and not engine.approximate


def test_inline_generic_array_infers_the_reference_varargs_type(tmp_path):
    result,engine,_=run(tmp_path,'''return Arrays.asList(decode("[\\"a\\",\\"b\\"]",String[].class)).size();''')
    assert result==2 and not engine.approximate


def test_an_object_cast_keeps_the_array_as_one_varargs_element(tmp_path):
    result,engine,_=run(tmp_path,'''Object values=decode("[\\"a\\",\\"b\\"]",String[].class);
      return Arrays.asList(values).size();''')
    assert result==1 and not engine.approximate


def test_observed_single_value_policy_does_not_force_array_failure(tmp_path):
    result,engine,_=run(tmp_path,'''ObjectMapper mapper=new ObjectMapper();
      mapper.enable(DeserializationFeature.ACCEPT_SINGLE_VALUE_AS_ARRAY);
      return mapper.readValue("7",int[].class);''')
    assert isinstance(result,JavaArray) and list(result)==[7] and not engine.approximate


@pytest.mark.parametrize('typ',['byte','char'])
def test_specialized_text_array_codec_is_explicitly_unresolved(tmp_path,typ):
    result,engine,_=run(tmp_path,'return decode("\\"YQ==\\"",'+typ+'[].class);')
    assert result is U and engine.outcome=='returned'
    assert any('specialized codec' in warning for warning in engine.warnings)


def test_same_dto_name_in_another_deployment_cannot_change_array_schema(tmp_path):
    merged={'nodes':{},'edges':[]};entries={}
    for module,field,value in [('first','code','"P7"'),('second','label','"other"')]:
        source='''import com.fasterxml.jackson.databind.ObjectMapper;
          class Parcel{public String '''+field+''';}class Api{Parcel[] entry(){return new ObjectMapper().readValue(
          "[{\\"'''+field+'''\\":\\"'''+json.loads(value)+'''\\"}]",Parcel[].class);}}'''
        project,db,ids=build(tmp_path/module,{'Api.java':source},module=module)
        for node in project.skeleton['nodes'].values():
            if node.get('file'):node['file']=module+'/'+node['file']
        merged['nodes'].update(project.skeleton['nodes']);merged['edges'].extend(project.skeleton['edges'])
        entries[module]=(ids['Api.entry'],field,json.loads(value))
    (tmp_path/'skeleton.json').write_text(json.dumps(merged));project=Project(tmp_path/'skeleton.json',tmp_path)
    for module,(entry,field,value) in entries.items():
        engine=Engine(project,ScenarioState(db));result=engine.run(entry,{})
        assert isinstance(result,JavaArray) and result[0][field]==value
        assert result[0].source_owner=='type:'+module+':Parcel' and not engine.approximate


def test_array_view_alias_survives_a_conservative_branch_join(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import com.fasterxml.jackson.databind.ObjectMapper;
      class Api{String entry(boolean flag){String[] array=new ObjectMapper().readValue("[\\"a\\"]",String[].class);
      List<String> view=Arrays.asList(array);if(flag){view.set(0,"x");}else{array[0]="x";}return view.get(0);}}'''})
    outcomes=run_paths(p,ScenarioState(db),ids['Api.entry'],{'flag':U},limit=1)
    assert {row['result'] for row in outcomes}=={'x'}
