"""Configuration semantics cannot depend on sibling services or file order."""
import pytest

from polygraph.analysis import analyze
from polygraph.project import Project
from polygraph.spring_config import parse
from polygraph.values import Unknown
from support import fixture,scenario,edge_set


CONTROLLER='''import org.springframework.web.bind.annotation.*;
@RestController class Endpoint {
 @RequestMapping(path="/value",method={RequestMethod.GET,RequestMethod.POST})
 String value(){return "source-result";}
}
'''


def test_java_properties_parser_preserves_escapes_continuations_duplicates_and_lines():
    raw=b'# header\nserver.servlet.context-path=/old\nserver.servlet.context-path=\\u002fpor\\\n tal\nkey\\:name=value#literal\n'
    data=parse('application.properties',raw)[0]
    assert data['server.servlet.context-path']==('/portal',3)
    assert data['key:name']==('value#literal',5)


def test_yaml_native_merge_and_nested_lists_keep_source_locations():
    raw=b'base: &base\n  context-path: /source\nserver:\n  servlet:\n    <<: *base\nspring:\n  profiles:\n    active: [a, b]\n'
    data=parse('application.yml',raw)[0]
    assert data['server.servlet.context-path']==('/source',2)
    assert data['spring.profiles.active[1]']==('b',8)


def test_nested_yaml_context_path_applies_once_to_every_http_verb(tmp_path):
    p,store,ids=fixture(tmp_path,{'Endpoint.java':CONTROLLER,'application.yml':'server:\n  servlet:\n    context-path: /api\n'})
    assert {endpoint.path for endpoint in p.endpoints}=={'/api/value'}
    for verb in ['GET','POST']:
        block,detail=analyze(p,store,{},scenario({'path':'/api/value','method':verb}))
        assert detail['paths'][0]['steps'][0]['response']['body']=='source-result'
        assert edge_set(block)=={('scenario:arbitrary','executes',ids['Endpoint.value'])}
    source=p.configuration.summary()['app']['used']['server.servlet.context-path']
    assert source[0]['file']=='application.yml' and source[0]['line']==3


def test_maven_main_resources_do_not_load_test_or_unrelated_files(tmp_path):
    p,store,_=fixture(tmp_path,{'src/main/java/Endpoint.java':CONTROLLER,
        'src/main/resources/application.yml':'server.servlet.context-path: /main\n',
        'src/test/resources/application.yml':'server.servlet.context-path: /wrong\n',
        'src/main/resources/unused.yml':'bad: !custom value\n'})
    assert p.configuration.context_path('app')=='/main'
    assert not any(d['code']=='configuration-parse' for d in p.diagnostics)
    _,detail=analyze(p,store,{},scenario({'path':'/main/value'}))
    assert detail['paths'][0]['steps'][0]['response']['status']==200


def test_config_and_profiles_are_isolated_per_deployment(tmp_path):
    alpha=CONTROLLER.replace('@RestController','@org.springframework.context.annotation.Profile("prod") @RestController')
    beta=CONTROLLER.replace('@RestController','@org.springframework.context.annotation.Profile("dev") @RestController')
    p,_,_=fixture(tmp_path,{'alpha/Endpoint.java':alpha,'beta/Endpoint.java':beta,
      'alpha/application.yml':'spring.profiles.active: prod\nserver.servlet.context-path: /one\n',
      'beta/application.yml':'spring.profiles.active: dev\nserver.servlet.context-path: /two\n'},modules={'first':'alpha','second':'beta'})
    assert {(e.module,e.path) for e in p.endpoints}=={('first','/one/value'),('second','/two/value')}
    assert all(p.enabled(p.methods[e.method]) is True for e in p.endpoints)


def test_profile_documents_filename_and_last_active_profile_order(tmp_path):
    p,_,_=fixture(tmp_path,{'Endpoint.java':CONTROLLER,
       'application.yml':'spring.profiles.active: [blue, green]\nserver.servlet.context-path: /base\n---\nspring.profiles: blue\nserver.servlet.context-path: /blue\n',
       'application-green.yml':'server.servlet.context-path: /green\n',
       'application-disabled.yml':'bad: !tag cannot-be-read\n'})
    assert p.configuration.context_path('app')=='/green'
    assert not any(d['file']=='application-disabled.yml' for d in p.diagnostics)


