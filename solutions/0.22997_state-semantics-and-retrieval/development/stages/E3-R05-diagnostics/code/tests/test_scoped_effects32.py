"""A source-reviewed equipment chain, with full tiny prefix and state oracle."""
from copy import deepcopy
import json
import pytest
from analyzer.engine import Engine
from analyzer.native_storage import JavaList
from analyzer.project import Project
from analyzer.state import ScenarioState,U
from builders import build

INITIAL=[{'id':'A','status':'free'},{'id':'B','status':'free'}]
RID='res:table:service.equipment'


def fixture(tmp_path,body='String projected=item;',suffix='',annotation=''):
    p,db,ids=build(tmp_path,{
      'Warehouse.java':'''import java.util.*;import org.springframework.data.jpa.repository.JpaRepository;
        class Warehouse{Store store;
        @GetMapping("/equipment/{id}")String read(@PathVariable String id){return store.findById(id).get().status;}
        @PostMapping("/reserve/{id}")String reserve(@PathVariable String id){Item item=store.findById(id).get();
          item.status="reserved";store.save(item);return item.status;}}
        @Entity @Table(name="equipment")class Item{@Id String id;public String status;}
        interface Store extends JpaRepository<Item,String>{Optional<Item> findById(String id);Item save(Item value);}''',
      'Approval.java':'''import java.util.*;import org.springframework.web.client.RestTemplate;
        class Approval{RestTemplate rest;'''+annotation+'''String entry(String id,List<String> unknown,boolean inspectOnly){
        String prefix=rest.getForObject("http://warehouse/equipment/"+id,String.class);
        if(inspectOnly){for(String item:unknown){'''+body+'''}'''+suffix+'''return prefix;}
        return rest.postForObject("http://warehouse/reserve/"+id,null,String.class);}}'''
    },rows={'equipment':deepcopy(INITIAL)})
    graph=p.skeleton
    for unit in ('approval','warehouse'):graph['nodes']['module:'+unit]={'kind':'module','name':unit,'deployment_units':[unit]}
    for node in graph['nodes'].values():
        if node.get('file')=='Approval.java':node['module']='approval'
        if node.get('file')=='Warehouse.java':node['module']='warehouse'
    for nid,node in list(graph['nodes'].items()):
        if node.get('kind')=='call_site' and node.get('file')=='Approval.java':
            target=ids['Warehouse.read'] if node.get('callee')=='getForObject' else ids['Warehouse.reserve'] if node.get('callee')=='postForObject' else None
            if target:graph['edges'].append({'source':nid,'type':'remote_call','target':target})
    (tmp_path/'skeleton.json').write_text(json.dumps(graph))
    return Project(tmp_path/'skeleton.json',tmp_path),db,ids


def run(p,db,ids,enabled,values=None,inspect=True,id_='A'):
    state=ScenarioState(db,{'scoped_effect_summary':enabled})
    values=JavaList() if values is None else values
    if not values:values.opaque=True
    engine=Engine(p,state)
    result=engine.run(ids['Approval.entry'],{'id':id_,'unknown':values,'inspectOnly':inspect})
    return result,engine


def prefix_oracle(ids):
    return {('','executes',ids['Approval.entry']),('','executes',ids['Warehouse.read']),
        (ids['Approval.entry'],'remote',ids['Warehouse.read']),(ids['Warehouse.read'],'data',RID)}


def test_readonly_stop_preserves_prefix_full_edges_and_unrelated_rows(tmp_path):
    p,db,ids=fixture(tmp_path)
    _,off=run(p,db,ids,False);result,on=run(p,db,ids,True)
    assert result is U and on.outcome=='unsupported_semantics boundary'
    assert off.outcome==on.outcome and off.edges==on.edges==prefix_oracle(ids)
    assert off.state.database.rows(p.nodes[RID]) is None
    assert on.state.database.rows(p.nodes[RID])==INITIAL
    assert [x['operation'] for x in on.data_operations]==['findById']
    assert any(x['model_version']=='readonly-native-foreach-stop/1' for x in on.effect_events)
    assert not any(x['widened_locations'] for x in on.loss_events)
    assert ScenarioState(db).database.rows(p.nodes[RID])==INITIAL


@pytest.mark.parametrize('enabled',[False,True])
def test_exact_source_read_remote_save_reread_control(tmp_path,enabled):
    p,db,ids=fixture(tmp_path);result,e=run(p,db,ids,enabled,JavaList(['one'],['String']),inspect=False)
    assert result=='reserved'
    expected=prefix_oracle(ids)|{('','executes',ids['Warehouse.reserve']),
        (ids['Approval.entry'],'remote',ids['Warehouse.reserve']),(ids['Warehouse.reserve'],'data',RID)}
    assert e.edges==expected
    assert [x['operation'] for x in e.data_operations]==['findById','findById','save']
    rows=e.state.database.rows(p.nodes[RID]);assert rows[0]['status']=='reserved' and rows[1]==INITIAL[1]
    reread=Engine(p,e.state);assert reread.run(ids['Warehouse.read'],{'id':'A'})=='reserved'


@pytest.mark.parametrize('enabled',[False,True])
def test_remote_failure_before_write_keeps_source_state(tmp_path,enabled):
    p,db,ids=fixture(tmp_path);result,e=run(p,db,ids,enabled,id_='missing')
    assert result is U and e.outcome=='uncaught application exception'
    assert e.state.database.rows(p.nodes[RID])==INITIAL
    assert e.edges==prefix_oracle(ids)
    assert not any(x.get('operation')=='save' for x in e.data_operations)


@pytest.mark.parametrize('body,suffix,annotation',[
    ('String projected=item;','rest.postForObject("http://warehouse/reserve/A",null,String.class);',''),
    ('rest.postForObject("http://warehouse/reserve/"+item,null,String.class);','',''),
    ('String projected=item;','','@Transactional '),
])
def test_potential_writes_and_transaction_do_not_get_readonly_summary(tmp_path,body,suffix,annotation):
    p,db,ids=fixture(tmp_path,body,suffix,annotation);_,e=run(p,db,ids,True)
    assert e.outcome=='unsupported_semantics boundary'
    assert not any(x.get('model_version')=='readonly-native-foreach-stop/1' for x in e.effect_events)


def test_native_qualifiers_do_not_become_first_input_loss(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'class Api{String entry(){return java.util.Base64.getEncoder().encodeToString("ab".getBytes());}}'})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})=='YWI='
    assert not e.loss_events
