"""Box identity follows values; source generic types do not rewrite the heap."""
import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from builders import build


def program(tmp_path,body,extra='',parameters='',schema=''):
    return build(tmp_path,{'Api.java':'import java.util.*;import java.util.stream.*;'+schema+
      'class Api{Object entry('+parameters+'){'+body+'}void after(){}'+extra+'}'})


def run(tmp_path,body,extra='',parameters='',params=None,schema='',conservative=False):
    p,db,ids=program(tmp_path,body,extra,parameters,schema)
    e=Engine(p,ScenarioState(db),conservative=conservative)
    return e.run(ids['Api.entry'],params or {}),e,ids


def after(e,ids):return any(kind=='executes' and target==ids['Api.after'] for _,kind,target in e.edges)


@pytest.mark.parametrize('literal,boxed,expected',[('1L','Long',1),('1','Integer',1),("'x'",'Character','x'),('"x"','String','x'),('true','Boolean',True)])
def test_object_local_keeps_its_observed_box_class(tmp_path,literal,boxed,expected):
    result,e,_=run(tmp_path,'Object value='+literal+';return ('+boxed+')value;')
    assert result==expected and not e.approximate


@pytest.mark.parametrize('first,last,boxed',[('1L','1','Long'),('1','1L','Integer'),('"x"',"'x'",'String')])
def test_reassignment_replaces_stale_box_provenance(tmp_path,first,last,boxed):
    result,e,ids=run(tmp_path,'Object value='+first+';value='+last+';var checked=('+boxed+')value;after();return checked;')
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


def test_object_argument_and_return_keep_box_provenance(tmp_path):
    result,e,_=run(tmp_path,'Object value=echo(1L);return (Long)value;','Object echo(Object value){return value;}')
    assert result==1 and not e.approximate


def test_a_primitive_formal_conversion_determines_boxing_inside_the_method(tmp_path):
    result,e,_=run(tmp_path,'Object value=echo(1);return (Long)value;','Object echo(long value){return value;}')
    assert result==1 and not e.approximate


def test_constructor_and_object_field_do_not_lose_native_kind(tmp_path):
    schema='class Holder{Object value;Holder(Object input){value=input;}Object getValue(){return value;}}'
    result,e,_=run(tmp_path,'Holder holder=new Holder(1L);Object value=holder.getValue();return (Long)value;',schema=schema)
    assert result==1 and not e.approximate


def test_object_widening_does_not_invent_box_provenance_for_untyped_input(tmp_path):
    result,e,_=run(tmp_path,'Object value=input;return (Long)value;',parameters='Object input',params={'input':1})
    assert result is U and e.approximate and any('runtime kind' in warning for warning in e.warnings)


def test_raw_list_pollution_fails_at_a_typed_assignment_before_after(tmp_path):
    body='List<Long> values=new ArrayList<Long>();List raw=values;raw.add(1);Long value=values.get(0);after();return value;'
    result,e,ids=run(tmp_path,body)
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


def test_widening_list_read_preserves_actual_box_instead_of_forcing_generic_type(tmp_path):
    body='List<Long> values=new ArrayList<Long>();List raw=values;raw.add(1);Object value=values.get(0);after();return (Integer)value;'
    result,e,ids=run(tmp_path,body)
    assert result==1 and e.outcome=='returned' and not e.approximate and after(e,ids)


def test_list_read_into_a_widening_return_preserves_actual_box(tmp_path):
    body='List<Long> values=new ArrayList<Long>();List raw=values;raw.add(1);Object value=read(values);return (Integer)value;'
    result,e,_=run(tmp_path,body,'Object read(List<Long> values){return values.get(0);}')
    assert result==1 and not e.approximate


def test_list_read_into_a_typed_return_fails_before_callers_continuation(tmp_path):
    body='List<Long> values=new ArrayList<Long>();List raw=values;raw.add(1);Object value=read(values);after();return value;'
    result,e,ids=run(tmp_path,body,'Long read(List<Long> values){return values.get(0);}')
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


