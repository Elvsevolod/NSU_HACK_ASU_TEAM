"""Source-declared type arguments survive reads, calls and later mutations."""
import json,re
import pytest
from analyzer.engine import Engine
from analyzer.project import Project,walk,text
from analyzer.java_collections import JavaRecord,JavaMap
from analyzer.native_storage import JavaList
from analyzer.native_arrays import JavaArray
from analyzer.state import ScenarioState,U
from builders import build


SCHEMA='''import java.util.*;class Counter{public int count;}
class Box<T>{public T value;T getValue(){return value;}}
class Child<X> extends Box<X>{}
class Holder<T>{public Box<T> box;Box<T> getBox(){return box;}}'''


def record(typ,**fields):
    return JavaRecord(typ,{'__type__':typ,**fields},wire_fields=fields)


def run(tmp_path,body,parameters='Box<Counter> box',params=None,schema=SCHEMA,extra=''):
    p,db,ids=build(tmp_path,{'Api.java':schema+'class Api{Object entry('+parameters+'){'+body+'}'+extra+'}'})
    e=Engine(p,ScenarioState(db));result=e.run(ids['Api.entry'],params if params is not None else {'box':record('Box',value=record('Counter',count=10))})
    return result,e,p,ids


@pytest.mark.parametrize('expression',['box.value.count+1','box.getValue().count+1'])
def test_declared_generic_field_and_getter_keep_the_numeric_member_type(tmp_path,expression):
    result,e,_,_=run(tmp_path,'return '+expression+';')
    assert result==11 and not e.approximate


def test_chained_parameterized_getters_keep_nested_arguments(tmp_path):
    value=record('Box',value=record('Box',value=record('Counter',count=10)))
    result,e,_,_=run(tmp_path,'return box.getValue().getValue().count+1;','Box<Box<Counter>> box',{'box':value})
    assert result==11 and not e.approximate


def test_parameterized_return_type_keeps_its_owner_argument(tmp_path):
    value=record('Holder',box=record('Box',value=record('Counter',count=10)))
    result,e,_,_=run(tmp_path,'return holder.getBox().getValue().count+1;','Holder<Counter> holder',{'holder':value})
    assert result==11 and not e.approximate


def test_generic_list_result_keeps_a_parameterized_element(tmp_path):
    value=record('Box',value=JavaList([record('Box',value=record('Counter',count=10))]))
    result,e,_,_=run(tmp_path,'return box.getValue().get(0).getValue().count+1;','Box<List<Box<Counter>>> box',{'box':value})
    assert result==11 and not e.approximate


def test_generic_array_result_keeps_its_component_type(tmp_path):
    value=record('Box',value=JavaArray([record('Counter',count=10)],'Counter'))
    result,e,_,_=run(tmp_path,'return box.getValue()[0].count+1;','Box<Counter[]> box',{'box':value})
    assert result==11 and not e.approximate


@pytest.mark.parametrize('expression',['box.value.count+1','box.getValue().count+1'])
def test_inherited_member_is_instantiated_at_its_declaring_owner(tmp_path,expression):
    result,e,_,_=run(tmp_path,'return '+expression+';','Child<Counter> box',{'box':record('Child',value=record('Counter',count=10))})
    assert result==11 and not e.approximate


def test_multiple_inheritance_levels_compose_container_arguments(tmp_path):
    schema=SCHEMA+'''class Middle<U> extends Box<List<U>>{}class Leaf<V> extends Middle<V>{}'''
    result,e,_,_=run(tmp_path,'return box.getValue().get(0).count+1;','Leaf<Counter> box',{'box':record('Leaf',value=JavaList([record('Counter',count=10)]))},schema)
    assert result==11 and not e.approximate


def test_implicit_this_field_uses_the_callers_generic_parameterization(tmp_path):
    schema='''import java.util.*;class Store<K>{public Map<K,String> values;
      void put(K key){values.put(key,"known");}String get(K key){return values.get(key);}}'''
    values=JavaMap({});store=record('Store',values=values)
    result,e,_,_=run(tmp_path,'store.put(1L);return store.get(1L);','Store<Long> store',{'store':store},schema)
    assert result=='known' and not e.approximate


