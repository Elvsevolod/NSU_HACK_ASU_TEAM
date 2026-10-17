from analyzer.frontend import Frontend
from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.state import ScenarioState, U
from analyzer.jsflow import definitions_before
from builders import build


def fixture(tmp_path, prefix, nested=False):
    project,db,_ = build(tmp_path, {'Api.java': '''class Api {
      @PostMapping("/parcels") String submit(@RequestBody Input input){return input.caption;}
    } class Input {String caption;}'''})
    (tmp_path/'page.html').write_text('<input id="entry"><span id="summary"></span><script src="ui.js"></script>')
    request = "$.ajax({url:'/parcels',type:'POST',data:{caption:$('#summary').text()}});"
    (tmp_path/'ui.js').write_text('function submit(){'+prefix+
        ("$('#dialog').modal({onConfirm:function(event){"+request+"}});" if nested else request)+'}')
    frontend = Frontend(project)
    site = next(iter(frontend.sites.values()))
    state = ScenarioState(db)
    frontend.enter(site,state)
    state.browser['dom']['#entry']='Before'
    grounder=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}})
    return frontend,site,state,grounder


def test_dom_scalar_snapshot_is_frozen_at_write_not_last_local_assignment(tmp_path):
    frontend,site,state,_=fixture(tmp_path,"var value='Before';$('#summary').text(value);value='After';")
    values=frontend.prepared_dom_values(site,state)
    assert values[('text','#summary')][0]=='Before'
    assert '#summary' not in state.browser.get('dom_text',{})


def test_prior_dom_read_uses_its_program_point(tmp_path):
    frontend,site,state,_=fixture(tmp_path,"$('#entry').val('Earlier');$('#summary').text($('#entry').val());$('#entry').val('Later');")
    assert frontend.prepared_dom_values(site,state)[('text','#summary')][0]=='Earlier'


def test_unknown_guard_does_not_keep_first_or_last_known_write(tmp_path):
    frontend,site,state,_=fixture(tmp_path,"$('#summary').text('A');if(unknown()){$('#summary').text('B');}")
    assert frontend.prepared_dom_values(site,state)[('text','#summary')][0] is U


def test_conditional_dom_writes_follow_known_input(tmp_path):
    frontend,site,state,_=fixture(tmp_path,"if($('#entry').val()=='Before'){$('#summary').text('A');}else{$('#summary').text('B');}")
    assert frontend.prepared_dom_values(site,state)[('text','#summary')][0]=='A'


def test_loop_and_async_callback_writes_are_not_final_value_proofs(tmp_path):
    for position, prefix in enumerate(("$('#summary').text('A');for(var i=0;i<5;i++){$('#summary').text('B');}",
        "$('#summary').text('A');setTimeout(function(){$('#summary').text('B');},1);",
        "$('#summary').text('A');var later=function(){$('#summary').text('B');};setTimeout(later,1);")):
        frontend,site,state,_=fixture(tmp_path/str(position),prefix)
        assert frontend.prepared_dom_values(site,state)[('text','#summary')][0] is U


def test_nested_request_can_read_source_preparation_with_explicit_hypothesis(tmp_path):
    _,_,state,grounder=fixture(tmp_path,"$('#summary').text($('#entry').val());",nested=True)
    proposal=grounder.step('Submit a parcel',state)[0][0]
    assert proposal['params']['caption']=='Before'
    assert any('DOM preparation' in issue and 'unobserved' in issue for issue in proposal['unresolved'])
    assert '#summary' not in state.browser.get('dom_text',{})


def test_function_parameter_shadow_cannot_borrow_outer_value(tmp_path):
    frontend,site,state,_=fixture(tmp_path,"var caption='Outer';$('#dialog').modal({onConfirm:function(caption){$('#summary').text(caption);}});")
    # An unrelated callback is not observed as executed before the HTTP request.
    assert frontend.prepared_dom_values(site,state)[('text','#summary')][0] is U


def test_text_setter_does_not_change_input_value_property(tmp_path):
    frontend,site,state,_=fixture(tmp_path,"$('#entry').text('Caption');$('#summary').text($('#entry').val());")
    assert frontend.prepared_dom_values(site,state)[('text','#summary')][0]=='Before'


def test_jquery_parameter_shadow_is_not_a_dom_contract(tmp_path):
    frontend,site,state,_=fixture(tmp_path,"$('#summary').text('A');")
    source=tmp_path/'ui.js'
    source.write_text(source.read_text().replace('function submit()','function submit($)'))
    fresh=Frontend(frontend.project)
    assert not fresh.prepared_dom_values(next(iter(fresh.sites.values())),state)
    assert any('shadowed jQuery' in issue for issue in fresh.warnings)


def test_later_captured_local_write_cannot_be_frozen_at_callback_creation(tmp_path):
    frontend,_,state,_=fixture(tmp_path,'')
    (tmp_path/'ui.js').write_text('''function submit(){var caption='Before';
      $('#dialog').modal({onConfirm:function(){ $('#summary').text(caption);
      $.ajax({url:'/parcels',type:'POST',data:{caption:$('#summary').text()}}); }});
      caption='After';}''')
    fresh=Frontend(frontend.project)
    assert fresh.prepared_dom_values(next(iter(fresh.sites.values())),state)[('text','#summary')][0] is U


def test_alias_or_native_dom_mutation_invalidates_literal_slice(tmp_path):
    for index,mutation in enumerate(("var el=$('#summary');el.text('Other');",
        "document.getElementById('summary').textContent='Other';","$('#parent').empty();")):
        frontend,site,state,_=fixture(tmp_path/str(index),"$('#summary').text('A');"+mutation)
        assert frontend.prepared_dom_values(site,state)[('text','#summary')][0] is U
        assert any('Unsupported DOM mutation' in issue for issue in frontend.warnings)
