from copy import deepcopy
from datetime import datetime

from analyzer.__main__ import analyze
from analyzer.contracts import ContractGrounder, ContractIndex, absent_field, explicit_value, read_static_context
from analyzer.frontend import Frontend, substitute
from analyzer.state import ScenarioState, U
from builders import build, INVENTORY, LIBRARY


def test_context_dates_and_credentials_come_from_input():
    result = read_static_context({'account': 'User alice / secret with no extra code',
                                  'date': 'All requests for 4 November 2031; system clock is 2 November 2031.'})
    assert result['clock'] == datetime(2031, 11, 2)
    assert result['facts']['request_date']['value'] == '2031-11-04'
    assert result['facts']['username']['value'] == 'alice'
    assert result['facts']['password']['value'] == 'secret'


def test_context_absence_is_field_local():
    raw = {'account': 'Use name / secret, no verification code at login'}
    assert absent_field(raw, 'verificationCode') == ('account', 'no verification code')
    assert absent_field(raw, 'username') is None
    assert absent_field(raw, 'code') is None


def test_context_absence_overrides_a_form_default(tmp_path):
    source = {'Access.java': '''@RestController class Access {
      @PostMapping("/login") String login(@RequestBody Credentials input) { return input.verificationCode; }
    }
    class Credentials { String username; String password; String verificationCode; }'''}
    project, db, _ = build(tmp_path, source)
    (tmp_path / 'page.html').write_text('<input id="code" value="1234"><script src="ui.js"></script>')
    (tmp_path / 'ui.js').write_text('$.ajax({url:"/login",type:"POST",data:{verificationCode:$("#code").val()}});')
    frontend = Frontend(project)
    context = read_static_context({'account': 'Person alice / secret, no verification code'})
    grounder = ContractGrounder(project, frontend, ContractIndex(project, frontend), None, context)
    choices, _ = grounder.step('Log in with username and password', ScenarioState(db))
    assert choices[0]['params']['verificationCode'] == ''
    assert choices[0]['bindings']['verificationCode']['source'] == 'context'


def test_identifier_substitution_preserves_literals_and_properties():
    assert substitute('path + obj.path + "path"', {'path': '"/books/"'}) == '("/books/") + obj.path + "path"'


def test_wrapper_routes_remain_paired_with_their_handlers(tmp_path):
    sources = dict(LIBRARY)
    javascript = '''function send(path, payload) {
      $.ajax({url: path, type: "POST", data: payload});
    }
    function addBook() { var body = {key:"k2", title:"Second"}; send("/books", body); }
    function release() { send("/unrelated", {key:"wrong"}); }
    '''
    project, db, ids = build(tmp_path, sources)
    (tmp_path / 'ui.js').write_text(javascript)
    frontend = Frontend(project)
    assert len(frontend.sites) == 1
    site = next(iter(frontend.sites.values()))
    assert site['handlers'] == [ids['BookController.add']]
    assert site['body_fields'] == {'key': '"k2"', 'title': '"Second"'}
    assert not db.tables


def test_grounding_has_no_independent_ui_selection(tmp_path):
    sources = dict(LIBRARY)
    javascript = '''$.ajax({url:"/books", type:"POST", data:{title:"A"}});
    $.ajax({url:"/catalog", type:"GET", data:{query:"B"}});'''
    project, db, ids = build(tmp_path, sources)
    (tmp_path / 'ui.js').write_text(javascript)
    frontend = Frontend(project)
    index = ContractIndex(project, frontend)
    grounder = ContractGrounder(project, frontend, index, None, {'facts': {}})
    choices, detail = grounder.step('Add book title "New book"', ScenarioState(db))
    assert choices and choices[0]['entry'] == ids['BookController.add']
    assert choices[0]['site'] is None
    assert choices[0]['params']['title']=='New book'
    assert any('direct HTTP hypothesis' in reason for reason in choices[0]['unresolved'])
    assert choices[0]['params']['title'] == 'New book'
    assert detail['ranking']


def test_unrelated_action_abstains_without_an_arbitrary_method(tmp_path):
    project, db, _ = build(tmp_path, LIBRARY)
    frontend = Frontend(project)
    grounder = ContractGrounder(project, frontend, ContractIndex(project, frontend), None, {'facts': {}})
    choices, detail = grounder.step('Teleport quarks', ScenarioState(db))
    assert not choices and detail['unresolved']


def test_unknown_parameters_do_not_inherit_an_unrelated_string(tmp_path):
    project, db, _ = build(tmp_path, LIBRARY)
    state = ScenarioState(db)
    state.history = [{'step': 1, 'result': {'username': 'alice'}}]
    frontend = Frontend(project)
    grounder = ContractGrounder(project, frontend, ContractIndex(project, frontend), None, {'facts': {}})
    choices, _ = grounder.step('Lookup book', state)
    assert 'key' not in choices[0]['params']
    assert choices[0]['unresolved']


def test_explicit_boolean_negative_and_numeric_labels():
    assert explicit_value('Reserve with enabled false', 'enabled', 'boolean')[0] is False
    assert explicit_value('Reserve without enabled', 'enabled', 'boolean')[0] is False
    assert explicit_value('Set count 7', 'count', 'int')[0] == 7
    assert explicit_value('Second request on 2031-11-04', 'count', 'int')[0] is U


def test_scenario_identifier_is_only_output_packaging(tmp_path):
    project, db, _ = build(tmp_path, INVENTORY, rows={'reservations': []})
    frontend = Frontend(project)
    index = ContractIndex(project, frontend)
    scenario = {'id': 'arbitrary', 'steps': [{'n': 1, 'action': 'Reserve key "k3" with enabled true'}]}
    before = deepcopy(db.tables)
    outputs = []
    for sid in ('arbitrary', 'unrelated-name'):
        scenario['id'] = sid
        block, report = analyze(project, frontend, index, None, db, {'facts': {}, 'unresolved': []},
                                scenario, grounder_type=ContractGrounder)
        outputs.append({('scenario' if e['relation'] == 'executes' else e['source'], e['relation'], e['target'])
                        for e in block['edges']})
        assert len(report['steps']) == 1
    assert outputs[0] == outputs[1]
    assert db.tables == before
