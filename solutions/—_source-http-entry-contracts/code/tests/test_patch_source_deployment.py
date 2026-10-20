import json
import pytest
from analyzer.engine import Engine
from analyzer.project import Project
from analyzer.state import ScenarioState,U
from analyzer.request_url import request_address
from builders import build


def profile(tmp_path,factory='HttpComponentsClientHttpRequestFactory',port=8123,second_port=8124,configured=True,datastore=False,server_status=None):
    sources={
      'client/src/main/java/Client.java':'''import org.springframework.web.client.RestTemplate;
      import org.springframework.http.client.*;
      @Configuration class Config {
        @Value("${endpoint}")String endpoint;
        @Bean RestTemplate client(){return new RestTemplate(new FACTORY());}
        @Bean Sender sender(RestTemplate client){return new Sender(client,endpoint);}}
      class Sender {final RestTemplate client;final String endpoint;
        Sender(RestTemplate client,String endpoint){this.client=client;this.endpoint=endpoint;}
        Object entry(){return client.patchForObject(endpoint,null,Void.class);}}
      '''.replace('FACTORY',factory),
      'alpha/src/main/java/Alpha.java':'''class Alpha{@PatchMapping("/items/{id}")String change(@PathVariable Long id){return encode(id);}String encode(Long id){return "alpha"+id;}}''',
      'beta/src/main/java/Beta.java':'''class Beta{@PatchMapping("/items/{id}")String change(@PathVariable Long id){return "wrong";}}'''}
    if datastore:
        sources['alpha/src/main/java/Alpha.java']='''import java.util.*;import jakarta.persistence.*;import org.springframework.data.jpa.repository.JpaRepository;
          @Entity @Table(name="items")class Item{@Id Long id;String state;}
          interface Store extends JpaRepository<Item,Long>{Optional<Item> findById(Long id);Item save(Item item);}
          class Alpha{Store store;@PatchMapping("/items/{id}")String change(@PathVariable Long id){
            Item item=store.findById(id).orElseThrow();item.state="changed";store.save(item);return encode(id);}
            String encode(Long id){return "alpha"+id;}}'''
    if server_status:
        sources['alpha/src/main/java/Alpha.java']='class Alpha{@PatchMapping("/items/{id}")Object change(@PathVariable Long id){return ResponseEntity.status('+str(server_status)+').build();}String encode(Long id){return "unused";}}'
    p,db,ids=build(tmp_path,sources,rows={'items':[{'id':9,'state':'old'},{'id':10,'state':'untouched'}]} if datastore else None)
    skeleton=p.skeleton
    for unit in ('client','alpha','beta'):skeleton['nodes']['module:'+unit]={'kind':'module','name':unit,'deployment_units':[unit]}
    for node in skeleton['nodes'].values():
        if node.get('file'):node['module']=node['file'].split('/')[0]
    (tmp_path/'skeleton.json').write_text(json.dumps(skeleton))
    for unit,text in [('client',f'endpoint=http://localhost:{port}/items/9\n'),('alpha','server.port=8123\n'),('beta',f'server.port={second_port}\n')]:
        path=tmp_path/unit/'src/main/resources/application.properties';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    p=Project(tmp_path/'skeleton.json',tmp_path)
    context={'loopback_deployment':configured,'environment_complete':True,'environment':{}}
    return p,db,ids,context


def test_patch_proves_factory_address_server_and_void_only_discards_client_body(tmp_path):
    p,db,ids,ctx=profile(tmp_path);e=Engine(p,ScenarioState(db,ctx))
    assert e.run(ids['Sender.entry'],{}) is None,e.warnings
    assert (ids['Sender.entry'],'remote',ids['Alpha.change']) in e.edges
    assert ('','executes',ids['Alpha.encode']) in e.edges
    assert ('','executes',ids['Beta.change']) not in e.edges
    assert e.http_responses[0]['body']=='alpha9'
    assert any(event.get('factory')=='HttpComponentsClientHttpRequestFactory' for event in e.effect_events)


@pytest.mark.parametrize('options',[
 {'factory':'SimpleClientHttpRequestFactory'}, {'factory':'UnknownFactory'},
 {'port':8999},{'second_port':8123}])
def test_no_proven_send_or_ambiguous_port_never_executes_server(tmp_path,options):
    p,db,ids,ctx=profile(tmp_path,**options);e=Engine(p,ScenarioState(db,ctx))
    assert e.run(ids['Sender.entry'],{}) is U
    assert not any(rel=='remote' for _,rel,_ in e.edges)
    assert not any(t in (ids['Alpha.change'],ids['Beta.change']) for _,rel,t in e.edges if rel=='executes')


def test_uri_components_preserve_port_and_reject_malformed_port():
    address=request_address('https://example.test:9443/a?b=c')
    assert address['scheme']=='https' and address['hostname']=='example.test' and address['port']==9443
    assert request_address('http://example.test:notaport/a') is None


def test_unknown_environment_does_not_select_property_default(tmp_path):
    p,db,ids,ctx=profile(tmp_path)
    path=tmp_path/'client/src/main/resources/application.properties';path.write_text('endpoint=${TARGET:http://localhost:8123/items/9}\n')
    ctx['environment_complete']=False;e=Engine(p,ScenarioState(db,ctx))
    assert e.run(ids['Sender.entry'],{}) is U
    assert e.outcome=='unsupported_semantics boundary' and not any(rel=='remote' for _,rel,_ in e.edges)


def test_patch_transfers_datastore_effects_and_preserves_other_row(tmp_path):
    p,db,ids,ctx=profile(tmp_path,datastore=True);e=Engine(p,ScenarioState(db,ctx))
    assert e.run(ids['Sender.entry'],{}) is None,e.warnings
    assert any(rel=='data' for _,rel,_ in e.edges)
    tables=e.state.snapshot(full=True)['tables']
    assert [{key:row[key] for key in ('id','state')} for row in tables['service.items']]==[{'id':9,'state':'changed'},{'id':10,'state':'untouched'}]
    assert (ids['Sender.entry'],'remote',ids['Alpha.change']) in e.edges
    assert ('','executes',ids['Alpha.encode']) in e.edges


@pytest.mark.parametrize('status',[404,500])
def test_server_http_error_is_not_hidden_by_void(tmp_path,status):
    p,db,ids,ctx=profile(tmp_path,server_status=status);e=Engine(p,ScenarioState(db,ctx))
    assert e.run(ids['Sender.entry'],{}) is U
    assert e.outcome=='uncaught application exception'
    assert any(r['status']==status for r in e.http_responses)
    assert (ids['Sender.entry'],'remote',ids['Alpha.change']) in e.edges
