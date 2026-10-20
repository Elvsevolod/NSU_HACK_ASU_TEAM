from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def test_joined_map_aliases_share_later_writes(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{Object entry(boolean flag){
      Map map=new HashMap();Map alias=map;if(flag){map.put("key","same");}else{map.put("key","same");}
      alias.put("later","visible");return map.get("later");}}'''})
    assert Engine(project,ScenarioState(db),conservative=True).run(ids['Api.entry'],{'flag':U})=='visible'


def test_joined_map_writes_are_visible_to_the_caller(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{Object entry(boolean flag){
      Map map=new HashMap();update(map,flag);return map.get("key");}
      void update(Map input,boolean flag){if(flag){input.put("key","same");}else{input.put("key","same");}}}'''})
    assert Engine(project,ScenarioState(db),conservative=True).run(ids['Api.entry'],{'flag':U})=='same'


def test_original_map_mutation_survives_reassigning_a_local_parameter(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{Object entry(boolean flag){
      Map map=new HashMap();update(map,flag);return map.get("key");}
      void update(Map input,boolean flag){if(flag){input.put("key","same");input=new HashMap();}
      else{input.put("key","same");input=new HashMap();}}}'''})
    assert Engine(project,ScenarioState(db),conservative=True).run(ids['Api.entry'],{'flag':U})=='same'


def test_caller_observes_agreed_source_object_field_writes(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Item{String value="old";}
      class Api{Object entry(boolean flag){Item item=new Item();update(item,flag);return item.value;}
      void update(Item item,boolean flag){if(flag){item.value="same";}else{item.value="same";}}}'''})
    assert Engine(project,ScenarioState(db),conservative=True).run(ids['Api.entry'],{'flag':U})=='same'


def test_conditional_alias_is_widened_before_a_later_mutation(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{Object entry(boolean flag){
      Map original=new HashMap();original.put("key","same");Map chosen=original;
      if(flag){chosen=new HashMap();chosen.put("key","same");}chosen.clear();return original.isEmpty();}}'''})
    engine=Engine(project,ScenarioState(db),conservative=True)
    assert engine.run(ids['Api.entry'],{'flag':U}) is U
    assert engine.approximate


def test_captured_map_alias_survives_join_and_later_callback(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import java.util.function.Function;import java.util.stream.Collectors;
      class Api{Object entry(boolean flag){Map data=new HashMap();Function<String,String> writer=key->{data.put(key,"visible");return key;};
      Function<String,String> alias=writer;if(flag){data.put("before","same");}else{data.put("before","same");}
      Arrays.asList("later").stream().map(alias).collect(Collectors.toList());return data.get("later");}}'''})
    assert Engine(project,ScenarioState(db),conservative=True).run(ids['Api.entry'],{'flag':U})=='visible'


def test_alias_widening_includes_source_fields_excluded_from_json(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import com.fasterxml.jackson.annotation.JsonIgnore;
      class Item{@JsonIgnore String secret="old";}
      class Api{Object entry(boolean flag){Item original=new Item();Item chosen=original;
      if(flag){chosen=new Item();}chosen.secret="changed";return original.secret;}}'''})
    engine=Engine(project,ScenarioState(db),conservative=True)
    assert engine.run(ids['Api.entry'],{'flag':U}) is U
    assert engine.approximate
