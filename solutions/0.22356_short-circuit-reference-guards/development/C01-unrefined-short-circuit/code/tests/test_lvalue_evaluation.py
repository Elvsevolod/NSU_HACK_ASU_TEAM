"""Source-only counterexamples for Java writable operands; no target project."""
import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from analyzer.java_collections import JavaRecord
from builders import build


def execute(tmp_path,body,params=None,parameters='Counter counter',extra=''):
    project,db,ids=build(tmp_path,{'Api.java':'''class Counter{
      public int count;public int visits;public byte small;public long wide;
      public char letter;public double amount;public float fraction;
      public Integer boxed;public Counter child;}
      class Api{Object entry('''+parameters+'){'+body+'}'+extra+'}'})
    engine=Engine(project,ScenarioState(db))
    result=engine.run(ids['Api.entry'],params or {})
    return result,engine


def counter(**fields):
    return JavaRecord('Counter',{'__type__':'Counter','count':10,'visits':0,**fields},wire_fields=fields.keys()|{'count','visits'})


@pytest.mark.parametrize('expression,before,after',[
    ('counter.count++',10,11),('++counter.count',11,11),
    ('counter.count--',10,9),('--counter.count',9,9),
    ('(counter.count)++',10,11),('++(counter.count)',11,11)])
def test_field_updates_return_the_correct_value_and_write_the_same_field(tmp_path,expression,before,after):
    value=counter();result,engine=execute(tmp_path,'return '+expression+';',{'counter':value})
    assert result==before and value['count']==after and not engine.approximate


def test_nested_receiver_updates_the_aliased_object(tmp_path):
    child=counter();outer=counter(child=child)
    result,_=execute(tmp_path,'counter.child.count++;return counter.child.count;',{'counter':outer})
    assert result==11 and child['count']==11


def test_receiver_is_evaluated_once(tmp_path):
    value=counter();result,engine=execute(tmp_path,'int old=target(counter).count++;return old+counter.count+counter.visits;',{'counter':value},extra='Counter target(Counter c){c.visits=c.visits+1;return c;}')
    assert result==22 and value['visits']==1 and value['count']==11 and not engine.approximate


def test_unqualified_field_is_written_to_this_instead_of_a_local_copy(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Counter{
      int count=10;int increment(){count++;return this.count;}}
      class Api{int entry(){Counter c=new Counter();c.increment();return c.count;}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})==11 and not engine.approximate


