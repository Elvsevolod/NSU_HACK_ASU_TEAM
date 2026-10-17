import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


@pytest.mark.parametrize('setup,stream',[
 ('List<String> keys=Arrays.asList("known");','keys.stream()'),
 ('','Arrays.asList("known").stream()'),
 ('','Arrays.asList("known").stream().map(key->key.substring(0,5))'),
])
def test_stream_element_contract_types_an_implicit_lambda_parameter(tmp_path,setup,stream):
    source='''import java.util.*;import java.util.stream.Collectors;class Api {Object entry(){Map map=new HashMap();'''+setup+stream+'''.map(key->{map.put(key,"found");return key;}).collect(Collectors.toList());return map.get("known");}}'''
    project,db,ids=build(tmp_path,{'Api.java':source})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='found'


def test_implicit_source_receiver_parameter_keeps_getter_return_type(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import java.util.stream.Collectors;
      class Item {String getKey(){return "known";}}class Api {Object entry(){Map map=new HashMap();
      List<Item> items=Arrays.asList(new Item());items.stream().map(item->{map.put(item.getKey(),"found");return item;})
      .collect(Collectors.toList());return map.get("known");}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='found'


def test_raw_or_object_element_contract_does_not_guess_boxed_numeric_type(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import java.util.stream.Collectors;
      class Api {Object entry(List<Object> input){Map map=new HashMap();input.stream().map(key->{
      map.put(key,"found");return key;}).collect(Collectors.toList());return map.get(1L);}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{'input':[1]}) is U
    assert engine.operation_issues[('unsupported_map_key','put')]


def test_different_boxed_return_types_do_not_become_a_fabricated_long_key(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import java.util.stream.Collectors;
      class Api {Object entry(){Map map=new HashMap();Arrays.asList("seed").stream()
      .map(key->{if(true){return 1;}return 2L;}).map(key->{map.put(key,"found");return key;})
      .collect(Collectors.toList());return map.get(1L);}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{}) is U
    assert engine.operation_issues[('unsupported_map_key','put')]