def test_unresolved_profile_override_does_not_pretend_base_value_is_final(tmp_path):
    p,store,_=fixture(tmp_path,{'Endpoint.java':CONTROLLER,
      'application.yml':'server.servlet.context-path: /base\n---\nspring.profiles: prod\nserver.servlet.context-path: /conditional\n'})
    assert isinstance(p.configuration.context_path('app'),Unknown)
    block,detail=analyze(p,store,{},scenario({'path':'/value'}))
    assert not edge_set(block) and detail['status']=='partial'
    assert any('configuration' in d['message'] for d in detail['paths'][0]['diagnostics'])


def test_ordered_native_environment_sources_override_in_declared_order(tmp_path):
    configuration={'app':{'profiles':['prod'],'propertySources':[
        {'name':'runtime','source':{'server.servlet.context-path':'${ROOT:/fallback}','flag':True,'text':'before-${flag}-after','ROOT':'/runtime'}},
        {'name':'classpath','source':{'server.servlet.context-path':'/ignored'}}]}}
    p,store,_=fixture(tmp_path,{'Endpoint.java':CONTROLLER,'bootstrap.yml':'spring.cloud.config.uri: http://config:8888\n'},configuration=configuration)
    assert p.configuration.context_path('app')=='/runtime'
    assert p.configuration.value('app','text')=='before-true-after'
    _,detail=analyze(p,store,{'configuration':configuration},scenario({'path':'/runtime/value'}))
    assert detail['paths'][0]['steps'][0]['response']['status']==200
    configuration['app']['propertySources'][0]['source']['ROOT']='/changed'
    assert p.configuration.context_path('app')=='/runtime'
    with pytest.raises(ValueError,match='rebuild Project'):analyze(p,store,{'configuration':configuration},scenario({'path':'/changed/value'}))


def test_external_config_without_snapshot_is_unknown_and_never_fetched(tmp_path):
    p,store,_=fixture(tmp_path,{'Endpoint.java':CONTROLLER,'bootstrap.yml':'spring.cloud.config.uri: http://unreachable.invalid:8888\nspring.profiles.active: local\nclient.url: http://local.invalid\n'})
    assert isinstance(p.configuration.context_path('app'),Unknown)
    assert isinstance(p.configuration.value('app','client.url'),Unknown)
    assert p.configuration.profiles['app'] is None
    block,detail=analyze(p,store,{},scenario({'path':'/value'}))
    assert not edge_set(block) and detail['paths'][0]['coverage']=='cutoff'


def test_configuration_and_profile_order_invalidate_ir_cache(tmp_path):
    cache=tmp_path/'cache.json'
    p,_,_=fixture(tmp_path,{'Endpoint.java':CONTROLLER,'application.properties':'server.servlet.context-path=/first\n'},cache=cache,profiles=['blue','green'])
    before=p.fingerprint;p.save_cache()
    (p.root/'application.properties').write_text('server.servlet.context-path=/second\n')
    changed=Project(p.root,p.skeleton,cache,profiles=['blue','green'])
    reordered=Project(p.root,p.skeleton,cache,profiles=['green','blue'])
    assert len({before,changed.fingerprint,reordered.fingerprint})==3
    assert changed.configuration.context_path('app')=='/second'


def test_disabled_config_client_does_not_invent_an_external_override(tmp_path):
    p,_,_=fixture(tmp_path,{'Endpoint.java':CONTROLLER,
        'bootstrap.properties':'spring.cloud.config.uri=http://unreachable.invalid\nspring.cloud.config.enabled=false\n',
        'application.yml':'server.servlet.context-path: /local\n'})
    assert p.configuration.context_path('app')=='/local'


def test_property_placeholders_default_cycle_and_missing_value(tmp_path):
    p,_,_=fixture(tmp_path,{'Endpoint.java':CONTROLLER,
      'application.properties':'server.servlet.context-path=${root:/fallback}\nfirst=${second}\nsecond=${first}\nmissing=${NOT_GIVEN}\n'})
    assert p.configuration.context_path('app')=='/fallback'
    assert isinstance(p.configuration.value('app','first'),Unknown)
    assert isinstance(p.configuration.value('app','missing'),Unknown)


