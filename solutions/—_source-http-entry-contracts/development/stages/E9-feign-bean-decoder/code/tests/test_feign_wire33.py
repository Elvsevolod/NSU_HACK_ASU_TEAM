"""Source-backed URL/query expectations, frozen before the implementation.

Spring Cloud's FeignClientFactoryBean/RequestParam processor and OpenFeign
10.10.1/13.5 Template, QueryTemplate, Expressions and UriUtils are the authority.
No target Java application is compiled or run.
"""
import pytest
from builders import build
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from analyzer.request import MISSING

IMPORTS='''import org.springframework.cloud.openfeign.*;
import org.springframework.web.bind.annotation.*;import java.util.*;'''


def outbound(engine):return [r for r in engine.request_events if r['request'] is not None]


def path_fixture(root,url,*,path='',prefix='',context=None,argument='7L',extra='',name='logical-client',parameters=''):
    annotation='@FeignClient(name="'+name+'",url="'+url+'",path="'+path+'")'
    source=IMPORTS+extra+annotation+'''interface Client{
      @GetMapping("/items/{id}")String read(@PathVariable("id") Long id);}
      class Api{Client client;String entry('''+parameters+'''){return client.read('''+argument+''');}}
      @RestController @RequestMapping("'''+prefix+'''") class Target{
        @GetMapping("/items/{id}")String read(@PathVariable("id")Long id){return "item-"+id;}}'''
    p,db,ids=build(root,{'Api.java':source},context=context)
    return Engine(p,ScenarioState(db)),ids


@pytest.mark.parametrize('url,expected',[
    ('http://service:8080','http://service:8080/items/7'),
    ('https://service:8443','https://service:8443/items/7'),
    ('service:8080','http://service:8080/items/7'),
    ('http://service:8080/','http://service:8080/items/7'),
])
def test_explicit_url_is_used_instead_of_the_logical_client_name(tmp_path,url,expected):
    e,ids=path_fixture(tmp_path,url)
    assert e.run(ids['Api.entry'],{})=='item-7' and not e.approximate
    sent=outbound(e);assert len(sent)==1
    assert sent[0]['request']['url']==expected
    assert sent[0]['entry']==ids['Target.read']
    assert sent[0]['bound_arguments']==[{'name':'id','declared_type':'java.lang.Long','value':7}]
    assert (ids['Api.entry'],'remote',ids['Target.read']) not in e.edges  # Same deployment in this fixture.


def test_url_path_and_annotation_path_are_both_applied(tmp_path):
    e,ids=path_fixture(tmp_path,'http://service:8080/root',path='/version/',prefix='/root/version')
    assert e.run(ids['Api.entry'],{})=='item-7' and not e.approximate
    assert outbound(e)[0]['request']['url']=='http://service:8080/root/version/items/7'


@pytest.mark.parametrize('literal,properties',[
    ('${client.url}',{'client.url':'http://service:8080/root'}),
    ('http://${client.host}:${client.port}/root',{'client.host':'service','client.port':8080}),
    ('${client.url:http://service:8080/root}',{}),
    ('${client.url}',{'client.url':'http://${client.host}:8080/root','client.host':'service'}),
])
def test_url_placeholders_use_the_supplied_calling_deployment(tmp_path,literal,properties):
    context={'configuration':{'service':{'propertySources':[{'name':'provided','source':properties}]}}}
    e,ids=path_fixture(tmp_path,literal,path='/version',prefix='/root/version',context=context)
    assert e.run(ids['Api.entry'],{})=='item-7' and not e.approximate
    assert outbound(e)[0]['request']['url']=='http://service:8080/root/version/items/7'


@pytest.mark.parametrize('url',[
    '${missing.url}','#{dynamicTarget}','http://service:bad','ftp://service',
    'http://user:password@service','http://service/path?unmodeled=1','http://service/#fragment',
    'http://service/repeated//path','http://service/%2Fpath','http://service/{unresolved}',
])
def test_unsupported_url_policy_cannot_dispatch_to_a_convenient_handler(tmp_path,url):
    e,ids=path_fixture(tmp_path,url)
    assert e.run(ids['Api.entry'],{}) is U
    assert not outbound(e)
    assert not any(kind=='executes' and target==ids['Target.read'] for _,kind,target in e.edges)


def test_foreign_configuration_does_not_resolve_a_missing_caller_property(tmp_path):
    context={'configuration':{'foreign':{'propertySources':[{'name':'provided','source':{'client.url':'http://service'}}]}}}
    e,ids=path_fixture(tmp_path,'${client.url}',context=context)
    assert e.run(ids['Api.entry'],{}) is U and not outbound(e)


def query_fixture(root,expression,*,typ='String',client_options='"q"',target_options='value="q",required=false,defaultValue="server-default"',
                  target_type='String',returns='q',result_type='String',extra='',client_annotation=''):
    source=IMPORTS+extra+'''@FeignClient(name="logical-client",url="http://service:8080")interface Client{
      '''+client_annotation+'''@GetMapping("/query")'''+result_type+''' read(@RequestParam('''+client_options+''')'''+typ+''' q);}
      class Api{Client client;'''+result_type+''' entry(){return client.read('''+expression+''');}}
      @RestController class Target{@GetMapping("/query")'''+result_type+''' read(@RequestParam('''+target_options+''')'''+target_type+''' q){return '''+returns+''';}}'''
    p,db,ids=build(root,{'Api.java':source})
    return Engine(p,ScenarioState(db)),ids


