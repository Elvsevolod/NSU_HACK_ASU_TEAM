"""A finite Java integral identity survives decimal wire text and Spring binding.

Independent obligations: JLS integral ranges, Java canonical decimal String
conversion, Spring's default String-to-number converters. No target IDs/fields.
"""
import pytest
from builders import build
from analyzer.engine import Engine
from analyzer.request import grounded_request, BoundParameters, wire_text
from analyzer.state import ScenarioState,U
from analyzer.java_collections import JsonObject


def fixture(root,typ='Long',annotation='PathVariable',extra=''):
    route='/items/{id}' if annotation=='PathVariable' else '/items'
    source='''import org.springframework.web.bind.annotation.*;
      @RestController class Api{@GetMapping("'''+route+'''") '''+typ+''' read(@'''+annotation+''' '''+typ+''' id){return id;}}'''+extra
    return build(root,{'Api.java':source})


@pytest.mark.parametrize('typ',['Long','long','Integer','int','Short','short','Byte','byte'])
@pytest.mark.parametrize('annotation',['PathVariable','RequestParam','RequestHeader'])
def test_same_width_integral_round_trip_preserves_the_original_native_value(tmp_path,typ,annotation):
    p,db,ids=fixture(tmp_path,typ,annotation);state=ScenarioState(db)
    original=state.generated_value(typ,'independent finite integral input')
    request=grounded_request(p,ids['Api.read'],{'id':original})
    text=wire_text(original)
    assert text['__type__']=='String' and text['__integral_origin__']==original
    e=Engine(p,state);actual=e.run(ids['Api.read'],BoundParameters({'id':original},request))
    assert actual==original and not e.approximate
    assert e.request_events[0]['bound_arguments'][0]['value']==original
    assert e.request_events[0]['bound_arguments'][0]['native_kind']=={'long':'Long','int':'Integer','short':'Short','byte':'Byte'}.get(typ,typ)


@pytest.mark.parametrize('value',[
    {'__symbol__':'text','__type__':'String','__constraints__':['non_null']},
    {'__symbol__':'nullable','__type__':'Long'},
    {'__symbol__':'object','__type__':'Other','__constraints__':['non_null']},
])
def test_an_arbitrary_symbol_does_not_prove_valid_decimal_text(tmp_path,value):
    p,db,ids=fixture(tmp_path);request=grounded_request(p,ids['Api.read'],{'id':value})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.read'],request) is U and e.approximate


def test_json_property_names_cannot_forge_a_native_integral(tmp_path):
    value=JsonObject({'__symbol__':'forged','__type__':'Long','__constraints__':['non_null']})
    assert wire_text(value) is U


def test_narrowing_is_not_assumed_successful(tmp_path):
    p,db,ids=fixture(tmp_path,'Integer');state=ScenarioState(db)
    original=state.generated_value('Long','finite input')
    e=Engine(p,state)
    assert e.run(ids['Api.read'],grounded_request(p,ids['Api.read'],{'id':original})) is U and e.approximate


def test_a_source_namesake_and_custom_binder_keep_the_boundary(tmp_path):
    for label,extra in [('namesake','class Long{}'),('binder','class Config{void addFormatters(){}}')]:
        p,db,ids=fixture(tmp_path/label,extra=extra);state=ScenarioState(db)
        value=state.generated_value('Long','finite input')
        e=Engine(p,state)
        assert e.run(ids['Api.read'],grounded_request(p,ids['Api.read'],{'id':value})) is U and e.approximate
