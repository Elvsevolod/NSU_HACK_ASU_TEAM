"""A finite consumer owns real source remote/data effects and their prefix."""
import json
import pytest
from analyzer.engine import Engine
from analyzer.project import Project
from analyzer.state import ScenarioState,U
from builders import build


def equipment(tmp_path,callback,rows=None):
    p,db,ids=build(tmp_path,{
      'Warehouse.java':'''import java.util.*;
        class Warehouse{Store store;
          @PostMapping("/reserve/{id}") String reserve(@PathVariable String id){
            Optional<Item> found=store.findById(id);if(found.isEmpty())throw new IllegalArgumentException();
            Item item=found.get();item.status="reserved";store.save(item);return item.status;}
          @GetMapping("/equipment/{id}") String read(@PathVariable String id){return store.findById(id).get().status;}}
        @Entity @Table(name="equipment") class Item{@Id String id;public String status;}
        interface Store extends JpaRepository<Item,String>{Optional<Item> findById(String id);Item save(Item value);}''',
      'Approval.java':'''import java.util.*;import org.springframework.web.client.RestTemplate;
        class Approval{RestTemplate rest;Object entry(){Arrays.asList("A","B").stream().forEach(id->{'''+callback+'''});
        return rest.getForObject("http://warehouse/equipment/A",String.class);}int after(){return 99;}}'''
    },rows={'equipment':rows if rows is not None else [{'id':'A','status':'free'},{'id':'B','status':'free'}]})
    graph=p.skeleton
    for unit in ('approval','warehouse'):
        graph['nodes']['module:'+unit]={'kind':'module','name':unit,'deployment_units':[unit]}
    for node in graph['nodes'].values():
        if node.get('file')=='Approval.java':node['module']='approval'
        if node.get('file')=='Warehouse.java':node['module']='warehouse'
    (tmp_path/'skeleton.json').write_text(json.dumps(graph))
    return Project(tmp_path/'skeleton.json',tmp_path),db,ids


def test_callback_remote_save_and_reread(tmp_path):
    p,db,ids=equipment(tmp_path,'rest.postForObject("http://warehouse/reserve/"+id,null,String.class);')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Approval.entry'],{})=='reserved'
    assert e.state.database.tables[('service','equipment')]==[{'id':'A','status':'reserved','__type__':'Item'},{'id':'B','status':'reserved','__type__':'Item'}]
    assert {edge for edge in e.edges if edge[1]=='remote'}=={
        (ids['Approval.entry'],'remote',ids['Warehouse.reserve']),
        (ids['Approval.entry'],'remote',ids['Warehouse.read'])}
    assert {edge for edge in e.edges if edge[1]=='data'}=={
        (ids['Warehouse.reserve'],'data','res:table:service.equipment'),
        (ids['Warehouse.read'],'data','res:table:service.equipment')}
    assert [x['operation'] for x in e.data_operations]==['findById','save','findById','save','findById']
    assert not e.approximate


def test_callback_remote_failure_keeps_first_write_and_stops_reread(tmp_path):
    p,db,ids=equipment(tmp_path,'rest.postForObject("http://warehouse/reserve/"+id,null,String.class);',rows=[{'id':'A','status':'free'}])
    e=Engine(p,ScenarioState(db));assert e.run(ids['Approval.entry'],{}) is U
    assert e.outcome=='uncaught application exception'
    assert e.state.database.tables[('service','equipment')]==[{'id':'A','status':'reserved','__type__':'Item'}]
    assert ('','executes',ids['Warehouse.read']) not in e.edges
    assert [x['operation'] for x in e.data_operations]==['findById','save','findById']