def test_generic_array_parameter_survives_a_source_method_frame(tmp_path):
    schema=SCHEMA+'''class Reader<T extends Counter>{int read(T[] values){return values[0].count+1;}}'''
    result,e,_,_=run(tmp_path,'return reader.read(values);','Reader<Counter> reader,Counter[] values',{'reader':record('Reader'),'values':[record('Counter',count=10)]},schema)
    assert result==11 and not e.approximate


def test_inferred_method_type_argument_comes_from_source_not_python_int_shape(tmp_path):
    result,e,_,_=run(tmp_path,'return identity(value)+1;','Long value',{'value':2147483647},extra='<T>T identity(T value){return value;}')
    assert result==2147483648 and not e.approximate


def test_inference_boxes_a_source_primitive_argument(tmp_path):
    result,e,_,_=run(tmp_path,'return identity(2147483647L)+1;','',{},extra='<T>T identity(T value){return value;}')
    assert result==2147483648 and not e.approximate


def test_explicit_method_type_arguments_are_kept(tmp_path):
    result,e,_,_=run(tmp_path,'return this.<Long>identity(2147483647L)+1;','',{},extra='<T>T identity(T value){return value;}')
    assert result==2147483648 and not e.approximate


@pytest.mark.parametrize('invocation',['box.pick(value)','box.<Long>pick(value)'])
def test_method_binder_shadows_class_binder(tmp_path,invocation):
    schema=SCHEMA+'class Choices<T>{<T>T pick(T value){return value;}}'
    result,e,_,_=run(tmp_path,'return '+invocation+'+1;','Choices<String> box,Long value',{'box':record('Choices'),'value':2147483647},schema)
    assert result==2147483648 and not e.approximate


def test_method_binding_flows_into_its_own_parameter_and_map_key(tmp_path):
    schema=SCHEMA+'''class Choices<K>{<K>String use(K key,Map<K,String> values){
      values.put(key,"known");return values.get(key);}}'''
    result,e,_,_=run(tmp_path,'return box.use(1L,values);','Choices<String> box,Map<Long,String> values',{'box':record('Choices'),'values':JavaMap({})},schema)
    assert result=='known' and not e.approximate


def test_explicit_source_parameterization_is_not_replaced_by_a_runtime_record_name(tmp_path):
    schema=SCHEMA+'class BigCounter{public long count;}'
    result,e,_,_=run(tmp_path,'return box.getValue().count+1;','Box<BigCounter> box',{'box':record('Box',value=record('BigCounter',count=2147483647))},schema)
    assert result==2147483648 and not e.approximate


def test_a_raw_member_with_a_source_bound_uses_its_erasure(tmp_path):
    schema='class Counter{public int count;}class Box<T extends Counter>{public T value;T getValue(){return value;}}'
    result,e,_,_=run(tmp_path,'return box.getValue().count+1;','Box box',None,schema)
    assert result==11 and not e.approximate


def declared_call_type(tmp_path,schema,parameters,expression,name):
    p,db,ids=build(tmp_path,{'Api.java':schema+'class Api{Object entry('+parameters+'){return '+expression+';}}'})
    e=Engine(p,ScenarioState(db));e.method=ids['Api.entry'];e.variable_types=dict(p.parameters(e.method))
    call=next(n for n in walk(p.ast[e.method]) if n.type=='method_invocation' and text(n.child_by_field_name('name'))==name)
    return e.source_type(call),e


def test_unbounded_raw_receiver_does_not_invent_its_payload_type(tmp_path):
    typ,_=declared_call_type(tmp_path,SCHEMA,'Box box','box.getValue()','getValue')
    assert typ=='java.lang.Object'


