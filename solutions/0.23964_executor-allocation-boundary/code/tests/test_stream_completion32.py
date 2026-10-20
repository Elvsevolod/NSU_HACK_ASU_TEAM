import pytest
from analyzer.engine import Engine
from analyzer.native_storage import JavaList
from analyzer.state import ScenarioState,U
from analyzer.paths import run_paths
from builders import build


def model(tmp_path,body,extra=''):
    return build(tmp_path,{'Api.java':'''import java.util.*;import java.util.stream.*;
      class Api{List<Integer> seen;Object entry(){seen=new ArrayList<>();'''+body+'''}
      void accept(Integer value){seen.add(value);}int after(){return 99;}'''+extra+'}'})


@pytest.mark.parametrize('terminal',['forEach','forEachOrdered'])
@pytest.mark.parametrize('callback',['x->{if(x==2)return;seen.add(x);}','this::accept'])
def test_consumer_void_return_capture_and_method_reference(tmp_path,terminal,callback):
    p,db,ids=model(tmp_path,'Arrays.asList(1,2,3).stream().'+terminal+'('+callback+');return seen;')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==([1,3] if 'return;' in callback else [1,2,3])
    assert not e.approximate


def test_null_consumer_on_empty_stream_throws_before_suffix(tmp_path):
    p,db,ids=model(tmp_path,'new ArrayList<Integer>().stream().forEach(null);return after();')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='uncaught application exception' and ('','executes',ids['Api.after']) not in e.edges


def test_throw_after_first_callback_effect_keeps_prefix_and_catch(tmp_path):
    p,db,ids=model(tmp_path,'''try{Arrays.asList(1,2,3).stream().forEach(x->{seen.add(x);
      if(x==2)throw new IllegalStateException();});return after();}catch(IllegalStateException ex){return seen;}''')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==[1,2]
    assert ('','executes',ids['Api.after']) not in e.edges


def test_reuse_linked_alias_catch_and_independent_stream(tmp_path):
    p,db,ids=model(tmp_path,'''Stream<Integer> first=Arrays.asList(1).stream();Stream<Integer> alias=first;
      Stream<Integer> linked=first.filter(x->true);try{alias.toList();return after();}
      catch(IllegalStateException ex){linked.forEach(this::accept);Arrays.asList(2).stream().forEach(this::accept);return seen;}''')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==[1,2]
    assert ('','executes',ids['Api.after']) not in e.edges


def test_lifecycle_observer_is_not_a_terminal_reuse(tmp_path):
    p,db,ids=model(tmp_path,'Stream<Integer> stream=Arrays.asList(1).stream();stream.toList();return stream.isParallel();')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is False


def test_unimplemented_callback_operation_stops_the_continuation(tmp_path):
    p,db,ids=model(tmp_path,'Arrays.asList(1).stream().peek(x->seen.add(x));return after();')
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='unsupported_semantics boundary' and ('','executes',ids['Api.after']) not in e.edges


def test_unknown_empty_backing_does_not_skip_consumer(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{
      Object entry(List<Integer> source){source.stream().forEach(x->after());return after();}int after(){return 99;}}'''})
    source=JavaList();source.opaque=True;e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{'source':source}) is U and e.outcome=='unsupported_semantics boundary'
    assert ('','executes',ids['Api.after']) not in e.edges


@pytest.mark.parametrize('expression,expected',[
    ('Optional.empty().isEmpty()',True),('Optional.of("x").map(x->x).isEmpty()',False),
    ('Optional.of("x").map(x->null).isEmpty()',True)])
def test_optional_empty_observer_uses_presence(tmp_path,expression,expected):
    p,db,ids=model(tmp_path,'return '+expression+';');e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{}) is expected and not e.approximate


def test_source_is_empty_keeps_its_own_body(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'class Bucket{boolean isEmpty(){return false;}}class Api{boolean entry(){return new Bucket().isEmpty();}}'})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is False
    assert ('','executes',ids['Bucket.isEmpty']) in e.edges


@pytest.mark.parametrize('enabled', [False, True])
def test_unknown_filter_with_alias_write_retains_stream_boundary_before_callback(tmp_path, enabled):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import jakarta.persistence.*;
      import org.springframework.beans.factory.annotation.Autowired;
      import org.springframework.data.jpa.repository.JpaRepository;
      class Api{@Autowired Store store;Object entry(List<String> input){
        input.stream().filter(id->{Item row=store.findById(id).get();Item alias=row;
          alias.status="held";store.save(alias);return true;}).toList();return after();}
        int after(){return 99;}}
      @Entity @Table(name="items")class Item{@Id public String id;public String status;}
      interface Store extends JpaRepository<Item,String>{Optional<Item> findById(String id);Item save(Item item);}'''},
      rows={'items':[{'id':'A','status':'free'}]})
    values=JavaList();values.opaque=True;e=Engine(p,ScenarioState(db,{'scoped_effect_summary':enabled}))
    assert e.run(ids['Api.entry'],{'input':values}) is U
    assert e.outcome=='unsupported_semantics boundary'
    assert ('','executes',ids['Api.after']) not in e.edges
    assert not e.data_operations
    assert not any(x.get('model_version') in ('readonly-native-foreach-stop/1','opaque-java-call/1') for x in e.effect_events)
    assert e.state.database.rows(p.nodes['res:table:service.items']) is None
