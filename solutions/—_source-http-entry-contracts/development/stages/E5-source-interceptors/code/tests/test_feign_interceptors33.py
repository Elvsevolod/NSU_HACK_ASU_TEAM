"""Frozen source expectations: native callback effects, registration and order.

Feign 10.10.1 RequestTemplate/HeaderTemplate and Spring Cloud 2.2.5 are the
source authority. Target JVMs and Spring applications are never started.
"""
from copy import deepcopy
import pytest
from builders import build
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U

IMPORTS='''import feign.RequestInterceptor;import feign.RequestTemplate;
import org.springframework.cloud.openfeign.*;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.*;
import org.springframework.core.annotation.Order;
import org.springframework.web.bind.annotation.*;import java.util.*;'''
BOOT='@SpringBootApplication @EnableFeignClients class App{}'


def fixture(root,extra,entry='return client.read(7L);',context=None,boot=BOOT,client_config=False,client_header=False):
    source=IMPORTS+boot+extra+'''
      @FeignClient(name="service",path="/wire")interface Client{
        @GetMapping("/items/{id}")String read(@PathVariable("id")Long id);}
      class Api{Client client;String entry(){'''+entry+'''}void after(){}}
      @RestController @RequestMapping("/wire")class Target{
        @GetMapping("/items/{id}")String read(@PathVariable("id")Long id){return "ok";}}'''
    if client_config:source=source.replace('@FeignClient(name="service",path="/wire")','@FeignClient(name="service",path="/wire",configuration=Header.class)')
    if client_header:
        key=client_header if isinstance(client_header,str) else 'X-Access'
        source=source.replace('String read(@PathVariable("id")Long id);','String read(@PathVariable("id")Long id,@RequestHeader("'+key+'")String key);')
    p,db,ids=build(root,{'Api.java':source},context=context)
    return p,db,ids


def outbound(e):return [row for row in e.request_events if row['request'] is not None]


def headers(e):return [row['request']['headers'] for row in outbound(e)]


def ran(e,mid):return any(kind=='executes' and target==mid for _,kind,target in e.edges)


@pytest.mark.parametrize('registration',['component','factory'])
def test_registered_source_callback_and_helper_execute_before_send(tmp_path,registration):
    extra=('@Component ' if registration=='component' else '')+'''
      class Header implements RequestInterceptor{String pick(){return "source-value";}
        public void apply(RequestTemplate template){template.header("X-Access",pick());}}'''
    if registration=='factory':extra+='''@Configuration class Wiring{
      @Bean RequestInterceptor outbound(){return new Header();}}'''
    p,db,ids=fixture(tmp_path,extra);e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{})=='ok' and not e.approximate
    assert headers(e)==[{'x-access':['source-value']}]
    assert ran(e,ids['Header.apply']) and ran(e,ids['Header.pick']) and ran(e,ids['Target.read'])
    assert (ids['Header.apply'],'calls',ids['Header.pick']) in e.edges
    if registration=='factory':assert not ran(e,ids['Wiring.outbound'])


def test_value_field_is_bound_from_its_own_module_configuration(tmp_path):
    context={'configuration':{'service':{'propertySources':[{'name':'provided','source':{'header.value':'configured'}}]}}}
    p,db,ids=fixture(tmp_path,'''@Component class Header implements RequestInterceptor{
      @Value("${header.value}")private String key;
      public void apply(RequestTemplate template){template.header("x-access",key);}}''',context=context)
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})=='ok' and not e.approximate
    assert headers(e)==[{'x-access':['configured']}]


