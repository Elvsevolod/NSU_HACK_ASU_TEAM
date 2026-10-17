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


def test_enum_numeric_value_requires_source_comparison_to_same_input(tmp_path):
    project,db,ids=build(tmp_path, {'Api.java': '''@RestController class Api {
      @PostMapping("/parcels") int add(@RequestBody Parcel input) {
        if (input.getPriority()==ParcelPriority.FAST.getCode()) { return 1; }
        return 0;
      }
    }
    class Parcel { int priority; int priorityCopy; int getPriority(){return priority;} }
    enum ParcelPriority { FAST(73,"ExpressParcel"), SLOW(19,"SlowParcel");
      int code; String label; ParcelPriority(int code,String label){this.code=code;this.label=label;}
      int getCode(){return code;}
    }'''})
    frontend=Frontend(project)
    choices,_=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}}).step(
      'Add an express parcel',ScenarioState(db))
    assert choices[0]['params']['priority']==73
    assert 'priorityCopy' not in choices[0]['params']


def test_preposition_does_not_introduce_an_address_literal(tmp_path):
    from analyzer.contracts import explicit_value
    assert explicit_value('Send parcel to a recipient', 'to', 'String')[0] is U
    assert explicit_value('Send parcel to="New Harbor"', 'to', 'String')[0]=='New Harbor'


def test_ordered_element_collection_uses_skeleton_and_source_columns(tmp_path):
    source={'Cart.java': '''@Entity @Table(name="carts") class Cart {
      @Id String key;
      @ElementCollection @OrderColumn(name="position") @Column(name="note_text")
      List<String> notes;
    }'''}
    project,db,ids=build(tmp_path, source, rows={'carts':[{'key':'c1'}], 'cart_notes':[
      {'cart_key':'c1','note_text':'second','position':1},
      {'cart_key':'c1','note_text':'first','position':0},
      {'cart_key':'other','note_text':'excluded','position':0}]})
    path=tmp_path/'skeleton.json'; skeleton=json.loads(path.read_text())
    skeleton['nodes']['res:notes']={'kind':'data_resource','name':'cart_notes','schema':'service',
      'collection_of':'type:service:Cart','origin':[{'file':'Cart.java','line':3}]}
    path.write_text(json.dumps(skeleton)); project=Project(path,tmp_path)
    resource='res:table:service.carts'
    db.schemas={'service':'${DATABASE:unresolved}'}
    assert project.materialize(db,resource,{'key':'c1'})['notes']==['first','second']
    db.unknown_tables.add(('service','cart_notes'))
    assert project.materialize(db,resource,{'key':'c1'})['notes'] is U


def test_pure_composite_identifier_conversion_and_query_role_state(tmp_path):
    from analyzer.provenance import source_string,history_role_value
    project,db,ids=build(tmp_path, {'Api.java': '''class Code {
      String prefix; int number; String toString(){return prefix+number;}
    } class Unsafe { String toString(){ erase(); return "bad"; } void erase(){} }
    class Envelope { Code parcelId; String startPlace; String endPlace; }'''})
    assert source_string(project,{'__type__':'Code','prefix':'P','number':8})=='P8'
    assert source_string(project,{'__type__':'Unsafe'}) is U
    history=[{'parameters':{'parcelId':'P8','from':'New Harbor','to':'Little Bay'},
              'result':{'__type__':'Envelope','parcelId':{'__type__':'Code','prefix':'P','number':8},
                        'startPlace':'New Harbor','endPlace':'Whole Line Terminal'}}]
    assert history_role_value(project,'endPlace',{'parcelId':'P8'},history)[1]=='Little Bay'
    assert history_role_value(project,'endPlace',{'parcelId':'Q3'},history) is None


def test_created_entity_identity_survives_a_status_only_response(tmp_path):
    from analyzer.__main__ import analyze
    source={'Api.java': '''@RestController class Api {
      @Autowired MessageStore repository;
      @PostMapping("/messages") String add(@RequestBody Message input) {repository.save(input); return "accepted";}
      @GetMapping("/messages/{id}") String read(@PathVariable String id) {return id;}
    }
    @Entity @Table(name="messages") class Message { @Id String id; String body; }
    interface MessageStore extends JpaRepository<Message,String> { Message save(Message input); }
    '''}
    project,db,ids=build(tmp_path,source,rows={'messages':[]});frontend=Frontend(project)
    _,report=analyze(project,frontend,ContractIndex(project,frontend),None,db,{'facts':{},'unresolved':[]},
      {'id':'mail','steps':[{'n':1,'action':'Add message id "m1" body "Hello"'},{'n':2,'action':'Read new message'}]},
      grounder_type=ContractGrounder)
    choice=report['steps'][1]['alternatives'][0]
    assert choice['parameters']['id']=='m1'
    assert choice['bindings']['id']['source']=='history'
    assert 'created_objects' in choice['bindings']['id']['reference']


