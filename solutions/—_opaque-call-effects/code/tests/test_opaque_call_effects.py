"""Unknown calls cannot prove that reachable state and control stay unchanged."""
import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState, U
from analyzer.java_collections import JavaRecord
from builders import build


def outcomes(tmp_path, body, extra='', limit=16, rows=None, params=None):
    project, database, ids = build(tmp_path, {'Api.java': '''import java.util.*;
      class Item {boolean active=false;Item child;}
      interface Plugin {void mutate(Item item);}
      class Api {String entry(boolean flag,Plugin plugin){'''+body+'''}
      String yes(){return "yes";}String no(){return "no";}
      String after(){return "after";}String caught(){return "caught";}}
      '''+extra}, rows=rows)
    # A non-null interface implementation supplied by the caller, whose body is
    # outside the provided source. No uninitialised local/default-null field.
    inputs={'plugin':JavaRecord('Plugin',{'__type__':'Plugin'},wire_fields=()),**(params or {})}
    return run_paths(project, ScenarioState(database), ids['Api.entry'], inputs, limit), ids


def returned(paths):
    return {p['result'] for p in paths if p['engine'].outcome == 'returned'}


def test_external_mutation_can_change_a_previously_known_object_field(tmp_path):
    paths, _ = outcomes(tmp_path, '''Item item=new Item();vendor.Plugin.mutate(item);
      if(item.active){return yes();}return no();''')
    assert returned(paths) == {'yes', 'no'}
    assert all(p['approximate'] for p in paths)


def test_nested_object_alias_is_invalidated_before_its_parent_loses_the_field(tmp_path):
    paths, _ = outcomes(tmp_path, '''Item parent=new Item();Item alias=new Item();parent.child=alias;
      vendor.Plugin.mutate(parent);if(alias.active){return yes();}return no();''')
    assert returned(paths) == {'yes', 'no'}


def test_unknown_list_shape_is_not_a_fabricated_empty_or_singleton_list(tmp_path):
    paths, _ = outcomes(tmp_path, '''List<String> items=new ArrayList();items.add("old");
      List<String> alias=items;vendor.Plugin.mutate(items);
      if(alias.size()==1){return yes();}return no();''')
    assert returned(paths) == {'yes', 'no'}


def test_unknown_map_effect_does_not_keep_a_known_mapping(tmp_path):
    paths, _ = outcomes(tmp_path, '''Map<String,String> map=new HashMap();map.put("key","old");
      vendor.Plugin.mutate(map);if("old".equals(map.get("key"))){return yes();}return no();''')
    assert returned(paths) == {'yes', 'no'}


def test_possible_throw_can_prevent_the_following_method(tmp_path):
    paths, ids = outcomes(tmp_path, 'vendor.Plugin.run();return after();')
    throw_paths = [p for p in paths if p['engine'].outcome == 'uncaught application exception']
    assert throw_paths and any(p['result'] == 'after' for p in paths)
    assert all(ids['Api.after'] not in {t for _,k,t in p['engine'].edges if k=='executes'} for p in throw_paths)


def test_unknown_exception_can_enter_a_source_catch(tmp_path):
    paths, _ = outcomes(tmp_path, '''try{vendor.Plugin.run();return after();}
      catch(RuntimeException failure){return caught();}''')
    assert {'caught', 'after'} <= returned(paths)


def test_source_contract_without_an_implementation_has_opaque_effects(tmp_path):
    paths, _ = outcomes(tmp_path, '''Item item=new Item();
      plugin.mutate(item);if(item.active){return yes();}return no();''')
    assert returned(paths) == {'yes', 'no'}
    assert all(p['engine'].opaque_effects for p in paths)


def test_entry_with_no_source_body_models_effects_and_possible_failure(tmp_path):
    project, db, ids = build(tmp_path, {'Native.java':'class Native {native void entry();}'}, rows={'items':[{'key':'old'}]})
    paths = run_paths(project, ScenarioState(db), ids['Native.entry'], {}, 4)
    assert {'returned', 'uncaught application exception'} == {p['engine'].outcome for p in paths}
    assert all(p['engine'].opaque_effects for p in paths)
    assert all(any('no source body' in w for w in p['engine'].warnings) for p in paths)


def test_unknown_call_does_not_discard_an_unreachable_local_object(tmp_path):
    paths, _ = outcomes(tmp_path, '''Item passed=new Item();Item untouched=new Item();
      vendor.Plugin.mutate(passed);if(untouched.active){return yes();}return no();''')
    assert returned(paths) == {'no'}


def test_known_source_and_native_library_calls_keep_their_contracts(tmp_path):
    paths, _ = outcomes(tmp_path, '''Item item=new Item();Worker worker=new Worker();
      worker.enable(item);List<String> items=new ArrayList();items.add("ok");
      if(item.active && items.size()==1){return yes();}return no();''',
      'class Worker{void enable(Item item){item.active=true;}}')
    assert returned(paths) == {'yes'} and len(paths) == 1
    assert not paths[0]['approximate']


