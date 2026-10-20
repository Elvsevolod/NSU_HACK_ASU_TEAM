import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from builders import build


SOURCE='''import java.util.*;class Api{
 String entry(){Map<String,List<String>> groups=new HashMap<>();
 groups.put("hardware",Arrays.asList("SKU7"));groups.put("office",Arrays.asList("SKU8"));groups.put("garden",Arrays.asList("SKU9"));
 Map<String,String> catalog=new HashMap<>();catalog.put("hardware","active");catalog.put("office","active");catalog.put("garden","active");
 List<String> items=new ArrayList<>(Arrays.asList("SKU7","SKU8","SKU9"));
 for(Map.Entry<String,List<String>> entry:groups.entrySet()){
   String category=entry.getKey();if(catalog.get(category)==null){items.removeAll(entry.getValue());}}
 return items.get(1);}}'''


@pytest.mark.parametrize('limit',[1,4,8])
def test_pure_false_guards_keep_membership_without_order_choices(tmp_path,limit):
    p,db,ids=build(tmp_path,{'Api.java':SOURCE})
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=limit)
    assert len(paths)==1 and paths[0]['result']=='SKU8'
    assert paths[0]['engine'].outcome=='returned' and not paths[0]['engine'].approximate
    assert any(e.get('model_version')=='native-map-noop/1' for e in paths[0]['engine'].effect_events)


def test_entry_value_null_checks_are_supported_without_calling_source(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{int entry(){
      Map<String,String> lookup=new HashMap<>();lookup.put("SKU7","active");lookup.put("SKU8","active");int count=2;
      for(Map.Entry<String,String> entry:lookup.entrySet()){if(entry.getValue()==null){count--;}}
      return count;}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{})==2 and not e.approximate


@pytest.mark.parametrize('body',[
    'return entry.getKey();',
    'String key=entry.getKey();if(key!=null){return key;}',
    'alias.clear();',
])
def test_observable_order_or_alias_writes_do_not_get_noop_summary(tmp_path,body):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{String entry(){
      Map<String,String> values=new HashMap<>();values.put("A","ready");values.put("B","ready");Map<String,String> alias=values;
      for(Map.Entry<String,String> entry:values.entrySet()){'''+body+'''}return "after";}}'''})
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=8)
    assert all(not any(event.get('model_version')=='native-map-noop/1' for event in row['engine'].effect_events) for row in paths)
    if body.startswith('return'):assert {row['result'] for row in paths}=={'A','B'}
    if body.startswith('alias'):assert any(row['engine'].outcome=='uncaught application exception' for row in paths)


def test_false_source_callback_is_still_executed_and_exported(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{
      boolean absent(String key){return false;}int entry(){Map<String,String> values=new HashMap<>();
       values.put("A","ready");values.put("B","ready");int count=2;
       for(String key:values.keySet()){if(absent(key)){count--;}}return count;}}'''})
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=8)
    assert all(row['result']==2 and ('','executes',ids['Api.absent']) in row['engine'].edges for row in paths)
    assert all(not any(event.get('model_version')=='native-map-noop/1' for event in row['engine'].effect_events) for row in paths)


def test_null_receiver_throw_is_not_eliminated(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{String entry(){
      Map<String,String> values=new HashMap<>();values.put("A",null);values.put("B",null);
      try{for(String key:values.keySet()){if(values.get(key).isEmpty()){return "bad";}}}
      catch(NullPointerException failure){return "failed";}return "after";}}'''})
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=8)
    assert all(row['result']=='failed' for row in paths)
    assert all(not any(event.get('model_version')=='native-map-noop/1' for event in row['engine'].effect_events) for row in paths)


def test_unknown_predicate_does_not_get_false_guard_proof(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import java.util.*;class Api{int entry(String missing){
      Map<String,String> values=new HashMap<>();values.put("A",missing);values.put("B",missing);int count=2;
      for(String key:values.keySet()){if(values.get(key)==null){count--;}}return count;}}'''})
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{'missing':U},limit=1)
    assert all(not any(event.get('model_version')=='native-map-noop/1' for event in row['engine'].effect_events) for row in paths)
