from copy import deepcopy
import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.native_storage import JavaList,ReadOnlyList
from analyzer.java_collections import reference_equal
from analyzer.state import ScenarioState,U
from builders import build


def make(tmp_path,body):
    return build(tmp_path,{'Api.java':'''import java.util.*;import java.util.stream.*;
    class Api {Object entry(){BODY} int visit(int n){return n*3;} }'''.replace('BODY',body)})


def test_materializes_null_aliases_and_new_storage(tmp_path):
    p,db,ids=make(tmp_path,'''Object a=new Object();List<Object> xs=new ArrayList<>();xs.add(a);xs.add(null);xs.add(a);
        List<Object> result=xs.stream().toList();xs.clear();return result;''')
    e=Engine(p,ScenarioState(db));result=e.run(ids['Api.entry'],{})
    assert isinstance(result,ReadOnlyList) and len(result)==3
    assert result[0] is result[2] and result[1] is None
    assert reference_equal(result,result) is True
    other=ReadOnlyList(JavaList());other.java_identity=None
    assert reference_equal(result,other) is U
    copied=deepcopy(result);assert copied.unmodifiable and len(copied)==3 and copied[0] is copied[2]


@pytest.mark.parametrize('mutation',['add(7)','set(0,7)','remove(0)','clear()','addAll(Arrays.asList(7))','removeAll(Arrays.asList(1))','iterator().remove()'])
def test_unmodifiable_including_empty_operations(tmp_path,mutation):
    p,db,ids=make(tmp_path,'List<Integer> xs=new ArrayList<>();List<Integer> out=xs.stream().toList();out.'+mutation+';return 9;')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert any('UnsupportedOperationException' in w for w in e.warnings),e.warnings


@pytest.mark.parametrize('terminal',['toList()','collect(Collectors.toList())'])
def test_previously_created_stream_cannot_materialize_opaque_empty_carrier(tmp_path,terminal):
    p,db,ids=make(tmp_path,'List<Integer> xs=new ArrayList<>();Stream<Integer> s=xs.stream();Extension.touch(xs);return s.'+terminal+';')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='unsupported_semantics boundary'
    assert any('unknown stream source membership' in w for w in e.warnings)


def test_source_callbacks_and_known_filter(tmp_path):
    p,db,ids=make(tmp_path,'return Arrays.asList(1,2,3).stream().filter(x->x>1).map(x->visit(x)).toList();')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==[6,9]
    assert (ids['Api.entry'],'calls',ids['Api.visit']) in e.edges


def test_unordered_callbacks_enumerated_without_inventing_encounter_order(tmp_path):
    p,db,ids=make(tmp_path,'return new HashSet<Integer>(Arrays.asList(1,2)).stream().map(x->visit(x)).toList();')
    outcomes=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=4)
    assert {tuple(o['result']) for o in outcomes}=={(3,6),(6,3)}
    assert all((ids['Api.entry'],'calls',ids['Api.visit']) in o['engine'].edges for o in outcomes)


def test_boxed_types_and_no_wire_mutability_marker(tmp_path):
    p,db,ids=make(tmp_path,'return Arrays.asList(true,1,1L,null).stream().toList();')
    e=Engine(p,ScenarioState(db));result=e.run(ids['Api.entry'],{})
    assert list(result)==[True,1,1,None] and result.kinds[:3]==['Boolean','Integer','Long']
    from analyzer.models import wire
    assert type(wire(result)) is list


@pytest.mark.parametrize('body',[
 'return Arrays.asList(1).stream().map(null).toList();',
 'List<Integer> xs=new ArrayList<>();xs.add(1);return xs.stream().map(x->{xs.add(2);return x;}).toList();',
 'return Arrays.asList(1,2).stream().map(x->{if(x==2)throw new IllegalStateException();return x;}).toList();'])
def test_null_interference_and_throw_do_not_return_list(tmp_path,body):
    p,db,ids=make(tmp_path,body);e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{}) is U and e.outcome!='returned'


def test_implicit_record_constructor_keeps_source_mapper_values(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;record Item(Long id,String text){}
       class Api {Item convert(Long id){return new Item(id,"mapped");}
       Object entry(){return Arrays.asList(6L,9L).stream().map(x->convert(x)).toList();}}'''})
    e=Engine(p,ScenarioState(db));from analyzer.models import wire
    assert wire(e.run(ids['Api.entry'],{}))==[{'id':6,'text':'mapped'},{'id':9,'text':'mapped'}]
    assert (ids['Api.entry'],'calls',ids['Api.convert']) in e.edges


def test_compact_record_constructor_is_not_silently_ignored(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''record Item(String value){Item {if(value==null)throw new IllegalArgumentException();}}
      class Api {Object entry(){return new Item(null);}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='unsupported_semantics boundary'
