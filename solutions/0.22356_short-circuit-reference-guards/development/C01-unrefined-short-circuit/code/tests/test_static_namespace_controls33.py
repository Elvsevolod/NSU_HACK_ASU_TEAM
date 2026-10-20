"""Distinct declaring owners for same-named static types in one deployment."""
import json

from analyzer.engine import Engine
from analyzer.project import Project
from analyzer.state import Database, ScenarioState


def test_static_import_and_qualified_cells_keep_both_packages_and_scenario_state(tmp_path):
    sources = {
        'alpha/Material.java': 'package alpha; public class Material {public static int count=2;}',
        'beta/Material.java': 'package beta; public class Material {public static int count=20;}',
        'app/Api.java': '''package app; import alpha.Material; import static beta.Material.count;
          public class Api {
            public int entry(){Material.count++;return Material.count+count;}
            public int alpha(){return Material.count;}
            public int beta(){return count;}
          }''',
    }
    nodes = {'module:m': {'kind': 'module', 'name': 'm', 'deployment_units': ['m']}}
    for name, file in [('alpha.Material', 'alpha/Material.java'),
                       ('beta.Material', 'beta/Material.java'), ('app.Api', 'app/Api.java')]:
        nodes['type:'+name] = {'kind': 'type', 'fqn': name, 'file': file, 'module': 'm'}
    for name, line in [('entry', 3), ('alpha', 4), ('beta', 5)]:
        nodes['method:app.Api#'+name] = {
            'kind': 'method', 'owner': 'type:app.Api', 'name': name, 'file': 'app/Api.java',
            'module': 'm', 'line': line, 'params_as_written': [], 'annotations': [], 'return_raw': 'int'}
    for file, source in sources.items():
        path = tmp_path/file; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(source)
    (tmp_path/'skeleton.json').write_text(json.dumps({'nodes': nodes, 'edges': []}))
    (tmp_path/'initial.sql').write_text('')
    p = Project(tmp_path/'skeleton.json', tmp_path)
    db = Database(tmp_path/'initial.sql'); state = ScenarioState(db)
    assert Engine(p, state).run('method:app.Api#entry', {}) == 23
    assert Engine(p, state).run('method:app.Api#alpha', {}) == 3
    assert Engine(p, state).run('method:app.Api#beta', {}) == 20
    assert state.static_fields['type:alpha.Material']['count'] == 3
    assert state.static_fields['type:beta.Material']['count'] == 20
    assert all(state.static_fields[owner].kinds['count'] == 'Integer'
               for owner in ('type:alpha.Material', 'type:beta.Material'))
    assert Engine(p, ScenarioState(db)).run('method:app.Api#alpha', {}) == 2
