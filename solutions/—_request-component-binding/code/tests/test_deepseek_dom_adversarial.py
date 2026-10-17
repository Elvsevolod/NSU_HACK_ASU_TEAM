from analyzer.frontend import Frontend
from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.state import ScenarioState, U
from builders import build


API = '''class Api {
  @PostMapping("/widgets") String submit(@RequestBody Input input){return input.caption;}
} class Input {String caption;}'''


def fixture(tmp_path, ui, markup='<input id="entry"><span id="summary"></span>'):
    project, db, _ = build(tmp_path, {'Api.java': API})
    (tmp_path/'page.html').write_text(markup+'<script src="ui.js"></script>')
    (tmp_path/'ui.js').write_text(ui)
    frontend = Frontend(project)
    site = next(iter(frontend.sites.values()))
    state = ScenarioState(db)
    frontend.enter(site, state)
    grounder = ContractGrounder(project, frontend, ContractIndex(project, frontend), None, {'facts': {}})
    return frontend, site, state, grounder


def stub(before='', after='', body='$("#summary").text()'):
    return ('function submit(){'+before+
            '$.ajax({url:"/widgets",type:"POST",data:{caption:'+body+'}});'+after+'}')


def stub_in_callback(before='', inside='', body='$("#summary").text()'):
    return ('function submit(){'+before+'$("#dialog").modal({onConfirm:function(){'+inside+
            '$.ajax({url:"/widgets",type:"POST",data:{caption:'+body+'}});}});}')


def guarded(body='$("#entry").val()'):
    return ('function submit(){if($("#entry").val().indexOf("X")){'
            '$.ajax({url:"/widgets",type:"POST",data:{caption:'+body+'}});}}')


def dom_value(frontend, site, state, method='text', control='#summary'):
    return frontend.prepared_dom_values(site, state).get((method, control), (U, None))[0]


def test_write_after_the_request_statement_is_not_visible_to_it(tmp_path):
    frontend, site, state, grounder = fixture(tmp_path, stub(after='$("#summary").text("Late");'))
    assert dom_value(frontend, site, state) is U
    proposals, _ = grounder.step('Submit a widget', state)
    assert proposals
    proposal = proposals[0]
    assert proposal['params'].get('caption') == ''
    assert not any('DOM preparation' in issue for issue in proposal['unresolved'])


def test_later_literal_write_wins_at_the_request_point(tmp_path):
    frontend, site, state, grounder = fixture(
        tmp_path, stub(before='$("#summary").text("First");$("#summary").text("Second");'))
    assert dom_value(frontend, site, state) == 'Second'
    proposals, _ = grounder.step('Submit a widget', state)
    assert proposals[0]['params']['caption'] == 'Second'


def test_inner_window_write_follows_outer_preparation(tmp_path):
    frontend, site, state, _ = fixture(tmp_path, stub_in_callback(
        before='$("#summary").text("A");', inside='$("#summary").text("B");'))
    assert dom_value(frontend, site, state) == 'B'


def test_unknown_guard_does_not_block_a_later_unconditional_write(tmp_path):
    frontend, site, state, _ = fixture(tmp_path, stub(
        before='if(unknown()){$("#summary").text("A");}$("#summary").text("B");'))
    assert dom_value(frontend, site, state) == 'B'


def test_unknown_guarded_write_in_the_request_window_invalidates_outer_state(tmp_path):
    frontend, site, state, _ = fixture(tmp_path, stub_in_callback(
        before='$("#summary").text("A");', inside='if(unknown()){$("#summary").text("B");}'))
    assert dom_value(frontend, site, state) is U


def test_value_property_write_does_not_supply_text(tmp_path):
    frontend, site, state, grounder = fixture(tmp_path, stub(before='$("#summary").val("Caption");'))
    assert dom_value(frontend, site, state, method='val') == 'Caption'
    proposals, _ = grounder.step('Submit a widget', state)
    assert proposals
    assert proposals[0]['params'].get('caption') == ''


def test_text_write_does_not_supply_the_value_property(tmp_path):
    frontend, site, state, grounder = fixture(
        tmp_path, stub(before='$("#entry").text("Caption");', body='$("#entry").val()'))
    assert dom_value(frontend, site, state, control='#entry') == 'Caption'
    state.browser['dom']['#entry'] = 'Before'
    proposals, _ = grounder.step('Submit a widget', state)
    assert proposals[0]['params']['caption'] == 'Before'


def test_captured_outer_local_is_not_pinned_inside_the_callback(tmp_path):
    frontend, site, state, grounder = fixture(tmp_path, stub_in_callback(
        before='var note="Captured";', inside='$("#summary").text(note);'))
    assert dom_value(frontend, site, state) is U
    proposals, _ = grounder.step('Submit a widget', state)
    assert proposals
    proposal = proposals[0]
    assert 'caption' not in proposal['params']
    assert any('DOM preparation' in issue and 'unobserved' in issue for issue in proposal['unresolved'])
    assert state.browser['dom_text'].get('#summary') == ''


def test_callback_local_declaration_shadows_the_outer_binding(tmp_path):
    frontend, site, state, _ = fixture(tmp_path, stub_in_callback(
        before='var note="Outer";', inside='var note="Inner";$("#summary").text(note);'))
    assert dom_value(frontend, site, state) == 'Inner'


def test_write_keeps_the_binding_value_at_its_program_point(tmp_path):
    frontend, site, state, _ = fixture(tmp_path, stub_in_callback(
        inside='var note="Inner";$("#summary").text(note);note="Later";'))
    assert dom_value(frontend, site, state) == 'Inner'


def test_async_callback_cannot_override_a_later_synchronous_write(tmp_path):
    frontend, site, state, _ = fixture(tmp_path, stub(
        before='setTimeout(function(){$("#summary").text("Late");},0);$("#summary").text("Now");'))
    assert dom_value(frontend, site, state) == 'Now'


def test_aliased_and_computed_writers_are_rejected_with_source_diagnostics(tmp_path):
    cases = ('$("#summary").text("A");$("#"+"summary").text("B");',
             '$("#summary").text("A");$("#summary").html("B");',
             '$("#summary").text("A");$("#summary")[0].textContent="B";')
    for index, before in enumerate(cases):
        frontend, site, state, grounder = fixture(tmp_path/str(index), stub(before=before))
        assert dom_value(frontend, site, state) is U
        assert any('Unsupported DOM mutation' in warning and 'ui.js' in warning for warning in frontend.warnings)
        proposals, _ = grounder.step('Submit a widget', state)
        assert proposals
        assert all('caption' not in proposal['params'] for proposal in proposals)


def test_zero_indexof_guard_excludes_the_request(tmp_path):
    frontend, site, state, grounder = fixture(tmp_path, guarded())
    state.browser['dom']['#entry'] = 'Xy'
    proposals, detail = grounder.step('Submit a widget', state)
    assert proposals == []
    assert any('guard' in issue.lower() for issue in detail['unresolved'])


def test_negative_one_indexof_guard_is_truthy_like_the_source(tmp_path):
    frontend, site, state, grounder = fixture(tmp_path, guarded())
    state.browser['dom']['#entry'] = 'Other'
    proposals, _ = grounder.step('Submit a widget', state)
    assert proposals
    assert proposals[0]['params']['caption'] == 'Other'


def test_unknown_guard_value_is_unresolved_not_confirmed(tmp_path):
    frontend, site, state, grounder = fixture(tmp_path, guarded())
    proposals, _ = grounder.step('Submit a widget', state)
    assert proposals
    assert any('guard' in issue.lower() for issue in proposals[0]['unresolved'])
    assert 'caption' not in proposals[0]['params']
