from analyzer.frontend import Page
from analyzer.frontend import Frontend
from analyzer.state import ScenarioState, U
from builders import build


def test_script_module_and_inline_ownership_are_available_to_the_adapter():
    page=Page()
    page.feed('''<script type="module" src="module.js"></script><script src="classic.js"></script>
      <script>cache = 3;</script><button onclick="resetCache()">Reset</button>''')
    assert page.scripts==['module.js','classic.js']
    assert page.script_kinds=={'module.js':'module','classic.js':''}
    assert page.inline_scripts==[{'src':None,'kind':'','text':'cache = 3;'}]
    assert page.inline_handlers==['resetCache()']


def test_json_script_is_not_mistaken_for_classic_javascript():
    page=Page()
    page.feed('<script type="application/json">{"cache":7}</script>')
    assert page.inline_scripts[0]['kind']=='application/json'


def test_script_store_is_page_local_and_unknown_page_is_not_reset(tmp_path):
    project,db,_=build(tmp_path,{'Api.java':'class Api {String read(){return "ok";}}'})
    frontend,state=Frontend(project),ScenarioState(db)
    a={'page':'a','defaults':{},'dom_defaults':{},'script_defaults':{'cache':['A']}}
    b={**a,'page':'b','script_defaults':{'cache':['B']}}
    frontend.enter(a,state)
    assert state.browser['script']['cache']==['A']
    frontend.enter(b,state)
    assert state.browser['script']['cache']==['B']
    frontend.enter(a,state)
    assert state.browser['script']['cache']==['A']
    state=ScenarioState(db)
    state.browser['pages']={'a':U}
    frontend.enter(a,state)
    assert state.browser['script']['cache'] is U


def test_late_demand_on_an_unknown_page_does_not_reinitialize_a_literal(tmp_path):
    project,db,_=build(tmp_path,{'Api.java':'class Api {String read(){return "ok";}}'})
    frontend,state=Frontend(project),ScenarioState(db)
    first={'page':'a','defaults':{},'dom_defaults':{},'script_defaults':{'first':['initial']}}
    second={**first,'script_defaults':{'second':['other-initial']}}
    state.browser['pages']={'a':U}
    frontend.enter(first,state)
    frontend.enter(second,state)
    assert state.browser['script']['first'] is U
    assert state.browser['script']['second'] is U
