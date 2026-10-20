"""Declaration-owned type parameters, independent of any application domain."""
import json
import re
import pytest
from analyzer.engine import Engine
from analyzer.http_json import decode_response
from analyzer.java_collections import JavaMap,JavaRecord,JsonObject
from analyzer.project import Project,walk,text
from analyzer.state import ScenarioState,U
from builders import build


def decoder(tmp_path,schema):
    sources={'Api.java':'class Api{Object entry(){return null;}}',**schema}
    project,db,ids=build(tmp_path,sources)
    # The fixture adapter supplies source namespaces, never generic bindings.
    skeleton=project.skeleton
    for node in skeleton['nodes'].values():
        if node.get('kind')=='type':
            package=re.search(r'\bpackage\s+([\w.]+)\s*;',sources[node['file']])
            declaration=next(decl for decl in walk(project.trees[node['file']].root_node)
                if decl.type in ('class_declaration','interface_declaration','enum_declaration')
                and text(decl.child_by_field_name('name'))==node['fqn'])
            owners=[];parent=declaration.parent
            while parent is not None:
                if parent.type in ('class_declaration','interface_declaration','enum_declaration'):
                    owners.insert(0,text(parent.child_by_field_name('name')))
                parent=parent.parent
            node['fqn']='.'.join(([package[1]] if package else [])+owners+[node['fqn']])
    (tmp_path/'skeleton.json').write_text(json.dumps(skeleton))
    project=Project(tmp_path/'skeleton.json',tmp_path)
    engine=Engine(project,ScenarioState(db));engine.method=ids['Api.entry']
    warnings=[]
    def decode(payload,written):
        return decode_response(project,JsonObject(payload),written,project.methods[ids['Api.entry']],engine.standard_type,warnings.append)
    return decode,warnings,project


def test_concrete_subclass_binds_an_inherited_map_field(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'''import java.util.*;
      class Parent<T>{public T payload;}class Child extends Parent<Map<String,String>>{}'''})
    result=decode({'payload':{'key':'ready'}},'Child')
    assert isinstance(result['payload'],JavaMap) and result['payload'].mapping=={'key':'ready'}
    assert not warnings


def test_multilevel_substitution_composes_nested_arguments_and_same_names(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'''import java.util.*;
      class Item{public String code;}class Base<T>{public T payload;}
      class Middle<T> extends Base<Map<String,List<T>>>{}class Child<T> extends Middle<T>{}'''})
    result=decode({'payload':{'one':[{'code':'ready'}]}},'Child<Item>')
    item=result['payload'].mapping['one'][0]
    assert isinstance(item,JavaRecord) and item.declared_type=='Item' and item['code']=='ready'
    assert not warnings


def test_generic_argument_keeps_its_original_imports_across_inheritance(tmp_path):
    decode,warnings,_=decoder(tmp_path,{
      'Base.java':'package schemas;public class Base<T>{public T payload;}',
      'Map.java':'package middle;public class Map{}',
      'Middle.java':'package middle;import schemas.Base;import java.util.List;public class Middle<T> extends Base<List<T>>{}',
      'Child.java':'package client;import middle.Middle;import java.util.Map;public class Child extends Middle<Map<String,String>>{}',
    })
    result=decode({'payload':[{'key':'ready'}]},'client.Child')
    assert isinstance(result['payload'][0],JavaMap) and result['payload'][0].mapping=={'key':'ready'}
    assert not warnings


def test_source_type_named_map_is_not_replaced_by_a_native_map(tmp_path):
    decode,warnings,_=decoder(tmp_path,{
      'Base.java':'package schemas;public class Base<T>{public T payload;}',
      'Map.java':'package business;public class Map{public String code;}',
      'Child.java':'package client;import schemas.Base;import business.Map;public class Child extends Base<Map>{}',
    })
    result=decode({'payload':{'code':'ready'}},'client.Child')
    assert isinstance(result['payload'],JavaRecord) and result['payload'].declared_type=='business.Map'
    assert result['payload']['code']=='ready' and not warnings


def test_raw_unbounded_parameter_becomes_object_without_guessing_string(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'''class Base<String>{public String payload;}
      class Child<T> extends Base<T>{}'''})
    result=decode({'payload':{'key':'ready'}},'Child')
    assert isinstance(result['payload'],JavaMap) and result['payload'].mapping=={'key':'ready'}
    assert not warnings


def test_raw_bound_uses_the_declared_upper_type(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'''class Item{public String code;}
      class Base<T extends Item>{public T payload;}class Child extends Base{}'''})
    result=decode({'payload':{'code':'ready'}},'Child')
    assert isinstance(result['payload'],JavaRecord) and result['payload'].declared_type=='Item'
    assert result['payload']['code']=='ready' and not warnings


def test_raw_bounded_parameter_named_string_cannot_masquerade_as_jdk_string(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'''class Item{public String code;}
      class Base<String extends Item>{public String payload;}class Child extends Base{}'''})
    result=decode({'payload':'wrong-scalar'},'Child')
    assert result['payload'] is U and warnings


