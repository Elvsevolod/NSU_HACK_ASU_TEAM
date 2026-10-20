"""Independent legal-order cases; frozen before the ORM order repair."""
from copy import deepcopy
import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from builders import build

ROWS=[{'id':1,'priority':20,'state':'OPEN'},{'id':2,'priority':10,'state':'OPEN'}]


def model(tmp_path,body='return repo.findByState("OPEN");',method='List<Reservation> findByState(String state);',rows=None):
    return build(tmp_path,{'Api.java':'''import java.util.*;import org.springframework.data.jpa.repository.*;
      class Api{Store repo;Object entry(){'''+body+'''}}
      @Entity @Table(name="reservations")class Reservation{@Id public Long id;public Integer priority;public String state;}
      interface Store extends JpaRepository<Reservation,Long>{Reservation save(Reservation value);'''+method+'}'},
      rows={'reservations':deepcopy(ROWS if rows is None else rows)})


def outcomes(p,db,ids):return run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=4)


def test_unsorted_repository_list_does_not_claim_dump_order(tmp_path):
    p,db,ids=model(tmp_path);e=Engine(p,ScenarioState(db));result=e.run(ids['Api.entry'],{})
    assert len(result)==2 and result.order_known is False


def test_inherited_find_all_is_a_collection_not_a_single_result(tmp_path):
    p,db,ids=model(tmp_path,'return repo.findAll();',method='')
    e=Engine(p,ScenarioState(db));result=e.run(ids['Api.entry'],{})
    assert len(result)==2 and result.order_known is False and e.outcome=='returned'


def test_incomplete_permutation_budget_cannot_prove_a_first_id(tmp_path):
    rows=[{'id':i,'priority':i,'state':'OPEN'} for i in range(4)]
    p,db,ids=model(tmp_path,'return repo.findByState("OPEN").get(0).id;',rows=rows)
    paths=outcomes(p,db,ids)
    assert all(path['result'] is U and not path['exploration']['complete'] for path in paths)
    assert all(path['exploration']['path_limit']==4 and path['exploration']['completion_budget']==8 for path in paths)


@pytest.mark.parametrize('reverse',[False,True])
def test_first_row_update_preserves_each_legal_id_and_state(tmp_path,reverse):
    p,db,ids=model(tmp_path,'''List<Reservation> rows=repo.findByState("OPEN");Reservation selected=rows.get(0);
      selected.state="HELD";repo.save(selected);return selected.id;''',rows=list(reversed(ROWS)) if reverse else ROWS)
    paths=outcomes(p,db,ids)
    assert {path['result'] for path in paths}=={1,2}
    for path in paths:
        rows=path['state'].database.tables[('service','reservations')]
        assert all(row['state']==('HELD' if row['id']==path['result'] else 'OPEN') for row in rows)
    assert ScenarioState(db).database.tables[('service','reservations')]==(list(reversed(ROWS)) if reverse else ROWS)


@pytest.mark.parametrize('method,query',[
    ('List<Reservation> findByStateOrderByPriorityAscIdAsc(String state);','findByStateOrderByPriorityAscIdAsc'),
    ('@Query("select r from Reservation r where r.state=?1 order by r.priority asc, r.id asc") List<Reservation> ordered(String state);','ordered')])
def test_source_numeric_total_order_determines_first_id(tmp_path,method,query):
    p,db,ids=model(tmp_path,'return repo.'+query+'("OPEN").get(0).id;',method)
    paths=outcomes(p,db,ids);assert {path['result'] for path in paths}=={2}
    assert all(path['engine'].outcome=='returned' for path in paths)


def test_equal_sort_keys_preserve_tie_alternatives(tmp_path):
    rows=[{**row,'priority':10} for row in ROWS]
    p,db,ids=model(tmp_path,'return repo.ordered("OPEN").get(0).id;',
        '@Query("select r from Reservation r where r.state=?1 order by r.priority asc") List<Reservation> ordered(String state);',rows)
    assert {path['result'] for path in outcomes(p,db,ids)}=={1,2}


def test_explicit_null_precedence_and_limit_follow_source_order(tmp_path):
    rows=[{**ROWS[0],'priority':None},ROWS[1]]
    p,db,ids=model(tmp_path,'return repo.ordered("OPEN").get(0).id;',
        '@Query("select r from Reservation r where r.state=?1 order by r.priority asc nulls last") List<Reservation> ordered(String state);',rows)
    assert {path['result'] for path in outcomes(p,db,ids)}=={2}


