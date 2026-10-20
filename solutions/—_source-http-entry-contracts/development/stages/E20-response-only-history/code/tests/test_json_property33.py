"""Expected JSON/access effects from Jackson's source, not analyzer predictions.

No JVM is compiled or launched. Creator, complex annotation and version-sensitive
READ_ONLY rename cases must stay explicit boundaries, rather than be guessed.
"""
import json
import pytest
from analyzer.bean_properties import default_bean_plan
from analyzer.engine import Engine
from analyzer.java_collections import JsonText
from analyzer.state import ScenarioState,U
from builders import build

IMPORTS='''import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonProperty.Access;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.databind.ObjectMapper;import java.util.*;'''


def fixture(root,bean,body='return new ObjectMapper().writeValueAsString(new Item());'):
    p,db,ids=build(root,{'Api.java':IMPORTS+bean+'class Api{Object entry(){'+body+'}void after(){}}'})
    return p,Engine(p,ScenarioState(db)),ids


def input_json(value):return json.dumps(json.dumps(value,ensure_ascii=False))


def plan(p,e,direction):return default_bean_plan(p,'type:service:Item',direction,e.standard_type)


@pytest.mark.parametrize('annotation',[
    '@JsonProperty("wire_name")','@JsonProperty(value="wire_name")',
    '@com.fasterxml.jackson.annotation.JsonProperty("wire_name")'])
def test_renamed_private_field_uses_wire_name_but_keeps_declaring_storage(tmp_path,annotation):
    p,e,ids=fixture(tmp_path, 'class Item{'+annotation+' private Long local=3L;Long raw(){return local;}}',
        'Item item=new ObjectMapper().readValue('+input_json({'wire_name':9})+',Item.class);return item;')
    value=e.run(ids['Api.entry'],{})
    assert value['local']==9 and 'wire_name' not in value and value._native_field_kinds['local']=='Long'
    read=plan(p,e,'serialize');write=plan(p,e,'deserialize')
    assert read['complete'] and write['complete']
    assert set(read['properties'])==set(write['properties'])=={'wire_name'}
    assert read['properties']['wire_name']['member']==write['properties']['wire_name']['member']=='local'


@pytest.mark.parametrize('annotation',['@JsonProperty','@JsonProperty()','@JsonProperty("")','@JsonProperty(value="")'])
def test_default_annotation_explicitly_exposes_private_field(tmp_path,annotation):
    p,e,ids=fixture(tmp_path,'class Item{'+annotation+' private String name="shown";}')
    value=e.run(ids['Api.entry'],{})
    assert isinstance(value,JsonText) and value.payload=={'name':'shown'} and not e.approximate


@pytest.mark.parametrize('qualifier',['Access','JsonProperty.Access','com.fasterxml.jackson.annotation.JsonProperty.Access'])
def test_read_only_field_is_not_overwritten_or_treated_as_unknown_input(tmp_path,qualifier):
    bean='class Item{@JsonProperty(access='+qualifier+'.READ_ONLY) private int value=7;int raw(){return value;}}'
    p,e,ids=fixture(tmp_path,bean,'Item item=new ObjectMapper().readValue('+input_json({'value':99})+',Item.class);return item.raw();')
    assert e.run(ids['Api.entry'],{})==7 and not e.approximate
    assert 'value' in plan(p,e,'deserialize')['ignored_properties']
    assert plan(p,e,'serialize')['properties']['value']['member']=='value'


def test_read_only_source_setter_is_not_invoked(tmp_path):
    p,e,ids=fixture(tmp_path,'''class Item{private int value=7;public int getValue(){return value;}
      @JsonProperty(access=Access.READ_ONLY)public void setValue(int input){throw new IllegalStateException();}}''',
        'return new ObjectMapper().readValue('+input_json({'value':99})+',Item.class).getValue();')
    assert e.run(ids['Api.entry'],{})==7 and not e.approximate
    assert not any(k=='executes' and target==ids['Item.setValue'] for _,k,target in e.edges)


