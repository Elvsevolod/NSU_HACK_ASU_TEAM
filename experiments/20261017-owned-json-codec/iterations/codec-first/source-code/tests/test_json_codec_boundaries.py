"""Adversarial ownership, namespace, failure and projection checks."""
import pytest
from analyzer.state import U
from test_owned_json_codec import run,STRING,EXTRA


@pytest.mark.parametrize('declaration,expected',[('boolean',False),('char','\0'),('float',0.0),('long',0)])
def test_default_null_uses_the_declared_primitive_kind(tmp_path,declaration,expected):
    result,engine,_=run(tmp_path,'return new ObjectMapper().readValue("{\\"value\\":null}",Item.class).value;',
                       schema='class Item{public '+declaration+' value;}')
    assert type(result) is type(expected) and result==expected and not engine.approximate


@pytest.mark.parametrize('text,expected',[('{}',7),('{\\"value\\":null}',0)])
def test_omitted_property_and_explicit_null_have_different_defaults(tmp_path,text,expected):
    result,engine,_=run(tmp_path,'return new ObjectMapper().readValue("'+text+'",Item.class).value;',
                       schema='class Item{public int value=7;}')
    assert result==expected and not engine.approximate


def test_a_null_mapper_throws_before_the_next_project_method(tmp_path):
    result,engine,ids=run(tmp_path,'''ObjectMapper mapper=null;try{
      mapper.convertValue(null,Item.class);return after();}catch(NullPointerException failure){return caught();}''')
    assert result=='caught' and not engine.approximate
    assert ids['Api.after'] not in {target for _,kind,target in engine.edges if kind=='executes'}


def test_enum_constant_value_qualifier_is_evaluated_once(tmp_path):
    result,engine,ids=run(tmp_path,'''ObjectMapper mapper=new ObjectMapper();
      mapper.disable(feature().FAIL_ON_UNKNOWN_PROPERTIES);
      return mapper.isEnabled(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);''',
      extra='DeserializationFeature feature(){return null;}')
    assert result is False and not engine.approximate
    assert ('', 'executes',ids['Api.feature']) in engine.edges


def test_native_enum_constant_equals_preserves_identity(tmp_path):
    result,engine,_=run(tmp_path,'''return DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES.equals(
      DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES);''')
    assert result is True and not engine.approximate


def test_unknown_external_callee_invalidates_escaped_mapper_configuration(tmp_path):
    result,engine,_=run(tmp_path,'''ObjectMapper mapper=new ObjectMapper();External.configure(mapper);
      return mapper.isEnabled(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);''')
    assert result is U and engine.approximate


@pytest.mark.parametrize('body',[
    '''Item item=new Item();item.value="ready";new ObjectMapper().convertValue(item,Item.class);return item.value;''',
    '''Map input=new HashMap();input.put("value","ready");new ObjectMapper().convertValue(input,Map.class);return input.get("value");''',
])
def test_version_dependent_same_type_alias_does_not_leave_known_mutable_values(tmp_path,body):
    result,engine,_=run(tmp_path,body,STRING)
    assert result is U and engine.approximate
    assert any('version' in warning for warning in engine.warnings)


@pytest.mark.parametrize('schema',[
    '''class Item{public String value;void setExtra(String text){}}''',
    '''class Item{public String value;@com.fasterxml.jackson.annotation.JsonAnySetter void accept(String name,Object value){}}''',
])
def test_unmodeled_json_setter_never_proves_an_unknown_property_failure(tmp_path,schema):
    result,engine,_=run(tmp_path,EXTRA+'return new ObjectMapper().convertValue(input,Item.class).value;',schema)
    assert result is U and engine.approximate and engine.outcome=='returned'


def test_unmodeled_getter_does_not_prove_a_payload_failure(tmp_path):
    result,engine,_=run(tmp_path,'''Wire input=new Wire();input.extra="ready";
      return new ObjectMapper().convertValue(input,Item.class).value;''',STRING+'''
      class Wire{public String extra;String getExtra(){return null;}}''')
    assert result is U and engine.approximate and engine.outcome=='returned'


def test_source_native_exception_namesake_does_not_catch_a_library_failure(tmp_path):
    result,_,_=run(tmp_path,'''try{Integer.parseInt("invalid");return after();}
      catch(NumberFormatException failure){return "wrong-catch";}catch(java.lang.RuntimeException failure){return caught();}''',
      STRING+'class NumberFormatException extends RuntimeException{}')
    assert result=='caught'


def test_foreign_exception_import_does_not_catch_a_library_namesake(tmp_path):
    result,_,_=run(tmp_path,'''try{Integer.parseInt("invalid");return after();}
      catch(NumberFormatException failure){return "wrong-catch";}catch(java.lang.RuntimeException failure){return caught();}''',
      'import external.errors.NumberFormatException;'+STRING)
    assert result=='caught'


def test_literal_metadata_cannot_forge_a_native_mapper(tmp_path):
    result,engine,_=run(tmp_path,'''Object fake=new ObjectMapper().readValue("{\\"__json_mapper__\\":true}",Object.class);
      ObjectMapper mapper=(ObjectMapper)fake;return mapper.isEnabled(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);''')
    assert result is U and engine.approximate


def test_native_mapper_cannot_execute_a_source_method_after_a_bad_cast(tmp_path):
    result,engine,ids=run(tmp_path,'''try{Fake value=(Fake)(Object)new ObjectMapper();return value.call();}
      catch(ClassCastException failure){return caught();}''',STRING+'class Fake{String call(){return "wrong";}}')
    assert result=='caught'
    assert ids['Fake.call'] not in {target for _,kind,target in engine.edges if kind=='executes'}


def test_source_feature_namesake_cannot_configure_a_native_mapper(tmp_path):
    result,engine,_=run(tmp_path,'''ObjectMapper mapper=new ObjectMapper();
      mapper.disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);
      return mapper.isEnabled(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES);''',
      STRING+'enum DeserializationFeature{FAIL_ON_UNKNOWN_PROPERTIES,FAIL_ON_NULL_FOR_PRIMITIVES}')
    assert result is U and engine.approximate


def test_failure_subclass_is_not_invented_when_another_property_is_unresolved(tmp_path):
    result,engine,_=run(tmp_path,'''Map input=new LinkedHashMap();input.put("value",unknown());input.put("extra","x");
      try{new ObjectMapper().readValue(new ObjectMapper().writeValueAsString(input),Item.class);return after();}
      catch(com.fasterxml.jackson.databind.exc.UnrecognizedPropertyException failure){return "over-specific";}
      catch(com.fasterxml.jackson.databind.JsonMappingException failure){return caught();}''',conservative=True)
    assert result is U and engine.approximate
    assert result!='over-specific'