def test_raw_member_erases_a_parameterized_return_type(tmp_path):
    schema='import java.util.*;class Counter{}class Box<T extends List<Counter>>{T getValue(){return null;}}'
    typ,_=declared_call_type(tmp_path,schema,'Box box','box.getValue()','getValue')
    assert typ=='java.util.List'


def test_conflicting_method_constraints_do_not_select_one_argument_type(tmp_path):
    schema='class Utility{static<T extends Number>T choose(T left,T right){return left;}}'
    typ,e=declared_call_type(tmp_path,schema,'Integer left,Long right','Utility.choose(left,right)','choose')
    assert typ not in ('Integer','java.lang.Integer','Long','java.lang.Long')
    assert not typ or typ=='java.lang.Number'


def test_unresolved_wildcard_is_visible_instead_of_using_runtime_field_width(tmp_path):
    result,e,_,_=run(tmp_path,'return box.getValue().count+1;','Box<? extends Counter> box')
    assert result is U and e.approximate
    assert any('generic' in warning or 'integer width' in warning for warning in e.warnings)


def test_a_source_field_write_uses_the_instantiated_declared_width(tmp_path):
    value=record('Box',value=record('Counter',count=2147483647))
    result,e,_,_=run(tmp_path,'box.getValue().count++;return box.getValue().count;','Box<Counter> box',{'box':value})
    assert result==-2147483648 and value['value']['count']==-2147483648 and not e.approximate


def test_changing_a_parameterization_between_calls_does_not_reuse_a_stale_type(tmp_path):
    schema=SCHEMA+'class BigCounter{public long count;}'
    first=record('Box',value=record('Counter',count=2147483647));second=record('Box',value=record('BigCounter',count=2147483647))
    body='int a=readSmall(first);long b=readBig(second);return a<0&&b>0;'
    extra='int readSmall(Box<Counter> b){return b.getValue().count+1;}long readBig(Box<BigCounter> b){return b.getValue().count+1;}'
    result,e,_,_=run(tmp_path,body,'Box<Counter> first,Box<BigCounter> second',{'first':first,'second':second},schema,extra)
    assert result is True and not e.approximate


def test_inferred_parameterized_method_result_retains_argument_structure(tmp_path):
    extra='<T>Box<T> same(Box<T> value){return value;}'
    result,e,_,_=run(tmp_path,'return same(box).getValue().count+1;',extra=extra)
    assert result==11 and not e.approximate


def test_inferred_method_array_result_preserves_reference_component(tmp_path):
    extra='<T>T[] same(T[] values){return values;}'
    result,e,_,_=run(tmp_path,'return same(values)[0].count+1;','Counter[] values',{'values':JavaArray([record('Counter',count=10)],'Counter')},extra=extra)
    assert result==11 and not e.approximate


def test_generic_argument_keeps_use_site_namespace_across_a_getter(tmp_path):
    sources={
      'schemas/Box.java':'package schemas;public class Box<T>{public T value;public T getValue(){return value;}}',
      'schemas/Map.java':'package schemas;public class Map{}',
      'client/Counter.java':'package client;public class Counter{public long count;}',
      'client/Api.java':'''package client;import java.util.Map;import schemas.Box;
        public class Api{long entry(Box<Map<String,Counter>> box){return box.getValue().get("a").count+1;}}'''}
    p,db,ids=build(tmp_path,sources)
    skeleton=p.skeleton
    for node in skeleton['nodes'].values():
        if node['kind']=='type':
            package=re.search(r'\bpackage\s+([\w.]+)\s*;',sources[node['file']])[1]
            node['fqn']=package+'.'+node['fqn']
    (tmp_path/'skeleton.json').write_text(json.dumps(skeleton));p=Project(tmp_path/'skeleton.json',tmp_path)
    e=Engine(p,ScenarioState(db));value=record('schemas.Box',value=JavaMap({'a':record('client.Counter',count=2147483647)}))
    assert e.run(ids['Api.entry'],{'box':value})==2147483648 and not e.approximate