def test_inherited_parameter_named_string_is_substituted_before_native_lookup(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'''class Item{public String code;}
      class Base<String>{public String payload;}class Child extends Base<Item>{}'''})
    result=decode({'payload':{'code':'ready'}},'Child')
    assert isinstance(result['payload'],JavaRecord) and result['payload']['code']=='ready'
    assert not warnings


def test_redeclared_field_uses_its_own_declaring_scope(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'''class Base<T>{public T payload;}
      class Child extends Base<Integer>{public String payload;}'''})
    result=decode({'payload':'ready'},'Child')
    assert result['payload']=='ready' and not warnings


def test_raw_dependent_bounds_resolve_through_their_own_scope(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'''class Item{public String code;}
      class Base<T extends Item,U extends T>{public U payload;}class Child extends Base{}'''})
    result=decode({'payload':{'code':'ready'}},'Child')
    assert isinstance(result['payload'],JavaRecord) and result['payload']['code']=='ready'
    assert not warnings


def test_recursive_generic_bound_stays_finite_for_a_finite_json_tree(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'''class Node<T>{public String code;public T next;}
      class Base<T extends Node<T>>{public T payload;}class Child extends Base{}'''})
    result=decode({'payload':{'code':'ready','next':None}},'Child')
    assert isinstance(result['payload'],JavaRecord) and result['payload']['code']=='ready'
    assert result['payload']['next'] is None and not warnings


@pytest.mark.parametrize('parent',['Base<String,Integer>','Base<? extends Item>'])
def test_unsupported_or_invalid_parent_arguments_remain_diagnostic(tmp_path,parent):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'class Item{public String code;}class Base<T>{public T payload;}class Child extends '+parent+'{}'})
    result=decode({'payload':{'code':'ready'}},'Child')
    assert result['payload'] is U and warnings


def test_interface_generic_parameters_are_extracted_in_their_own_scope(tmp_path):
    _,_,project=decoder(tmp_path,{'Schema.java':'interface Root<T>{}interface Left<T> extends Root<T>{}interface Right<U> extends Root<U>{}class Child implements Left<String>,Right<String>{}'})
    left=next(tid for tid,node in project.nodes.items() if node.get('fqn')=='Left')
    assert list(project.type_variables[left])==['T']
    assert project.generic_parents[left]==['Root<T>']


def test_annotation_before_a_type_parameter_does_not_become_its_name(tmp_path):
    decode,_,project=decoder(tmp_path,{'Schema.java':'class Base<@Mark T>{public T payload;}class Child extends Base<String>{}'})
    base=next(tid for tid,node in project.nodes.items() if node.get('fqn')=='Base')
    assert list(project.type_variables[base])==['T']
    assert decode({'payload':'ready'},'Child')['payload']=='ready'


def test_an_unknown_json_property_does_not_become_a_source_field(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'class Item{public String code;}class Base<T>{public T payload;}class Child extends Base<Item>{}'})
    result=decode({'payload':{'code':'known','undeclared':'wrong'}},'Child')
    assert result['payload'] is U
    assert any('undeclared JSON properties' in w for w in warnings)


def test_explicit_native_ignore_unknown_policy_discards_only_unknown_properties(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'''import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
      @JsonIgnoreProperties(ignoreUnknown=true) class Item{public String code;}
      class Base<T>{public T payload;}class Child extends Base<Item>{}'''})
    item=decode({'payload':{'code':'known','undeclared':'wrong'}},'Child')['payload']
    assert isinstance(item,JavaRecord) and item['code']=='known' and 'undeclared' not in item
    assert warnings # Other annotation/lifecycle effects remain outside the model.


def test_comments_around_a_real_literal_policy_do_not_hide_it(tmp_path):
    decode,_,_=decoder(tmp_path,{'Schema.java':'''import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
      @JsonIgnoreProperties(ignoreUnknown=/*proof*/true) class Item{public String code;}'''})
    item=decode({'code':'known','undeclared':'ignored'},'Item')
    assert isinstance(item,JavaRecord) and item['code']=='known' and 'undeclared' not in item


@pytest.mark.parametrize('annotation',[
    '@JsonIgnoreProperties',
    '@JsonIgnoreProperties(ignoreUnknown=false)',
    '@JsonIgnoreProperties(value="ignoreUnknown=true")',
    '@JsonIgnoreProperties(/*(ignoreUnknown=true)*/ value="safe")',
    '@Unrelated(value="ignoreUnknown=true")',
])
def test_a_false_or_quoted_annotation_option_does_not_accept_unknown_properties(tmp_path,annotation):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'import com.fasterxml.jackson.annotation.JsonIgnoreProperties;'+annotation+' class Item{public String code;}'})
    assert decode({'code':'known','undeclared':'wrong'},'Item') is U
    assert warnings


def test_an_external_annotation_namesake_does_not_supply_a_native_policy(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'import external.library.JsonIgnoreProperties;@JsonIgnoreProperties(ignoreUnknown=true) class Item{public String code;}'})
    assert decode({'code':'known','undeclared':'wrong'},'Item') is U
    assert warnings