def test_unknown_external_write_cannot_leave_a_database_snapshot_certain(tmp_path):
    paths, _ = outcomes(tmp_path, 'vendor.Plugin.run();return after();', rows={'items':[{'key':'old'}]})
    assert all(('service','items') in p['state'].database.unknown_tables for p in paths)


def test_budget_widening_records_an_unexplored_failure_continuation(tmp_path):
    paths, _ = outcomes(tmp_path, 'vendor.Plugin.run();return after();', limit=1)
    assert len(paths) == 1 and paths[0]['approximate']
    effects = getattr(paths[0]['engine'], 'opaque_effects', [])
    assert any(e['completion'] == 'normal-or-throw-widened' for e in effects)


def test_mutated_list_alias_in_a_callers_frame_is_not_stale(tmp_path):
    paths, _ = outcomes(tmp_path, '''List<String> items=new ArrayList();items.add("old");
      Worker worker=new Worker();worker.call(items);
      if(items.size()==1){return yes();}return no();''',
      'class Worker{void call(List<String> values){vendor.Plugin.mutate(values);}}')
    assert returned(paths) == {'yes', 'no'}


@pytest.mark.parametrize('name', ['println', 'info'])
def test_a_method_name_is_not_a_purity_contract(tmp_path, name):
    paths, _ = outcomes(tmp_path, '''Item item=new Item();vendor.Plugin.'''+name+'''(item);
      if(item.active){return yes();}return no();''')
    assert returned(paths) == {'yes', 'no'}


def test_conservative_fork_does_not_hide_a_list_effect_from_a_caller(tmp_path):
    paths, ids = outcomes(tmp_path, '''List<String> items=new ArrayList();items.add("old");
      Worker worker=new Worker();worker.call(items,flag);
      if(items.size()==1){return yes();}return no();''',
      'class Worker{void call(List<String> values,boolean flag){if(flag){vendor.Plugin.mutate(values);}}}', limit=1)
    targets={t for p in paths for _,k,t in p['engine'].edges if k=='executes'}
    assert ids['Api.yes'] in targets and ids['Api.no'] in targets


def test_mutation_does_not_change_the_identity_of_an_argument_reference(tmp_path):
    paths, _ = outcomes(tmp_path, '''Item item=new Item();Item alias=item;
      vendor.Plugin.mutate(item);return item==alias ? "yes" : "no";''')
    assert returned(paths)=={'yes'}


def test_business_metadata_named_fields_are_invalidated_too(tmp_path):
    from analyzer.opaque_effects import havoc
    from analyzer.java_collections import JavaObject
    item=JavaObject('Item',{'__type__':'business','__http_entity__':True},wire_fields={'__type__','__http_entity__'})
    alias=item;env={'a':item,'b':alias}
    havoc([item],[env])
    assert item.java_type=='Item' and env['a'] is env['b']
    assert item['__type__'] is U and item['__http_entity__'] is U


def test_an_already_evaluated_argument_does_not_keep_a_stale_list_shape(tmp_path):
    paths, _ = outcomes(tmp_path, '''List<String> items=new ArrayList();items.add("old");
      Worker worker=new Worker();return worker.inspect(items,vendor.Plugin.mutate(items));''',
      '''class Worker{String inspect(List<String> items,Object ignored){
        if(items.size()==1){return "yes";}return "no";}}''')
    assert returned(paths)=={'yes','no'}


def test_reachable_cycles_and_nested_list_aliases_do_not_lose_unknown_effects():
    from analyzer.opaque_effects import havoc
    from analyzer.java_collections import JavaObject
    items=['old'];holder=JavaObject('Holder',{'items':items},wire_fields={'items','self'})
    holder['self']=holder;env={'holder':holder,'alias':items}
    havoc([holder],[env])
    assert env['alias'] is U and holder['items'] is U and holder['self'] is U


def test_immutable_serialized_text_does_not_expose_its_internal_payload_to_mutation():
    from analyzer.opaque_effects import havoc
    from analyzer.java_collections import JsonText,JsonObject
    text=JsonText(JsonObject({'value':'old'}));env={'text':text}
    havoc([text],[env])
    assert env['text'] is text and text.payload['value']=='old'


def test_unknown_completion_does_not_execute_a_literal_false_branch(tmp_path):
    paths, ids = outcomes(tmp_path, 'vendor.Plugin.run();if(false){return yes();}return no();',limit=1)
    targets={t for p in paths for _,k,t in p['engine'].edges if k=='executes'}
    assert ids['Api.yes'] not in targets and ids['Api.no'] in targets
    assert any('exceptional continuation not explored' in w for p in paths for w in p['engine'].warnings)


def test_enum_business_metadata_names_cannot_escape_invalidation():
    from analyzer.opaque_effects import havoc
    from analyzer.java_collections import JavaEnumValue
    value=JavaEnumValue('Stage.READY','type:Stage',{'__type__':'business','active':False})
    havoc([value],[{'stage':value}])
    assert value.enum_key=='Stage.READY' and value.enum_owner=='type:Stage'
    assert value['__type__'] is U and value['active'] is U
