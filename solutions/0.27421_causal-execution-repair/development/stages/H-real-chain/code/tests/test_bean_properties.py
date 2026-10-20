"""Bean discovery is independently checked before any callback execution."""
import pytest
from analyzer.bean_properties import default_bean_plan
from analyzer.engine import Engine
from analyzer.state import ScenarioState
from builders import build


def plan(tmp_path,source,direction='serialize',owner='Item'):
    p,db,ids=build(tmp_path,{'Api.java':source+'class Api{void entry(){}}'})
    e=Engine(p,ScenarioState(db))
    return default_bean_plan(p,'type:service:'+owner,direction,e.standard_type),ids


def test_computed_getter_beats_the_public_field(tmp_path):
    result,ids=plan(tmp_path,'class Item{public int value;public int getValue(){return 2;}}')
    assert result['complete'] and result['properties']['value']['member']==ids['Item.getValue']


def test_private_and_transient_fields_are_not_default_wire_properties(tmp_path):
    result,_=plan(tmp_path,'class Item{private int hidden;public transient int cache;public int shown;}')
    assert result['complete'] and set(result['properties'])=={'shown'}


@pytest.mark.parametrize('access',['private','protected','public',''])
def test_default_setter_visibility_is_any_and_return_type_need_not_be_void(tmp_path,access):
    result,ids=plan(tmp_path,'class Item{private String value;'+access+' int setValue(String input){value=input;return 4;}}','deserialize')
    assert result['complete'] and result['properties']['value']['member']==ids['Item.setValue']
    assert result['properties']['value']['type']=='String'


def test_same_named_private_field_can_be_inferred_from_a_visible_getter(tmp_path):
    result,_=plan(tmp_path,'class Item{private String name;public String getName(){return name;}}','deserialize')
    assert result['complete'] and result['properties']['name']['kind']=='field'


def test_readonly_computed_scalar_getter_is_not_a_writable_field(tmp_path):
    result,_=plan(tmp_path,'class Item{public String getName(){return "x";}}','deserialize')
    assert result['complete'] and result['properties']=={}


def test_boolean_source_namesake_is_not_a_native_is_getter(tmp_path):
    result,_=plan(tmp_path,'class Boolean{}class Item{public int visible;public Boolean isReady(){return null;}}')
    assert result['complete'] and set(result['properties'])=={'visible'}


def test_native_void_getter_is_skipped_but_source_namesake_is_a_property(tmp_path):
    result,_=plan(tmp_path/'native','class Item{public java.lang.Void getValue(){return null;}}')
    assert result['complete'] and result['properties']=={}
    result,_=plan(tmp_path/'source','class Void{}class Item{public Void getValue(){return null;}}')
    assert result['complete'] and 'value' in result['properties']


@pytest.mark.parametrize('method,wire',[('getURL','url'),('getURLValue','urlvalue'),('getvalue','value'),('get_value','_value')])
def test_default_legacy_names_differ_from_standard_introspector(tmp_path,method,wire):
    result,_=plan(tmp_path,'class Item{public String '+method+'(){return "x";}}')
    assert result['complete'] and set(result['properties'])=={wire}


def test_inherited_accessors_merge_and_a_nearer_getter_wins(tmp_path):
    source='class Base{public String getName(){return "base";}}class Item extends Base{public String getName(){return "child";}private void setName(String v){}}'
    result,ids=plan(tmp_path/'read',source)
    assert result['complete'] and result['properties']['name']['member']==ids['Item.getName']
    result,ids=plan(tmp_path/'write',source,'deserialize')
    assert result['complete'] and result['properties']['name']['member']==ids['Item.setName']


def test_regular_getter_beats_is_getter_at_same_depth(tmp_path):
    result,ids=plan(tmp_path,'class Item{public boolean getReady(){return false;}public boolean isReady(){return true;}}')
    assert result['complete'] and result['properties']['ready']['member']==ids['Item.getReady']


def test_overloaded_setter_selection_is_diagnosed_instead_of_guessed(tmp_path):
    result,_=plan(tmp_path,'class Item{public void setValue(String v){}public void setValue(int v){}}','deserialize')
    assert not result['complete'] and any('selection' in x for x in result['issues'])


