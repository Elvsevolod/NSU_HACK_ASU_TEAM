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


@pytest.mark.parametrize('enabled,expected',[(True,2),(False,0)])
def test_slf4j_formatting_calls_source_to_string_only_for_used_arguments(tmp_path,enabled,expected):
    project,db,ids=qualified_project(tmp_path,{'Api.java':'''package sample;import org.slf4j.Logger;
      class Value {int count; public String toString(){count++;return "value";}}
      class Api {Logger log;int entry(Value value,Value unused){log.info("{} {}",value,value,unused);return value.count+unused.count*10;}}'''})
    value=JavaRecord('sample.Value',{'__type__':'sample.Value','count':0},['count'])
    unused=JavaRecord('sample.Value',{'__type__':'sample.Value','count':0},['count'])
    state=ScenarioState(db);state.context['logging']={'enabled':enabled}
    outcomes=run_paths(project,state,ids['Api.entry'],{'value':value,'unused':unused},limit=1)
    assert {row['result'] for row in outcomes}=={expected}
    assert all((any(target==ids['Value.toString'] for _,kind,target in row['engine'].edges if kind=='executes')) is enabled for row in outcomes)


def test_slf4j_catches_formatting_throwable_and_continues(tmp_path):
    project,db,ids=qualified_project(tmp_path,{'Api.java':'''package sample;import org.slf4j.Logger;
      class Value {public String toString(){throw new IllegalArgumentException();}}
      class Api {Logger log;int entry(){log.info("{}",new Value());return after();}int after(){return 31;}}'''})
    state=ScenarioState(db);state.context['logging']={'enabled':True}
    outcomes=run_paths(project,state,ids['Api.entry'],{},limit=1)
    assert {row['result'] for row in outcomes}=={31}
    assert all(('', 'executes',ids['Value.toString']) in row['engine'].edges for row in outcomes)


def test_known_null_logger_throws_after_evaluating_its_argument(tmp_path):
    project,db,ids=qualified_project(tmp_path,{'Api.java':'''package sample;import org.slf4j.Logger;
      class Api {int entry(){Logger log=null;log.info("value {}",touch());return after();}
        int touch(){return 1;}int after(){return 19;}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Api.entry'],{},limit=1)
    assert all(('', 'executes',ids['Api.touch']) in row['engine'].edges for row in outcomes)
    assert all(('', 'executes',ids['Api.after']) not in row['engine'].edges for row in outcomes)
    assert all(row['engine'].outcome=='uncaught application exception' for row in outcomes)