def test_observed_fail_on_ignored_policy_still_throws_for_read_only_input(tmp_path):
    p,e,ids=fixture(tmp_path,'class Item{@JsonProperty(access=Access.READ_ONLY)public String value;}',
        'ObjectMapper m=new ObjectMapper();m.enable(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_IGNORED_PROPERTIES);'
        'm.readValue('+input_json({'value':'incoming'})+',Item.class);after();return true;')
    assert e.run(ids['Api.entry'],{}) is U and e.outcome=='uncaught application exception'
    assert not any(k=='executes' and target==ids['Api.after'] for _,k,target in e.edges)


def test_write_only_does_not_call_a_throwing_getter_or_emit_the_value(tmp_path):
    p,e,ids=fixture(tmp_path,'''class Item{public String marker="shown";
      @JsonProperty(access=Access.WRITE_ONLY)private String secret="hidden";
      public String getSecret(){throw new IllegalStateException();}}''')
    value=e.run(ids['Api.entry'],{})
    assert isinstance(value,JsonText) and value.payload=={'marker':'shown'} and not e.approximate
    assert not any(c['method']==ids['Item.getSecret'] for c in e.semantic_callbacks)


def test_write_only_renamed_field_accepts_input_into_java_member(tmp_path):
    p,e,ids=fixture(tmp_path,'''class Item{@JsonProperty(value="incoming",access=Access.WRITE_ONLY)
      private String secret="seed";String raw(){return secret;}}''',
        'return new ObjectMapper().readValue('+input_json({'incoming':'assigned'})+',Item.class).raw();')
    assert e.run(ids['Api.entry'],{})=='assigned' and not e.approximate


@pytest.mark.parametrize('access,expected',[('AUTO',3),('READ_WRITE',4),('READ_ONLY',4)])
def test_access_policy_controls_private_getter_visibility(tmp_path,access,expected):
    p,e,ids=fixture(tmp_path,'class Item{@JsonProperty(access=Access.'+access+')private int value=3;'
        'private int getValue(){return value+1;}}')
    value=e.run(ids['Api.entry'],{})
    assert isinstance(value,JsonText) and value.payload=={'value':expected} and not e.approximate


@pytest.mark.parametrize('direction',['serialize','deserialize'])
def test_getter_rename_is_shared_by_the_unannotated_setter(tmp_path,direction):
    bean='''class Item{private String value="seed";@JsonProperty("external") public String getValue(){return value;}
      public void setValue(String input){value=input+"!";}}'''
    body=('return new ObjectMapper().writeValueAsString(new Item());' if direction=='serialize' else
          'return new ObjectMapper().readValue('+input_json({'external':'new'})+',Item.class).getValue();')
    p,e,ids=fixture(tmp_path,bean,body);value=e.run(ids['Api.entry'],{})
    assert not e.approximate
    if direction=='serialize':assert isinstance(value,JsonText) and value.payload=={'external':'seed'}
    else:
        assert value=='new!'
        assert any(k=='executes' and target==ids['Item.setValue'] for _,k,target in e.edges)


def test_annotated_nonbean_methods_merge_by_explicit_wire_name(tmp_path):
    bean='''class Item{private String stored="seed";
      @JsonProperty("wire")private String expose(){return stored;}
      @JsonProperty("wire")private void accept(String value){stored=value+"!";}}'''
    p,e,ids=fixture(tmp_path,bean,'return new ObjectMapper().writeValueAsString('
        'new ObjectMapper().readValue('+input_json({'wire':'new'})+',Item.class));')
    value=e.run(ids['Api.entry'],{})
    assert isinstance(value,JsonText) and value.payload=={'wire':'new!'} and not e.approximate
    assert any(k=='executes' and target==ids['Item.accept'] for _,k,target in e.edges)


def test_split_ignore_getter_and_explicit_setter_is_write_only(tmp_path):
    bean='''class Item{public String marker="shown";private String name="seed";
      @JsonIgnore public String getName(){throw new IllegalStateException();}
      @JsonProperty public void setName(String value){name=value+"!";}String raw(){return name;}}'''
    p,e,ids=fixture(tmp_path,bean,'return new ObjectMapper().readValue('+input_json({'name':'new'})+',Item.class).raw();')
    assert e.run(ids['Api.entry'],{})=='new!' and not e.approximate
    p,e,ids=fixture(tmp_path/'serialize',bean);value=e.run(ids['Api.entry'],{})
    assert isinstance(value,JsonText) and value.payload=={'marker':'shown'} and not e.approximate