@pytest.mark.parametrize('source,kind',[
    ('class Item{public int value;}','implicit'),
    ('class Item{private Item(){}public int value;}','source'),
    ('class Item{public Item(String value){}public int value;}','missing'),
])
def test_default_constructor_selection_is_source_derived(tmp_path,source,kind):
    result,_=plan(tmp_path,source,'deserialize')
    assert result['complete'] and result['constructor']['kind']==kind


def test_source_annotation_named_data_does_not_generate_lombok_methods(tmp_path):
    result,_=plan(tmp_path,'@interface Data{}@Data class Item{private String name;}')
    assert result['complete'] and result['properties']=={}


def test_default_lombok_uses_the_actual_boolean_backing_field(tmp_path):
    result,_=plan(tmp_path,'import lombok.Data;@Data class Item{private boolean isReady;private String name;}','deserialize')
    assert result['complete'] and result['constructor']['kind']=='generated'
    assert result['properties']['ready']['member']=='isReady' and result['properties']['ready']['kind']=='generated'


def test_lombok_explicit_method_suppression_retains_source_behavior(tmp_path):
    result,ids=plan(tmp_path,'import lombok.Data;@Data class Item{private String name;public String getName(){return "explicit";}}')
    assert result['complete'] and result['properties']['name']['member']==ids['Item.getName']


def test_lombok_required_fields_do_not_create_an_invented_noarg_constructor(tmp_path):
    result,_=plan(tmp_path,'import lombok.Data;@Data class Item{private final String name;}','deserialize')
    assert result['complete'] and result['constructor']['kind']=='missing'


def test_transient_lombok_field_still_has_a_generated_getter(tmp_path):
    result,_=plan(tmp_path,'import lombok.Data;@Data class Item{private transient String name;}')
    assert result['complete'] and result['properties']['name']['kind']=='generated'


def test_lombok_accessors_and_observed_config_have_explicit_boundaries(tmp_path):
    result,_=plan(tmp_path/'accessors','import lombok.Data;import lombok.experimental.Accessors;@Data @Accessors(fluent=true) class Item{private String name;}')
    assert not result['complete'] and any('Accessors' in x for x in result['issues'])
    root=tmp_path/'config';root.mkdir();(root/'lombok.config').write_text('lombok.accessors.fluent = true\n')
    result,_=plan(root,'import lombok.Data;@Data class Item{private String name;}')
    assert not result['complete'] and any('lombok.config' in x for x in result['issues'])


def test_value_fields_are_final_unless_native_nonfinal_overrides_generation(tmp_path):
    result,_=plan(tmp_path/'final','import lombok.Value;import lombok.Setter;@Value class Item{@Setter String name;}','deserialize')
    assert result['complete'] and result['constructor']['kind']=='missing'
    assert 'setName' not in {key[0] for key in result['generated_accessors']}
    result,_=plan(tmp_path/'mutable','import lombok.Value;import lombok.Setter;import lombok.experimental.NonFinal;'
        '@Value class Item{@Setter @NonFinal String name;}','deserialize')
    assert result['complete'] and ('setName',1) in result['generated_accessors']


@pytest.mark.parametrize('method,complete',[('public boolean getReady(){return false;}',True),('public boolean isReady(String... ignored){return false;}',False)])
def test_boolean_getter_alternate_names_and_varargs_suppress_generation(tmp_path,method,complete):
    result,_=plan(tmp_path,'import lombok.Data;@Data class Item{private boolean isReady;'+method+'}')
    assert result['complete'] is complete and ('isReady',0) not in result['generated_accessors']
    if not complete:assert any('source body is unavailable' in issue for issue in result['issues'])


def test_source_collection_namesake_is_not_a_getter_only_native_collection(tmp_path):
    result,_=plan(tmp_path,'class List{}class Item{public List getNames(){return null;}}','deserialize')
    assert result['complete'] and result['properties']=={}


def test_hidden_fields_are_diagnosed_instead_of_flattening_the_two_storage_slots(tmp_path):
    result,_=plan(tmp_path,'class Base{protected String name="base";public String getName(){return name;}}'
        'class Item extends Base{private String name="child";}')
    assert not result['complete'] and any('hidden Java fields' in issue for issue in result['issues'])
