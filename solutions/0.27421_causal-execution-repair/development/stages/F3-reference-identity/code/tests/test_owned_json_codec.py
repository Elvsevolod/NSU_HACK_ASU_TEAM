"""Observed codec ownership/configuration, with no application-specific names."""
import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


IMPORTS='''import java.util.*;import com.fasterxml.jackson.databind.*;
  import com.fasterxml.jackson.core.JsonProcessingException;'''
PRIMITIVE='class Item{public int value;}'
STRING='class Item{public String value;}'
INPUT='Map input=new HashMap();input.put("value",null);'
EXTRA='Map input=new HashMap();input.put("value","ready");input.put("extra","other");'


def run(tmp_path,body,schema=PRIMITIVE,extra='',params=None,conservative=False):
    p,db,ids=build(tmp_path,{'Api.java':IMPORTS+schema+'''class Api{Object entry(boolean flag){'''+body+'''}
      String after(){return "wrong";}String caught(){return "caught";}'''+extra+'}'})
    engine=Engine(p,ScenarioState(db),conservative=conservative)
    return engine.run(ids['Api.entry'],params or {}),engine,ids


def test_owned_default_mapper_uses_a_proven_primitive_null_default(tmp_path):
    result,engine,_=run(tmp_path,INPUT+'Item item=new ObjectMapper().convertValue(input,Item.class);return item.value;')
    assert result==0 and not engine.approximate


@pytest.mark.parametrize('declaration',['Integer','String'])
def test_reference_null_does_not_become_a_primitive_default(tmp_path,declaration):
    result,_,_=run(tmp_path,INPUT+'Item item=new ObjectMapper().convertValue(input,Item.class);return item.value;',
                   'class Item{public '+declaration+' value;}')
    assert result is None


def test_convert_value_wraps_a_known_null_failure_and_stops_the_body(tmp_path):
    result,engine,ids=run(tmp_path,INPUT+'''ObjectMapper mapper=new ObjectMapper();
      mapper.enable(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES);
      try{mapper.convertValue(input,Item.class);return after();}catch(IllegalArgumentException failure){return caught();}''')
    assert result=='caught'
    assert ids['Api.after'] not in {target for _,kind,target in engine.edges if kind=='executes'}


def test_read_value_exposes_the_checked_json_failure(tmp_path):
    result,engine,ids=run(tmp_path,INPUT+'''String text=new ObjectMapper().writeValueAsString(input);
      ObjectMapper mapper=new ObjectMapper();mapper.enable(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES);
      try{mapper.readValue(text,Item.class);return after();}catch(JsonProcessingException failure){return caught();}''')
    assert result=='caught'
    assert ids['Api.after'] not in {target for _,kind,target in engine.edges if kind=='executes'}


def test_default_unknown_property_failure_is_wrapped_by_convert_value(tmp_path):
    result,_,_=run(tmp_path,EXTRA+'''ObjectMapper mapper=new ObjectMapper();
      try{mapper.convertValue(input,Item.class);return after();}catch(IllegalArgumentException failure){return caught();}''',STRING)
    assert result=='caught'


def test_unknown_property_read_failure_selects_a_native_parent_catch(tmp_path):
    result,_,_=run(tmp_path,EXTRA+'''String text=new ObjectMapper().writeValueAsString(input);
      try{new ObjectMapper().readValue(text,Item.class);return after();}
      catch(JsonMappingException failure){return caught();}''',STRING)
    assert result=='caught'


@pytest.mark.parametrize('setting',[
    'mapper.disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);',
    'mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES,false);',
])
def test_explicit_unknown_property_policy_preserves_known_fields(tmp_path,setting):
    result,engine,_=run(tmp_path,EXTRA+'ObjectMapper mapper=new ObjectMapper();'+setting+
      'Item item=mapper.convertValue(input,Item.class);return item.value;',STRING)
    assert result=='ready' and not engine.approximate


def test_copy_has_independent_settings_and_allocation(tmp_path):
    result,engine,_=run(tmp_path,'''ObjectMapper original=new ObjectMapper();ObjectMapper copy=original.copy();
      copy.disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);
      return original!=copy && original.isEnabled(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
         && !copy.isEnabled(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);''')
    assert result is True and not engine.approximate


