"""Declaration-owned type parameters, independent of any application domain."""
import json
import re
import pytest
from analyzer.engine import Engine
from analyzer.http_json import decode_response
from analyzer.java_collections import JavaMap,JavaRecord,JsonObject
from analyzer.project import Project
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
            if package:node['fqn']=package[1]+'.'+node['fqn']
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


@pytest.mark.parametrize('annotation',[
    '@JsonIgnoreProperties(ignoreUnknown=false)',
    '@JsonIgnoreProperties(value="ignoreUnknown=true")',
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
