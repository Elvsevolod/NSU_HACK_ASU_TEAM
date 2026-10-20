import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from analyzer.native_arrays import JavaArray
from builders import build


def fixture(root,bytes_expression='"ab".getBytes()',context=None):
    return build(root,{'Material.java':'''import java.util.Base64;import java.nio.charset.StandardCharsets;
      class Material{static int prefix=7;private static String encoded=Base64.getEncoder().encodeToString(EXPRESSION);
        String entry(){return encoded;}}
    '''.replace('EXPRESSION',bytes_expression)},context=context)


def test_unobserved_default_charset_is_a_static_initialization_boundary(tmp_path):
    p,db,ids=fixture(tmp_path);e=Engine(p,ScenarioState(db))
    assert e.run(ids['Material.entry'],{}) is U
    assert e.outcome=='unsupported_semantics boundary'
    assert any('default charset' in warning for warning in e.warnings)
    assert e.state.static_fields['type:service:Material']['prefix']==7


@pytest.mark.parametrize('expression,expected',[
    ('"ab".getBytes("UTF-8")','YWI='),
    ('"ab".getBytes(StandardCharsets.UTF_8)','YWI='),
    ('"ab".getBytes(StandardCharsets.UTF_16BE)','AGEAYg=='),
    ('"я".getBytes(StandardCharsets.UTF_8)','0Y8='),
])
def test_computed_static_uses_observed_charset_or_typed_bytes(tmp_path,expression,expected):
    p,db,ids=fixture(tmp_path,expression);e=Engine(p,ScenarioState(db))
    assert e.run(ids['Material.entry'],{})==expected
    assert e.outcome=='returned' and not e.approximate
    assert e.state.static_fields['type:service:Material'].kinds['encoded']=='String'


def test_supplied_default_charset_controls_the_same_source_without_rewriting_it(tmp_path):
    p,db,ids=fixture(tmp_path)
    assert Engine(p,ScenarioState(db,{'java_default_charset':'UTF-8'})).run(ids['Material.entry'],{})=='YWI='
    assert Engine(p,ScenarioState(db,{'java_default_charset':'UTF-16BE'})).run(ids['Material.entry'],{})=='AGEAYg=='


def test_unknown_byte_element_stops_before_normal_suffix(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.Base64;
      class Api{String entry(byte[] values){Base64.getEncoder().encodeToString(values);return "after";}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{'values':JavaArray([U],'byte',['Byte'])}) is U
    assert e.outcome=='unsupported_semantics boundary'


def test_source_namesake_base64_does_not_gain_a_jdk_contract(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Base64{static Base64 getEncoder(){return null;}
      String encodeToString(byte[] bytes){return "custom";}}
      class Api{String entry(){Base64 value=new Base64();return value.encodeToString(null);}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})=='custom'


def test_supplied_signed_byte_array_is_encoded_without_an_array_creation_model(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.Base64;
      class Api{String entry(byte[] values){return Base64.getEncoder().encodeToString(values);}}'''})
    assert Engine(p,ScenarioState(db)).run(ids['Api.entry'],{'values':JavaArray([-128,0,127],'byte',['Byte']*3)})=='gAB/'
