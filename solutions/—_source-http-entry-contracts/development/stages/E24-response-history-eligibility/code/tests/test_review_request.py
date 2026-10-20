from dataclasses import FrozenInstanceError
import pytest

from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.engine import Engine
from analyzer.frontend import Frontend
from analyzer.request import Request, MISSING, grounded_request, BoundParameters
from analyzer.state import ScenarioState, U
from builders import build


SOURCE = '''import java.util.*; import org.springframework.web.bind.annotation.*;
class Api {
  @GetMapping("/items/{key}") String show(@PathVariable UUID key,@RequestParam List<String> tag){return tag.get(0)+"/"+tag.get(1);}
  @PostMapping("/items") String add(@RequestBody Input input){return input.name;}
} class Input {public String name;}'''
KEY = '12345678-1234-1234-1234-123456789abc'


def test_request_is_owned_and_deeply_immutable():
    data = {'values': ['before']}
    request = Request.http('server', 'POST', '/items', body=data)
    data['values'].append('outside')
    copy = request.body
    copy['values'].append('inside')
    assert request.body == {'values': ['before']}
    with pytest.raises(FrozenInstanceError):request.method = 'GET'


@pytest.mark.parametrize('key,entered', [(KEY, True), ('invalid-uuid', False)])
def test_initial_binding_matches_the_remote_binding(tmp_path, key, entered):
    project, db, ids = build(tmp_path, {'Api.java': SOURCE})
    request = Request.http('service', 'GET', '/items/'+key+'?tag=a&tag=b')
    engine = Engine(project, ScenarioState(db))
    result = engine.run(ids['Api.show'], request)
    assert (('', 'executes', ids['Api.show']) in engine.edges) is entered
    if entered:
        assert result == 'a/b'
        other = Engine(project, ScenarioState(db))
        assert other.bind_request(ids['Api.show'], request, 'remote') == engine.bind_request(ids['Api.show'], request, 'scenario')
    else:
        assert engine.outcome == 'HTTP binding failure'


@pytest.mark.parametrize('body', [MISSING, None])
def test_missing_or_null_required_body_fails_before_handler(tmp_path, body):
    project, db, ids = build(tmp_path, {'Api.java': SOURCE})
    engine = Engine(project, ScenarioState(db))
    engine.run(ids['Api.add'], Request.http('service', 'POST', '/items', body=body))
    assert engine.outcome == 'HTTP binding failure'
    assert ('', 'executes', ids['Api.add']) not in engine.edges


def test_grounded_and_explicit_requests_have_identical_arguments_and_graph(tmp_path):
    project, db, ids = build(tmp_path, {'Api.java': SOURCE})
    state = ScenarioState(db)
    grounder = ContractGrounder(project, Frontend(project), ContractIndex(project, Frontend(project)), None, {'facts': {}})
    proposals, _ = grounder.step('GET /items/'+KEY+'?tag=a&tag=b', state)
    assert len(proposals) == 1
    explicit = proposals[0]['request']
    inferred = grounded_request(project, ids['Api.show'], {'key': KEY, 'tag': ['a', 'b']})
    engines = [Engine(project, ScenarioState(db)) for _ in range(2)]
    assert [engine.run(ids['Api.show'], request) for engine, request in zip(engines, [explicit, inferred])] == ['a/b', 'a/b']
    assert engines[0].edges == engines[1].edges


def test_nl_invalid_uuid_is_preserved_for_binding_rejection(tmp_path):
    project, db, ids = build(tmp_path, {'Api.java': SOURCE})
    frontend = Frontend(project)
    grounder = ContractGrounder(project, frontend, ContractIndex(project, frontend), None, {'facts': {}})
    choices, _ = grounder.step('Show item with key "invalid-uuid"', ScenarioState(db))
    assert choices[0]['params']['key'] == 'invalid-uuid'
    request = grounded_request(project, ids['Api.show'], choices[0]['params'])
    engine = Engine(project, ScenarioState(db))
    engine.run(ids['Api.show'], BoundParameters(choices[0]['params'], request))
    assert engine.outcome == 'HTTP binding failure'


@pytest.mark.parametrize('actor,owner', [('student', 'StudentApi'), ('librarian', 'LibrarianApi')])
def test_actor_constrains_source_declared_role(tmp_path, actor, owner):
    source = '''class StudentApi { @Secured("ROLE_STUDENT") @PostMapping("/student/books") String reserve(){return "s";} }
    class LibrarianApi { @Secured("ROLE_LIBRARIAN") @PostMapping("/librarian/books") String reserve(){return "l";} }'''
    project, db, ids = build(tmp_path, {'Api.java': source})
    frontend = Frontend(project)
    grounder = ContractGrounder(project, frontend, ContractIndex(project, frontend), None, {'facts': {}})
    choices, _ = grounder.step('As a '+actor+', reserve book', ScenarioState(db))
    assert choices and {choice['entry'] for choice in choices} == {ids[owner+'.reserve']}
    assert choices[0]['actor'] == actor


