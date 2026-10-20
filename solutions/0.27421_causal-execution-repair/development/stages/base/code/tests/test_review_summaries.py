from analyzer.engine import Engine
from analyzer.getter_effects import footprint
from analyzer import getter_effects
from analyzer.state import ScenarioState
from analyzer.java_collections import JavaRecord
from builders import build


def test_effect_summary_has_versions_and_does_not_cache_values(tmp_path,monkeypatch):
    project,db,ids=build(tmp_path,{'Api.java':'''class Item{public int value;public int getValue(){return value;}}
      class Api{@PostMapping("/read") Item read(@RequestBody Item input){return input;}}'''})
    engine=Engine(project,ScenarioState(db));prop={'kind':'method','member':ids['Item.getValue']}
    assert footprint(engine,prop)==({'value'},set())
    first=list(project._getter_effect_summaries.values())[0]
    assert all(first[key] for key in ('source','model','config','receiver','alias_preconditions','read_state_preconditions'))
    for value in (1,2):
        assert Engine(project,ScenarioState(db)).run(ids['Api.read'],{'input':{'value':value}})['value']==value
    monkeypatch.setattr(getter_effects,'VERSION','source-getter-effects/test-new-model')
    footprint(engine,prop)
    assert len(project._getter_effect_summaries)==2


def test_reassigned_copy_is_not_proved_fresh(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;import org.springframework.beans.support.*;
      class Item{List<String> values;public List<String> getValues(){List<String> copy=new ArrayList<>(values);
        copy=values;PropertyComparator.sort(copy,new MutableSortDefinition("name",true,true));return copy;}}'''})
    assert footprint(Engine(project,ScenarioState(db)),{'kind':'method','member':ids['Item.getValues']}) is None
