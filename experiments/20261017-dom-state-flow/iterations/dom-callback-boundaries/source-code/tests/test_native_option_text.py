from analyzer.frontend import Frontend
from analyzer.html_options import document_options
from analyzer.state import ScenarioState, U
from analyzer.contracts import ContractGrounder, ContractIndex
from builders import build


def native_page(tmp_path, markup):
    project, db, _ = build(tmp_path, {'Api.java': '''class Api {
      @PostMapping("/quotes") String submit(@RequestBody Input input){return input.caption;}
    } class Input {String caption;}'''})
    (tmp_path/'page.html').write_text(markup+'<script src="ui.js"></script>')
    (tmp_path/'ui.js').write_text('''function submit(){ $.ajax({url:"/quotes",type:"POST",
      data:{caption:$('#mode').find('option:selected').text()}}); }''')
    frontend = Frontend(project)
    site = next(iter(frontend.sites.values()))
    state = ScenarioState(db)
    frontend.enter(site,state)
    return frontend, site, state


def test_native_selected_text_uses_html5_raw_text_without_trimming(tmp_path):
    frontend, _, state = native_page(tmp_path, '''<select id="mode">
      <option value="x">\r\n  Fast &amp; safe\n </option></select>''')
    state.browser['dom']['#mode'] = 'x'
    assert frontend.evaluate("$('#mode').find('option:selected').text()",state) == '\n  Fast & safe\n '
    assert frontend.evaluate("$('#mode').find('option:selected').val()",state) == 'x'
    assert frontend.evaluate("$('#mode').find('option:selected').text().indexOf('Fast')",state) == 3


def test_native_option_value_is_not_the_displayed_text(tmp_path):
    frontend, _, state = native_page(tmp_path,'<select id="mode"><option value="7">Priority</option></select>')
    state.browser['dom']['#mode'] = '7'
    assert frontend.evaluate("$('#mode').find('option:selected').text()",state) == 'Priority'


def test_unobserved_or_ambiguous_selected_option_stays_unknown(tmp_path):
    frontend, _, state = native_page(tmp_path,'''<select id="mode"><option value="x">First</option>
      <option value="x">Second</option></select>''')
    assert frontend.evaluate("$('#mode').find('option:selected').text()",state) is U
    state.browser['dom']['#mode'] = 'x'
    assert frontend.evaluate("$('#mode').find('option:selected').text()",state) is U
    assert any('ambiguous native selected' in issue for issue in state.limitations)


def test_explicit_native_option_label_can_bind_request(tmp_path):
    frontend, _, state = native_page(tmp_path,'''<select id="mode"><option value="x">Priority</option>
      <option value="y">Economy</option></select>''')
    grounder = ContractGrounder(frontend.project,frontend,ContractIndex(frontend.project,frontend),None,{'facts':{}})
    proposal = grounder.step('Submit a quote with Priority',state)[0][0]
    assert proposal['params']['caption'] == 'Priority'
    assert state.browser['dom'].get('#mode') is None


def test_invalid_select_ownership_cannot_supply_options():
    for markup in ('<select id="x" multiple><option value="1">A</option></select>',
                   '<template><select id="x"><option value="1">A</option></select></template>',
                   '<select id="x"><option value="1">A</option></select><div id="x"></div>',
                   '<select id="x" v-for="x in rows"><option value="1">A</option></select>',
                   '<select id="x"><optgroup disabled><option value="1">A</option></optgroup></select>'):
        assert not document_options(markup)[0]
