import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState
from builders import build


SOURCE='''import java.util.*;
class Plan {List<String> stations;int visits;
 Plan(List<String> input){stations=input;}List<String> stops(){return stations;}}
class Item {String origin;String destination;
 Item(String start,String end){origin=start;destination=end;}
 String from(){return origin;}String to(){return destination;}}
class Api {Object entry(){
 Map<String,List<String>> groups=new HashMap<>();groups.put("G1",Arrays.asList("A"));
 groups.put("G2",Arrays.asList("B"));groups.put("G3",Arrays.asList("C"));
 Plan shared=new Plan(Arrays.asList("North","South"));Map<String,Plan> plans=new HashMap<>();
 plans.put("G1",shared);plans.put("G2",shared);
 Map<String,Item> items=new HashMap<>();items.put("A",new Item("North","South"));
 items.put("B",new Item("North","West"));items.put("C",new Item("North","South"));
 Set<String> allowed=new HashSet<>(Arrays.asList("A","B","C"));
 for(Map.Entry<String,List<String>> entry:groups.entrySet()){
  String code=entry.getKey();
  if(plans.get(code)==null){allowed.removeAll(entry.getValue());}
  else{Plan plan=plans.get(code);for(String id:entry.getValue()){
   Item item=items.get(id);
   if(!plan.stops().contains(item.from()) || !plan.stops().contains(item.to()) ||
      plan.stops().indexOf(item.from())>=plan.stops().indexOf(item.to())){allowed.remove(id);}
  }}
 }
 return allowed;
}}'''


def certificates(engine):
    return [event for event in engine.effect_events if event.get('model_version')=='native-map-removal/1']


@pytest.mark.parametrize('limit',[1,4])
def test_known_live_filter_keeps_source_callbacks_and_membership(tmp_path,limit):
    p,db,ids=build(tmp_path,{'Api.java':SOURCE})
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=limit)
    assert len(paths)==1
    row=paths[0];engine=row['engine']
    assert list(row['result'])==['A'] and not row['result'].order_known
    assert engine.outcome=='returned' and certificates(engine)
    for method in ('Plan.stops','Item.from','Item.to'):
        assert ('','executes',ids[method]) in engine.edges
        assert (ids['Api.entry'],'calls',ids[method]) in engine.edges
    assert all(condition['value'] in (True,False) for condition in certificates(engine)[0]['guards'])


def test_representative_matches_all_small_reference_orders(tmp_path,monkeypatch):
    import analyzer.map_filter_proof as proof
    p,db,ids=build(tmp_path,{'Api.java':SOURCE})
    fast=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=1)
    monkeypatch.setattr(proof,'certify',lambda *args:False)
    slow=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=64)
    assert len(fast)==1 and len(slow)==6
    expected=fast[0]
    for row in slow:
        assert row['engine'].outcome==expected['engine'].outcome=='returned'
        assert sorted(row['result'])==sorted(expected['result'])
        assert row['result'].kinds==expected['result'].kinds
        assert row['engine'].edges==expected['engine'].edges
        assert row['state'].database.unknown_tables==expected['state'].database.unknown_tables


def test_all_present_valid_members_are_retained(tmp_path):
    source=SOURCE.replace('plans.put("G2",shared);','plans.put("G2",shared);plans.put("G3",shared);').replace(
        'new Item("North","West")','new Item("North","South")')
    p,db,ids=build(tmp_path,{'Api.java':source})
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=1)
    assert len(paths)==1 and sorted(paths[0]['result'])==['A','B','C']
    assert certificates(paths[0]['engine'])


def test_private_trial_cannot_leak_mutating_getter_effects(tmp_path):
    source=SOURCE.replace('List<String> stops(){return stations;}',
                          'List<String> stops(){visits++;return stations;}').replace('return allowed;','return shared.visits;')
    p,db,ids=build(tmp_path,{'Api.java':source})
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=64)
    assert paths and all(row['result']==6 for row in paths)
    assert all(not certificates(row['engine']) for row in paths)


@pytest.mark.parametrize('body',[
    'Set<String> alias=allowed;',
    'Map<String,Set<String>> aliases=new HashMap<>();aliases.put("saved",allowed);',
])
def test_alias_to_target_declines_commutativity_certificate(tmp_path,body):
    source=SOURCE.replace('for(Map.Entry<String,List<String>> entry:',body+'for(Map.Entry<String,List<String>> entry:')
    p,db,ids=build(tmp_path,{'Api.java':source})
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=64)
    assert paths and all(sorted(row['result'])==['A'] for row in paths)
    assert all(not certificates(row['engine']) for row in paths)


@pytest.mark.parametrize('change',[
    'allowed.removeAll(entry.getValue());throw new IllegalStateException();',
    'allowed.removeAll(entry.getValue());groups.clear();',
    'if(allowed.size()>1){allowed.removeAll(entry.getValue());}',
])
def test_throw_source_mutation_and_target_read_decline_proof(tmp_path,change):
    source=SOURCE.replace('allowed.removeAll(entry.getValue());',change)
    p,db,ids=build(tmp_path,{'Api.java':source})
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=64)
    assert paths and all(not certificates(row['engine']) for row in paths)


def test_native_nondeterministic_callback_is_outside_certificate(tmp_path):
    source=SOURCE.replace('String code=entry.getKey();',
                          'String unused=UUID.randomUUID().toString();String code=entry.getKey();')
    p,db,ids=build(tmp_path,{'Api.java':source})
    paths=run_paths(p,ScenarioState(db),ids['Api.entry'],{},limit=64)
    assert paths and all(not certificates(row['engine']) for row in paths)