def test_lombok_read_only_does_not_disable_the_java_generated_setter(tmp_path):
    bean='''import lombok.Data;import lombok.NoArgsConstructor;
      @Data @NoArgsConstructor class Item{@JsonProperty(access=Access.READ_ONLY)private int value=7;}'''
    p,e,ids=fixture(tmp_path,bean,'Item item=new ObjectMapper().readValue('+input_json({'value':99})+',Item.class);'
        'item.setValue(8);return new ObjectMapper().writeValueAsString(item);')
    value=e.run(ids['Api.entry'],{})
    assert isinstance(value,JsonText) and value.payload=={'value':8} and not e.approximate
    assert ('setValue',1) in plan(p,e,'serialize')['generated_accessors']


def test_access_annotation_priority_depends_on_direction(tmp_path):
    bean='''class Base{@JsonProperty(access=Access.READ_ONLY)protected int value=3;}
      class Item extends Base{@JsonProperty(access=Access.READ_WRITE)public int getValue(){return value+1;}}'''
    p,e,ids=fixture(tmp_path,bean,'return new ObjectMapper().writeValueAsString('
        'new ObjectMapper().readValue('+input_json({'value':99})+',Item.class));')
    value=e.run(ids['Api.entry'],{})
    assert isinstance(value,JsonText) and value.payload=={'value':4} and not e.approximate


def test_read_only_collection_does_not_invoke_getter_only_mutation(tmp_path):
    bean='''class Item{private List<String> tags;public Item(){tags=new ArrayList<>();}
      @JsonProperty(access=Access.READ_ONLY)public List<String> getTags(){return tags;}int size(){return tags.size();}}'''
    p,e,ids=fixture(tmp_path,bean,'return new ObjectMapper().readValue('+input_json({'tags':['incoming']})+',Item.class).size();')
    assert e.run(ids['Api.entry'],{})==0 and not e.approximate
    assert not any(c['method']==ids['Item.getTags'] for c in e.semantic_callbacks)


@pytest.mark.parametrize('field',[
    '@JsonProperty("внешнее") private String local="shown";',
    '@JsonProperty("external") private transient String local="shown";'])
def test_literal_wire_names_and_explicit_transient_inclusion(tmp_path,field):
    p,e,ids=fixture(tmp_path,'class Item{'+field+'}');value=e.run(ids['Api.entry'],{})
    expected='внешнее' if 'внешнее' in field else 'external'
    assert isinstance(value,JsonText) and value.payload=={expected:'shown'} and not e.approximate


def test_source_annotation_namesake_cannot_expose_private_field(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import com.fasterxml.jackson.databind.ObjectMapper;
      @interface JsonProperty{String value()default "";}
      class Item{@JsonProperty("external")private String local="hidden";public String marker="shown";}
      class Api{Object entry(){return new ObjectMapper().writeValueAsString(new Item());}}'''})
    e=Engine(p,ScenarioState(db));value=e.run(ids['Api.entry'],{})
    assert isinstance(value,JsonText) and value.payload=={'marker':'shown'} and not e.approximate


@pytest.mark.parametrize('bean',[
    'class Item{static final String NAME="wire";@JsonProperty(NAME)public String value;}',
    'class Item{@JsonProperty(index=2)public String value;}',
    'class Item{@JsonProperty(value="wire",access=Access.READ_ONLY)public String value;}',
    'class Item{public String marker;@com.fasterxml.jackson.annotation.JsonCreator Item(@JsonProperty("value")String value){}}',
])
def test_unmodeled_property_policies_do_not_silently_become_default_fields(tmp_path,bean):
    p,e,ids=fixture(tmp_path,bean)
    result=plan(p,e,'deserialize')
    assert not result['complete'] and result['issues']