def test_a_deferred_callback_keeps_generic_bindings_after_its_method_returns(tmp_path):
    schema='''import java.util.*;import java.util.stream.*;class Store<K>{Map<K,String> values;
      Stream<String> plan(List<K> keys){return keys.stream().map(key->{values.put(key,"known");return values.get(key);});}}'''
    result,e,_,_=run(tmp_path,'return store.plan(keys).collect(Collectors.toList()).get(0);',
      'Store<Long> store,List<Long> keys',{'store':record('Store',values=JavaMap({})),'keys':[1]},schema)
    assert result=='known' and not e.approximate


def test_a_raw_call_keeps_generic_declaration_bounds_inside_the_body(tmp_path):
    schema='''import java.util.*;class Counter{int count;}
      class Reader<T extends List<Counter>>{T value;int read(){return value.get(0).count+1;}}'''
    result,e,_,_=run(tmp_path,'return reader.read();','Reader reader',{'reader':record('Reader',value=JavaList([record('Counter',count=10)]))},schema)
    assert result==11 and not e.approximate


def test_a_root_generic_entry_uses_its_source_bound_for_a_member_read(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'class Counter{int count;}class Api{<T extends Counter>int entry(T input){return input.count+1;}}'})
    e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{'input':record('Counter',count=10)})==11 and not e.approximate


