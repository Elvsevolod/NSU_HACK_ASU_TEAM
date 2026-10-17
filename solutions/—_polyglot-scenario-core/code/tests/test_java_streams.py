"""Independent callback/effect and lazy-consumption contracts, not app names."""
import pytest

from polygraph.analysis import analyze
from support import fixture,scenario,edge_set


def probe(tmp_path,body,helpers='',classes='',**limits):
    source='''import org.springframework.web.bind.annotation.*;
import java.util.List;import java.util.ArrayList;import java.util.Arrays;
import java.util.stream.Stream;import java.util.stream.Collectors;
import java.util.function.Function;
@RestController class Endpoint {
 private int seen=0;
 @GetMapping("/value") Object value(){'''+body+'}\n'+helpers+'}\n'+classes
    project,store,ids=fixture(tmp_path,{'Endpoint.java':source})
    block,detail=analyze(project,store,{},scenario({'path':'/value'}),**limits)
    return block,detail,ids


def response(detail):return detail['paths'][0]['steps'][0]['response']['body']


def test_creating_a_pipeline_does_not_execute_its_callback(tmp_path):
    block,detail,ids=probe(tmp_path,'Stream<Integer> pending=Arrays.asList(1,2).stream().map(this::tap);return seen;',
        'private int tap(int n){seen++;return n*2;}')
    assert response(detail)==0
    assert ids['Endpoint.tap'] not in {edge[2] for edge in edge_set(block,'executes')}


def test_bound_receiver_factory_is_evaluated_once_before_consumption(tmp_path):
    block,detail,ids=probe(tmp_path,'Stream<Integer> pending=Arrays.asList(1,2).stream().map(target()::tap);return seen;',
        'Endpoint target(){seen++;return this;} int tap(int n){seen++;return n;}')
    assert response(detail)==1
    assert ids['Endpoint.target'] in {edge[2] for edge in edge_set(block,'executes')}
    assert ids['Endpoint.tap'] not in {edge[2] for edge in edge_set(block,'executes')}


def test_null_bound_receiver_throws_when_reference_is_created_even_for_empty_stream(tmp_path):
    block,detail,ids=probe(tmp_path,'Endpoint target=null;Stream<Integer> pending=Stream.empty().map(target::tap);return later();',
        'int tap(int n){return n;} int later(){return 9;}')
    assert detail['paths'][0]['steps'][0]['response']['status']==500
    assert not ({ids['Endpoint.tap'],ids['Endpoint.later']} & {edge[2] for edge in edge_set(block,'executes')})


def test_filter_map_reduce_use_source_static_and_bound_references(tmp_path):
    block,detail,ids=probe(tmp_path,'return Arrays.asList(1,2,3).stream().filter(this::keep).map(Endpoint::twice).reduce(0,Endpoint::sum);',
        'boolean keep(int n){return n>1;} static int twice(int n){return n*2;} static int sum(int left,int right){return left+right;}')
    assert response(detail)==10 and len(detail['paths'])==1
    assert all((ids['Endpoint.value'],'calls',ids['Endpoint.'+name]) in edge_set(block) for name in ['keep','twice','sum'])


def test_escaped_stream_keeps_callback_callsite_owner(tmp_path):
    block,detail,ids=probe(tmp_path,'return pending().collect(Collectors.toList());',
        'Stream<Integer> pending(){return Arrays.asList(1,2).stream().map(this::tap);} int tap(int n){return n*3;}')
    assert response(detail)==[3,6]
    assert (ids['Endpoint.pending'],'calls',ids['Endpoint.tap']) in edge_set(block)
    assert (ids['Endpoint.value'],'calls',ids['Endpoint.tap']) not in edge_set(block)


@pytest.mark.parametrize('terminal,expected', [('findFirst().get()',10),('limit(1).collect(Collectors.toList())',[10]),('limit(0).collect(Collectors.toList())',[])])
def test_short_circuiting_does_not_run_later_throwing_callbacks(tmp_path,terminal,expected):
    block,detail,ids=probe(tmp_path,'return Arrays.asList(1,2).stream().map(this::tap).'+terminal+';',
        'int tap(int n){if(n==2)return later();return n*10;} int later(){throw new IllegalStateException();}')
    assert response(detail)==expected
    assert ids['Endpoint.later'] not in {edge[2] for edge in edge_set(block,'executes')}