@pytest.mark.parametrize('formal,should_fail',[('Object',False),('Long',True)])
def test_list_read_cast_depends_on_the_consuming_formal_parameter(tmp_path,formal,should_fail):
    body='List<Long> values=new ArrayList<Long>();List raw=values;raw.add(1);Object value=take(values.get(0));after();return value;'
    result,e,ids=run(tmp_path,body,'Object take('+formal+' value){return value;}')
    if should_fail:assert result is U and e.outcome=='uncaught application exception' and not after(e,ids)
    else:assert result==1 and e.outcome=='returned' and after(e,ids)
    assert not e.approximate


def test_numeric_consumption_of_polluted_list_read_requires_the_long_box(tmp_path):
    body='List<Long> values=new ArrayList<Long>();List raw=values;raw.add(1);long value=values.get(0)+1;after();return value;'
    result,e,ids=run(tmp_path,body)
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


def test_a_known_compatible_list_element_survives_an_object_alias(tmp_path):
    body='List<Long> values=new ArrayList<Long>();List raw=values;raw.add(1L);Object value=values.get(0);return (Long)value;'
    result,e,_=run(tmp_path,body)
    assert result==1 and not e.approximate


def test_list_copy_preserves_boxes_but_owns_its_storage(tmp_path):
    body='List first=new ArrayList();first.add(1L);List second=new ArrayList(first);first.add(2);Object value=second.get(0);return (Long)value;'
    result,e,_=run(tmp_path,body)
    assert result==1 and not e.approximate


def test_raw_character_in_a_list_cannot_be_cast_to_string(tmp_path):
    result,e,ids=run(tmp_path,'List values=new ArrayList();values.add(\'x\');String value=(String)values.get(0);after();return value;')
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


def test_null_list_element_remains_a_valid_reference_cast(tmp_path):
    result,e,_=run(tmp_path,'List<Long> values=new ArrayList<Long>();values.add(null);Long value=values.get(0);return value;')
    assert result is None and not e.approximate


def test_object_local_scope_restores_the_outer_kind(tmp_path):
    result,e,_=run(tmp_path,'Object value=1L;{Object other=1;value=2L;}return (Long)value;')
    assert result==2 and not e.approximate


def test_agreed_branch_box_provenance_survives_frame_join(tmp_path):
    result,e,_=run(tmp_path,'Object value=null;if(flag){value=1L;}else{value=1L;}return (Long)value;',
                   parameters='boolean flag',params={'flag':U},conservative=True)
    assert result==1
    assert not any('runtime kind' in warning for warning in e.warnings)


def test_equal_payloads_with_different_boxes_do_not_merge_to_a_known_long(tmp_path):
    result,e,_=run(tmp_path,'Object value=null;if(flag){value=1L;}else{value=1;}return (Long)value;',
                   parameters='boolean flag',params={'flag':U},conservative=True)
    assert result is U and e.approximate and any('runtime kind' in warning for warning in e.warnings)


def test_list_branch_boxes_stay_distinct_in_explored_paths(tmp_path):
    body='List<Long> values=new ArrayList<Long>();List raw=values;if(flag){raw.add(1L);}else{raw.add(1);}Long value=values.get(0);after();return value;'
    p,db,ids=program(tmp_path,body,parameters='boolean flag')
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{'flag':U},limit=8)
    assert len(paths)==2 and {x['engine'].outcome for x in paths}=={'returned','uncaught application exception'}
    assert sum(after(x['engine'],ids) for x in paths)==1


def test_conservative_list_join_does_not_pick_a_box_from_equal_payloads(tmp_path):
    body='List<Long> values=new ArrayList<Long>();List raw=values;if(flag){raw.add(1L);}else{raw.add(1);}Long value=values.get(0);return value;'
    result,e,_=run(tmp_path,body,parameters='boolean flag',params={'flag':U},conservative=True)
    assert result is U and e.approximate and e.warnings


@pytest.mark.parametrize('declaration,should_fail',[('Long',True),('var',True),('Object',False)])
def test_enhanced_for_casts_use_the_iteration_variable_context(tmp_path,declaration,should_fail):
    body='List<Long> values=new ArrayList<Long>();List raw=values;raw.add(1);for('+declaration+' value:values){after();}return 1;'
    result,e,ids=run(tmp_path,body)
    assert not e.approximate
    if should_fail:assert result is U and e.outcome=='uncaught application exception' and not after(e,ids)
    else:assert result==1 and after(e,ids)


