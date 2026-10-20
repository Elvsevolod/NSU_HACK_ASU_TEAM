from decimal import Decimal
import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U,Database
from builders import build


def evaluate(tmp_path,body):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.math.BigDecimal;import java.util.*;class Api {
      Object entry(){BODY} BigDecimal add(BigDecimal left,BigDecimal right){return left.add(right);}
      }'''.replace('BODY',body)})
    e=Engine(p,ScenarioState(db));return e.run(ids['Api.entry'],{}),e,ids


@pytest.mark.parametrize('body,expected',[
 ('List<BigDecimal> xs=new ArrayList<>();return xs.stream().reduce(BigDecimal.ONE,BigDecimal::add);',Decimal('1')),
 ('return Arrays.asList(new BigDecimal("2.50"),new BigDecimal("3.25")).stream().reduce(BigDecimal.ZERO,BigDecimal::add);',Decimal('5.75')),
 ('return Arrays.asList(new BigDecimal("2.50"),new BigDecimal("3.25")).stream().reduce(BigDecimal.ZERO,(a,b)->add(a,b));',Decimal('5.75')),
 ('return new BigDecimal("2.0").equals(new BigDecimal("2.00"));',False),
 ('return new BigDecimal("2.0").compareTo(new BigDecimal("2.00"));',0)])
def test_typed_binary_reduce_empty_values_scale_and_source_calls(tmp_path,body,expected):
    value,e,ids=evaluate(tmp_path,body);assert value==expected,(value,e.warnings)
    if 'add(a,b)' in body:assert (ids['Api.entry'],'calls',ids['Api.add']) in e.edges


@pytest.mark.parametrize('terminal',[
 'reduce(BigDecimal.ZERO,BigDecimal::add,BigDecimal::add)',
 'reduce(BigDecimal::add)', 'parallel().reduce(BigDecimal.ZERO,BigDecimal::add)',
 'reduce(BigDecimal.ZERO,null)',
 'reduce(BigDecimal.ZERO,(a,b)->{throw new IllegalStateException();})'])
def test_unsupported_overloads_parallel_null_and_throw_do_not_complete(tmp_path,terminal):
    value,e,_=evaluate(tmp_path,'return Arrays.asList(new BigDecimal("2.5")).stream().'+terminal+';')
    assert value is U and e.outcome!='returned'


def test_sql_decimal_lexeme_is_not_reconstructed_from_float(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.math.BigDecimal;import java.util.*;import jakarta.persistence.*;import org.springframework.data.jpa.repository.JpaRepository;
       @Entity @Table(name="costs")class Cost{@Id Long id;BigDecimal amount;}
       interface Store extends JpaRepository<Cost,Long>{Optional<Cost> findById(Long id);}
       class Api{Store store;Object entry(){return store.findById(1L).orElseThrow().amount;}}'''})
    dump=tmp_path/'decimal.sql';dump.write_text('USE `service`;\nCREATE TABLE `costs` (\n `id` bigint,\n `amount` decimal(38,6)\n) ENGINE=InnoDB;\nINSERT INTO `costs` VALUES (1,12345678901234567890.012300);\n')
    e=Engine(p,ScenarioState(Database(dump)));value=e.run(ids['Api.entry'],{})
    assert isinstance(value,Decimal) and value.as_tuple()==Decimal('12345678901234567890.012300').as_tuple()


@pytest.mark.parametrize('value,expected',[(3,3),(0,None),(-1,None)])
def test_guard_record_and_component_accessor_follow_source(tmp_path,value,expected):
    p,db,ids=build(tmp_path,{'Api.java':'''record Count(int value){Count{if(value<=0)throw new IllegalArgumentException("positive");}}
      class Api{Object entry(int n){return new Count(n).value();}}'''})
    e=Engine(p,ScenarioState(db));actual=e.run(ids['Api.entry'],{'n':value})
    assert actual==expected if expected is not None else actual is U and e.outcome=='uncaught application exception'


def test_skeleton_constructor_with_wrong_arity_does_not_supply_unknown_extra_parameter(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Error{String text;String detail;
      Error(String text){this.text=text;this.detail=null;}
      Error(String text,String detail){this.text=text;this.detail=detail;}}
      class Api{Object entry(){return new Error("message");}}'''})
    # The fixture skeleton links overloaded names to the final overload; source arity must refine it.
    e=Engine(p,ScenarioState(db));value=e.run(ids['Api.entry'],{})
    assert value['text']=='message' and value['detail'] is None,(value,e.warnings)
    executed={t for _,r,t in e.edges if r=='executes'}
    assert 'method:service:Error#<init>(String)' in executed
    assert 'method:service:Error#<init>(String,String)' not in executed
