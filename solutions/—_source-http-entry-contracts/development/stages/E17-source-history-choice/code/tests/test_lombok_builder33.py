"""Generated builders need source ownership, native annotations and typed aliases."""
import json
import re
import pytest
from builders import build
from analyzer.engine import Engine
from analyzer.project import Project
from analyzer.state import ScenarioState,U
from analyzer.java_collections import JavaObject


def fixture(root,*,annotation='@lombok.Builder',fields='public String name;',
            body='Item item=Item.builder().name("ready").build();return item.name;',
            extra='',api_extra='',imports='import records.Item;',returned='String'):
    sources={'Item.java':'package records;'+annotation+' public class Item{'+fields+extra+'}',
             'Api.java':'package caller;'+imports+' class Api{'+returned+' entry(){'+body+'}'+api_extra+'}'}
    p,db,ids=build(root,sources)
    data=json.loads((root/'skeleton.json').read_text())
    for node in data['nodes'].values():
        if node['kind']=='type':
            package=re.search(r'package\s+([\w.]+)',sources[node['file']])[1]
            node['fqn']=package+'.'+node['fqn']
    (root/'skeleton.json').write_text(json.dumps(data))
    return Engine(Project(root/'skeleton.json',root),ScenarioState(db)),ids


@pytest.mark.parametrize('annotation',['@lombok.Builder','import lombok.Builder;@Builder','@lombok.Builder @lombok.NoArgsConstructor @lombok.AllArgsConstructor'])
def test_imported_class_builder_resolves_the_source_qualified_owner(tmp_path,annotation):
    e,ids=fixture(tmp_path,annotation=annotation)
    assert e.run(ids['Api.entry'],{})=='ready' and not e.approximate
    assert e.edges=={('','executes',ids['Api.entry'])}


def test_fully_qualified_builder_ignores_untrusted_skeleton_receiver_spelling(tmp_path):
    e,ids=fixture(tmp_path,imports='',body='records.Item item=records.Item.builder().name("ready").build();return item.name;')
    for node in e.p.nodes.values():
        if node['kind']=='call_site' and node.get('callee')=='builder':node['receiver_type']='unrelated.Item'
    assert e.run(ids['Api.entry'],{})=='ready' and not e.approximate


def test_built_references_share_arguments_but_not_subsequent_builder_assignments(tmp_path):
    e,ids=fixture(tmp_path,fields='public java.util.List<String> names;',returned='boolean',body='''
      java.util.List<String> names=new java.util.ArrayList<String>();names.add("first");
      Item.ItemBuilder builder=Item.builder().names(names);Item first=builder.build();
      names.add("shared");builder.names(new java.util.ArrayList<String>());Item second=builder.build();
      return first.names.size()==2 && second.names.isEmpty() && first!=second;''')
    assert e.run(ids['Api.entry'],{}) is True and not e.approximate,e.warnings


def test_native_defaults_and_declared_numeric_kinds_are_preserved(tmp_path):
    e,ids=fixture(tmp_path,fields='public long id;public boolean active;public char marker;public String name;',
        returned='Item',body='return Item.builder().id(7L).build();')
    value=e.run(ids['Api.entry'],{})
    assert isinstance(value,JavaObject) and value.java_type=='records.Item'
    assert {k:value[k] for k in ('id','active','marker','name')}=={'id':7,'active':False,'marker':'\0','name':None}
    assert value._native_field_kinds['id']=='Long' and not e.approximate


def test_builder_initializes_the_declaring_class_once(tmp_path):
    e,ids=fixture(tmp_path,fields='public String name;public static int initialized=1;',
                  body='Item.builder().build();Item.builder().build();return "ready";')
    assert e.run(ids['Api.entry'],{})=='ready' and not e.approximate
    assert e.state.static_fields['type:service:Item']['initialized']==1


def test_generated_all_args_builder_does_not_execute_an_unrelated_source_noarg_constructor(tmp_path):
    e,ids=fixture(tmp_path,annotation='@lombok.Builder @lombok.AllArgsConstructor',
                  extra='public Item(){throw new IllegalStateException("noarg is not the builder target");}')
    assert e.run(ids['Api.entry'],{})=='ready' and not e.approximate
    assert not any(kind=='executes' and target==ids['Item.<init>'] for _,kind,target in e.edges)


@pytest.mark.parametrize('annotation,fields,extra',[
    ('@lombok.Builder(toBuilder=true)','public String name;',''),
    ('@lombok.Builder','@lombok.Builder.Default public String name="initial";',''),
    ('@lombok.Builder','@lombok.NonNull public String name;',''),
    ('@lombok.Builder','@lombok.Singular public java.util.List<String> names;',''),
    ('@lombok.Builder','public String name;','public Item(String name){this.name=name;}'),
    ('@lombok.Builder','public String name;','public static class ItemBuilder{public Item build(){return null;}}'),
    ('@lombok.Builder','public String name="initializer";',''),
])
def test_nondefault_builder_contracts_do_not_run_a_success_suffix(tmp_path,annotation,fields,extra):
    e,ids=fixture(tmp_path,annotation=annotation,fields=fields,extra=extra,
                  body='Item.builder();return after();',api_extra='String after(){return "wrong";}')
    assert e.run(ids['Api.entry'],{}) is U and e.approximate
    assert not any(kind=='executes' and target==ids['Api.after'] for _,kind,target in e.edges)


def test_source_builder_method_has_priority_over_generated_construction(tmp_path):
    e,ids=fixture(tmp_path,extra='''public Item(String value){name=value;}
      public static Item builder(){return new Item("source");}''',body='return Item.builder().name;')
    assert e.run(ids['Api.entry'],{})=='source' and not e.approximate
    assert any(kind=='executes' and target==ids['Item.builder'] for _,kind,target in e.edges)


def test_a_user_annotation_namesake_cannot_enable_generated_code(tmp_path):
    e,ids=fixture(tmp_path,annotation='@interface Builder{} @Builder',body='return Item.builder().name;',
        extra='public static Item builder(){Item item=new Item();item.name="source";return item;}')
    assert e.run(ids['Api.entry'],{})=='source' and not e.approximate
    assert any(kind=='executes' and target==ids['Item.builder'] for _,kind,target in e.edges)
