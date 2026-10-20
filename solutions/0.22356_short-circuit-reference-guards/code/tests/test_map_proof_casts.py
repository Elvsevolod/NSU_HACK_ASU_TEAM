import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState
from builders import build


@pytest.mark.parametrize('proof_enabled', [True, False])
def test_array_in_polluted_map_cannot_skip_required_cast(tmp_path, monkeypatch, proof_enabled):
    import analyzer.map_loop_proof as proof
    if not proof_enabled:
        monkeypatch.setattr(proof, 'prove', lambda *args: False)
    p, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;class Api{
      void touch(){throw new IllegalStateException();}
      String entry(){Map raw=new HashMap();raw.put("x","v".split(","));
        Map<String,List<String>> typed=raw;
        try{for(Map.Entry<String,List<String>> entry:typed.entrySet()){
          List<String> values=entry.getValue();if(values==null){touch();}}}
        catch(ClassCastException failure){return "cast";}return "after";}}'''})
    engine = Engine(p, ScenarioState(db))
    assert engine.run(ids['Api.entry'], {}) == 'cast'
    assert ('', 'executes', ids['Api.touch']) not in engine.edges
    assert not any(event.get('model_version') == 'native-map-noop/1' for event in engine.effect_events)


@pytest.mark.parametrize('declared, actual, result', [
    ('Collection<String>', 'new HashSet<String>()', 'after'),
    ('List<String>', 'new HashSet<String>()', 'cast'),
    ('List<String>', 'new ArrayList<String>()', 'after'),
    ('Collection<String>', 'null', 'null'),
])
def test_pure_proof_and_ordinary_reference_cast_agree(tmp_path, monkeypatch, declared, actual, result):
    import analyzer.map_loop_proof as proof
    outcomes = []
    original = proof.prove
    for enabled in (True, False):
        monkeypatch.setattr(proof, 'prove', original if enabled else lambda *args: False)
        source = '''import java.util.*;class Api{String entry(){Map raw=new HashMap();raw.put("x",''' + actual + ''');
          Map<String,''' + declared + '''> typed=raw;String answer="after";
          try{for(Map.Entry<String,''' + declared + '''> entry:typed.entrySet()){
             ''' + declared + ''' values=entry.getValue();if(values==null){return "null";}}}
          catch(ClassCastException failure){return "cast";}return answer;}}'''
        p, db, ids = build(tmp_path / str(enabled), {'Api.java': source})
        engine = Engine(p, ScenarioState(db))
        observed = engine.run(ids['Api.entry'], {})
        assert observed == result
        outcomes.append((observed, engine.outcome, engine.edges, engine.state.database.tables))
    assert outcomes[0] == outcomes[1]


def test_set_collection_false_guard_proof_is_side_effect_free(tmp_path):
    p, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;class Api{int entry(){
      Map<String,Collection<String>> values=new HashMap<>();values.put("x",new HashSet<String>());
      for(Map.Entry<String,Collection<String>> entry:values.entrySet()){
        Collection<String> group=entry.getValue();if(group==null){return 1;}}
      return values.size();}}'''})
    engine = Engine(p, ScenarioState(db))
    assert engine.run(ids['Api.entry'], {}) == 1
    assert any(event.get('model_version') == 'native-map-noop/1' for event in engine.effect_events)