def test_deferred_lambda_captures_object_box_provenance(tmp_path):
    body='Object value=1L;List<Long> result=Arrays.asList(1).stream().map(x->(Long)value).collect(Collectors.toList());return result.get(0);'
    result,e,_=run(tmp_path,body)
    assert result==1 and not e.approximate


def test_stream_parameter_cast_runs_even_when_lambda_ignores_its_argument(tmp_path):
    body='List<Long> values=new ArrayList<Long>();List raw=values;raw.add(1);values.stream().map(x->{after();return 1;}).collect(Collectors.toList());return 1;'
    result,e,ids=run(tmp_path,body)
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


def test_stream_mapping_preserves_the_actual_result_box(tmp_path):
    body='List<Object> values=Arrays.asList(1).stream().map(x->{Object result=1L;return result;}).collect(Collectors.toList());return (Long)values.get(0);'
    result,e,_=run(tmp_path,body)
    assert result==1 and not e.approximate


def test_lambda_return_uses_its_own_reference_context(tmp_path):
    body='List<Object> values=Arrays.asList(1).stream().map(x->{return null;}).collect(Collectors.toList());return values.get(0)==null;'
    p,db,ids=build(tmp_path,{'Api.java':'import java.util.*;import java.util.stream.*;class Api{boolean entry(){'+body+'}}'})
    e=Engine(p,ScenarioState(db))
    assert e.run(ids['Api.entry'],{}) is True and not e.approximate


def test_enhanced_for_unboxes_before_primitive_widening(tmp_path):
    result,e,_=run(tmp_path,'List<Integer> values=Arrays.asList(1);for(long value:values){return (Long)(Object)value;}return null;')
    assert result==1 and not e.approximate


@pytest.mark.parametrize('literal,boxed,expected',[("'x'",'Character','x'),('1L','Long',1),('-1L','Long',-1),('-2147483648','Integer',-2147483648)])
def test_source_object_field_initializer_retains_its_literal_class(tmp_path,literal,boxed,expected):
    result,e,_=run(tmp_path,'Holder holder=new Holder();return ('+boxed+')holder.value;',schema='class Holder{Object value='+literal+';}')
    assert result==expected and not e.approximate


def test_json_typed_list_supplies_element_classes(tmp_path):
    from analyzer.http_json import decode_response
    p,db,ids=program(tmp_path,'Object value=values.get(0);return (Long)value;',parameters='List<Long> values')
    e=Engine(p,ScenarioState(db));e.method=ids['Api.entry'];warnings=[]
    values=decode_response(p,[1],'List<Long>',p.methods[e.method],e.standard_type,warnings.append)
    assert e.run(ids['Api.entry'],{'values':values})==1 and not e.approximate and not warnings


def test_untyped_json_number_does_not_invent_a_long_box(tmp_path):
    from analyzer.java_collections import raw_json_map
    result,e,_=run(tmp_path,'Object value=values.get(0);return (Long)value;',parameters='List values',params={'values':raw_json_map([1])})
    assert result is U and e.approximate and any('runtime kind' in w for w in e.warnings)


def test_erased_parameterized_cast_checks_the_record_class_then_later_consumers(tmp_path):
    schema='class Box<T>{T value;Box(T input){value=input;}T getValue(){return value;}}'
    result,e,ids=run(tmp_path,'Object input=new Box<Integer>(1);Box<Long> selected=(Box<Long>)input;Long value=selected.getValue();after();return value;',schema=schema)
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


def test_widened_parameterized_cast_does_not_check_erased_type_arguments(tmp_path):
    schema='class Box<T>{T value;Box(T input){value=input;}T getValue(){return value;}}'
    result,e,_=run(tmp_path,'Object input=new Box<Integer>(1);Box<Long> selected=(Box<Long>)input;Object value=selected.getValue();return (Integer)value;',schema=schema)
    assert result==1 and not e.approximate


@pytest.mark.parametrize('expression',['(double)0.1f','(float)0.1'])
def test_unmodeled_float_conversion_is_diagnosed(tmp_path,expression):
    result,e,_=run(tmp_path,'return '+expression+';')
    assert result is U and e.approximate and any('float' in w for w in e.warnings)


def test_native_constant_names_cannot_override_an_instance_field(tmp_path):
    result,e,_=run(tmp_path,'Holder Long=new Holder();return Long.MAX_VALUE;',schema='class Holder{int MAX_VALUE=7;}')
    assert result==7 and not e.approximate