def test_js_date_values_come_from_supplied_clock(tmp_path):
    from datetime import datetime
    project,db,_=build(tmp_path,LIBRARY);frontend=Frontend(project);state=ScenarioState(db)
    state.now=datetime(2042,3,9)
    assert frontend.evaluate('new Date().getFullYear()',state)==2042
    assert frontend.evaluate('new Date().getMonth()',state)==2
    state.now=U
    assert frontend.evaluate('new Date().getFullYear()',state) is U


def test_omitted_properties_remain_proven_when_another_value_is_conditional(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java': '''@RestController class Api {
      @PostMapping("/notes") String add(@RequestBody Note input){return input.text;}
    } class Note { String id; String text; int amount; }'''})
    (tmp_path/'add_note.js').write_text('''function addNote(){ var n=new Object();
      n.text="fixed"; if (unknown()) {n.amount=2;} else {n.amount=7;}
      $.ajax({url:"/notes",type:"POST",data:JSON.stringify(n)});
    }''')
    frontend=Frontend(project)
    choices,_=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}}).step('Add note',ScenarioState(db))
    assert choices[0]['params']['id'] is None
    assert choices[0]['params']['text']=='fixed'
    assert 'amount' not in choices[0]['params']
    assert choices[0]['unresolved']==['Unknown input: amount']


def test_date_filter_uses_matching_mutator_and_supplied_clock(tmp_path):
    from datetime import datetime
    from analyzer.request_semantics import filter_bindings
    source={'Api.java': '''@RestController class Api {
      @PostMapping("/events/query") String query(@RequestBody EventQuery input){return "ok";}
    } class EventQuery {
      boolean deliveryEnabled; boolean boughtEnabled;
      String deliveryDateStart; String deliveryDateEnd; String boughtDateStart; String boughtDateEnd;
      void enableDeliveryDateQuery(String startTime,String endTime){deliveryEnabled=true;deliveryDateStart=startTime;deliveryDateEnd=endTime;}
      void enableBoughtDateQuery(String startTime,String endTime){boughtEnabled=true;boughtDateStart=startTime;boughtDateEnd=endTime;}
    }'''}
    project,db,ids=build(tmp_path,source)
    result=filter_bindings(project,ids['Api.query'],'List events filtered by purchase date (today)',datetime(2044,2,29,8,10))
    bound={key:value for key,value,_,_ in result}
    assert bound=={'boughtEnabled':True,'boughtDateStart':'2044-02-29 00:00:00','boughtDateEnd':'2044-02-29 23:59:59'}
    result=filter_bindings(project,ids['Api.query'],'List events filtered by delivery date (September — December 2044)')
    bound={key:value for key,value,_,_ in result}
    assert bound=={'deliveryEnabled':True,'deliveryDateStart':'2044-09-01 00:00:00','deliveryDateEnd':'2044-12-31 23:59:59'}


def test_unresolved_route_suffix_and_method_do_not_broaden_dispatch():
    import pytest
    from baseline_closure import ann_paths,RouteWarning
    with pytest.warns(RouteWarning):
        assert ann_paths([{'name':'GetMapping','args':'(BASE + "/suffix")'}])==[]
    with pytest.warns(RouteWarning):
        assert ann_paths([{'name':'RequestMapping','args':'(value="/items",method=METHOD)'}])==[]
    assert ann_paths([{'name':'RequestMapping','args':'(path={}, method={})'}])==[('REQUEST',[''])]
    assert ann_paths([{'name':'RequestMapping','args':'(value="/a" + "/b", method=RequestMethod . PATCH)'}])==[('PATCH',['/a/b'])]


def test_integer_division_and_remainder_follow_java_sign_rules(tmp_path):
    from analyzer.engine import Engine
    project,db,ids=build(tmp_path,{'Api.java': '''@RestController class Api {
      @GetMapping("/quotient") int quotient(){return -7 / 3;}
      @GetMapping("/remainder") int remainder(){return -7 % 3;}
      @GetMapping("/fraction") double fraction(){return 7.0 / 2;}
    }'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.quotient'],{})==-2
    assert Engine(project,ScenarioState(db)).run(ids['Api.remainder'],{})==-1
    assert Engine(project,ScenarioState(db)).run(ids['Api.fraction'],{})==3.5
