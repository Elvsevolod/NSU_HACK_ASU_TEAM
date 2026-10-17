import pytest
from analyzer.frontend import Frontend
from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.state import ScenarioState
from test_script_state import fixture


def probe(tmp_path, tail='', callback='cachedItems=reply;', html=None):
    initial,_,state,_,_=fixture(tmp_path,callback=callback,initializer='[{id:"initial"}]')
    path=tmp_path/'ui.js'
    path.write_text(path.read_text()+tail)
    if html is not None:
        (tmp_path/'page.html').write_text(html)
    frontend=Frontend(initial.project)
    index=ContractIndex(initial.project,frontend)
    site=next(s for s in frontend.sites.values() if s['url']=='"/catalog"')
    contract=next(c for c in index.contracts.values() if c['site'] and c['site']['url']=='"/checkout"')
    grounder=ContractGrounder(initial.project,frontend,index,None,{'facts':{}})
    frontend.enter(site,state)
    frontend.apply_response(site,[{'id':'received'}],state)
    return frontend,site,state,grounder,contract


def selected(grounder,state,contract):
    return grounder._bind('Checkout item',state,contract,1)['params'].get('selectedId')


@pytest.mark.parametrize('tail',[
    'function reset(){cachedItems=[];}',
    'function reset(){cachedItems.push({id:"mutated"});}',
    'function reset(){cachedItems[0].id="mutated";}',
    'function reset(){cachedItems+=[];}',
    'function reset(){cachedItems++;}',
    'function reset(){unknown(cachedItems);}',
    'var alias=cachedItems;function reset(){alias[0].id="mutated";}',
    'function reset(){window.cachedItems=[];}',
    'function reset(){var box={rows:cachedItems};box.rows[0].id="mutated";}',
    'function escape(){return cachedItems;}',
])
def test_unobserved_or_alias_writers_do_not_supply_stale_values(tmp_path,tail):
    frontend,site,state,grounder,contract=probe(tmp_path,tail)
    assert selected(grounder,state,contract) is None
    assert site['script_diagnostics']


@pytest.mark.parametrize('callback',[
    'return;cachedItems=reply;',
    'throw new Error();cachedItems=reply;',
    'unknown(reply);cachedItems=reply;',
    'cachedItems=reply;unknown(reply);',
    'reply=[{id:"replacement"}];cachedItems=reply;',
    'cachedItems=reply;reply[0].id="mutated";',
    'setTimeout(function(){cachedItems=reply;},0);',
    'for(var i=0;i<1;i++){cachedItems=reply;}',
])
def test_unsupported_callback_execution_cannot_confirm_a_script_value(tmp_path,callback):
    _,site,state,grounder,contract=probe(tmp_path,callback=callback)
    assert selected(grounder,state,contract) is None
    assert site['script_diagnostics']


@pytest.mark.parametrize('html',[
    '<script type="module" src="ui.js"></script>',
    '<script src="ui.js"></script><script src="ui.js"></script>',
    '<script src="ui.js"></script><script>cachedItems=[];</script>',
    '<script src="ui.js"></script><script src="missing.js"></script>',
    '<script src="ui.js"></script><button onclick="cachedItems=[]">Reset</button>',
])
def test_unresolved_page_ownership_is_explicit(tmp_path,html):
    _,site,state,grounder,contract=probe(tmp_path,html=html)
    assert selected(grounder,state,contract) is None
    assert site['script_diagnostics']


def test_other_included_script_cannot_silently_mutate_a_binding(tmp_path):
    (tmp_path/'other.js').write_text('function reset(){cachedItems=[];}')
    _,site,state,grounder,contract=probe(tmp_path,html='<script src="ui.js"></script><script src="other.js"></script>')
    assert selected(grounder,state,contract) is None
    assert any('another included script' in message for message in site['script_diagnostics'])