def test_cyclic_source_inheritance_is_not_used_to_confirm_a_property_type(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'class Base<T> extends Child{public T payload;}class Child extends Base<String>{}'})
    assert decode({'payload':'wrong-known'},'Child')['payload'] is U
    assert warnings


def test_annotation_text_cannot_inject_a_source_superclass(tmp_path):
    decode,warnings,project=decoder(tmp_path,{'Schema.java':'''class Fake{public Integer foreign;}
      class Base<T>{public T payload;}@SuppressWarnings("extends Fake {") class Child extends Base<String>{}'''})
    child=next(tid for tid,node in project.nodes.items() if node.get('fqn')=='Child')
    assert set(project.type_fields[child])=={'payload'}
    assert decode({'payload':'ready'},'Child')['payload']=='ready' and not warnings


def test_all_source_superinterfaces_are_retained(tmp_path):
    _,_,project=decoder(tmp_path,{'Schema.java':'interface First<T>{}interface Second<T>{}interface Child<T> extends First<T>,Second<T>{}'})
    child=next(tid for tid,node in project.nodes.items() if node.get('fqn')=='Child')
    assert {project.nodes[tid]['fqn'] for tid in project.type_parents[child]}=={'First','Second'}


def test_annotated_method_type_variable_still_shadows_a_native_class(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{
      <@Mark String> Object entry(String input){Map map=new HashMap();map.put(input,"wrong-known");return map.get("x");}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{'input':'x'}) is U
    assert engine.approximate and engine.warnings


@pytest.mark.parametrize('reverse',[False,True])
def test_source_path_cache_does_not_share_bindings_between_instantiations(tmp_path,reverse):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'''import java.util.*;class Item{public String code;}
      class Base<T>{public T payload;}class Child<T> extends Base<T>{}'''})
    cases=[('Child<String>','text'),('Child<Item>',{'code':'record'}),
           ('Child<java.util.Map<String,String>>',{'key':'map'})]
    if reverse:cases.reverse()
    observed={written:decode({'payload':value},written)['payload'] for written,value in cases}
    assert observed['Child<String>']=='text'
    assert observed['Child<Item>']['code']=='record'
    assert observed['Child<java.util.Map<String,String>>'].mapping=={'key':'map'}
    assert not warnings


def test_swapped_parent_arguments_keep_their_declaration_positions(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'''class Base<A,B>{public A first;public B second;}
      class Child<P,Q> extends Base<Q,P>{}'''})
    item=decode({'first':7,'second':'ready'},'Child<String,Long>')
    assert item['first']==7 and item['second']=='ready' and not warnings


def test_raw_intersection_bound_uses_the_first_declared_type(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'''class Item{public String code;}
      class Base<T extends Item & java.io.Serializable>{public T payload;}class Child extends Base{}'''})
    item=decode({'payload':{'code':'ready'}},'Child')['payload']
    assert isinstance(item,JavaRecord) and item.declared_type=='Item' and item['code']=='ready'
    assert not warnings


def test_argument_does_not_borrow_imports_from_its_class_declaration(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'''import java.util.Map;
      class Base<T>{public T payload;}class Child<T> extends Base<T>{}'''})
    assert decode({'payload':{'key':'unknown'}},'Child<Map<String,String>>')['payload'] is U
    assert warnings


@pytest.mark.parametrize('declaration',[
    'abstract class Item{public String code;}',
    'interface Item{}',
])
def test_an_abstract_raw_bound_never_invents_a_default_concrete_instance(tmp_path,declaration):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':declaration+'class Base<T extends Item>{public T payload;}class Child extends Base{}'})
    assert decode({'payload':{}},'Child')['payload'] is U
    assert warnings


def test_a_nonstatic_member_class_needs_its_enclosing_instance_context(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'class Outer<String>{class Inner{public String payload;}}'})
    assert decode({'payload':'wrong-known'},'Outer.Inner') is U
    assert warnings


@pytest.mark.parametrize('declaration',[
    'class Outer{static class Inner{public String code;}}',
    'interface Outer{class Inner{public String code;}}',
])
def test_a_static_or_implicitly_static_member_can_use_the_bounded_field_model(tmp_path,declaration):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':declaration})
    assert decode({'code':'ready'},'Outer.Inner')['code']=='ready'
    assert not warnings


@pytest.mark.parametrize('primitive',['int','long','short','byte','char','boolean','double','float'])
def test_json_null_is_not_invented_as_a_java_primitive_null_reference(tmp_path,primitive):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'class Item{public '+primitive+' value;}'})
    assert decode({'value':None},'Item')['value'] is U
    assert any('primitive' in warning and 'policy' in warning for warning in warnings)


def test_json_null_for_a_boxed_value_remains_a_real_null_reference(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'class Item{public Integer value;}'})
    assert decode({'value':None},'Item')['value'] is None and not warnings


def test_json_null_for_an_inherited_generic_reference_needs_no_instance(tmp_path):
    decode,warnings,_=decoder(tmp_path,{'Schema.java':'abstract class Item{}class Base<T>{public T value;}class Child extends Base<Item>{}'})
    assert decode({'value':None},'Child')['value'] is None and not warnings