@pytest.mark.parametrize('body,expected',[
    ('template.header("X-Access","one","two","one");',['one','two']),
    ('template.header("X-Access","one");template.header("x-access","two","one");',['one','two']),
    ('template.header("X-Access","one").header("x-access","two");',['one','two']),
    ('template.header("X-Access","one");template.header("x-access");',None),
    ('template.header("X-Access","one");template.removeHeader("x-access");',None),
    ('template.header("X-Access","one");template.header("x-access"," ","",(String)null);',['one']),
    ('template.header("x-access",Arrays.asList("one","two","one"));',['one','two']),
])
def test_native_literal_header_contract(tmp_path,body,expected):
    p,db,ids=fixture(tmp_path,'@Component class Header implements RequestInterceptor{public void apply(RequestTemplate template){'+body+'}}')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})=='ok' and not e.approximate
    assert headers(e)==([{}] if expected is None else [{'x-access':expected}])


def test_interceptor_throw_preserves_prefix_and_prevents_outbound_request(tmp_path):
    p,db,ids=fixture(tmp_path,'''@Component class Header implements RequestInterceptor{
      void prefix(){}void skipped(){}public void apply(RequestTemplate template){
      prefix();template.header("x-access","prefix");throw new IllegalStateException();}}''',
      'try{return client.read(7L);}catch(IllegalStateException expected){return "caught";}')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})=='caught' and not e.approximate
    assert ran(e,ids['Header.apply']) and ran(e,ids['Header.prefix'])
    assert not ran(e,ids['Header.skipped']) and not ran(e,ids['Target.read']) and not outbound(e)


@pytest.mark.parametrize('name',['null','""'])
def test_invalid_header_name_throws_native_argument_error_before_send(tmp_path,name):
    p,db,ids=fixture(tmp_path,'@Component class Header implements RequestInterceptor{public void apply(RequestTemplate template){template.header('+name+',"value");}}',
      'try{return client.read(7L);}catch(IllegalArgumentException expected){return "invalid";}')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})=='invalid' and not e.approximate
    assert ran(e,ids['Header.apply']) and not outbound(e) and not ran(e,ids['Target.read'])


def test_bean_instance_persists_across_requests_and_isolated_scenarios(tmp_path):
    p,db,ids=fixture(tmp_path,'''@Component class Header implements RequestInterceptor{private int count;
      public void apply(RequestTemplate template){count++;template.header("x-access","call-"+count);}}''',
      'client.read(7L);return client.read(8L);')
    for state in (ScenarioState(db),ScenarioState(db)):
        e=Engine(p,state);assert e.run(ids['Api.entry'],{})=='ok' and not e.approximate
        assert headers(e)==[{'x-access':['call-1']},{'x-access':['call-2']}]


def test_two_unordered_callbacks_enumerate_legal_orders_even_with_order_annotation(tmp_path):
    p,db,ids=fixture(tmp_path,'''@Component @Order(1)class Alpha implements RequestInterceptor{
      public void apply(RequestTemplate template){template.header("x-access","a");}}
      @Component @Order(2)class Beta implements RequestInterceptor{
      public void apply(RequestTemplate template){template.header("x-access","b");}}''')
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=4)
    assert len(paths)==2 and all(row['exploration']['complete'] and row['result']=='ok' for row in paths)
    assert {tuple(headers(row['engine'])[0]['x-access']) for row in paths}=={('a','b'),('b','a')}
    assert all(ran(row['engine'],ids['Alpha.apply']) and ran(row['engine'],ids['Beta.apply']) for row in paths)


def test_exhausted_order_budget_never_picks_a_convenient_callback_order(tmp_path):
    extra=''.join('@Component class '+name+' implements RequestInterceptor{public void apply(RequestTemplate template){template.header("x-access","'+name+'");}}'
        for name in ('Alpha','Beta','Gamma'))
    p,db,ids=fixture(tmp_path,extra);paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=2)
    assert paths and all(not row['exploration']['complete'] and not outbound(row['engine']) for row in paths)
    assert all(row['engine'].outcome=='unsupported_semantics boundary' for row in paths)


