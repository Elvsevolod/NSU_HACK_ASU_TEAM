from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState
from builders import build
from analyzer.project import Project
import json
import pytest


def executed(outcomes):
    return {target for outcome in outcomes for _,relation,target in outcome['engine'].edges if relation=='executes'}


def test_constructed_receiver_excludes_another_implementation(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''interface Worker {String run();}
      class Premium implements Worker {public String run(){return "premium";}}
      class Basic implements Worker {public String run(){return "basic";}}
      class Api {String entry(){Worker worker=new Premium();return worker.run();}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert executed(outcomes)=={ids['Api.entry'],ids['Premium.run']}
    assert [outcome['result'] for outcome in outcomes]==['premium']


def test_constructor_type_refines_a_nonabstract_superclass_target(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Base {String run(){return "base";}}
      class Specialized extends Base {String run(){return "specialized";}}
      class Api {String entry(){Base worker=new Specialized();return worker.run();}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert executed(outcomes)=={ids['Api.entry'],ids['Specialized.run']}


def test_static_method_hiding_is_not_virtual_dispatch(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Base {static String run(){return "base";}}
      class Specialized extends Base {static String run(){return "specialized";}}
      class Api {String entry(){Base worker=new Specialized();return worker.run();}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert executed(outcomes)=={ids['Api.entry'],ids['Base.run']}


def test_private_method_in_an_inherited_body_keeps_its_declaring_class(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Base {
      String run(){return hidden();}private String hidden(){return "base";}}
      class Specialized extends Base {String hidden(){return "specialized";}}
      class Api {String entry(){Base worker=new Specialized();return worker.run();}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert executed(outcomes)=={ids['Api.entry'],ids['Base.run'],ids['Base.hidden']}


def test_annotation_strings_do_not_make_a_virtual_method_static_or_private(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''interface Worker {String run();}
      class Premium implements Worker {@SuppressWarnings("private static")
        public String run(){return "premium";}}
      class Basic implements Worker {public String run(){return "basic";}}
      class Api {String entry(){Worker worker=new Premium();return worker.run();}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert executed(outcomes)=={ids['Api.entry'],ids['Premium.run']}
    assert [outcome['result'] for outcome in outcomes]==['premium']


def test_annotation_string_does_not_allow_an_instance_method_on_null(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Worker {
      @SuppressWarnings("static") String run(){return "wrong";}}
      class Api {String entry(){try{Worker worker=null;return worker.run();}
        catch(NullPointerException failure){return "null-receiver";}}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert executed(outcomes)=={ids['Api.entry']}
    assert [outcome['result'] for outcome in outcomes]==['null-receiver']


def test_fully_qualified_parameter_and_imported_parameter_match(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.List;
      class Base {String run(java.util.List<String> input){return "base";}}
      class Specialized extends Base {String run(List<String> input){return "specialized";}}
      class Api {String entry(){Base worker=new Specialized();return worker.run(null);}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert executed(outcomes)=={ids['Api.entry'],ids['Specialized.run']}
    assert [outcome['result'] for outcome in outcomes]==['specialized']


def test_an_overload_does_not_hide_an_inherited_override(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Base {String run(Object input){return "base";}}
      class Middle extends Base {String run(Object input){return "middle";}}
      class Specialized extends Middle {String run(String input){return "overload";}}
      class Api {String entry(){Base worker=new Specialized();return worker.run(new Object());}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert executed(outcomes)=={ids['Api.entry'],ids['Middle.run']}
    assert [outcome['result'] for outcome in outcomes]==['middle']


def test_subclass_overload_does_not_override_the_declared_signature(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Base {String run(Object input){return "base";}}
      class Specialized extends Base {String run(String input){return "overload";}}
      class Api {String entry(){Base worker=new Specialized();return worker.run("text");}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert executed(outcomes)=={ids['Api.entry'],ids['Base.run']}
    assert [outcome['result'] for outcome in outcomes]==['base']


def test_unsupported_type_variable_override_is_diagnosed_and_retains_both(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Base<T> {String run(T input){return "base";}}
      class Specialized extends Base<String> {String run(String input){return "specialized";}}
      class Api {String entry(){Base<String> worker=new Specialized();return worker.run("text");}}'''})
    # A skeleton supplies the erased declaration; the source fixture builder
    # deliberately has no compiler/type-variable substitution machinery.
    site=next(site for site in project.sites[ids['Api.entry']] if project.nodes[site]['callee']=='run')
    project.edges[site]['calls'].add(ids['Base.run'])
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert executed(outcomes)=={ids['Api.entry'],ids['Base.run'],ids['Specialized.run']}
    assert all(outcome['engine'].approximate for outcome in outcomes)
    assert all(any('dispatch signature' in warning for warning in outcome['engine'].warnings) for outcome in outcomes)


@pytest.mark.parametrize('middle,expected',[(False,'Base.run'),(True,'Specialized.run')])
def test_package_access_and_a_public_override_bridge(tmp_path,middle,expected):
    sources={'Base.java':'''package first;public class Base {
      String run(){return "base";}public String invoke(){return run();}}''',
      'Specialized.java':'''package second;import first.'''+('Middle' if middle else 'Base')+''';
        public class Specialized extends '''+('Middle' if middle else 'Base')+''' {
          public String run(){return "specialized";}}''',
      'Api.java':'''package first;import second.Specialized;
        class Api {String entry(){Base value=new Specialized();return value.invoke();}}'''}
    if middle:
        sources['Middle.java']='package first;public class Middle extends Base {public String run(){return "middle";}}'
    original,db,ids=build(tmp_path,sources)
    skeleton=original.skeleton
    for node in skeleton['nodes'].values():
        if node.get('kind')=='type':
            node['fqn']=('second.' if node['fqn']=='Specialized' else 'first.')+node['fqn']
    (tmp_path/'skeleton.json').write_text(json.dumps(skeleton))
    project=Project(tmp_path/'skeleton.json',tmp_path)
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{})
    assert executed(outcomes)=={ids['Api.entry'],ids['Base.invoke'],ids[expected]}
    assert {outcome['result'] for outcome in outcomes}=={'specialized' if middle else 'base'}
