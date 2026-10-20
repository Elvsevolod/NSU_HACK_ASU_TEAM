from analyzer.engine import Engine
from analyzer.frontend import Frontend
from analyzer.models import construct, library, wire,known,key_equal
from analyzer.state import ScenarioState, U
from test_script_state import fixture, parameters
from builders import build
import pytest


def test_a_java_map_has_a_plain_json_view_at_the_browser_boundary(tmp_path):
    frontend,site,state,grounder,contract=fixture(tmp_path,callback='cachedItems=reply.batches;')
    _,mapping=construct('java.util.HashMap',[],U)
    library('put',mapping,['batches',[{'__type__':'Item','id':'from-map'}]],'mapping',U)
    frontend.apply_response(site,mapping,state)
    assert parameters(grounder,state,contract)['selectedId']=='from-map'


def test_internal_map_serialization_does_not_unwrap_an_ordinary_business_field():
    _,mapping=construct('java.util.HashMap',[],U)
    library('put',mapping,['part','real-value'],'mapping',U)
    assert wire(mapping)=={'part':'real-value'}
    business={'__type__':'DomainEnvelope','__map__':{'part':'ordinary-field'}}
    assert wire(business)==business
    handled,value=library('get',business,['part'],'envelope',U)
    assert not handled and value is U


def test_map_copy_constructor_preserves_the_source_mappings():
    _,original=construct('java.util.HashMap',[],U)
    library('put',original,['label','first'],'original',U)
    _,copied=construct('java.util.HashMap',[original],U)
    assert library('get',copied,['label'],'copied',U)==(True,'first')
    library('put',copied,['label','replacement'],'copied',U)
    assert library('get',original,['label'],'original',U)==(True,'first')


def test_a_map_received_as_map_class_retains_java_map_operations(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {@GetMapping("/flags") Map flags(){
        Map data=new HashMap();data.put("mode","ready");return data;}}
      class Caller {RestTemplate rest;String entry(){
        Map result=rest.getForObject("http://service/flags",Map.class);
        return (String)result.get("mode");}}
      '''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='ready'


def test_non_string_keys_are_not_silently_conflated_with_string_keys(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {String entry(){Map data=new HashMap();
        data.put(1,"integer");data.put("1","string");
        return (String)data.get(1);}}
      '''})
    engine=Engine(project,ScenarioState(db));value=engine.run(ids['Api.entry'],{})
    assert value in ('integer',U)
    if value is U:
        assert any('map' in warning.lower() for warning in engine.warnings)


def test_null_value_and_absent_key_stay_distinguishable():
    _,mapping=construct('java.util.HashMap',[],U)
    library('put',mapping,['present',None],'mapping',U)
    assert library('get',mapping,['present'],'mapping',U)==(True,None)
    assert library('get',mapping,['absent'],'mapping',U)==(True,None)
    assert library('containsKey',mapping,['present'],'mapping',U)==(True,True)
    assert library('containsKey',mapping,['absent'],'mapping',U)==(True,False)
    assert wire(mapping)=={'present':None}


def test_copy_constructor_shares_nested_values_but_not_top_level_mappings():
    _,original=construct('java.util.HashMap',[],U)
    rows=['first'];library('put',original,['rows',rows],'original',U)
    _,copied=construct('java.util.HashMap',[original],U)
    rows.append('second')
    assert library('get',copied,['rows'],'copied',U)[1] is rows
    library('put',copied,['extra','copy-only'],'copied',U)
    assert library('containsKey',original,['extra'],'original',U)==(True,False)


def test_nested_raw_map_response_retains_inner_java_operations(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {@GetMapping("/nested") Map nested(){
        Map inner=new HashMap();inner.put("mode","ready");
        Map outer=new HashMap();outer.put("inner",inner);return outer;}}
      class Caller {RestTemplate rest;String entry(){
        Map outer=rest.getForObject("http://service/nested",Map.class);
        return (String)((Map)outer.get("inner")).get("mode");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Caller.entry'],{})=='ready'


def test_cyclic_http_map_stops_default_client_and_selects_server_error_catch(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {@GetMapping("/cycle") Map cycle(){
        Map data=new HashMap();data.put("self",data);return data;}}
      class Caller {RestTemplate rest;String entry(){try{
        rest.getForObject("http://service/cycle",Map.class);return after();
        }catch(HttpServerErrorException failure){return rejected();}}
        String after(){return "wrong";}String rejected(){return "rejected";}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='rejected'
    assert ids['Caller.after'] not in {target for _,relation,target in engine.edges if relation=='executes'}
    assert any('cyclic' in warning for warning in engine.warnings)


def test_cycle_does_not_run_a_browser_success_callback(tmp_path):
    frontend,site,state,grounder,contract=fixture(tmp_path,initializer='[{id:"old"}]')
    _,mapping=construct('java.util.HashMap',[],U)
    library('put',mapping,['self',mapping],'mapping',U)
    frontend.apply_response(site,mapping,state)
    assert parameters(grounder,state,contract)['selectedId']=='old'
    assert any('success callback not executed' in warning for warning in state.limitations)


def test_mapping_contents_participate_in_knownness_and_equality():
    _,left=construct('java.util.HashMap',[],U)
    _,right=construct('java.util.HashMap',[],U)
    library('put',left,['__business_key__','left'],'left',U)
    library('put',right,['__business_key__','right'],'right',U)
    assert key_equal(left,right) is False
    library('put',right,['__business_key__',U],'right',U)
    assert not known(right)
    assert key_equal(left,right) is U
    library('put',left,['self',left],'left',U)
    assert not known(left)


def test_ordinary_business_field_does_not_create_a_java_map_type():
    value={'__type__':'Envelope','__map__':{'mode':'business-data'}}
    assert library('get',value,['mode'],'value',U)==(False,U)
    assert wire(value)==value


def test_an_imported_unresolved_namesake_is_not_a_native_java_map(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import external.library.HashMap;
      class Api {Object entry(){HashMap map=new HashMap();map.put("key","wrong-model");
        return map.get("key");}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{}) is U
    assert engine.warnings


@pytest.mark.parametrize('argument,caught',[('-1','IllegalArgumentException'),('(Map)null','NullPointerException')])
def test_guaranteed_map_constructor_failure_skips_following_call(tmp_path,argument,caught):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;
      class Api {String entry(){try{new HashMap('''+argument+''');return after();}
        catch('''+caught+''' failure){return "rejected";}}
        String after(){return "wrong";}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})=='rejected'
    assert ids['Api.after'] not in {target for _,relation,target in engine.edges if relation=='executes'}


def test_basic_map_updates_and_default_lookup_preserve_null_vs_absent():
    _,original=construct('java.util.HashMap',[],U)
    library('put',original,['present',None],'map',U)
    assert library('getOrDefault',original,['present','fallback'],'map',U)==(True,None)
    assert library('getOrDefault',original,['absent','fallback'],'map',U)==(True,'fallback')
    _,copied=construct('java.util.HashMap',[],U)
    assert library('putAll',copied,[original],'map',U)==(True,None)
    assert library('containsKey',copied,['present'],'map',U)==(True,True)
    assert library('remove',copied,['present'],'map',U)==(True,None)
    assert library('containsKey',copied,['present'],'map',U)==(True,False)
    library('put',copied,['more','value'],'map',U)
    assert library('clear',copied,[],'map',U)==(True,None)
    assert library('isEmpty',copied,[],'map',U)==(True,True)