def test_a_generic_return_can_carry_an_array_without_becoming_a_list(tmp_path):
    from analyzer.native_arrays import JavaArray
    result,e,_=run(tmp_path,'Object value=echo(values);return ((Long[])value)[0];',
                   extra='<T>T echo(T value){return value;}',parameters='Long[] values',params={'values':JavaArray([1],'java.lang.Long',['Long'])})
    assert result==1 and not e.approximate


def test_array_and_list_evidence_survives_alias_preserving_branch_copy():
    from analyzer.native_arrays import JavaArray
    from analyzer.native_storage import JavaList
    from analyzer.heap_join import clone_environment
    array=JavaArray([1],'java.lang.Long',['Long']);values=JavaList([array])
    (first,second),_=clone_environment((array,values))
    assert first is second[0] and type(first) is JavaArray and first.component=='java.lang.Long' and first.kinds==['Long']


@pytest.mark.parametrize('component,target',[('java.lang.Long','Integer[]'),('long','Object[]')])
def test_known_array_component_cast_failure_stops_continuation(tmp_path,component,target):
    from analyzer.native_arrays import JavaArray
    result,e,ids=run(tmp_path,'Object value=values;Object checked=('+target+')value;after();return checked;',parameters=component+'[] values',
                     params={'values':JavaArray([1],component,['Long'])})
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


def test_reference_array_covariance_preserves_the_actual_element_class(tmp_path):
    from analyzer.native_arrays import JavaArray
    result,e,_=run(tmp_path,'Number[] numbers=(Number[])(Object)values;Object value=numbers[0];return (Integer)value;',parameters='Integer[] values',
                   params={'values':JavaArray([1],'java.lang.Integer',['Integer'])})
    assert result==1 and not e.approximate


def test_list_equals_does_not_equate_long_and_integer_payloads(tmp_path):
    result,e,_=run(tmp_path,'return Arrays.asList(1L).equals(Arrays.asList(1));')
    assert result is False and not e.approximate


def test_list_reference_equality_uses_allocation_identity(tmp_path):
    result,e,_=run(tmp_path,'List first=new ArrayList();List second=new ArrayList();return first==second;')
    assert result is False and not e.approximate


def test_boxed_integer_remove_uses_the_object_overload(tmp_path):
    result,e,_=run(tmp_path,'List<Integer> values=new ArrayList<Integer>();values.add(9);values.add(1);Integer selected=1;boolean changed=values.remove(selected);return changed&&values.get(0)==9&&values.size()==1;')
    assert result is True and not e.approximate


def test_index_remove_keeps_the_removed_box_class(tmp_path):
    result,e,_=run(tmp_path,'List values=new ArrayList();values.add(1L);Object removed=values.remove(0);return (Long)removed;')
    assert result==1 and not e.approximate


def test_iterator_read_keeps_box_provenance_and_checks_a_typed_consumer(tmp_path):
    result,e,ids=run(tmp_path,'List<Long> values=new ArrayList<Long>();List raw=values;raw.add(1);Iterator<Long> iterator=values.iterator();Long value=iterator.next();after();return value;')
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


def test_iterator_detects_a_structural_change_even_if_contents_are_restored(tmp_path):
    result,e,ids=run(tmp_path,'List<Long> values=new ArrayList<Long>();values.add(1L);Iterator<Long> iterator=values.iterator();values.remove(0);values.add(1L);Object value=iterator.next();after();return value;')
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


def test_bulk_list_removal_compares_box_classes(tmp_path):
    result,e,_=run(tmp_path,'List values=new ArrayList();values.add(1L);values.removeAll(Arrays.asList(1));return (Long)values.get(0);')
    assert result==1 and not e.approximate


def test_typed_entry_list_binding_preserves_shared_parameter_aliases(tmp_path):
    shared=[1]
    result,e,_=run(tmp_path,'first.add(2L);return second.size()==2;',parameters='List<Long> first,List<Long> second',params={'first':shared,'second':shared})
    assert result is True and not e.approximate


def test_unknown_large_box_identity_is_not_python_payload_equality(tmp_path):
    result,e,_=run(tmp_path,'Object first=200L;Object second=200L;return first==second;')
    assert result is U and e.approximate and any('identity' in warning for warning in e.warnings)