def test_constructor_and_unbound_instance_references_are_deferred(tmp_path):
    block,detail,ids=probe(tmp_path,'return Arrays.asList("A","B").stream().map(Item::new).map(Item::title).collect(Collectors.toList());',
        classes='class Item {private String text;Item(String value){text=value;} String title(){return text;}}')
    assert response(detail)==['A','B']
    assert all((ids['Endpoint.value'],'calls',ids[name]) in edge_set(block) for name in ['Item.<init>','Item.title'])


def test_native_unbound_string_reference_uses_native_value_at_invocation(tmp_path):
    _,detail,_=probe(tmp_path,'return Arrays.asList("a","abc").stream().map(String::length).collect(Collectors.toList());')
    assert response(detail)==[1,3]


@pytest.mark.parametrize('reuse', ['pending.collect(Collectors.toList());pending.collect(Collectors.toList());',
                                  'pending.map(this::tap);pending.collect(Collectors.toList());'])
def test_linked_or_consumed_stream_is_not_reused(tmp_path,reuse):
    _,detail,_=probe(tmp_path,'Stream<Integer> pending=Arrays.asList(1).stream();try{'+reuse+'return "wrong";}catch(IllegalStateException e){return "reuse";}',
        'int tap(int n){return n;}')
    assert response(detail)=='reuse'


def test_source_collection_is_bound_late_at_terminal_operation(tmp_path):
    _,detail,_=probe(tmp_path,'List<Integer> rows=new ArrayList();rows.add(1);Stream<Integer> pending=rows.stream().map(this::tap);rows.add(2);return pending.collect(Collectors.toList());',
        'int tap(int n){return n*2;}')
    assert response(detail)==[2,4]


def test_clear_and_restore_same_source_element_is_still_interference(tmp_path):
    block,detail,ids=probe(tmp_path,'rows.add(1);rows.stream().map(this::tap).collect(Collectors.toList());return later();',
        'private List<Integer> rows=new ArrayList();int tap(int n){rows.clear();rows.add(n);return n;} int later(){return 9;}')
    assert all(path['coverage']=='cutoff' for path in detail['paths'])
    assert any('Interference' in note['message'] for path in detail['paths'] for note in path['diagnostics'])
    assert ids['Endpoint.later'] not in {edge[2] for edge in edge_set(block,'executes')}


def test_count_does_not_claim_a_version_dependent_callback_execution(tmp_path):
    block,detail,ids=probe(tmp_path,'return Arrays.asList(1,2).stream().map(this::tap).count();','int tap(int n){seen++;return n;}')
    assert all(path['coverage']=='cutoff' for path in detail['paths'])
    assert ids['Endpoint.tap'] not in {edge[2] for edge in edge_set(block,'executes')}


def test_plain_count_needs_no_callback_or_encounter_order(tmp_path):
    _,detail,_=probe(tmp_path,'return Arrays.asList(1,2).stream().count();')
    assert response(detail)==2


