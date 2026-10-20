from polygraph.analysis import analyze
from support import fixture,scenario,edge_set


def test_source_enum_method_is_indexed_and_executed_like_other_java_methods(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
enum Mode { VALUE; public static int capacity(){return 7;} }
@RestController class Reader {@GetMapping("/value") int value(){return Mode.capacity();}}
'''
    p,store,ids=fixture(tmp_path,{'Reader.java':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value'}))
    assert detail['paths'][0]['steps'][0]['response']['body']==7
    assert edge_set(block)=={('scenario:arbitrary','executes',ids['Reader.value']),('scenario:arbitrary','executes',ids['Mode.capacity']),(ids['Reader.value'],'calls',ids['Mode.capacity'])}


def test_feign_interface_uses_proxy_while_source_fallback_waits_for_failure(tmp_path):
    gateway='''import org.springframework.web.bind.annotation.*;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.beans.factory.annotation.Autowired;
@FeignClient(name="catalog",fallback=Failover.class)
interface Client {@GetMapping("/item") int read();}
class Failover implements Client {public int read(){return -7;}}
@RestController class Gateway {
 @Autowired private Client client;
 @GetMapping("/read") int read(){return client.read();}
}
'''
    target='''import org.springframework.web.bind.annotation.*;
@RestController class Catalog {@GetMapping("/item") int item(){return 9;}}
'''
    p,store,ids=fixture(tmp_path,{'front/Gateway.java':gateway,'back/Catalog.java':target},modules={'gateway':'front','catalog':'back'})
    block,detail=analyze(p,store,{},scenario({'module':'gateway','path':'/read'}))
    assert detail['paths'][0]['steps'][0]['response']['body']==9
    assert ids['Failover.read'] not in {e[2] for e in edge_set(block,'executes')}
    assert (ids['Gateway.read'],'remote',ids['Catalog.item']) in edge_set(block)


def test_wrong_http_method_stops_scenario_before_later_source_effects(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
@RestController class Endpoint {@GetMapping("/value") int value(){return 7;}}
'''
    p,store,_=fixture(tmp_path,{'Endpoint.java':source})
    block,detail=analyze(p,store,{},scenario({'module':'app','path':'/value','method':'POST'},{'module':'app','path':'/value'}))
    assert not edge_set(block)
    assert len(detail['paths'])==1 and len(detail['paths'][0]['steps'])==1
    assert detail['paths'][0]['steps'][0]['response']['status']==405
    assert detail['paths'][0]['steps'][0]['response']['headers']['Allow']=='GET'


def test_request_outside_known_context_does_not_reach_controller(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
@RestController class Endpoint {@GetMapping("/value") int value(){return 7;}}
'''
    p,store,_=fixture(tmp_path,{'Endpoint.java':source,'application.yml':'server.servlet.context-path: /api\n'})
    block,detail=analyze(p,store,{},scenario({'module':'app','path':'/value'},{'module':'app','path':'/api/value'}))
    assert not edge_set(block) and len(detail['paths'][0]['steps'])==1
    assert detail['paths'][0]['steps'][0]['response']['status']==404