@pytest.mark.parametrize('policy',['missing_value','unknown_template_operation','custom_scan','constructor','custom_client_configuration'])
def test_unproved_registration_initialization_or_effects_remain_boundaries(tmp_path,policy):
    body='template.header("x-access","value");';fields='';ctor='';boot=BOOT
    if policy=='missing_value':fields='@Value("${missing.value}")private String key;';body='template.header("x-access",key);'
    if policy=='unknown_template_operation':body='template.query("unmodeled","value");'
    if policy=='custom_scan':boot='@SpringBootApplication @EnableFeignClients @ComponentScan("unmodeled")class App{}'
    if policy=='constructor':ctor='Header(){throw new IllegalStateException();}'
    extra='@Component class Header implements RequestInterceptor{'+fields+ctor+'public void apply(RequestTemplate template){'+body+'}}'
    p,db,ids=fixture(tmp_path,extra,boot=boot,client_config=policy=='custom_client_configuration')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U and e.outcome=='unsupported_semantics boundary'
    assert not outbound(e) and not ran(e,ids['Target.read'])


def test_source_bean_and_template_copies_preserve_native_ownership(tmp_path):
    p,db,ids=fixture(tmp_path,'@Component class Header implements RequestInterceptor{public void apply(RequestTemplate template){RequestTemplate alias=template;alias.header("x-access","owned");}}')
    original=ScenarioState(db);e=Engine(p,original)
    assert e.run(ids['Api.entry'],{})=='ok' and headers(e)==[{'x-access':['owned']}]
    copied=deepcopy(original);other=Engine(p,copied)
    assert other.run(ids['Api.entry'],{})=='ok' and headers(other)==[{'x-access':['owned']}]


@pytest.mark.parametrize('key',['X-Access','x-access'])
def test_callback_appends_to_existing_client_header_as_one_value(tmp_path,key):
    p,db,ids=fixture(tmp_path,'@Component class Header implements RequestInterceptor{public void apply(RequestTemplate template){template.header("x-access","hook");}}',
      'return client.read(7L,"seed");',client_header=key)
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})=='ok' and not e.approximate
    assert headers(e)==[{'x-access':['seed','hook']}]


def test_null_varargs_array_throws_in_arrays_as_list_before_header_update(tmp_path):
    p,db,ids=fixture(tmp_path,'@Component class Header implements RequestInterceptor{public void apply(RequestTemplate template){template.header("x-access",(String[])null);}}',
      'try{return client.read(7L);}catch(NullPointerException expected){return "null-array";}')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})=='null-array' and not e.approximate and not outbound(e)


@pytest.mark.parametrize('typ',['Iterable<String>','List<String>'])
def test_null_iterable_header_values_clear_instead_of_appending_null(tmp_path,typ):
    p,db,ids=fixture(tmp_path,'@Component class Header implements RequestInterceptor{public void apply(RequestTemplate template){template.header("x-access","seed");template.header("x-access",('+typ+')null);}}')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})=='ok' and not e.approximate
    assert headers(e)==[{}]


@pytest.mark.parametrize('policy',['condition','factory_scope','duplicate_name'])
def test_unproved_conditional_scope_or_duplicate_bean_registration_never_dispatches(tmp_path,policy):
    annotation='@org.springframework.boot.autoconfigure.condition.ConditionalOnProperty(name="unmodeled")' if policy=='condition' else ''
    extra=('@Component ' if policy!='factory_scope' else '')+annotation+'''class Header implements RequestInterceptor{
      public void apply(RequestTemplate template){template.header("x-access","hook");}}'''
    if policy in ('factory_scope','duplicate_name'):
        scope='@Scope("prototype")' if policy=='factory_scope' else ''
        extra+='@Configuration class Wiring{@Bean '+scope+' RequestInterceptor header(){return new Header();}}'
    p,db,ids=fixture(tmp_path,extra);e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{}) is U and e.outcome=='unsupported_semantics boundary'
    assert not outbound(e) and not ran(e,ids['Header.apply'])
