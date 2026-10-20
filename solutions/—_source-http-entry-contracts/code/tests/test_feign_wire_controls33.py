"""Independent counterexamples for native identity, order and configuration."""
import pytest
from builders import build
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from analyzer.native_storage import JavaList
from analyzer.native_arrays import JavaArray

IMPORTS='''import java.util.*;import org.springframework.web.bind.annotation.*;
import org.springframework.cloud.openfeign.FeignClient;'''


def outbound(e):return [r for r in e.request_events if r['request'] is not None]


def test_configured_property_url_is_not_silently_replaced_by_the_client_name(tmp_path):
    source=IMPORTS+'''@FeignClient(name="service")interface Client{@GetMapping("/read")String read();}
      class Api{Client client;String entry(){return client.read();}}
      @RestController class Target{@GetMapping("/read")String read(){return "wrong";}}'''
    context={'configuration':{'service':{'propertySources':[{'name':'provided','source':{
        'spring.cloud.openfeign.client.config.service.url':'http://unmapped.example'}}]}}}
    p,db,ids=build(tmp_path,{'Api.java':source},context=context);e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{}) is U and not outbound(e)


def test_an_annotation_url_has_priority_over_property_url(tmp_path):
    source=IMPORTS+'''@FeignClient(name="service",url="http://service:8080")interface Client{@GetMapping("/read")String read();}
      class Api{Client client;String entry(){return client.read();}}
      @RestController class Target{@GetMapping("/read")String read(){return "right";}}'''
    context={'configuration':{'service':{'propertySources':[{'name':'provided','source':{
        'spring.cloud.openfeign.client.config.service.url':'http://unmapped.example'}}]}}}
    p,db,ids=build(tmp_path,{'Api.java':source},context=context);e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{})=='right' and not e.approximate
    assert outbound(e)[0]['request']['url']=='http://service:8080/read'


@pytest.mark.parametrize('parameters,call',[
    ('@RequestParam("q")String first,@RequestParam("q")String second','"a","b"'),
    ('@RequestParam(QUERY)String q','"a"'),
    ('@org.springframework.cloud.openfeign.SpringQueryMap Map<String,String> q','new HashMap<String,String>()'),
])
def test_unmodeled_named_template_customization_cannot_become_a_normal_body(tmp_path,parameters,call):
    source=IMPORTS+'''@FeignClient(name="service",url="http://service:8080")interface Client{
        String QUERY="q";@GetMapping("/read")String read('''+parameters+''');}
      class Api{Client client;String entry(){return client.read('''+call+''');}}
      @RestController class Target{@GetMapping("/read")String read(){return "wrong";}}'''
    p,db,ids=build(tmp_path,{'Api.java':source});e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{}) is U and not outbound(e)


@pytest.mark.parametrize('array',[False,True])
def test_unobserved_order_and_array_conversion_are_not_exploded_as_a_convenient_list(tmp_path,array):
    source=IMPORTS+'''@FeignClient(name="service",url="http://service:8080")interface Client{
      @GetMapping("/read")String read(@RequestParam("q")Object q);}
      class Api{Client client;String entry(Object values){return client.read(values);}}
      @RestController class Target{@GetMapping("/read")String read(){return "wrong";}}'''
    p,db,ids=build(tmp_path,{'Api.java':source});e=Engine(p,ScenarioState(db))
    values=JavaArray(['a','b'],'java.lang.String',['String','String']) if array else JavaList(['a','b'],['String','String'])
    if not array:values.order_known=False
    assert e.run(ids['Api.entry'],{'values':values}) is U and not outbound(e)


def test_a_leading_empty_element_does_not_duplicate_before_a_symbolic_integral(tmp_path):
    source=IMPORTS+'''@FeignClient(name="service",url="http://service:8080")interface Client{
      @GetMapping("/read")Integer read(@RequestParam("q")List<Object> q);}
      class Api{Client client;Integer entry(Long id){return client.read(Arrays.asList("",id));}}
      @RestController class Target{@GetMapping("/read")Integer read(@RequestParam("q")List<String> q){return q.size();}}'''
    p,db,ids=build(tmp_path,{'Api.java':source});e=Engine(p,ScenarioState(db))
    identity=e.state.generated_value('Long','independent integral producer')
    assert e.run(ids['Api.entry'],{'id':identity})==2 and not e.approximate
    query=outbound(e)[0]['request']['query']['q']
    assert len(query)==2 and query[0]=='' and query[1]['__integral_origin__']==identity


@pytest.mark.parametrize('option',['headers="X-Mode=research"','params="mode=research"'])
def test_unmodeled_mapping_conditions_are_an_analysis_boundary(tmp_path,option):
    source=IMPORTS+'''@FeignClient(name="service",url="http://service:8080")interface Client{
      @GetMapping(value="/read",'''+option+''')String read();}
      class Api{Client client;String entry(){return client.read();}}
      @RestController class Target{@GetMapping("/read")String read(){return "read";}}'''
    p,db,ids=build(tmp_path,{'Api.java':source});e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{}) is U and e.outcome=='unsupported_semantics boundary'
    assert not outbound(e)


def test_explicit_default_collection_format_uses_the_proven_native_enum(tmp_path):
    source=IMPORTS+'''@FeignClient(name="service",url="http://service:8080")interface Client{
      @org.springframework.cloud.openfeign.CollectionFormat(feign.CollectionFormat.EXPLODED)
      @GetMapping("/read")Integer read(@RequestParam("q")List<String> q);}
      class Api{Client client;Integer entry(){return client.read(Arrays.asList("a","a"));}}
      @RestController class Target{@GetMapping("/read")Integer read(@RequestParam("q")List<String> q){return q.size();}}'''
    p,db,ids=build(tmp_path,{'Api.java':source});e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{})==2 and not e.approximate
    assert outbound(e)[0]['request']['query']=={'q':['a','a']}


def test_a_mapping_annotation_namesake_cannot_create_a_feign_http_method(tmp_path):
    source='''import org.springframework.cloud.openfeign.FeignClient;
      @interface GetMapping{String value();}
      @FeignClient(name="service",url="http://service:8080")interface Client{@GetMapping("/read")String read();}
      class Api{Client client;String entry(){return client.read();}}
      @org.springframework.web.bind.annotation.RestController class Target{
        @org.springframework.web.bind.annotation.GetMapping("/read")String read(){return "wrong";}}'''
    p,db,ids=build(tmp_path,{'Api.java':source});e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{}) is U and not outbound(e)


@pytest.mark.parametrize('route,encoded',[
    ('/items/a b','/items/a%20b'),
    ('/items/пример','/items/%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D1%80'),
    ('/items/100%','/items/100%25'),
    ('/items/a:b','/items/a:b'),
])
def test_literal_method_uri_uses_the_literal_encoding_contract(tmp_path,route,encoded):
    source=IMPORTS+'''@FeignClient(name="service",url="http://service:8080")interface Client{
      @GetMapping("'''+route+'''")String read();}
      class Api{Client client;String entry(){return client.read();}}
      @RestController class Target{@GetMapping("'''+route+'''")String read(){return "right";}}'''
    p,db,ids=build(tmp_path,{'Api.java':source});e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{})=='right' and not e.approximate
    assert outbound(e)[0]['request']['url']=='http://service:8080'+encoded
