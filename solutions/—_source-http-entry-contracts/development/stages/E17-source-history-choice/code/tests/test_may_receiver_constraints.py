"""A supplied may edge does not override source receiver type facts."""
import json

from analyzer.engine import Engine
from analyzer.project import Project
from analyzer.state import ScenarioState
from builders import build


def add_may_target(root, project, target, callee):
    for key, node in project.nodes.items():
        if node['kind'] == 'call_site' and node['callee'] == callee:
            project.skeleton['edges'].append({'source': key, 'type': 'calls', 'target': target})
    (root/'skeleton.json').write_text(json.dumps(project.skeleton))
    return Project(root/'skeleton.json', root)


def test_field_receiver_does_not_call_an_unrelated_same_named_method(tmp_path):
    project, db, ids = build(tmp_path, {'Api.java': '''
      class Store {String read(){return "source";}}
      class Other {String read(){return "unrelated";}}
      class Api {Store store;String entry(){return store.read();}}
    '''})
    project = add_may_target(tmp_path, project, ids['Other.read'], 'read')
    engine = Engine(project, ScenarioState(db))
    assert engine.run(ids['Api.entry'], {}) == 'source'
    assert (ids['Api.entry'], 'calls', ids['Store.read']) in engine.edges
    assert ids['Other.read'] not in {target for _, kind, target in engine.edges if kind == 'executes'}


def test_interface_receiver_preserves_its_implementation_and_rejects_other_types(tmp_path):
    project, db, ids = build(tmp_path, {'Api.java': '''
      interface Reader {String read();}
      class Store implements Reader {public String read(){return "source";}}
      class Other {String read(){return "unrelated";}}
      class Api {Reader store;String entry(){return store.read();}}
    '''})
    project = add_may_target(tmp_path, project, ids['Other.read'], 'read')
    engine = Engine(project, ScenarioState(db))
    assert engine.run(ids['Api.entry'], {}) == 'source'
    assert (ids['Api.entry'], 'calls', ids['Store.read']) in engine.edges
    assert ids['Other.read'] not in {target for _, kind, target in engine.edges if kind == 'executes'}


def test_new_expression_does_not_invoke_a_different_constructor(tmp_path):
    project, db, ids = build(tmp_path, {'Api.java': '''
      class Store {Store(){}}
      class Other {Other(){changed();}void changed(){}}
      class Api {Store entry(){return new Store();}}
    '''})
    project = add_may_target(tmp_path, project, ids['Other.<init>'], '<init>')
    engine = Engine(project, ScenarioState(db))
    engine.run(ids['Api.entry'], {})
    assert (ids['Api.entry'], 'calls', ids['Store.<init>']) in engine.edges
    assert ids['Other.changed'] not in {target for _, kind, target in engine.edges if kind == 'executes'}