@pytest.mark.parametrize('expression,typ,expected,url',[
    ('"plain"','String','plain','http://service:8080/query?q=plain'),
    ('7L','Long','7','http://service:8080/query?q=7'),
    ('true','Boolean','true','http://service:8080/query?q=true'),
    ('"а б&c=1+%"','String','а б&c=1+%','http://service:8080/query?q=%D0%B0%20%D0%B1%26c%3D1%2B%25'),
    ('"10%20off"','String','10 off','http://service:8080/query?q=10%20off'),
    ('"10%20 off"','String','10%20 off','http://service:8080/query?q=10%2520%20off'),
    ('""','String','server-default','http://service:8080/query?q='),
    ('null','String','server-default','http://service:8080/query'),
])
def test_scalar_query_has_actual_encoding_and_normal_server_binding(tmp_path,expression,typ,expected,url):
    e,ids=query_fixture(tmp_path,expression,typ=typ)
    assert e.run(ids['Api.entry'],{})==expected and not e.approximate
    sent=outbound(e);assert len(sent)==1 and sent[0]['request']['url']==url
    assert sent[0]['request']['query_complete'] is True
    assert sent[0]['request']['body'] is MISSING


def test_client_default_value_does_not_invent_an_argument_or_override_the_server_default(tmp_path):
    e,ids=query_fixture(tmp_path,'null',client_options='value="q",required=false,defaultValue="client-default"')
    assert e.run(ids['Api.entry'],{})=='server-default' and not e.approximate
    assert outbound(e)[0]['request']['query']=={}


@pytest.mark.parametrize('expression,size,url,query',[
    ('Arrays.asList("a","a","b")',3,'http://service:8080/query?q=a&q=a&q=b',{'q':['a','a','b']}),
    ('Arrays.asList("a",null,"b")',2,'http://service:8080/query?q=a&q=b',{'q':['a','b']}),
    ('new ArrayList<String>()',0,'http://service:8080/query?q=',{'q':['']}),
    ('Arrays.asList("a","")',1,'http://service:8080/query?q=a',{'q':['a']}),
    ('Arrays.asList("","b")',2,'http://service:8080/query?q=&q=b',{'q':['','b']}),
    ('Arrays.asList("a,b","c")',2,'http://service:8080/query?q=a%2Cb&q=c',{'q':['a,b','c']}),
])
def test_default_exploded_query_preserves_order_duplicates_and_empty_expansion_rules(tmp_path,expression,size,url,query):
    e,ids=query_fixture(tmp_path,expression,typ='List<String>',target_options='"q"',target_type='List<String>',returns='q.size()',result_type='Integer')
    assert e.run(ids['Api.entry'],{})==size and not e.approximate
    sent=outbound(e);assert len(sent)==1
    assert sent[0]['request']['url']==url and sent[0]['request']['query']==query


def test_a_single_comma_value_is_split_by_the_server_collection_converter(tmp_path):
    e,ids=query_fixture(tmp_path,'Arrays.asList("a,b")',typ='List<String>',target_options='"q"',
                        target_type='List<String>',returns='q.size()',result_type='Integer')
    assert e.run(ids['Api.entry'],{})==2 and not e.approximate
    assert outbound(e)[0]['request']['url']=='http://service:8080/query?q=a%2Cb'


@pytest.mark.parametrize('extra,annotation',[
    ('','@org.springframework.cloud.openfeign.CollectionFormat(feign.CollectionFormat.CSV)'),
    ('@interface RequestParam{String value();}',''),
])
def test_nondefault_format_or_annotation_namesake_is_not_treated_as_default_query(tmp_path,extra,annotation):
    e,ids=query_fixture(tmp_path,'"x"',extra=extra,client_annotation=annotation)
    assert e.run(ids['Api.entry'],{}) is U and not outbound(e)


def test_symbolic_integral_path_retains_the_producer_identity(tmp_path):
    e,ids=path_fixture(tmp_path,'http://service:8080',argument='id',parameters='Long id')
    value=e.state.generated_value('Long','independent source identity')
    e.run(ids['Api.entry'],{'id':value})
    sent=outbound(e);assert len(sent)==1
    assert sent[0]['bound_arguments'][0]['value']==value
    assert sent[0]['request']['path'][1]['__integral_origin__']==value
    assert not e.approximate


def test_source_interceptor_prefix_runs_even_when_destination_handler_is_unknown(tmp_path):
    extra='''import org.springframework.boot.autoconfigure.SpringBootApplication;
      import org.springframework.stereotype.Component;import feign.RequestInterceptor;import feign.RequestTemplate;
      @SpringBootApplication @EnableFeignClients class App{}
      @Component class Header implements RequestInterceptor{public void apply(RequestTemplate template){template.header("x-proof","source");}}'''
    e,ids=path_fixture(tmp_path,'http://unmapped.example',extra=extra)
    assert e.run(ids['Api.entry'],{}) is U and not outbound(e)
    assert any(k=='executes' and t==ids['Header.apply'] for _,k,t in e.edges)
    assert not any(k=='executes' and t==ids['Target.read'] for _,k,t in e.edges)
