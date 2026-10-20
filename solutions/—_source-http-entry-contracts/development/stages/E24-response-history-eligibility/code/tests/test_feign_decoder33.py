"""Feign's default Spring/Jackson decoder executes the JavaBean lifecycle."""
import pytest
from builders import build
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from analyzer.paths import run_paths

IMPORTS='''import org.springframework.cloud.openfeign.*;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.*;
import org.springframework.context.annotation.*;
import com.fasterxml.jackson.annotation.*;import java.util.*;'''
BOOT='@SpringBootApplication @EnableFeignClients class App{}'
DTO='''class Item{private String name;public void setName(String value){name=value.toUpperCase();}
  public String getName(){return name;}}'''


def fixture(root,*,bean=DTO,returned='Item',entry='return client.read().getName();',body='return new Wire();',
            wire='class Wire{public String name="alpha";}',extra='',boot=BOOT,context=None):
    source=IMPORTS+boot+extra+'''@FeignClient(name="service",url="http://service:8080")interface Client{
      @GetMapping("/read")'''+returned+''' read();}
      class Api{Client client;String entry(){'''+entry+'''}String after(){return "after";}}
      @RestController class Target{@GetMapping("/read")Wire read(){'''+body+'''}}'''+wire+bean
    if boot.startswith('@interface SpringBootApplication'):
        source=source.replace('import org.springframework.boot.autoconfigure.SpringBootApplication;','')
    p,db,ids=build(root,{'Api.java':source},context=context)
    return Engine(p,ScenarioState(db)),ids


def executed(e,mid):return any(k=='executes' and target==mid for _,k,target in e.edges)


def test_source_setter_runs_and_changes_the_decoded_value(tmp_path):
    e,ids=fixture(tmp_path)
    assert e.run(ids['Api.entry'],{})=='ALPHA' and not e.approximate
    assert executed(e,ids['Item.setName'])
    assert (ids['Api.entry'],'calls',ids['Item.setName']) not in e.edges


def test_source_default_constructor_precedes_the_setter_but_is_a_reflection_root(tmp_path):
    e,ids=fixture(tmp_path,bean='''class Item{private String prefix="field:";private String name;
      public Item(){prefix="ctor:";}public void setName(String value){name=prefix+value;}
      public String getName(){return name;}}''')
    assert e.run(ids['Api.entry'],{})=='ctor:alpha' and not e.approximate
    assert executed(e,ids['Item.setName']) and not executed(e,ids['Item.<init>'])


def test_boot_unknown_property_default_is_not_a_private_field_projection(tmp_path):
    e,ids=fixture(tmp_path,wire='class Wire{public String name="alpha";public String extra="ignored";}')
    assert e.run(ids['Api.entry'],{})=='ALPHA' and not e.approximate
    assert executed(e,ids['Item.setName'])


def test_a_boot_annotation_namesake_cannot_prove_ignore_unknown(tmp_path):
    boot='@interface SpringBootApplication{} @SpringBootApplication @EnableFeignClients class App{}'
    e,ids=fixture(tmp_path,boot=boot,wire='class Wire{public String name="alpha";public String extra="unproved";}')
    paths=run_paths(e.p,e.state,ids['Api.entry'],{})
    assert len(paths)==2
    assert all(path['result'] is U and path['engine'].approximate for path in paths)


def test_json_property_read_only_preserves_initial_value_and_skips_the_setter(tmp_path):
    e,ids=fixture(tmp_path,bean='''class Item{@JsonProperty(access=JsonProperty.Access.READ_ONLY)
      private String name="local";public void setName(String value){throw new IllegalStateException();}
      public String getName(){return name;}}''')
    assert e.run(ids['Api.entry'],{})=='local' and not e.approximate
    assert not executed(e,ids['Item.setName'])


@pytest.mark.parametrize('failure',['setter','constructor'])
def test_client_construction_failure_stops_the_success_suffix(tmp_path,failure):
    bean=('''class Item{public Item(){throw new IllegalStateException();}public String name;
      public String getName(){return name;}}''' if failure=='constructor' else
      '''class Item{private String name;public void setName(String value){throw new IllegalStateException();}
      public String getName(){return name;}}''')
    e,ids=fixture(tmp_path,bean=bean,entry='client.read();return after();')
    assert e.run(ids['Api.entry'],{}) is U and not executed(e,ids['Api.after'])
    assert executed(e,ids['Target.read'])


def test_lists_decode_elements_through_the_same_source_setter(tmp_path):
    e,ids=fixture(tmp_path,returned='List<Item>',entry='return client.read().get(0).getName();',
        body='return new Wire();',wire='class Wire{public String name="alpha";}')
    # Replace only the source server return type/body before rebuilding its
    # skeleton. A different response shape is a different explicit test input.
    source=(tmp_path/'Api.java').read_text().replace('Wire read(){return new Wire();}',
        'List<Wire> read(){return Arrays.asList(new Wire());}')
    p,db,ids=build(tmp_path,{'Api.java':source});e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{})=='ALPHA' and not e.approximate
    assert executed(e,ids['Item.setName'])


