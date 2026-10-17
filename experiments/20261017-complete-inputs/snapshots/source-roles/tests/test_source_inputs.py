"""Source inputs keep type namespaces and conditional expression provenance."""
import json
from analyzer.project import Project
from analyzer.frontend import Frontend
from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.state import ScenarioState, U
from builders import build, LIBRARY


def test_explicit_java_import_resolves_duplicate_simple_dto_names(tmp_path):
    for folder, source in {'alpha/Record.java':'package alpha; class Record { String alphaOnly; }',
                           'beta/Record.java':'package beta; class Record { int betaOnly; }',
                           'api/Api.java': '''package api; import alpha.Record;
                             /* import beta.Record; */
                             class Api { @PostMapping("/records") Record add(@RequestBody Record input) { return input; } }'''}.items():
        path = tmp_path / folder
        path.parent.mkdir(exist_ok=True)
        path.write_text(source)
    owner = 'type:api:Api'
    method = 'method:api:Api#add(alpha.Record)'
    nodes = {owner:{'kind':'type','fqn':'api.Api','module':'api','file':'api/Api.java'},
      'type:alpha:Record':{'kind':'type','fqn':'alpha.Record','module':'models','file':'alpha/Record.java'},
      'type:beta:Record':{'kind':'type','fqn':'beta.Record','module':'models','file':'beta/Record.java'},
      method:{'kind':'method','name':'add','owner':owner,'module':'api','file':'api/Api.java',
        'line':3,'params_as_written':['Record'],'annotations':[{'name':'PostMapping','args':'("/records")'}]}}
    path=tmp_path/'skeleton.json'
    path.write_text(json.dumps({'nodes':nodes,'edges':[]}))
    project=Project(path,tmp_path)
    assert project.resolve_type('alpha.Record','api') == 'type:alpha:Record'
    assert project.resolve_type('Record','api') is None
    assert project.resolve_type('Record','api','api/Api.java') == 'type:alpha:Record'
    assert project.parameters(method) == [('input','alpha.Record')]
    assert project.request_fields(method) == {'alphaOnly':'String'}


def test_conditional_url_retains_two_source_cases_and_known_guard(tmp_path):
    sources={'Api.java': '''@RestController class Api {
      @PostMapping("/letters/express") String express(@RequestBody Letter input) { return "express"; }
      @PostMapping("/letters/standard") String standard(@RequestBody Letter input) { return "standard"; }
    } class Letter { String key; }'''}
    project,db,ids=build(tmp_path,sources)
    (tmp_path/'create_letter.js').write_text('''function createLetter() {
      var letter=new Object(); letter.key="x9";
      var prefix=letter.key.charAt(0);
      if(prefix=="x") { path="/letters/express"; } else { path="/letters/standard"; }
      $.ajax({url:path,type:"POST",data:JSON.stringify(letter)});
    }''')
    frontend=Frontend(project)
    site=next(iter(frontend.sites.values()))
    assert set(site['handlers']) == {ids['Api.express'],ids['Api.standard']}
    assert len(site['url_cases']) == 2
    grounder=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}})
    choices,_=grounder.step('Create letter',ScenarioState(db))
    assert len(choices)==1
    assert choices[0]['entry'] == ids['Api.express']
    assert choices[0]['params']=={'key':'x9'}


def test_unknown_url_guard_keeps_both_routes_explicit(tmp_path):
    project,db,ids=build(tmp_path, {'Api.java': '''@RestController class Api {
      @PostMapping("/express") String express() { return "express"; }
      @PostMapping("/standard") String standard() { return "standard"; }
    }'''})
    (tmp_path/'create.js').write_text('''function create(){
      if(unknown()) { path="/express"; } else { path="/standard"; }
      $.ajax({url:path,type:"POST"});
    }''')
    frontend=Frontend(project)
    choices,_=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}}).step('Create',ScenarioState(db))
    assert {c['entry'] for c in choices} == {ids['Api.express'],ids['Api.standard']}
    assert all(any('Unknown UI request guard' in p for p in c['unresolved']) for c in choices)


def test_write_in_same_branch_as_request_is_a_known_input(tmp_path):
    project,db,ids=build(tmp_path, LIBRARY)
    (tmp_path/'add.js').write_text('''function add(){if(allowed()){
      var body=new Object(); body.key="branch"; body.title="Known";
      $.ajax({url:"/books",type:"POST",data:JSON.stringify(body)});
    }}''')
    frontend=Frontend(project);site=next(iter(frontend.sites.values()))
    assert site['body_complete']
    assert site['body_fields']=={'key':'"branch"','title':'"Known"'}


def test_role_literals_keep_multiword_values_and_override_ui_defaults(tmp_path):
    source={'Api.java': '''@RestController class Api {
      @PostMapping("/shipments/search") String search(@RequestBody Search input) { return "ok"; }
    } class Search { String startPlace; String endPlace; }'''}
    project,db,ids=build(tmp_path,source)
    (tmp_path/'ui.js').write_text('''var app={data:{from:"Old Town",to:"Other Town"},
      search(){var input={startPlace:this.from,endPlace:this.to};
      $.ajax({url:"/shipments/search",type:"POST",data:JSON.stringify(input)});}};''')
    frontend=Frontend(project)
    choices,_=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}}).step(
      'Search shipments from New Harbor to Little Bay departing on 1 October 2026', ScenarioState(db))
    assert choices[0]['params']=={'startPlace':'New Harbor','endPlace':'Little Bay'}


def test_creation_name_is_a_literal_after_declared_entity_label(tmp_path):
    project,db,ids=build(tmp_path, {'Api.java': '''@RestController class Api {
      @PostMapping("/depots") String add(@RequestBody Depot input) { return input.name; }
    } class Depot { String name; int capacity; }'''})
    frontend=Frontend(project)
    choices,_=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}}).step(
      'Add a new Depot New Harbor with capacity 4',ScenarioState(db))
    assert choices[0]['params']['name']=='New Harbor'
    assert choices[0]['params']['capacity']==4
    assert 'Unknown input: capacity' not in choices[0]['unresolved']


def test_literal_date_overrides_empty_ui_date(tmp_path):
    project,db,ids=build(tmp_path, {'Api.java': '''@RestController class Api {
      @PostMapping("/events/search") String search(@RequestBody Search input) { return input.departureTime; }
    } class Search { String departureTime; }'''})
    (tmp_path/'search.js').write_text('''var app={data:{selectedDate:""},search(){
      $.ajax({url:"/events/search",type:"POST",data:{departureTime:this.selectedDate+" 00:00:00"}});}}''')
    frontend=Frontend(project)
    choices,_=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}}).step(
      'Search events on 1 October 2026',ScenarioState(db))
    assert choices[0]['params']['departureTime'].startswith('2026-10-01')