def test_top_limit_uses_order_before_selecting_entity(tmp_path):
    p,db,ids=model(tmp_path,'return repo.findFirstByStateOrderByPriorityAscIdAsc("OPEN").id;',
        'Reservation findFirstByStateOrderByPriorityAscIdAsc(String state);')
    assert {path['result'] for path in outcomes(p,db,ids)}=={2}


def test_large_unordered_ordinal_is_a_boundary_in_the_bounded_model(tmp_path):
    rows=[{'id':i,'priority':i,'state':'OPEN'} for i in range(8)]
    p,db,ids=model(tmp_path,'return repo.findByState("OPEN").get(0).id;',rows=rows)
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='unsupported_semantics boundary'


def test_loop_and_stream_keep_source_order_between_tie_groups(tmp_path):
    rows=[{'id':1,'priority':10,'state':'OPEN'},{'id':2,'priority':10,'state':'OPEN'},{'id':3,'priority':20,'state':'OPEN'}]
    method='@Query("select r from Reservation r where r.state=?1 order by r.priority asc") List<Reservation> ordered(String state);'
    p,db,ids=model(tmp_path/'loop','for(Reservation value:repo.ordered("OPEN")){return value.id;}return -1;',method,rows)
    assert {path['result'] for path in outcomes(p,db,ids)}=={1,2}
    p,db,ids=model(tmp_path/'stream','return repo.ordered("OPEN").stream().map(x->x.id).toList();',method,rows)
    assert {tuple(path['result']) for path in outcomes(p,db,ids)}=={(1,2,3),(2,1,3)}


def test_unspecified_null_order_retains_both_provider_policies(tmp_path):
    p,db,ids=model(tmp_path,'return repo.findByStateOrderByPriorityAsc("OPEN").get(0).id;',
        'List<Reservation> findByStateOrderByPriorityAsc(String state);',
        [{**ROWS[0],'priority':None},ROWS[1]])
    assert {path['result'] for path in outcomes(p,db,ids)}=={1,2}


@pytest.mark.parametrize('parameter',['Sort','Pageable','Limit'])
def test_dynamic_order_and_pagination_stop_before_normal_suffix(tmp_path,parameter):
    p,db,ids=model(tmp_path,'repo.findByState("OPEN",null);return 77;',
        'List<Reservation> findByState(String state,org.springframework.data.domain.'+parameter+' order);')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='unsupported_semantics boundary'
    assert not e.data_operations


def test_source_query_namesake_is_not_a_spring_query(tmp_path):
    p,db,ids=model(tmp_path,'repo.ordered("OPEN");return 77;',
        '@Query("select r from Reservation r where r.state=?1") List<Reservation> ordered(String state);}\n@interface Query{}\ninterface Other{')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert 'annotation identity' in ' '.join(e.warnings)


def test_fully_qualified_query_is_supported(tmp_path):
    p,db,ids=model(tmp_path,'return repo.ordered("OPEN").get(0).id;',
        '@org.springframework.data.jpa.repository.Query("select r from Reservation r where r.state=?1 order by r.id asc") List<Reservation> ordered(String state);')
    assert {path['result'] for path in outcomes(p,db,ids)}=={1}


def test_unproved_collation_stops_an_ordinal_consumer(tmp_path):
    p,db,ids=model(tmp_path,'repo.ordered("OPEN").get(0);return 77;',
        '@Query("select r from Reservation r where r.state=?1 order by r.state asc") List<Reservation> ordered(String state);')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='unsupported_semantics boundary'


def test_order_groups_survive_json_and_immutable_request(tmp_path):
    from analyzer.models import wire
    from analyzer.request import Request
    from analyzer.http_json import decode_response
    rows=[{'id':1,'priority':10,'state':'OPEN'},{'id':2,'priority':10,'state':'OPEN'},{'id':3,'priority':20,'state':'OPEN'}]
    p,db,ids=model(tmp_path,method='@Query("select r from Reservation r where r.state=?1 order by r.priority asc") List<Reservation> findByState(String state);',rows=rows)
    e=Engine(p,ScenarioState(db));result=e.run(ids['Api.entry'],{})
    payload=Request.http('service','POST','/rows',body=wire(result)).body
    decoded=decode_response(p,payload,'Reservation[]',p.methods[ids['Api.entry']],e.standard_type,
        lambda message:pytest.fail(message))
    assert decoded.order_known is False
    assert decoded.repository_order['variants']==[[[0,1],[2]]]


def test_nonfinite_decimal_is_an_unproved_comparator():
    from decimal import Decimal
    from analyzer.native_storage import JavaList
    from analyzer.repository_order import apply
    rows=JavaList([{'amount':Decimal('NaN')},{'amount':Decimal(1)}])
    apply(rows,[('amount','asc','last')],'source query')
    assert not rows.order_known and rows.repository_order['supported'] is False