def test_a_shadowing_local_still_owns_its_update(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Counter{int count=10;
      int increment(){int count=2;count++;return count+this.count;}}
      class Api{int entry(){return new Counter().increment();}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==13


@pytest.mark.parametrize('field,initial,expression,expected',[
    ('count',2147483647,'++counter.count',-2147483648),
    ('small',127,'++counter.small',-128),
    ('wide',9223372036854775807,'++counter.wide',-9223372036854775808),
    ('letter','\uffff','++counter.letter','\u0000'),
    ('amount',2.5,'++counter.amount',3.5)])
def test_update_uses_declared_numeric_type(tmp_path,field,initial,expression,expected):
    value=counter(**{field:initial})
    result,engine=execute(tmp_path,'return '+expression+';',{'counter':value})
    assert result==expected and value[field]==expected and not engine.approximate


def test_float_update_does_not_claim_double_rounding(tmp_path):
    value=counter(fraction=16777216.0)
    result,engine=execute(tmp_path,'return ++counter.fraction;',{'counter':value})
    assert result is U and value['fraction'] is U
    assert engine.approximate and any('float' in x for x in engine.warnings)


def test_null_boxed_operand_throws_before_following_source_call(tmp_path):
    value=counter(boxed=None)
    result,engine=execute(tmp_path,'counter.boxed++;after();return 1;',{'counter':value},extra='void after(){}')
    assert result is U and engine.outcome=='uncaught application exception'
    assert not any('#after(' in e[2] for e in engine.edges if e[1]=='executes')
    assert value['boxed'] is None


def test_null_instance_receiver_throws_before_following_source_call(tmp_path):
    result,engine=execute(tmp_path,'counter.count++;after();return 1;',{'counter':None},extra='void after(){}')
    assert result is U and engine.outcome=='uncaught application exception'
    assert not any('#after(' in e[2] for e in engine.edges if e[1]=='executes')


def test_array_update_keeps_the_original_index_and_postfix_result(tmp_path):
    values=[10,30]
    result,engine=execute(tmp_path,'int index=0;int old=values[index++]++;return old+values[0]+index;',{'values':values},'int[] values')
    assert result==22 and values==[11,30] and not engine.approximate


def test_narrow_array_component_has_its_declared_width(tmp_path):
    values=[127]
    result,engine=execute(tmp_path,'return ++values[0];',{'values':values},'byte[] values')
    assert result==-128 and values==[-128] and not engine.approximate


def test_array_bounds_failure_does_not_run_following_source(tmp_path):
    result,engine=execute(tmp_path,'values[4]++;after();return 1;',{'values':[1]},'int[] values',extra='void after(){}')
    assert result is U and engine.outcome=='uncaught application exception'
    assert not any('#after(' in e[2] for e in engine.edges if e[1]=='executes')


def test_replay_applies_an_update_only_once_per_owned_path(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Counter{int count;}
      class Api{int entry(Counter counter,boolean flag){counter.count++;if(flag){}return counter.count;}}'''})
    value=counter();paths=run_paths(project,ScenarioState(db),ids['Api.entry'],{'counter':value,'flag':U},limit=1)
    assert [p['result'] for p in paths]==[11] and value['count']==10


def test_simple_field_assignment_evaluates_receiver_before_rhs(tmp_path):
    value=counter()
    result,engine=execute(tmp_path,'target(counter).count=rhs(counter);return counter.visits;',{'counter':value},extra='Counter target(Counter c){c.visits=c.visits*10+1;return c;}int rhs(Counter c){c.visits=c.visits*10+2;return 7;}')
    assert result==12 and value['count']==7 and not engine.approximate


def test_compound_assignment_does_not_evaluate_receiver_twice(tmp_path):
    value=counter()
    result,engine=execute(tmp_path,'target(counter).count+=rhs(counter);return counter.visits+counter.count;',{'counter':value},extra='Counter target(Counter c){c.visits=c.visits+1;return c;}int rhs(Counter c){c.count=50;return 2;}')
    assert result==13 and value['count']==12 and value['visits']==1 and not engine.approximate


def test_simple_null_field_assignment_evaluates_rhs_before_null_check(tmp_path):
    value=counter()
    result,engine=execute(tmp_path,'try{missing.count=rhs(counter);}catch(NullPointerException e){return counter.visits;}return 0;',{'counter':value,'missing':None},'Counter counter,Counter missing',extra='int rhs(Counter c){c.visits=7;return 2;}')
    assert result==7 and value['visits']==7 and not engine.approximate


def test_compound_null_field_assignment_fails_before_rhs(tmp_path):
    value=counter()
    result,engine=execute(tmp_path,'try{missing.count+=rhs(counter);}catch(NullPointerException e){return counter.visits;}return 0;',{'counter':value,'missing':None},'Counter counter,Counter missing',extra='int rhs(Counter c){c.visits=7;return 2;}')
    assert result==0 and value['visits']==0 and not engine.approximate


def test_receiver_exception_prevents_simple_assignment_rhs(tmp_path):
    value=counter()
    result,engine=execute(tmp_path,'try{missing().count=rhs(counter);}catch(IllegalStateException e){return counter.visits;}return 0;',{'counter':value},extra='Counter missing(){throw new IllegalStateException();}int rhs(Counter c){c.visits=7;return 2;}')
    assert result==0 and value['visits']==0 and not engine.approximate


def test_unknown_update_is_not_replaced_with_a_number(tmp_path):
    value=counter(count=U)
    result,engine=execute(tmp_path,'return ++counter.count;',{'counter':value})
    assert result is U and value['count'] is U and engine.approximate


@pytest.mark.parametrize('expression,expected,stored',[
    ('++ /* operand */ counter.count',11,11),
    ('counter /* ++ is a comment */ .count--',10,9),
    ('(counter.count /* operand */)++',10,11)])
def test_comments_do_not_choose_an_update_operator_or_an_operand(tmp_path,expression,expected,stored):
    value=counter();result,engine=execute(tmp_path,'return '+expression+';',{'counter':value})
    assert result==expected and value['count']==stored and not engine.approximate


def test_a_simple_assignment_retains_receiver_when_rhs_rebinds_its_name(tmp_path):
    first,second=counter(count=1),counter(count=7)
    result,engine=execute(tmp_path,'first.count=(first=second).count;return alias.count;',{'first':first,'second':second,'alias':first},'Counter first,Counter second,Counter alias')
    assert result==7 and first['count']==7 and second['count']==7 and not engine.approximate


def test_unqualified_simple_assignment_updates_this(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Counter{int count=10;
      int change(){count=7;return this.count;}}class Api{int entry(){return new Counter().change();}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})==7 and not engine.approximate


@pytest.mark.parametrize('operator,values,expected',[
    ('=',None,12),('+=',None,1),('=',[],12),('+=',[],1)])
def test_array_assignment_checks_null_and_bounds_at_the_java_point(tmp_path,operator,values,expected):
    value=counter();result,engine=execute(tmp_path,'try{values[index(counter)]'+operator+'rhs(counter);}catch(RuntimeException e){return counter.visits;}return 0;',{'counter':value,'values':values},'Counter counter,int[] values',extra='int index(Counter c){c.visits=c.visits*10+1;return 4;}int rhs(Counter c){c.visits=c.visits*10+2;return 7;}')
    assert result==expected and value['visits']==expected and not engine.approximate


def test_primitive_array_assignment_captures_index_before_rhs_mutates_it(tmp_path):
    values=[1,2];value=counter(count=0)
    result,engine=execute(tmp_path,'values[counter.count]=rhs(counter);return values[0];',{'counter':value,'values':values},'Counter counter,int[] values',extra='int rhs(Counter c){c.count=1;return 7;}')
    assert result==7 and values==[7,2] and value['count']==1 and not engine.approximate


def test_unknown_array_index_widens_every_possible_changed_component(tmp_path):
    values=[1,2]
    result,engine=execute(tmp_path,'values[index]=7;return values[0];',{'values':values,'index':U},'int[] values,int index')
    assert result is U and values==[U,U] and engine.approximate


def test_reference_array_store_has_a_visible_runtime_type_limit(tmp_path):
    values=['before']
    result,engine=execute(tmp_path,'values[0]=replacement;return values[0];',{'values':values,'replacement':counter()},'Object[] values,Object replacement')
    assert result is U and values==[U] and engine.approximate
    assert any('reference array store runtime component type' in x for x in engine.warnings)


def test_static_storage_updates_a_scenario_cell_instead_of_an_instance_slot(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'class Globals{static int count=0;}class Api{int entry(){return ++Globals.count;}}'})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})==1 and not engine.approximate
    assert engine.state.static_fields['type:service:Globals']['count']==1
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==1


def test_array_length_keeps_its_integer_type_in_arithmetic(tmp_path):
    result,engine=execute(tmp_path,'return values.length+1;',{'values':[1,2]},'int[] values')
    assert result==3 and not engine.approximate


def test_local_updates_preserve_narrowing_and_postfix_values(tmp_path):
    result,engine=execute(tmp_path,'byte value=127;int old=value++;return old+value;',{},'')
    assert result==-1 and not engine.approximate


def test_commented_parenthesized_update_keeps_its_type_when_used_in_arithmetic(tmp_path):
    value=counter()
    result,engine=execute(tmp_path,'return (++(counter.count /* operand */))+1;',{'counter':value})
    assert result==12 and value['count']==11 and not engine.approximate


def test_assignment_expression_keeps_the_type_of_its_lhs(tmp_path):
    value=counter()
    result,engine=execute(tmp_path,'return (counter.count=7)+1;',{'counter':value})
    assert result==8 and value['count']==7 and not engine.approximate


def test_array_compound_assignment_uses_the_component_width(tmp_path):
    values=[127]
    result,engine=execute(tmp_path,'values[0]+=1;return values[0];',{'values':values},'byte[] values')
    assert result==-128 and values==[-128] and not engine.approximate


def test_primitive_assignment_unboxes_before_store(tmp_path):
    value=counter()
    result,engine=execute(tmp_path,'try{counter.count=(Integer)null;}catch(NullPointerException e){return counter.count;}return 0;',{'counter':value})
    assert result==10 and value['count']==10 and not engine.approximate


def test_float_compound_assignment_does_not_silently_use_double_rounding(tmp_path):
    value=counter(fraction=16777216.0)
    result,engine=execute(tmp_path,'counter.fraction+=1;return counter.fraction;',{'counter':value})
    assert result is U and value['fraction'] is U and engine.approximate
    assert any('float rounding' in x for x in engine.warnings)


def test_double_compound_assignment_converts_integral_representation(tmp_path):
    value=counter(amount=2)
    result,engine=execute(tmp_path,'counter.amount+=1;return counter.amount;',{'counter':value})
    assert type(result) is float and result==3.0 and value['amount']==3.0 and not engine.approximate


def test_char_compound_assignment_narrows_to_utf16_component(tmp_path):
    value=counter(letter='\uffff')
    result,engine=execute(tmp_path,'counter.letter+=1;return counter.letter;',{'counter':value})
    assert result=='\u0000' and value['letter']=='\u0000' and not engine.approximate


def test_unsupported_floating_to_integer_compound_conversion_is_diagnosed(tmp_path):
    value=counter()
    result,engine=execute(tmp_path,'counter.count+=1.5;return counter.count;',{'counter':value})
    assert result is U and value['count'] is U and engine.approximate


@pytest.mark.parametrize('body',[
    'Child child=new Child();Base base=child;base.count++;return base.count;',
    'Child child=new Child();child.count++;return child.count;'])
def test_hidden_fields_do_not_share_a_confirmed_storage_slot(tmp_path,body):
    project,db,ids=build(tmp_path,{'Api.java':'''class Base{int count=1;}
      class Child extends Base{int count=5;}class Api{int entry(){'''+body+'}}'})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{}) is U and engine.approximate
    assert any('hidden Java fields require separate' in x for x in engine.warnings)


def test_binary_nested_type_name_selects_its_lexical_owner(tmp_path):
    import json
    from analyzer.project import Project
    project,_,_=build(tmp_path,{'Outer.java':'''class OuterA{static class Inner{int one;}}
      class OuterB{static class Inner{String two;}}'''})
    skeleton=project.skeleton
    skeleton['nodes']['type:service:Inner']['fqn']='OuterB$Inner'
    (tmp_path/'skeleton.json').write_text(json.dumps(skeleton))
    project=Project(tmp_path/'skeleton.json',tmp_path)
    assert set(project.type_fields['type:service:Inner'])=={'two'}
    assert project.type_fields['type:service:Inner']['two']['type']=='String'