def test_custom_collectors_class_is_executed_as_source(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;import java.util.Arrays;
class Collectors {static String toList(){return "custom";}}
@RestController class Endpoint {@GetMapping("/value") Object value(){return Arrays.asList(1).stream().collect(Collectors.toList());}}'''
    p,store,ids=fixture(tmp_path,{'Endpoint.java':source});block,detail=analyze(p,store,{},scenario({'path':'/value'}))
    assert all(path['coverage']=='cutoff' for path in detail['paths'])
    assert ids['Collectors.toList'] in {edge[2] for edge in edge_set(block,'executes')}


def test_stream_budget_is_a_cutoff_without_a_claim_of_no_more_effects(tmp_path):
    _,detail,_=probe(tmp_path,'return Arrays.asList(1,2,3).stream().map(this::tap).collect(Collectors.toList());','int tap(int n){return n;}',loop_limit=2)
    assert not detail['fully_explored_in_model'] and detail['must']==[]
    assert all(path['coverage']=='cutoff' for path in detail['paths'])


def test_source_hashcode_and_collision_equals_callbacks_are_not_skipped(tmp_path):
    block,detail,ids=probe(tmp_path,'java.util.Set<Item> items=Arrays.asList("FB","Ea","FB").stream().map(this::item).collect(Collectors.toSet());return Arrays.asList(items.size(),hashes,comparisons);',
        'private int hashes=0;private int comparisons=0;Item item(String title){return new Item(title,this);}void hashed(){hashes++;}void compared(){comparisons++;}',
        'class Item {private String title;private Endpoint owner;Item(String title,Endpoint owner){this.title=title;this.owner=owner;}public int hashCode(){owner.hashed();return title.hashCode();}public boolean equals(Object other){owner.compared();return title.equals(((Item)other).title);}}')
    assert response(detail)==[2,3,2]
    assert ids['Item.hashCode'] in {edge[2] for edge in edge_set(block,'executes')}
    assert ids['Item.equals'] in {edge[2] for edge in edge_set(block,'executes')}


def test_unordered_set_stream_does_not_fabricate_callback_order(tmp_path):
    block,detail,ids=probe(tmp_path,'return Arrays.asList("a","b").stream().collect(Collectors.toSet()).stream().map(this::tap).collect(Collectors.toList());',
        'String tap(String text){return text;}')
    assert all(path['coverage']=='cutoff' for path in detail['paths'])
    assert ids['Endpoint.tap'] not in {edge[2] for edge in edge_set(block,'executes')}


def test_singleton_set_can_feed_unbound_reference_without_order_uncertainty(tmp_path):
    _,detail,_=probe(tmp_path,'return Arrays.asList("a","a").stream().collect(Collectors.toSet()).stream().map(String::length).collect(Collectors.toList());')
    assert response(detail)==[1]


@pytest.mark.parametrize('reference',['String::length','java.lang.String::length'])
def test_incompatible_native_unbound_receiver_does_not_call_same_named_method(tmp_path,reference):
    _,detail,_=probe(tmp_path,'try{return Arrays.asList(1).stream().map('+reference+').collect(Collectors.toList());}catch(ClassCastException e){return "cast";}')
    assert response(detail)=='cast'


def test_incompatible_source_receiver_does_not_dispatch_to_an_unrelated_class(tmp_path):
    block,detail,ids=probe(tmp_path,'try{return Arrays.asList(new Other()).stream().map(Item::title).collect(Collectors.toList());}catch(ClassCastException e){return "cast";}',
        classes='class Item {String title(){return "expected";}} class Other {String title(){return "wrong";}}')
    assert response(detail)=='cast'
    assert ids['Other.title'] not in {edge[2] for edge in edge_set(block,'executes')}


def test_fully_qualified_native_type_is_not_a_chain_of_unknown_fields(tmp_path):
    _,detail,_=probe(tmp_path,'return java.util.stream.Stream.of("ab").map(java.lang.String::length).collect(Collectors.toList());')
    assert response(detail)==[2]


def test_imported_source_type_is_resolved_before_static_or_method_reference_dispatch(tmp_path):
    sources={'other/Names.java':'package other; public class Names {public static int value(){return 11;} public static int twice(int n){return n*2;}}',
        'Endpoint.java':'''import org.springframework.web.bind.annotation.*;import other.Names;import java.util.Arrays;import java.util.stream.Collectors;
@RestController class Endpoint {@GetMapping("/value") Object value(){return Arrays.asList(Names.value()).stream().map(Names::twice).collect(Collectors.toList());}}'''}
    p,store,ids=fixture(tmp_path,sources);block,detail=analyze(p,store,{},scenario({'path':'/value'}))
    assert response(detail)==[22]
    assert all(ids[name] in {edge[2] for edge in edge_set(block,'executes')} for name in ['Names.value','Names.twice'])


def test_direct_functional_interface_call_uses_captured_receiver(tmp_path):
    _,detail,_=probe(tmp_path,'Function<Integer,Integer> action=this::tap;return action.apply(3);','int tap(int n){return n*4;}')
    assert response(detail)==12
