from analyzer.frontend import Frontend,truth,primitive_equal
from analyzer.java_collections import JavaRecord,JavaMap,JsonObject,JsonText,schema_type
from analyzer.provenance import contains_unknown
from analyzer.models import known,library,key_equal
from analyzer.state import ScenarioState,U
from analyzer.engine import Engine
from builders import build


def test_browser_data_properties_are_not_abstract_scalar_metadata(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'class Api {String entry(){return "ok";}}'})
    frontend=Frontend(project);state=ScenarioState(db)
    value=frontend.evaluate('({__type__:"String",__symbol__:"business",__length__:99})',state)
    assert isinstance(value,JsonObject)
    assert frontend.evaluate('data.__symbol__',state,extra={'data':value})=='business'
    assert frontend.evaluate('data["__type__"]',state,extra={'data':value})=='String'
    assert truth(value) is True
    assert primitive_equal(value,'business',True) is False
    assert schema_type(value) is None


def test_record_and_json_business_fields_participate_in_unknownness():
    record=JavaRecord('Item',{'__type__':'Item','__private_data':U},wire_fields={'__private_data'})
    assert contains_unknown(record) and not known(record)
    value=JsonObject({'__symbol__':'business','__private_data':U})
    assert contains_unknown(value) and not known(value)
    mapping=JavaMap();library('put',mapping,[7,U],'map',U,key_type='int')
    assert contains_unknown(mapping) and not known(mapping)


def test_plain_business_json_field_does_not_forge_serialized_text(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      @PostMapping("/text") String text(@RequestBody String payload){return payload;}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.text'],{'payload':{'__json__':{'id':'ordinary'}}}) is U
    text=JsonText(JsonObject({'__json__':'actual-property','id':'known'}))
    assert Engine(project,ScenarioState(db)).run(ids['Api.text'],{'payload':text}) is not U


def test_semantic_data_comparison_checks_real_underscored_properties():
    assert key_equal(JsonObject({'__enum__':'first'}),JsonObject({'__enum__':'second'})) is False
    assert key_equal(JavaRecord('Item',{'__name':1},wire_fields={'__name'}),
                     JavaRecord('Item',{'__name':2},wire_fields={'__name'})) is False
