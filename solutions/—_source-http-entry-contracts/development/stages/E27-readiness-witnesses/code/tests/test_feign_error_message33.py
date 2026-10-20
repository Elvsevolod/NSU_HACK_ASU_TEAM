"""Feign error messages are typed String values with response provenance."""
import pytest
from datetime import datetime
import hashlib
import json
from builders import build
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U


def fixture(root,status=404,extra='',body='"source error"',returned='String',entry='''try{client.read();return after();}
    catch(feign.FeignException failure){return failure.getMessage();}'''):
    p,db,ids=build(root,{'Api.java':'''import org.springframework.cloud.openfeign.*;
      import org.springframework.boot.autoconfigure.SpringBootApplication;
      import org.springframework.web.bind.annotation.*;import org.springframework.http.ResponseEntity;
      import org.springframework.context.annotation.*;
      @SpringBootApplication @EnableFeignClients class App{}
      @FeignClient(name="service",url="http://service:8080")interface Client{@GetMapping("/item") String read();}
      class Api{Client client;String entry(){'''+entry+'''}String after(){return "wrong";}}
      @RestController class Target{@GetMapping("/item")ResponseEntity<'''+returned+'''> read(){return ResponseEntity.status('''+str(status)+''').body('''+body+''');}}'''+extra})
    return Engine(p,ScenarioState(db)),ids


@pytest.mark.parametrize('status',[400,404,500,503])
def test_default_error_message_retains_the_request_and_response_without_inventing_bytes(tmp_path,status):
    e,ids=fixture(tmp_path,status)
    value=e.run(ids['Api.entry'],{})
    assert value is not U and value['__type__']=='String' and 'non_null' in value['__constraints__']
    fact=value['__feign_error_message__']
    assert fact['status']==status and fact['client_method']==ids['Client.read']
    assert fact['request']['method']=='GET' and fact['request']['path']==['item']
    assert fact['response_body']=='source error' and fact['request_id']==2
    assert not e.approximate and not any(kind=='executes' and target==ids['Api.after'] for _,kind,target in e.edges)
    assert e.request_events[1]['transport_response']['body']=='source error'


def test_generic_exception_catch_receives_the_same_native_message(tmp_path):
    e,ids=fixture(tmp_path,entry='try{client.read();return after();}catch(Exception failure){return failure.getMessage();}')
    value=e.run(ids['Api.entry'],{})
    assert value is not U and value['__type__']=='String' and not e.approximate
    assert value['__feign_error_message__']['response_body']=='source error'


def test_source_custom_error_decoder_does_not_activate_default_error_semantics(tmp_path):
    extra='''class Custom implements feign.codec.ErrorDecoder{
      public Exception decode(String key,feign.Response response){return new IllegalStateException();}}
      @Configuration class Config{@Bean feign.codec.ErrorDecoder custom(){return new Custom();}}'''
    e,ids=fixture(tmp_path,extra=extra)
    assert e.run(ids['Api.entry'],{}) is U and e.approximate
    assert any(kind=='executes' and target==ids['Target.read'] for _,kind,target in e.edges)
    assert not any(kind=='executes' and target==ids['Api.after'] for _,kind,target in e.edges)


def test_error_message_symbol_survives_the_report_datetime_representation(tmp_path):
    e,ids=fixture(tmp_path,returned='Wire',body='new Wire()',
        extra='class Wire{public java.time.LocalDateTime timestamp=java.time.LocalDateTime.now();}')
    e.state.now=datetime(2026,1,2,3,4,5)
    value=e.run(ids['Api.entry'],{})
    assert value is not U and not e.approximate
    recorded=json.loads(json.dumps(value,default=lambda value:value.isoformat()))
    expected='feign-message-'+hashlib.sha256(json.dumps(recorded['__feign_error_message__'],sort_keys=True,ensure_ascii=True).encode()).hexdigest()[:20]
    assert recorded['__symbol__']==expected
