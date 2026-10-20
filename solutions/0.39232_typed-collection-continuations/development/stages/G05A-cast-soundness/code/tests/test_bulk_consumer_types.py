import pytest
from analyzer.engine import Engine
from analyzer.native_storage import JavaList
from analyzer.state import ScenarioState, U
from builders import build


@pytest.mark.parametrize('flavor', ['ArrayList', 'HashSet'])
@pytest.mark.parametrize('operation, expected', [('removeAll', ['A', 'C']), ('retainAll', ['B'])])
def test_direct_generic_read_matches_typed_local(tmp_path, flavor, operation, expected):
    results = []
    for label, prepare, operand in [('direct', '', 'groups.get("obsolete")'),
                                    ('local', 'List<String> selected=groups.get("obsolete");', 'selected')]:
        source = '''import java.util.*;class Api{Collection<String> entry(){
          Collection<String> out=new ''' + flavor + '''<>(Arrays.asList("A","B","C"));
          Map<String,List<String>> groups=new HashMap<>();groups.put("obsolete",Arrays.asList("B"));
          ''' + prepare + '''if(!out.''' + operation + '(' + operand + ''')){throw new IllegalStateException();}
          return out;}}'''
        p, db, ids = build(tmp_path / label, {'Api.java': source})
        engine = Engine(p, ScenarioState(db))
        result = engine.run(ids['Api.entry'], {})
        assert isinstance(result, JavaList) and not result.opaque
        assert sorted(result) == expected
        assert result.kinds == ['String'] * len(expected)
        assert engine.outcome == 'returned'
        results.append((sorted(result), result.flavor, result.order_known))
    assert results[0] == results[1]


@pytest.mark.parametrize('flavor', ['ArrayList', 'HashSet'])
@pytest.mark.parametrize('operation, expected', [('removeAll', True), ('retainAll', False)])
def test_bulk_self_alias_preserves_boolean_contract(tmp_path, flavor, operation, expected):
    p, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;class Api{boolean entry(){
      Collection<String> out=new ''' + flavor + '''<>(Arrays.asList("A","B"));
      boolean changed=out.''' + operation + '''(out);
      if(out.size()!=''' + ('0' if operation == 'removeAll' else '2') + '''){throw new IllegalStateException();}
      return changed;}}'''})
    assert Engine(p, ScenarioState(db)).run(ids['Api.entry'], {}) is expected


@pytest.mark.parametrize('flavor', ['ArrayList', 'HashSet'])
@pytest.mark.parametrize('operation', ['removeAll', 'retainAll'])
def test_null_bulk_operand_throws(tmp_path, flavor, operation):
    p, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;class Api{String entry(){
      Collection<String> out=new ''' + flavor + '''<>(Arrays.asList("A"));
      Map<String,List<String>> groups=new HashMap<>();
      try{out.''' + operation + '''(groups.get("missing"));}
      catch(NullPointerException failure){return "null";}return "after";}}'''})
    assert Engine(p, ScenarioState(db)).run(ids['Api.entry'], {}) == 'null'


def test_polluted_map_array_is_not_a_collection(tmp_path):
    p, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;class Api{String entry(){
      String[] invalid="B".split(",");Map raw=new HashMap();raw.put("obsolete",invalid);
      Map<String,List<String>> groups=raw;List<String> out=new ArrayList<>(Arrays.asList("A","B"));
      try{out.removeAll(groups.get("obsolete"));}
      catch(ClassCastException failure){return "cast";}return "after";}}'''})
    assert Engine(p, ScenarioState(db)).run(ids['Api.entry'], {}) == 'cast'


@pytest.mark.parametrize('constructor', ['Arrays.asList("A","B")',
    'Collections.unmodifiableList(new ArrayList<>(Arrays.asList("A","B")))'])
def test_fixed_and_unmodifiable_bulk_removal_throws(tmp_path, constructor):
    p, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;class Api{String entry(){
      List<String> out=''' + constructor + ''';Map<String,List<String>> groups=new HashMap<>();
      groups.put("obsolete",Arrays.asList("B"));try{out.removeAll(groups.get("obsolete"));}
      catch(UnsupportedOperationException failure){return "fixed";}return "after";}}'''})
    assert Engine(p, ScenarioState(db)).run(ids['Api.entry'], {}) == 'fixed'


def test_custom_namesake_uses_source_parameter_and_body(tmp_path):
    p, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;
      class Custom {boolean removeAll(List<String> values){return values.get(0).equals("B");}}
      class Api {boolean entry(){Map<String,List<String>> groups=new HashMap<>();
        groups.put("obsolete",Arrays.asList("B"));return new Custom().removeAll(groups.get("obsolete"));}}'''})
    engine = Engine(p, ScenarioState(db))
    assert engine.run(ids['Api.entry'], {}) is True
    assert ('', 'executes', ids['Custom.removeAll']) in engine.edges


def test_unknown_operand_keeps_unknown_membership(tmp_path):
    p, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;class Api{
      List<String> entry(Collection<String> selected){List<String> out=new ArrayList<>(Arrays.asList("A","B"));
        out.removeAll(selected);return out;}}'''})
    engine = Engine(p, ScenarioState(db))
    result = engine.run(ids['Api.entry'], {'selected': U})
    assert result is U or isinstance(result, JavaList) and result.opaque
    assert any('bulk' in warning for warning in engine.warnings)


def test_hashset_copy_preserves_unique_boxed_kinds_and_owns_container(tmp_path):
    p, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;class Api{int entry(){
      List<Object> values=new ArrayList<>();values.add(true);values.add(1);values.add(1L);
      values.add(null);values.add(null);values.add(1);
      Set<Object> copied=new HashSet<>(values);values.clear();return copied.size();}}'''})
    assert Engine(p, ScenarioState(db)).run(ids['Api.entry'], {}) == 4


def test_unsupported_array_allocation_remains_explicit_before_bulk(tmp_path):
    p, db, ids = build(tmp_path, {'Api.java': '''import java.util.*;class Api{Object entry(){
      Map raw=new HashMap();raw.put("obsolete",new String[]{"B"});
      Map<String,List<String>> groups=raw;List<String> out=new ArrayList<>(Arrays.asList("A","B"));
      out.removeAll(groups.get("obsolete"));return out;}}'''})
    engine = Engine(p, ScenarioState(db))
    assert engine.run(ids['Api.entry'], {}) is U
    assert engine.outcome == 'unsupported_semantics boundary'
    assert any('array_creation_expression' in warning for warning in engine.warnings)
