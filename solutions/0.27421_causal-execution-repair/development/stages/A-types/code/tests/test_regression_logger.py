import json

import pytest

from analyzer.paths import run_paths
from analyzer.java_collections import JavaRecord
from analyzer.project import Project
from analyzer.state import ScenarioState
from builders import build


def qualified_project(tmp_path, sources):
    project, database, ids = build(tmp_path, sources)
    graph = project.skeleton
    for node in graph['nodes'].values():
        if node['kind'] == 'type':
            node['fqn'] = 'sample.' + node['fqn']
    (tmp_path / 'skeleton.json').write_text(json.dumps(graph))
    return Project(tmp_path / 'skeleton.json', tmp_path), database, ids


@pytest.mark.parametrize('receiver', ['LOGGER', 'Api.LOGGER', 'sample.Api.LOGGER'])
def test_standard_logger_spelling_keeps_the_same_continuation(tmp_path, receiver):
    project, database, ids = qualified_project(tmp_path, {'Api.java': '''package sample;
      import org.slf4j.Logger; import org.slf4j.LoggerFactory;
      class Api {static final Logger LOGGER=LoggerFactory.getLogger(Api.class);
        int entry(){''' + receiver + '''.info("message {}", 3); return after();}
        int after(){return 17;} }'''})
    outcomes = run_paths(project, ScenarioState(database), ids['Api.entry'], {}, limit=1)
    assert outcomes and all(row['result'] == 17 for row in outcomes)
    assert all(any(target == ids['Api.after'] for _, relation, target in row['engine'].edges
                   if relation == 'executes') for row in outcomes)
    assert not any(effect['operation'] == 'info' for row in outcomes for effect in row['engine'].effect_events)


def test_imported_static_logger_uses_the_declaring_field_type(tmp_path):
    project, database, ids = qualified_project(tmp_path, {
        'Api.java': '''package sample; import org.slf4j.Logger; import org.slf4j.LoggerFactory;
          class Api {public static final Logger LOGGER=LoggerFactory.getLogger(Api.class);}''',
        'Other.java': '''package sample; import static sample.Api.LOGGER;
          class Other {int entry(){LOGGER.debug("quiet");return 23;}}'''})
    outcomes = run_paths(project, ScenarioState(database), ids['Other.entry'], {}, limit=1)
    assert outcomes and all(row['result'] == 23 for row in outcomes)
    assert not any(effect['operation'] == 'debug' for row in outcomes for effect in row['engine'].effect_events)


def test_logger_arguments_keep_source_side_effects(tmp_path):
    project, database, ids = qualified_project(tmp_path, {'Api.java': '''package sample;
      import org.slf4j.Logger;
      class Counter {int n;}
      class Api {Logger log;
        int touch(Counter c){c.n++;return c.n;}
        int entry(Counter c){log.debug("value {}",touch(c));return c.n;} }'''})
    counter = JavaRecord('sample.Counter', {'__type__':'sample.Counter','n':0}, ['n'])
    outcomes = run_paths(project, ScenarioState(database), ids['Api.entry'], {'c':counter}, limit=1)
    assert outcomes and all(row['result'] == 1 for row in outcomes)
    assert all(any(target == ids['Api.touch'] for _, relation, target in row['engine'].edges
                   if relation == 'executes') for row in outcomes)


def test_local_shadow_and_source_info_are_not_native_logging(tmp_path):
    project, database, ids = qualified_project(tmp_path, {'Api.java': '''package sample;
      import org.slf4j.Logger;
      class Counter {int n;}
      class Sink {void info(Counter c){c.n=9;}}
      class Api {static Logger LOGGER;
        int entry(){Counter c=new Counter();Sink LOGGER=new Sink();LOGGER.info(c);return c.n;} }'''})
    outcomes = run_paths(project, ScenarioState(database), ids['Api.entry'], {}, limit=1)
    assert outcomes and all(row['result'] == 9 for row in outcomes)
    assert all(any(target == ids['Sink.info'] for _, relation, target in row['engine'].edges
                   if relation == 'executes') for row in outcomes)