def test_mandatory_small_box_cache_can_prove_reference_equality(tmp_path):
    result,e,_=run(tmp_path,'Object first=100L;Object second=100L;return first==second;')
    assert result is True and not e.approximate


def test_the_same_reference_expression_remains_reflexive(tmp_path):
    result,e,_=run(tmp_path,'Object value=200L;return value==value;')
    assert result is True and not e.approximate


def test_fixed_size_arrays_list_rejects_structural_changes(tmp_path):
    result,e,ids=run(tmp_path,'List<Integer> values=Arrays.asList(1);values.add(2);after();return 1;')
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


def test_iterator_set_is_not_a_structural_change(tmp_path):
    result,e,_=run(tmp_path,'List<Long> values=new ArrayList<Long>();values.add(1L);Iterator<Long> iterator=values.iterator();values.set(0,2L);Object value=iterator.next();return (Long)value;')
    assert result==2 and not e.approximate


def test_a_cyclic_native_list_can_cross_a_source_call_frame(tmp_path):
    result,e,_=run(tmp_path,'List values=new ArrayList();values.add(values);return length(values);',extra='int length(List values){return values.size();}')
    assert result==1 and not e.approximate


def test_a_default_char_field_boxes_its_zero_code_unit(tmp_path):
    result,e,_=run(tmp_path,'Holder holder=new Holder();Object value=holder.value;return (Character)value;',schema='class Holder{char value;}')
    assert result=='\0' and not e.approximate


@pytest.mark.parametrize('argument',['-1','(Collection)null'])
def test_native_list_constructor_failure_stops_following_calls(tmp_path,argument):
    result,e,ids=run(tmp_path,'List values=new ArrayList('+argument+');after();return values;')
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


def test_copying_an_opaque_list_does_not_make_its_length_known(tmp_path):
    from analyzer.native_storage import JavaList
    values=JavaList([1],['Long']);values.opaque=True
    result,e,_=run(tmp_path,'List copy=new ArrayList(values);return copy.size();',parameters='List<Long> values',params={'values':values})
    assert result is U and e.approximate


def test_one_element_stream_interference_throws_after_the_callback(tmp_path):
    body='List<Integer> values=new ArrayList<Integer>();values.add(1);values.stream().map(x->{values.add(2);return x;}).collect(Collectors.toList());after();return 1;'
    result,e,ids=run(tmp_path,body)
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


@pytest.mark.parametrize('declaration,body,url',[
 ('@RequestParam List<Long> values','Object value=values.get(0);return (Long)value;','?values=1&values=2'),
 ('@RequestParam Optional<Long> value','Object selected=value.get();return (Long)selected;','?value=1')])
def test_named_http_conversion_retains_the_converted_native_class(tmp_path,declaration,body,url):
    p,db,ids=program(tmp_path,body,parameters=declaration)
    e=Engine(p,ScenarioState(db));e.method=ids['Api.entry']
    arguments=e.request_arguments(e.method,'http://service/items'+url,{},None,'independent query')
    assert e.invoke(e.method,arguments)==1 and not e.approximate


@pytest.mark.parametrize('comparison',['first==second','first.equals(second)'])
def test_separately_allocated_iterators_have_distinct_identities(tmp_path,comparison):
    result,e,_=run(tmp_path,'List values=new ArrayList();Iterator first=values.iterator();Iterator second=values.iterator();return '+comparison+';')
    assert result is False and not e.approximate


def test_an_iterator_alias_keeps_identity_through_a_branch_clone(tmp_path):
    result,e,_=run(tmp_path,'List values=new ArrayList();Iterator first=values.iterator();Iterator second=first;if(flag){values.add(1L);}else{values.add(1L);}return first==second;',
                   parameters='boolean flag',params={'flag':U},conservative=True)
    assert result is True and not any('identity' in w for w in e.warnings)


def test_enhanced_for_growth_terminates_at_the_next_iterator_check(tmp_path):
    result,e,ids=run(tmp_path,'List<Integer> values=new ArrayList<Integer>();values.add(1);for(Integer value:values){values.add(2);}after();return 1;')
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


