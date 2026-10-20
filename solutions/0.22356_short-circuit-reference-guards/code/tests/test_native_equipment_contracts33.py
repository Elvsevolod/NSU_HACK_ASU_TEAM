"""Imported Spring/JPA counterpart of the R03/R05 kernel fixtures.

The supplied skeleton defines deployment/SQL ownership. Component scanning,
repository and RestTemplate beans are assumed available; no JVM is launched.
Expected finite edges, messages and rows are derived from the source below.
The opaque-input checks are application slices, not concrete HTTP messages.
"""
from copy import deepcopy
import json

import pytest

from analyzer.engine import Engine
from analyzer.native_storage import JavaList
from analyzer.project import Project
from analyzer.request import Request
from analyzer.state import ScenarioState, U
from builders import build


INITIAL = [{'id': 'A', 'status': 'free'}, {'id': 'B', 'status': 'free'}]
RID = 'res:table:service.equipment'


def equipment(root, rows=None, body='String projected=item;', suffix=''):
    sources = {
        'warehouse/WarehouseApp.java': '''import org.springframework.boot.autoconfigure.SpringBootApplication;
          @SpringBootApplication public class WarehouseApp {}''',
        'warehouse/Warehouse.java': '''import java.util.Optional;
          import org.springframework.beans.factory.annotation.Autowired;
          import org.springframework.web.bind.annotation.*;
          import org.springframework.http.ResponseEntity;
          @RestController public class Warehouse {
            @Autowired Store store;
            @GetMapping("/equipment/{id}") public String read(@PathVariable String id) {
              return store.findById(id).get().status;
            }
            @PostMapping("/reserve/{id}") public ResponseEntity<String> reserve(@PathVariable String id) {
              Optional<Item> found=store.findById(id);
              if(found.isEmpty()) return ResponseEntity.status(404).body("absent");
              Item item=found.get();item.status="reserved";store.save(item);
              return ResponseEntity.ok(item.status);
            }
          }''',
        'warehouse/Item.java': '''import jakarta.persistence.*;
          @Entity @Table(name="equipment") public class Item {
            @Id public String id; public String status;
            protected Item() {}
          }''',
        'warehouse/Store.java': '''import java.util.Optional;
          import org.springframework.data.jpa.repository.JpaRepository;
          public interface Store extends JpaRepository<Item,String> {
            Optional<Item> findById(String id); Item save(Item value);
          }''',
        'approval/ApprovalApp.java': '''import org.springframework.boot.autoconfigure.SpringBootApplication;
          import org.springframework.context.annotation.Bean;
          import org.springframework.web.client.RestTemplate;
          @SpringBootApplication public class ApprovalApp {
            @Bean public RestTemplate restTemplate(){return new RestTemplate();}
          }''',
        'approval/Approval.java': '''import java.util.*;
          import org.springframework.beans.factory.annotation.Autowired;
          import org.springframework.web.bind.annotation.*;
          import org.springframework.web.client.RestTemplate;
          @RestController public class Approval {
            @Autowired RestTemplate rest;
            @PostMapping("/approval") public String entry() {
              Arrays.asList("A","B").stream().forEach(id->{
                rest.postForObject("http://warehouse/reserve/"+id,null,String.class);
              });
              return rest.getForObject("http://warehouse/equipment/A",String.class);
            }
            public String inspect(String id,List<String> unknown,boolean inspectOnly) {
              String prefix=rest.getForObject("http://warehouse/equipment/"+id,String.class);
              if(inspectOnly){for(String item:unknown){BODY}SUFFIX return prefix;}
              return rest.postForObject("http://warehouse/reserve/"+id,null,String.class);
            }
          }'''.replace('BODY', body).replace('SUFFIX', suffix),
    }
    p, db, ids = build(root, sources, rows={'equipment': deepcopy(INITIAL if rows is None else rows)})
    graph = p.skeleton
    for unit in ('approval', 'warehouse'):
        graph['nodes']['module:'+unit] = {'kind': 'module', 'name': unit, 'deployment_units': [unit]}
    for node in graph['nodes'].values():
        if node.get('file'):
            node['module'] = node['file'].split('/')[0]
    # Possible transport edges belong to the input skeleton, not the oracle.
    for nid, node in list(graph['nodes'].items()):
        if node.get('kind') == 'call_site' and node.get('file') == 'approval/Approval.java':
            target = {'getForObject': 'Warehouse.read', 'postForObject': 'Warehouse.reserve'}.get(node.get('callee'))
            if target:
                graph['edges'].append({'source': nid, 'type': 'remote_call', 'target': ids[target]})
    (root/'skeleton.json').write_text(json.dumps(graph))
    return Project(root/'skeleton.json', root), db, ids


def source_edges(ids, caller, targets):
    return {('', 'executes', ids[caller])} | {
        edge for target in targets for edge in (
            ('', 'executes', ids[target]),
            (ids[caller], 'remote', ids[target]),
            (ids[target], 'data', RID),
        )
    }