def test_a_null_generic_boolean_bound_fails_before_following_source(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{int entry(){return check(null);}
      <T extends Boolean>int check(T input){if(input){return after();}return 0;}int after(){return 1;}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='uncaught application exception' and not e.approximate
    assert not any(target==ids['Api.after'] for _,kind,target in e.edges if kind=='executes')


def test_local_var_infers_from_a_generic_result_without_runtime_value_guessing(tmp_path):
    result,e,_,_=run(tmp_path,'var selected=identity(value);return selected+1;',
      'Long value',{'value':2147483647},extra='<T>T identity(T value){return value;}')
    assert result==2147483648 and not e.approximate


@pytest.mark.parametrize('declaration,values',[
    ('List<Counter> values',[record('Counter',count=10)]),
    ('Counter[] values',[record('Counter',count=10)])])
def test_enhanced_for_var_keeps_its_declared_element_type(tmp_path,declaration,values):
    result,e,_,_=run(tmp_path,'int total=0;for(var value:values){total+=value.count;}return total;',declaration,{'values':values})
    assert result==10 and not e.approximate


def test_unknown_var_initializer_type_remains_diagnosed(tmp_path):
    result,e,_,_=run(tmp_path,'var value=external.read();return value;','External external',{'external':record('External')})
    assert result is U and e.approximate
    assert any('local var initializer' in warning for warning in e.warnings)


def test_parameterized_creation_keeps_the_enclosing_method_binding(tmp_path):
    schema='''class Counter{int count;}class Box<T>{T value;Box(T value){this.value=value;}T getValue(){return value;}}'''
    extra='<T extends Counter>int read(T input){return new Box<T>(input).getValue().count+1;}'
    result,e,_,_=run(tmp_path,'return read(input);','Counter input',{'input':record('Counter',count=10)},schema,extra)
    assert result==11 and not e.approximate


def test_unchecked_type_variable_cast_does_not_confirm_a_false_payload_type(tmp_path):
    schema=SCHEMA+'class Wrong{public int count=5;}'
    extra='<T>T pretend(Object value){return (T)value;}'
    result,e,_,_=run(tmp_path,'return this.<Counter>pretend(new Wrong()).count+1;','',{},schema,extra)
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate
    assert any('ClassCastException' in warning for warning in e.warnings)


def test_unchecked_parameterized_cast_checks_its_erasure_and_later_nested_read(tmp_path):
    value=record('Box',value=record('Counter',count=10))
    result,e,_,_=run(tmp_path,'Box<Counter> selected=(Box<Counter>)input;return selected.getValue().count+1;','Object input',{'input':value})
    assert result==11 and not e.approximate


def test_cast_of_a_source_proven_parameterization_preserves_known_data(tmp_path):
    result,e,_,_=run(tmp_path,'Box<Counter> selected=(Box<Counter>)box;return selected.getValue().count+1;')
    assert result==11 and not e.approximate


def test_generic_null_cast_remains_a_known_null_reference(tmp_path):
    result,e,_,_=run(tmp_path,'return this.<Counter>pretend(null);','',{},extra='<T>T pretend(Object value){return (T)value;}')
    assert result is None and not e.approximate


@pytest.mark.parametrize('expression',['(Long)(Object)1','(String)(Object)\'x\''])
def test_known_incompatible_boxing_cast_stops_following_source_calls(tmp_path,expression):
    result,e,_,ids=run(tmp_path,'var value='+expression+';after();return value;','',{},extra='void after(){}')
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate
    assert not any(target==ids['Api.after'] for _,kind,target in e.edges if kind=='executes')


def test_matching_source_box_kind_survives_object_widening(tmp_path):
    result,e,_,_=run(tmp_path,'var value=(Long)(Object)1L;return value+1;','',{})
    assert result==2 and not e.approximate


def test_unknown_object_kind_is_not_guessed_from_a_python_integer(tmp_path):
    result,e,_,_=run(tmp_path,'return (Long)input;','Object input',{'input':1})
    assert result is U and e.approximate
    assert e.operation_issues[('unresolved_native_cast','cast')]


def test_a_raw_map_character_is_not_cast_to_string(tmp_path):
    result,e,_,ids=run(tmp_path,'Map values=new HashMap();values.put("k",\'x\');String value=(String)values.get("k");after();return value;','',{},extra='void after(){}')
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate
    assert not any(target==ids['Api.after'] for _,kind,target in e.edges if kind=='executes')


def test_return_kind_is_preserved_when_finally_evaluates_a_different_kind(tmp_path):
    extra='Object selected(){try{return 1L;}finally{Map other=new HashMap();other.put("x",\'a\');other.get("x");}}'
    result,e,_,_=run(tmp_path,'var value=(Long)selected();return value+1;','',{},extra=extra)
    assert result==2 and not e.approximate


def test_a_source_method_return_does_not_reevaluate_the_receiver(tmp_path):
    extra='Object selected(Counter c){c.count=c.count+1;return 1L;}'
    result,e,_,_=run(tmp_path,'Long value=(Long)selected(counter);return counter.count;','Counter counter',{'counter':record('Counter',count=0)},extra=extra)
    assert result==1 and not e.approximate


def test_native_map_heap_pollution_has_a_visible_implicit_cast_boundary(tmp_path):
    body='Map<String,Long> values=new HashMap();Map raw=values;raw.put("k",1);Long value=values.get("k");after();return value;'
    result,e,_,ids=run(tmp_path,body,'',{},extra='void after(){}')
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate
    assert any('ClassCastException' in warning for warning in e.warnings)
    assert not any(target==ids['Api.after'] for _,kind,target in e.edges if kind=='executes')


def test_a_generic_record_cast_uses_the_source_schema_instead_of_a_marker_field(tmp_path):
    extra='<T>T selected(Object value){return (T)value;}'
    result,e,_,_=run(tmp_path,'return this.<Counter>selected(input).count+1;','Object input',{'input':record('Counter',count=10)},extra=extra)
    assert result==11 and not e.approximate


def test_a_marker_shaped_java_map_does_not_prove_a_generic_record_type(tmp_path):
    extra='<T>T selected(Object value){return (T)value;}'
    result,e,_,_=run(tmp_path,'return this.<Counter>selected(input).count+1;','Object input',{'input':JavaMap({'__type__':'Counter','count':10})},extra=extra)
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate
    assert any('ClassCastException' in warning for warning in e.warnings)


def test_widened_implicit_map_read_is_not_claimed_to_be_a_guaranteed_throw(tmp_path):
    body='Map<String,Long> values=new HashMap();Map raw=values;raw.put("k",1);Object value=values.get("k");after();return value;'
    result,e,_,ids=run(tmp_path,body,'',{},extra='void after(){}')
    assert result==1 and not e.approximate and e.outcome=='returned' and e.last_invoke_kind=='Integer'
    assert any(target==ids['Api.after'] for _,kind,target in e.edges if kind=='executes')


@pytest.mark.parametrize('write',['raw.value=new Wrong();','raw.setValue(new Wrong());'])
def test_raw_generic_alias_cannot_confirm_a_wrong_projected_payload(tmp_path,write):
    schema=SCHEMA.replace('T getValue(){return value;}','T getValue(){return value;}void setValue(T input){value=input;}')+'class Wrong{int count=5;}'
    body='Box<Counter> box=new Box<Counter>();Box raw=box;'+write+'return box.getValue().count+1;'
    result,e,_,_=run(tmp_path,body,'',{},schema)
    assert result is U and e.outcome=='uncaught application exception'
    assert any('ClassCastException' in warning for warning in e.warnings)


def test_raw_to_parameterized_binding_preserves_values_until_a_narrow_consumer(tmp_path):
    schema=SCHEMA.replace('T getValue(){return value;}','Box(T input){value=input;}T getValue(){return value;}')
    body='Box<Object> first=new Box<Object>(1);Box raw=first;Box<String> selected=raw;return selected.getValue();'
    result,e,_,_=run(tmp_path,body,'',{},schema)
    assert result==1 and not e.approximate and e.last_invoke_kind=='Integer'


def test_a_known_compatible_record_survives_a_raw_generic_write(tmp_path):
    body='Box<Counter> box=new Box<Counter>();Box raw=box;raw.value=input;return box.getValue().count+1;'
    result,e,_,_=run(tmp_path,body,'Counter input',{'input':record('Counter',count=10)})
    assert result==11 and not e.approximate


def test_nested_parameterization_is_not_proved_by_the_record_base_name(tmp_path):
    schema=SCHEMA+'class Wrong{int count=5;}'
    body='Box<Box<Counter>> box=new Box<Box<Counter>>();Box<Wrong> inner=new Box<Wrong>();inner.value=new Wrong();Box raw=box;raw.value=inner;return box.getValue().getValue().count+1;'
    result,e,_,_=run(tmp_path,body,'',{},schema)
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate
    assert any('ClassCastException' in warning for warning in e.warnings)


def test_hidden_field_read_is_diagnosed_instead_of_using_the_child_slot(tmp_path):
    schema='class Parent{int count=1;}class Child extends Parent{int count=5;}'
    result,e,_,_=run(tmp_path,'Parent parent=new Child();return parent.count;','',{},schema)
    assert result is U and e.approximate
    assert any('hidden Java fields' in warning for warning in e.warnings)


def test_raw_generic_json_keeps_payload_but_does_not_prove_a_projected_record(tmp_path):
    from analyzer.http_json import decode_response
    from analyzer.java_collections import JsonObject
    p,db,ids=build(tmp_path,{'Api.java':SCHEMA+'class Api{int entry(Box input){Box<Counter> selected=input;return selected.getValue().count+1;}}'})
    e=Engine(p,ScenarioState(db));e.method=ids['Api.entry']
    value=decode_response(p,JsonObject({'value':JsonObject({'count':10})}),'Box',p.methods[e.method],e.standard_type,lambda reason:e.warnings.add(reason))
    assert isinstance(value['value'],JavaMap) and value['value'].mapping['count']==10
    assert e.run(e.method,{'input':value}) is U and e.outcome=='uncaught application exception' and not e.approximate
    assert any('ClassCastException' in warning for warning in e.warnings)
    assert value['value'].mapping['count']==10
    from analyzer.models import wire
    other=Engine(p,ScenarioState(db));other.method=ids['Api.entry']
    rebound=decode_response(p,wire(value),'Box<Counter>',p.methods[other.method],other.standard_type,lambda reason:other.warnings.add(reason))
    assert other.run(other.method,{'input':rebound})==11 and not other.approximate


def test_typed_generic_json_records_its_actual_native_box_kind(tmp_path):
    from analyzer.http_json import decode_response
    from analyzer.java_collections import JsonObject
    p,db,ids=build(tmp_path,{'Api.java':SCHEMA+'class Api{long entry(Box<Long> input){return (Long)(Object)input.getValue();}}'})
    e=Engine(p,ScenarioState(db));e.method=ids['Api.entry']
    value=decode_response(p,JsonObject({'value':1}),'Box<Long>',p.methods[e.method],e.standard_type,lambda reason:e.warnings.add(reason))
    assert e.run(e.method,{'input':value})==1 and not e.approximate


def test_a_branch_join_preserves_raw_generic_alias_evidence(tmp_path):
    schema=SCHEMA+'class Wrong{int count=5;}'
    box=record('Box',value=record('Counter',count=10))
    body='if(flag){Box raw=box;raw.value=new Wrong();}return box.getValue().count+1;'
    p,db,ids=build(tmp_path,{'Api.java':schema+'class Api{int entry(Box<Counter> box,boolean flag){'+body+'}}'})
    e=Engine(p,ScenarioState(db),conservative=True);result=e.run(ids['Api.entry'],{'box':box,'flag':U})
    assert result is U and e.approximate
    assert 'value' in box._unchecked_generic_fields


@pytest.mark.parametrize('write',['raw.value=new Wrong();','raw.setValue(new Wrong());'])
def test_generated_accessor_projection_uses_the_same_generic_heap_guard(tmp_path,write):
    schema='import lombok.Data;@Data class Box<T>{T value;}class Counter{int count;}class Wrong{int count=5;}'
    body='Box<Counter> box=new Box<Counter>();Box raw=box;'+write+'return box.getValue().count+1;'
    result,e,_,_=run(tmp_path,body,'',{},schema)
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate
    assert any('ClassCastException' in warning for warning in e.warnings)


def test_generated_accessor_keeps_source_proven_generic_data(tmp_path):
    schema='import lombok.Data;@Data class Box<T>{T value;}class Counter{int count;}'
    result,e,_,_=run(tmp_path,'Box<Counter> box=new Box<Counter>();box.setValue(input);return box.getValue().count+1;',
                    'Counter input',{'input':record('Counter',count=10)},schema)
    assert result==11 and not e.approximate


@pytest.mark.parametrize('target',['Long','java.lang.Long'])
def test_a_boxed_reference_cast_retains_its_source_numeric_width(tmp_path,target):
    result,e,_,_=run(tmp_path,'return ('+target+')(Object)2147483647L+1;','',{})
    assert result==2147483648 and not e.approximate


def test_a_type_variable_cast_retains_the_instantiated_numeric_width(tmp_path):
    extra='<T extends Long>long read(T input){return ((T)input)+1;}'
    result,e,_,_=run(tmp_path,'return read(2147483647L);','',{},extra=extra)
    assert result==2147483648 and not e.approximate


@pytest.mark.parametrize('primitive,boxed',[('byte','Byte'),('short','Short'),('int','Integer'),('long','Long')])
def test_boxing_after_a_primitive_method_return_uses_its_declared_conversion(tmp_path,primitive,boxed):
    result,e,_,_=run(tmp_path,'return ('+boxed+')(Object)selected();','',{},extra=primitive+' selected(){return 1;}')
    assert result==1 and not e.approximate and e.outcome=='returned'


def test_a_primitive_return_conversion_cannot_inherit_the_expressions_box_kind(tmp_path):
    result,e,_,ids=run(tmp_path,'Integer value=(Integer)(Object)selected();after();return value;','',{},
                     extra='long selected(){return 1;}void after(){}')
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate
    assert not any(target==ids['Api.after'] for _,kind,target in e.edges if kind=='executes')