@pytest.mark.parametrize('url,method,status', [('/wrong','GET',404),('/items/'+KEY,'POST',405)])
def test_dispatch_checks_route_and_verb_before_the_handler(tmp_path,url,method,status):
    project,db,ids=build(tmp_path,{'Api.java':SOURCE})
    engine=Engine(project,ScenarioState(db))
    engine.run(ids['Api.show'],Request.http('service',method,url))
    assert engine.http_responses[-1]['status']==status
    assert not engine.edges


def test_header_names_and_occurrences_are_case_insensitive():
    request=Request.http('service','GET','/',{'X-Name':'one','x-name':['two']})
    assert request.headers=={'x-name':['one','two']}


@pytest.mark.parametrize('media,status,entered',[('application/json',201,True),('text/plain',415,False),('application/x-www-form-urlencoded',415,False)])
def test_media_and_source_response_status(tmp_path,media,status,entered):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
    @PostMapping(value="/items", consumes="application/json") @ResponseStatus(HttpStatus.CREATED)
    String create(@RequestBody Input input){return input.name;}}
    class Input{public String name;}'''})
    engine=Engine(project,ScenarioState(db))
    result=engine.run(ids['Api.create'],Request.http('service','POST','/items',{'Content-Type':media},{'name':'A'}))
    assert engine.http_responses[-1]['status']==status
    assert (('', 'executes', ids['Api.create']) in engine.edges) is entered
    if entered:assert result=='A'


def test_source_exception_response_status(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api{
    @GetMapping("/items") Object read(){throw new Missing();}}
    @ResponseStatus(HttpStatus.NOT_FOUND) class Missing extends RuntimeException{}'''})
    engine=Engine(project,ScenarioState(db))
    engine.run(ids['Api.read'],Request.http('service','GET','/items'))
    assert engine.http_responses[-1]['status']==404


def test_explicit_http_json_body_uses_the_shared_request_binder(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':SOURCE})
    frontend=Frontend(project)
    grounder=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}})
    choices,_=grounder.step('POST /items\n{"name":"A"}',ScenarioState(db))
    assert len(choices)==1
    assert Engine(project,ScenarioState(db)).run(ids['Api.add'],choices[0]['request'])=='A'


def test_ui_nl_and_explicit_http_share_parameters_response_and_graph(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':SOURCE})
    plain=Frontend(project)
    nl=ContractGrounder(project,plain,ContractIndex(project,plain),None,{'facts':{}})
    choices,_=nl.step('Add item name "A"',ScenarioState(db))
    request_nl=grounded_request(project,ids['Api.add'],choices[0]['params'])
    (tmp_path/'ui.js').write_text('''function addItem(){$.ajax({url:"/items",type:"POST",contentType:"application/json",data:JSON.stringify({name:$("#name").val()})});}''')
    ui=Frontend(project);grounder=ContractGrounder(project,ui,ContractIndex(project,ui),None,{'facts':{}})
    choices,_=grounder.step('Add item name "A"',ScenarioState(db))
    assert choices[0]['site'] is not None
    request_ui=grounded_request(project,ids['Api.add'],choices[0]['params'],media_type=choices[0]['site']['content_type'])
    requests=[request_nl,request_ui,Request.http('service','POST','/items',body={'name':'A'})]
    engines=[Engine(project,ScenarioState(db)) for _ in requests]
    assert [engine.run(ids['Api.add'],request) for engine,request in zip(engines,requests)]==['A']*3
    assert engines[0].edges==engines[1].edges==engines[2].edges
    assert [engine.http_responses[-1]['status'] for engine in engines]==[200]*3


def test_existing_username_is_not_a_semantic_account_identifier(tmp_path):
    from analyzer.contracts import read_static_context
    project,db,ids=build(tmp_path,{'Api.java':'''class Api{@GetMapping("/accounts/{accountId}") String readAccount(@PathVariable String accountId){return accountId;}}'''})
    ui=Frontend(project);context=read_static_context({'context':'The username is alice and the userId is USER-1.'})
    grounder=ContractGrounder(project,ui,ContractIndex(project,ui),None,context)
    choices,_=grounder.step('Read account',ScenarioState(db))
    assert choices and choices[0]['params'].get('accountId',None) not in ('alice','USER-1')


def test_unknown_actor_preserves_endpoint_ambiguity(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class StudentApi{@Secured("ROLE_STUDENT") @PostMapping("/student/books") String reserve(){return "s";}}
      class LibrarianApi{@Secured("ROLE_LIBRARIAN") @PostMapping("/librarian/books") String reserve(){return "l";}}'''})
    ui=Frontend(project);grounder=ContractGrounder(project,ui,ContractIndex(project,ui),None,{'facts':{}})
    choices,detail=grounder.step('Reserve book',ScenarioState(db))
    assert {choice['entry'] for choice in choices}=={ids['StudentApi.reserve'],ids['LibrarianApi.reserve']}
    assert any('Ambiguous' in message for message in detail['unresolved'])