@pytest.mark.parametrize('implementation,fails',[('ArrayList',True),('LinkedList',False)])
def test_enhanced_for_removal_uses_the_actual_iterator_has_next_rule(tmp_path,implementation,fails):
    result,e,ids=run(tmp_path,'List<Integer> values=new '+implementation+'<Integer>();values.add(1);for(Integer value:values){values.remove(0);}after();return values.size();')
    assert not e.approximate
    if fails:assert result is U and e.outcome=='uncaught application exception' and not after(e,ids)
    else:assert result==0 and e.outcome=='returned' and after(e,ids)


def test_ordinary_source_class_cast_rejects_an_incompatible_allocation(tmp_path):
    result,e,ids=run(tmp_path,'Object value=new Wrong();Counter checked=(Counter)value;after();return checked.count;',schema='class Counter{int count;}class Wrong{int count=5;}')
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


def test_unmodeled_foreign_reference_cast_has_an_explicit_boundary(tmp_path):
    result,e,_=run(tmp_path,'Foreign selected=(Foreign)input;return selected;',parameters='Object input',params={'input':{}},schema='import external.library.Foreign;')
    assert result is U and e.approximate and any('cast' in w for w in e.warnings)


def test_an_array_list_cannot_be_cast_to_a_map(tmp_path):
    result,e,ids=run(tmp_path,'Object value=new ArrayList();Map checked=(Map)value;after();return checked;')
    assert result is U and e.outcome=='uncaught application exception' and not e.approximate and not after(e,ids)


@pytest.mark.parametrize('expression,expected',[('(double)1',1.0),("(int)'A'",65),("(double)'A'",65.0)])
def test_primitive_cast_changes_payload_with_the_java_primitive_type(tmp_path,expression,expected):
    result,e,_=run(tmp_path,'return '+expression+';')
    assert type(result) is type(expected) and result==expected and not e.approximate


@pytest.mark.parametrize('other,known',[('1',False),('1L',True)])
def test_return_kind_join_keeps_only_agreed_branch_evidence(tmp_path,other,known):
    result,e,_=run(tmp_path,'Object value=choose(flag);return (Long)value;',extra='Object choose(boolean flag){if(flag){return 1L;}else{return '+other+';}}',
                   parameters='boolean flag',params={'flag':U},conservative=True)
    if known:assert result==1 and not any('runtime kind' in w for w in e.warnings)
    else:assert result is U and e.approximate and any('runtime kind' in w for w in e.warnings)


@pytest.mark.parametrize('literal',['1L',"'x'"])
def test_boxed_equals_does_not_compare_different_classes_by_python_payload(tmp_path,literal):
    other='1' if literal=='1L' else '"x"'
    result,e,_=run(tmp_path,'Object value='+literal+';return value.equals('+other+');')
    assert result is False and not e.approximate


def test_distinct_box_classes_cannot_be_the_same_object(tmp_path):
    result,e,_=run(tmp_path,'Object first=1L;Object second=1;return first==second;')
    assert result is False and not e.approximate


@pytest.mark.parametrize('declaration,body,expected',[
 ('Object value=1;', 'return (long)value;', 'throw'),
 ('Integer value=1;', 'return (long)value;', 1),
 ('Number value=1;', 'return (long)value;', 'throw'),
 ('Object value=1L;', 'return (long)value;', 1)])
def test_explicit_primitive_cast_distinguishes_erased_and_exact_wrapper_sources(tmp_path,declaration,body,expected):
    result,e,_=run(tmp_path,declaration+body)
    if expected=='throw':assert result is U and e.outcome=='uncaught application exception'
    else:assert result==expected and e.outcome=='returned'
    assert not e.approximate


def test_plain_map_payload_does_not_invent_an_integer_wrapper(tmp_path):
    from analyzer.java_collections import JavaMap
    result,e,_=run(tmp_path,'Object value=values.get("k");return (Long)value;',parameters='Map values',params={'values':JavaMap({'k':1})})
    assert result is U and e.approximate and e.outcome=='returned'


def test_generic_type_variable_cast_checks_its_bound_before_consumption(tmp_path):
    schema='class Reader<T extends Number>{int read(){T value=(T)(Object)1;return (int)value;}}'
    result,e,_=run(tmp_path,'return new Reader<Long>().read();',schema=schema)
    assert result==1 and not e.approximate
