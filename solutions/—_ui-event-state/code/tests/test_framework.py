from copy import deepcopy
import pytest
from analyzer.frontend import Frontend
from analyzer.engine import Engine
from analyzer.paths import run_paths, join_states
from analyzer.state import ScenarioState, U
from builders import build, INVENTORY


def test_qualifier_resolves_source_bean_name(tmp_path):
    sources = {
        'Entry.java': 'class Entry { @Qualifier("blue") Driver driver; int entry() { return driver.send(); } }',
        'Driver.java': 'interface Driver { int send(); }',
        'Red.java': '@Service("red") class Red implements Driver { int send() { return 1; } }',
        'Blue.java': '@Service("blue") class Blue implements Driver { int send() { return 2; } }',
    }
    project, db, ids = build(tmp_path, sources)
    paths = run_paths(project, ScenarioState(db), ids['Entry.entry'], {})
    assert len(paths) == 1 and paths[0]['result'] == 2
    executed = {e[2] for e in paths[0]['engine'].edges}
    assert ids['Blue.send'] in executed and ids['Red.send'] not in executed


@pytest.mark.parametrize('profile,expected', [('default', 1), ('archive', 2)])
def test_profile_selects_implementation(tmp_path, profile, expected):
    sources = {
        'Entry.java': 'class Entry { Driver driver; int entry() { return driver.send(); } }',
        'Driver.java': 'interface Driver { int send(); }',
        'Main.java': '@Profile("default") class Main implements Driver { int send() { return 1; } }',
        'Archive.java': '@Profile("archive") class Archive implements Driver { int send() { return 2; } }',
    }
    project, db, ids = build(tmp_path, sources)
    project.active_profiles = {profile}
    paths = run_paths(project, ScenarioState(db), ids['Entry.entry'], {})
    assert len(paths) == 1 and paths[0]['result'] == expected


def test_source_call_can_be_resolved_when_skeleton_site_is_absent(tmp_path):
    sources = {'Entry.java': 'class Entry { void entry() { helper(); } void helper() {} }'}
    project, db, ids = build(tmp_path, sources)
    project.by_line.clear()
    paths = run_paths(project, ScenarioState(db), ids['Entry.entry'], {})
    assert (ids['Entry.entry'], 'calls', ids['Entry.helper']) in paths[0]['engine'].edges


def test_caught_exception_restores_calling_method_context(tmp_path):
    sources = {'Entry.java': '''class Entry {
      void entry() { try { fail(); } catch (Exception exception) { recover(); } }
      void fail() { throw new RuntimeException(); }
      void recover() {}
    }'''}
    project, db, ids = build(tmp_path, sources)
    paths = run_paths(project, ScenarioState(db), ids['Entry.entry'], {})
    assert (ids['Entry.entry'], 'calls', ids['Entry.recover']) in paths[0]['engine'].edges
    assert not any(s == ids['Entry.fail'] and t == ids['Entry.recover'] for s, _, t in paths[0]['engine'].edges)


def test_filter_exception_is_an_outcome_and_does_not_enter_controller(tmp_path):
    sources = {'Entry.java': 'class Entry { void entry() {} }',
               'Gate.java': 'class Gate extends OncePerRequestFilter { void doFilterInternal() { throw new RuntimeException(); } }'}
    project, db, ids = build(tmp_path, sources)
    path = run_paths(project, ScenarioState(db), ids['Entry.entry'], {})[0]
    assert path['engine'].outcome == 'uncaught application exception'
    assert not any(edge[2] == ids['Entry.entry'] for edge in path['engine'].edges)


def test_browser_pages_keep_separate_form_defaults(tmp_path):
    project, db, ids = build(tmp_path, INVENTORY, rows={'reservations': []})
    frontend = Frontend(project)
    a = {'page': 'first.html', 'defaults': {'key': 'a'}, 'dom_defaults': {}}
    b = {'page': 'second.html', 'defaults': {'key': 'b'}, 'dom_defaults': {}}
    state = ScenarioState(db)
    frontend.enter(a, state)
    state.browser['form']['key'] = 'edited'
    frontend.enter(b, state)
    assert state.browser['form']['key'] == 'b'
    frontend.enter(a, state)
    assert state.browser['form']['key'] == 'edited'


def test_unknown_active_page_does_not_become_a_dictionary_key(tmp_path):
    project, db, _ = build(tmp_path, INVENTORY, rows={'reservations': []})
    frontend = Frontend(project)
    left, right = ScenarioState(db), ScenarioState(db)
    frontend.enter({'page': 'a', 'defaults': {'key': 'a'}, 'dom_defaults': {}}, left)
    frontend.enter({'page': 'b', 'defaults': {'key': 'b'}, 'dom_defaults': {}}, right)
    joined = join_states([left, right])
    frontend.enter({'page': 'c', 'defaults': {'key': 'c'}, 'dom_defaults': {}}, joined)
    assert all(isinstance(key, str) for key in joined.browser['pages'])
    join_states([joined, left])


def test_unknown_response_key_widens_existing_values(tmp_path):
    project, db, _ = build(tmp_path, INVENTORY, rows={'reservations': []})
    frontend, state = Frontend(project), ScenarioState(db)
    state.browser['storage']['selected'] = 'before'
    frontend.apply_response({'id': 'screen:1', 'response_name': 'response', 'response_definitions': {},
        'effects': [{'space': 'storage', 'key': U, 'expr': 'response.item', 'conditions': []}]}, {'item': 'after'}, state)
    assert state.browser['storage'] == {'selected': U}
    assert any('unknown browser response key' in item for item in state.limitations)


def test_unknown_previous_page_does_not_restore_known_defaults(tmp_path):
    project, db, _ = build(tmp_path, INVENTORY, rows={'reservations': []})
    frontend, state = Frontend(project), ScenarioState(db)
    state.browser['pages'] = {'a': U}
    frontend.enter({'page': 'a', 'defaults': {'key': 'initial'}, 'dom_defaults': {}}, state)
    assert state.browser['form']['key'] is U


def test_symbolic_input_does_not_become_a_concrete_browser_url(tmp_path):
    project, db, _ = build(tmp_path, INVENTORY, rows={'reservations': []})
    frontend, state = Frontend(project), ScenarioState(db)
    state.browser['form']['key'] = state.fresh_input('key')
    url=frontend.evaluate('"/items/" + this.key', state)
    assert isinstance(url,dict) and url['__text_parts__'][-1]==state.browser['form']['key']
    assert Engine(project,state).request_address(url) is None