def test_response_entity_wrapper_delegates_body_decoding(tmp_path):
    e,ids=fixture(tmp_path,returned='org.springframework.http.ResponseEntity<Item>',
                  entry='return client.read().getBody().getName();')
    assert e.run(ids['Api.entry'],{})=='ALPHA' and not e.approximate
    assert executed(e,ids['Item.setName'])


def test_known_custom_decoder_does_not_silently_use_the_default_decoder(tmp_path):
    extra='''class Custom implements feign.codec.Decoder{
      public Object decode(feign.Response response,java.lang.reflect.Type type){return null;}}
      @Configuration class Wiring{@Bean feign.codec.Decoder custom(){return new Custom();}}'''
    e,ids=fixture(tmp_path,extra=extra,entry='client.read();return after();')
    assert e.run(ids['Api.entry'],{}) is U and not executed(e,ids['Api.after'])
    assert executed(e,ids['Target.read']) and not executed(e,ids['Item.setName'])


def test_explicit_fail_on_unknown_property_preserves_the_failure_prefix(tmp_path):
    context={'configuration':{'service':{'propertySources':[{'name':'provided','source':{
        'spring.jackson.deserialization.fail-on-unknown-properties':True}}]}}}
    e,ids=fixture(tmp_path,context=context,wire='class Wire{public String name="alpha";public String extra="reject";}',
                  entry='client.read();return after();')
    paths=run_paths(e.p,e.state,ids['Api.entry'],{})
    assert len(paths)==2
    for path in paths:
        actual=path['engine']
        assert path['result'] is U and not executed(actual,ids['Api.after'])
        assert executed(actual,ids['Target.read']) and not actual.approximate
        assert actual.outcome=='uncaught application exception'
    assert {executed(path['engine'],ids['Item.setName']) for path in paths}=={False,True}


def test_default_decode_failure_has_the_native_feign_runtime_type(tmp_path):
    bean='''class Item{public void setName(String value){throw new IllegalStateException();}
      public String getName(){return "unused";}}'''
    e,ids=fixture(tmp_path,bean=bean,entry='''try{client.read();return after();}
      catch(feign.codec.DecodeException failure){return "decode";}
      catch(com.fasterxml.jackson.core.JsonProcessingException failure){return "wrong";}''')
    assert e.run(ids['Api.entry'],{})=='decode' and not e.approximate
    assert not executed(e,ids['Api.after']) and executed(e,ids['Item.setName'])


def test_server_getter_is_executed_once_before_client_setter(tmp_path):
    wire='''class Wire{static int reads=0;public String getName(){reads++;return "alpha";}}'''
    e,ids=fixture(tmp_path,wire=wire)
    assert e.run(ids['Api.entry'],{})=='ALPHA' and not e.approximate
    assert e.state.static_fields['type:service:Wire']['reads']==1
    callbacks=[event for event in e.semantic_callbacks if event['method']==ids['Wire.getName']]
    assert len(callbacks)==1 and callbacks[0]['outcome']=='returned'
    assert not executed(e,ids['Wire.getName']) and executed(e,ids['Item.setName'])
    assert e.request_events[-1]['transport_response']['body']=={'name':'alpha'}


@pytest.mark.parametrize('customization', ['client','scan','property','mapper','boot'])
def test_unobserved_custom_codec_registration_stops_after_the_server_prefix(tmp_path,customization):
    extra='';boot=BOOT;context=None
    if customization=='client':extra='class ClientConfig{}'
    if customization=='scan':boot=BOOT.replace('@EnableFeignClients','@EnableFeignClients(defaultConfiguration=ClientConfig.class)');extra='class ClientConfig{}'
    if customization=='property':
        context={'configuration':{'service':{'propertySources':[{'name':'provided','source':{
            'spring.cloud.openfeign.client.config.service.decoder':'foreign.CustomDecoder'}}]}}}
    if customization=='mapper':extra='@Configuration class Wiring{@Bean com.fasterxml.jackson.databind.ObjectMapper custom(){return new com.fasterxml.jackson.databind.ObjectMapper();}}'
    if customization=='boot':boot=BOOT.replace('@SpringBootApplication','@SpringBootApplication(exclude=org.springframework.boot.autoconfigure.jackson.JacksonAutoConfiguration.class)')
    e,ids=fixture(tmp_path,extra=extra,boot=boot,context=context,entry='client.read();return after();')
    if customization=='client':
        source=(tmp_path/'Api.java').read_text().replace('url="http://service:8080"','url="http://service:8080",configuration=ClientConfig.class')
        p,db,ids=build(tmp_path,{'Api.java':source});e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{}) is U and e.approximate
    assert executed(e,ids['Target.read']) and not executed(e,ids['Api.after'])
    assert not executed(e,ids['Item.setName'])
