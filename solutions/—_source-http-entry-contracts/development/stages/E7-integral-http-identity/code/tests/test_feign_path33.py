"""Feign's literal target path is independent from a server's context path."""
import pytest
from builders import build
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U

IMPORTS='''import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.*;'''


def fixture(root,annotation,prefix='/api/edition',class_mapping='',extra=''):
    source=IMPORTS+extra+annotation+class_mapping+''' interface Client{
      @GetMapping("/items/{id}") String read(@PathVariable("id") Long id);}
      class Api{Client client;String entry(){return client.read(7L);}}
      @RestController @RequestMapping("'''+prefix+'''") class Target{
      @GetMapping("/items/{id}") String read(@PathVariable("id") Long id){return "item-"+id;}}'''
    p,db,ids=build(root,{'Api.java':source})
    return Engine(p,ScenarioState(db)),ids


@pytest.mark.parametrize('path',['/api/edition','api/edition/',' /api/edition/ '])
def test_literal_client_prefix_is_applied_before_method_route(tmp_path,path):
    e,ids=fixture(tmp_path,'@FeignClient(name="service",path="'+path+'")')
    assert e.run(ids['Api.entry'],{})=='item-7' and not e.approximate
    outbound=[request for request in e.request_events if request['request'] is not None]
    assert len(outbound)==1
    request=outbound[0]
    assert request['entry']==ids['Target.read']
    assert request['request']['url']=='http://service/api/edition/items/7'
    assert request['bound_arguments']==[{'name':'id','declared_type':'java.lang.Long','value':7}]


def test_client_prefix_and_interface_mapping_are_both_preserved(tmp_path):
    e,ids=fixture(tmp_path,'@FeignClient(path="/api/edition",value="service")',
        '/api/edition/base','@RequestMapping("/base")')
    assert e.run(ids['Api.entry'],{})=='item-7' and not e.approximate
    outbound=[request for request in e.request_events if request['request'] is not None]
    assert len(outbound)==1 and outbound[0]['request']['path']==['api','edition','base','items','7']


@pytest.mark.parametrize('path',['','/'])
def test_empty_client_prefix_keeps_existing_route(tmp_path,path):
    e,ids=fixture(tmp_path,'@FeignClient(value="service",path="'+path+'")','')
    assert e.run(ids['Api.entry'],{})=='item-7' and not e.approximate


@pytest.mark.parametrize('path',['//api/edition','/api/edition//','///api/edition///'])
def test_repeated_slashes_are_not_silently_normalized_to_a_different_target(tmp_path,path):
    e,ids=fixture(tmp_path,'@FeignClient(name="service",path="'+path+'")')
    assert e.run(ids['Api.entry'],{}) is U and e.outcome=='unsupported_semantics boundary'
    assert not any(request['request'] is not None for request in e.request_events)
    assert not any(k=='executes' and t==ids['Target.read'] for _,k,t in e.edges)


@pytest.mark.parametrize('annotation',[
    '@FeignClient(name="service",path=PREFIX)',
    '@FeignClient(name="service",path="${client.prefix}")',
    '@FeignClient(name="service",value="different")',
    '@FeignClient(name="service",url="https://unmapped.example")',
])
def test_unproved_destination_policy_is_not_silently_ignored(tmp_path,annotation):
    e,ids=fixture(tmp_path,annotation,'')
    assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='unsupported_semantics boundary'
    assert not any(request['request'] is not None for request in e.request_events)
    assert not any(k=='executes' and t==ids['Target.read'] for _,k,t in e.edges)