@pytest.mark.parametrize('enabled', [False, True])
def test_native_finite_callback_full_http_edges_and_rows(tmp_path, enabled):
    p, db, ids = equipment(tmp_path)
    assert {x['status'] for x in p.handler_registration} == {'conditional_controller'}
    e = Engine(p, ScenarioState(db, {'scoped_effect_summary': enabled}))
    assert e.run(ids['Approval.entry'], Request.http('approval', 'POST', 'http://approval/approval')) == 'reserved'
    assert e.outcome == 'returned' and not e.approximate
    assert e.edges == source_edges(ids, 'Approval.entry', ['Warehouse.reserve', 'Warehouse.read'])
    assert [x['operation'] for x in e.data_operations] == ['findById', 'save', 'findById', 'save', 'findById']
    assert e.state.database.rows(p.nodes[RID]) == [
        {'id': 'A', 'status': 'reserved', '__type__': 'Item'},
        {'id': 'B', 'status': 'reserved', '__type__': 'Item'}]
    assert [(x['request']['method'], x['request']['url']) for x in e.request_events] == [
        ('POST', 'http://approval/approval'), ('POST', 'http://warehouse/reserve/A'),
        ('POST', 'http://warehouse/reserve/B'), ('GET', 'http://warehouse/equipment/A')]
    assert {x['request']: (x['status'], x['body']) for x in e.http_responses} == {
        n: (200, 'reserved') for n in (1, 2, 3, 4)}
    assert ScenarioState(db).database.rows(p.nodes[RID]) == INITIAL


@pytest.mark.parametrize('enabled', [False, True])
def test_native_callback_http404_retains_prefix_and_never_reads_suffix(tmp_path, enabled):
    p, db, ids = equipment(tmp_path, INITIAL[:1])
    e = Engine(p, ScenarioState(db, {'scoped_effect_summary': enabled}))
    assert e.run(ids['Approval.entry'], Request.http('approval', 'POST', 'http://approval/approval')) is U
    assert e.outcome == 'uncaught application exception'
    assert e.edges == source_edges(ids, 'Approval.entry', ['Warehouse.reserve'])
    assert [x['operation'] for x in e.data_operations] == ['findById', 'save', 'findById']
    assert e.state.database.rows(p.nodes[RID]) == [{'id': 'A', 'status': 'reserved', '__type__': 'Item'}]
    responses = {x['request']: x for x in e.http_responses}
    assert (responses[2]['status'], responses[2]['body']) == (200, 'reserved')
    assert (responses[3]['status'], responses[3]['body']) == (404, 'absent')
    assert len(e.request_events) == 3


def test_native_readonly_slice_is_a_boundary_with_precise_independent_rows(tmp_path):
    p, db, ids = equipment(tmp_path)
    engines = []
    for enabled in (False, True):
        unknown = JavaList(); unknown.opaque = True
        e = Engine(p, ScenarioState(db, {'scoped_effect_summary': enabled}))
        assert e.run(ids['Approval.inspect'], {'id': 'A', 'unknown': unknown, 'inspectOnly': True}) is U
        assert e.outcome == 'unsupported_semantics boundary'
        assert e.edges == source_edges(ids, 'Approval.inspect', ['Warehouse.read'])
        assert [x['operation'] for x in e.data_operations] == ['findById']
        assert [(x['status'], x.get('body')) for x in e.http_responses] == [(200, 'free')]
        engines.append(e)
    assert engines[0].state.database.rows(p.nodes[RID]) is None
    assert engines[1].state.database.rows(p.nodes[RID]) == INITIAL
    summary = next(x for x in engines[1].effect_events if x.get('model_version') == 'readonly-native-foreach-stop/1')
    assert summary['write_footprint'] == [] and summary['completion'] == 'analysis boundary retained'
    assert summary['return'] == summary['throw'] == 'not supplied'
    assert ScenarioState(db).database.rows(p.nodes[RID]) == INITIAL


def test_loss_records_observed_reads_and_current_request_after_remote_return(tmp_path):
    p, db, ids = equipment(tmp_path)
    unknown = JavaList(); unknown.opaque = True
    e = Engine(p, ScenarioState(db, {'scoped_effect_summary': True}))
    e.run(ids['Approval.inspect'], {'id': 'A', 'unknown': unknown, 'inspectOnly': True})
    loss = next(x for x in e.loss_events if x['phase'] == 'unsupported')
    assert loss['read_locations'] == [
        {'resource': RID, 'operation': 'findById', 'request_id': 2, 'data_operation_index': 0}]
    assert loss['request_id'] == 1
    assert loss['producer_lineage']['request_event_reference'] == 'requests[0]'
    assert loss['producer_lineage']['bound_arguments_reference'] == 'requests[0].bound_arguments'
    assert loss['producer_lineage']['entry'] == ids['Approval.inspect']
    assert loss['location']['file'] == 'approval/Approval.java' and loss['location']['line'] is not None
    assert loss['actual_effect_count'] == 1 and not loss['widened_locations']


@pytest.mark.parametrize('body,suffix', [
    ('rest.postForObject("http://warehouse/reserve/"+item,null,String.class);', ''),
    ('RestTemplate alias=rest;alias.postForObject("http://warehouse/reserve/"+item,null,String.class);', ''),
    ('String projected=item;', 'rest.postForObject("http://warehouse/reserve/A",null,String.class);'),
])
def test_native_potential_remote_write_cannot_get_a_readonly_summary(tmp_path, body, suffix):
    p, db, ids = equipment(tmp_path, body=body, suffix=suffix)
    unknown = JavaList(); unknown.opaque = True
    e = Engine(p, ScenarioState(db, {'scoped_effect_summary': True}))
    assert e.run(ids['Approval.inspect'], {'id': 'A', 'unknown': unknown, 'inspectOnly': True}) is U
    assert e.outcome == 'unsupported_semantics boundary'
    assert not any(x.get('model_version') == 'readonly-native-foreach-stop/1' for x in e.effect_events)
    assert not any(x.get('operation') == 'save' for x in e.data_operations)
    assert e.state.database.rows(p.nodes[RID]) is None