def test_alias_configuration_updates_the_same_owned_mapper(tmp_path):
    result,_,_=run(tmp_path,'''ObjectMapper original=new ObjectMapper();ObjectMapper alias=original;
      alias.disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);
      return original.isEnabled(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);''')
    assert result is False


def test_unknown_flag_value_does_not_destroy_an_independent_feature(tmp_path):
    result,engine,_=run(tmp_path,'''ObjectMapper mapper=new ObjectMapper();
      mapper.configure(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES,flag);
      return mapper.isEnabled(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);''',params={'flag':U})
    assert result is True and engine.approximate


def test_unknown_module_registration_does_not_leave_an_old_codec_proven(tmp_path):
    result,engine,_=run(tmp_path,EXTRA+'''ObjectMapper mapper=new ObjectMapper();
      mapper.disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);mapper.findAndRegisterModules();
      Item item=mapper.convertValue(input,Item.class);return item.value;''',STRING)
    assert result is U and engine.approximate


def test_configuration_after_use_is_not_assumed_to_rebuild_cached_behavior(tmp_path):
    result,engine,_=run(tmp_path,'''ObjectMapper mapper=new ObjectMapper();mapper.writeValueAsString("used");
      mapper.disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);
      return mapper.isEnabled(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);''')
    assert result is U and engine.approximate


def test_declared_injected_mapper_does_not_prove_default_configuration(tmp_path):
    result,engine,_=run(tmp_path,'Map input=new HashMap();input.put("value","ready");Item item=mapper.convertValue(input,Item.class);return item.value;',schema=STRING,extra='ObjectMapper mapper;')
    assert result is U and engine.approximate


def test_source_subclass_cannot_be_mistaken_for_the_exact_native_constructor(tmp_path):
    result,engine,_=run(tmp_path,'''Map input=new HashMap();input.put("value","ready");ObjectMapper mapper=new Custom();
      Item item=mapper.convertValue(input,Item.class);return item.value;''',schema=STRING+'class Custom extends ObjectMapper{}')
    assert result is U and engine.approximate


def test_agreed_caller_configuration_survives_a_conservative_join(tmp_path):
    result,_,_=run(tmp_path,'''ObjectMapper mapper=new ObjectMapper();setup(mapper,flag);
      return mapper.isEnabled(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);''',params={'flag':U},conservative=True,
      extra='''void setup(ObjectMapper input,boolean flag){if(flag){input.disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);}
      else{input.disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);}}''')
    assert result is False


def test_conditional_mapper_alias_is_not_treated_as_an_independent_object(tmp_path):
    result,engine,_=run(tmp_path,'''ObjectMapper original=new ObjectMapper();ObjectMapper chosen=original;
      if(flag){chosen=new ObjectMapper();}chosen.disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);
      return original.isEnabled(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);''',params={'flag':U},conservative=True)
    assert result is U and engine.approximate


def test_a_source_exception_namesake_is_not_the_native_json_parent(tmp_path):
    result,_,_=run(tmp_path,EXTRA+'''String text=new ObjectMapper().writeValueAsString(input);
      try{new ObjectMapper().readValue(text,Item.class);return after();}
      catch(JsonMappingException failure){return "wrong-catch";}catch(java.io.IOException failure){return caught();}''',
      STRING+'class JsonMappingException extends RuntimeException{}')
    assert result=='caught'


def test_supported_feature_reference_through_a_null_native_enum_variable_is_static(tmp_path):
    result,engine,_=run(tmp_path,'''ObjectMapper mapper=new ObjectMapper();DeserializationFeature feature=null;
      mapper.disable(feature.FAIL_ON_UNKNOWN_PROPERTIES);
      return mapper.isEnabled(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);''')
    assert result is False and not engine.approximate


def test_literal_json_uses_the_owned_default_codec(tmp_path):
    result,engine,_=run(tmp_path,'''Item item=new ObjectMapper().readValue("{\\"value\\":null}",Item.class);return item.value;''')
    assert result==0 and not engine.approximate