def test_config_snapshot_conflict_is_detected_before_indexing_routes(tmp_path):
    with pytest.raises(ValueError,match='conflict'):
        fixture(tmp_path,{'Endpoint.java':CONTROLLER},profiles=['dev'],configuration={'app':{'profiles':['prod'],'propertySources':[]}})


@pytest.mark.parametrize('version,path', [('1.5.22.RELEASE','/legacy'),('2.0.3.RELEASE','/modern')])
def test_boot_version_selects_the_supported_context_path_property(tmp_path,version,path):
    pom='<project><parent><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-parent</artifactId><version>'+version+'</version></parent></project>'
    p,_,_=fixture(tmp_path,{'Endpoint.java':CONTROLLER,'pom.xml':pom,
        'application.properties':'server.context-path=/legacy\nserver.servlet.context-path=/modern\n'})
    assert p.configuration.context_path('app')==path


def test_config_yaml_profile_syntax_is_not_retroactively_applied_to_old_boot(tmp_path):
    p,_,_=fixture(tmp_path,{'Endpoint.java':CONTROLLER,
        'pom.xml':'<project><parent><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-parent</artifactId><version>2.0.3.RELEASE</version></parent></project>',
        'application.yml':'server.servlet.context-path: /base\n---\nspring.config.activate.on-profile: prod\nserver.servlet.context-path: /unconditional-in-this-version\n'},profiles=['dev'])
    assert p.configuration.context_path('app')=='/unconditional-in-this-version'


def test_equal_values_across_unknown_profile_do_not_invent_an_unknown_prefix(tmp_path):
    p,_,_=fixture(tmp_path,{'Endpoint.java':CONTROLLER,
        'application.yml':'server.servlet.context-path: /same\n---\nspring.profiles: prod\nserver.servlet.context-path: /same\n'})
    assert p.configuration.context_path('app')=='/same'


def test_null_in_higher_property_source_does_not_hide_lower_value(tmp_path):
    configuration={'app':{'propertySources':[{'name':'higher','source':{'server.servlet.context-path':None}},
        {'name':'lower','source':{'server.servlet.context-path':'/source'}}]}}
    p,_,_=fixture(tmp_path,{'Endpoint.java':CONTROLLER},configuration=configuration)
    assert p.configuration.context_path('app')=='/source'


def test_resolved_snapshot_does_not_hide_a_custom_dispatcher_servlet_path(tmp_path):
    configuration={'app':{'propertySources':[{'name':'runtime','source':{'spring.mvc.servlet.path':'/custom'}}]}}
    p,store,_=fixture(tmp_path,{'Endpoint.java':CONTROLLER},configuration=configuration)
    assert isinstance(p.configuration.context_path('app'),Unknown)
    _,detail=analyze(p,store,{'configuration':configuration},scenario({'path':'/value'}))
    assert all(path['coverage']=='cutoff' for path in detail['paths'])


def test_default_profile_snapshot_conflicts_with_explicit_active_profile(tmp_path):
    with pytest.raises(ValueError,match='conflict'):
        fixture(tmp_path,{'Endpoint.java':CONTROLLER},profiles=['prod'],configuration={'app':{'profiles':[],'propertySources':[]}})


@pytest.mark.parametrize('extra',['spring.profiles.include: extra\n','spring.profiles.group.prod: extra\n','spring.config.activate.on-cloud-platform: kubernetes\n'])
def test_unsupported_profile_activation_does_not_confirm_local_configuration(tmp_path,extra):
    p,store,_=fixture(tmp_path,{'Endpoint.java':CONTROLLER,
        'application.yml':'spring.profiles.active: prod\nserver.servlet.context-path: /base\n'+extra})
    assert p.configuration.profiles['app'] is None
    assert isinstance(p.configuration.context_path('app'),Unknown)
    block,detail=analyze(p,store,{},scenario({'path':'/value'}))
    assert not edge_set(block) and all(path['coverage']=='cutoff' for path in detail['paths'])