def test_source_feign_annotation_namesake_keeps_ordinary_java_dispatch(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
      @interface FeignClient{String name();String path()default "";}
      @FeignClient(name="service") interface Client{@GetMapping("/items")String read();}
      class Local implements Client{public String read(){return "local";}}
      class Api{String entry(){Client client=new Local();return client.read();}}
      @RestController class Target{@GetMapping("/items")String read(){return "wrong-http";}}'''
    p,db,ids=build(tmp_path,{'Api.java':source});e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{})=='local' and not e.approximate
    assert not any(request['request'] is not None for request in e.request_events)


@pytest.mark.parametrize('registration',['component','factory'])
def test_source_interceptor_effects_cannot_be_silently_skipped(tmp_path,registration):
    extra='''import feign.RequestInterceptor;import feign.RequestTemplate;
      import org.springframework.stereotype.Component;import org.springframework.context.annotation.*;'''
    extra+=('@Component ' if registration=='component' else '')+'''
      class Header implements RequestInterceptor{public void apply(RequestTemplate template){template.header("x-access","secret");}}'''
    if registration=='factory':extra+='''@Configuration class Wiring{
      @Bean RequestInterceptor outbound(){return new Header();}}'''
    e,ids=fixture(tmp_path,'@FeignClient(name="service",path="/api/edition")',extra=extra)
    assert e.run(ids['Api.entry'],{}) is U and e.outcome=='unsupported_semantics boundary'
    assert any('source interceptor' in message for message in e.warnings)
    assert not any(request['request'] is not None for request in e.request_events)
    assert not any(k=='executes' and t==ids['Target.read'] for _,k,t in e.edges)


@pytest.mark.parametrize('native',['import feign.RequestInterceptor;import feign.RequestTemplate;','interface RequestInterceptor{void apply(Object value);}'])
def test_unregistered_or_namesake_interceptor_does_not_change_transport(tmp_path,native):
    annotation='' if native.startswith('import') else '@org.springframework.stereotype.Component '
    argument='RequestTemplate' if native.startswith('import') else 'Object'
    extra=native+annotation+'class Header implements RequestInterceptor{public void apply('+argument+' value){throw new IllegalStateException();}}'
    e,ids=fixture(tmp_path,'@FeignClient(name="service",path="/api/edition")',extra=extra)
    assert e.run(ids['Api.entry'],{})=='item-7' and not e.approximate


@pytest.mark.parametrize('policy',['native','side_effect','namesake','text_only'])
def test_supplied_oauth_context_requires_the_existing_proven_native_factory(tmp_path,policy):
    extra='''import feign.RequestInterceptor;import feign.RequestTemplate;
      import org.springframework.context.annotation.*;'''
    if policy=='text_only':extra+='class Note{String value="OAuth2FeignRequestInterceptor";}'
    else:
        if policy=='namesake':extra+='''class OAuth2FeignRequestInterceptor implements RequestInterceptor{
          public void apply(RequestTemplate template){template.header("unmodeled","value");}}'''
        else:extra+='''import org.springframework.cloud.security.oauth2.client.feign.OAuth2FeignRequestInterceptor;
          import org.springframework.security.oauth2.client.DefaultOAuth2ClientContext;
          import org.springframework.security.oauth2.client.token.grant.client.ClientCredentialsResourceDetails;'''
        arguments='' if policy=='namesake' else 'new DefaultOAuth2ClientContext(),new ClientCredentialsResourceDetails()'
        extra+='''@Configuration class Wiring{
          @Bean RequestInterceptor outbound(){'''+('touch();' if policy=='side_effect' else '')+'''
          return new OAuth2FeignRequestInterceptor('''+arguments+''');}void touch(){throw new IllegalStateException();}}'''
    e,ids=fixture(tmp_path,'@FeignClient(name="service",path="/api/edition")',extra=extra)
    e.state.context['client_oauth_contexts']={'service':{'token':'supplied-fixture-token'}}
    value=e.run(ids['Api.entry'],{})
    requests=[r['request'] for r in e.request_events if r['request'] is not None]
    if policy in ('side_effect','namesake'):
        assert value is U and e.outcome=='unsupported_semantics boundary' and not requests
    else:
        assert value=='item-7' and not e.approximate and len(requests)==1
        assert requests[0]['headers'].get('authorization')==(['Bearer supplied-fixture-token'] if policy=='native' else None)
