"""Grounding oracles cover input origin, not just expected JSON shape."""
import pytest

from polygraph.analysis import analyze
from polygraph.grounding import Grounder
from polygraph.input_context import facts
from polygraph.kernel import Kernel
from polygraph.state import State
from polygraph.values import Unknown
from support import edge_set, fixture, scenario


@pytest.mark.parametrize('language', ['java', 'python'])
def test_narrative_credentials_and_absence_bind_for_both_stacks(tmp_path, language):
    java = '''import org.springframework.web.bind.annotation.*;
class Credentials {String username;String password;String verificationCode;}
@RestController class Accounts {
 @PostMapping("/login") String login(@RequestBody Credentials credentials){
  if(credentials.username.equals("dana") && credentials.password.equals("0042") && credentials.verificationCode.equals(""))return accepted();
  return rejected();
 }
 String accepted(){return "accepted";}
 String rejected(){return "rejected";}
}'''
    python = '''from fastapi import FastAPI
from sqlmodel import SQLModel
app=FastAPI()
class Credentials(SQLModel):
    username:str
    password:str
    verificationCode:str
def accepted():return "accepted"
def rejected():return "rejected"
@app.post("/login")
def login(credentials:Credentials):
    if credentials.username=="dana" and credentials.password=="0042" and credentials.verificationCode=="":return accepted()
    return rejected()
'''
    p, store, ids = fixture(tmp_path, {'Accounts.java' if language == 'java' else 'accounts.py': java if language == 'java' else python})
    p.skeleton['context'] = {'account': 'The pre-registered user is dana / 0042; no verification code at login.'}
    block, detail = analyze(p, store, {}, {'id': 'credentials', 'steps': [{'action': 'Log in with username and password'}]})
    owner = 'Accounts' if language == 'java' else 'accounts'
    login, accepted = ids[owner + '.login'], ids[owner + '.accepted']
    assert edge_set(block) == {('scenario:credentials', 'executes', login), ('scenario:credentials', 'executes', accepted), (login, 'calls', accepted)}
    step = detail['paths'][0]['steps'][0]
    assert step['response']['body'] == 'accepted'
    assert step['request']['body'] == {'username': 'dana', 'password': '0042', 'verificationCode': ''}
    assert all(binding['references'] for binding in step['grounding']['provenance'])


def test_conflicting_credentials_are_unknown_and_new_credentials_do_not_reuse_old_ones(tmp_path):
    p, store, _ = fixture(tmp_path, {'main.py': '''from fastapi import FastAPI
app=FastAPI()
@app.post("/login")
def login(username:str,password:str):return username
'''})
    p.skeleton['context'] = {'account': 'User: dana / 0042 or lee / 0099'}
    engine = Kernel(p, State(store)); engine.scenario_id = 'conflict'
    request, _ = Grounder(p).bind(engine, {}, {'action': 'Log in'}, {})
    assert isinstance(request['query']['username'], Unknown)
    assert isinstance(request['query']['password'], Unknown)
    p.skeleton['context'] = {'account': 'User: dana / 0042'}
    request, _ = Grounder(p).bind(engine, {}, {'action': 'Log in with new username and password'}, {})
    assert isinstance(request['query']['username'], Unknown)
    assert isinstance(request['query']['password'], Unknown)


def test_explicit_values_override_context_and_other_steps_cannot_supply_literals(tmp_path):
    p, store, _ = fixture(tmp_path, {'main.py': '''from fastapi import FastAPI
app=FastAPI()
@app.get("/record")
def read_record(record_id:int):return record_id
'''})
    engine = Kernel(p, State(store), context={'inputs': {'record_id': 17}})
    engine.scenario_id = 'value'
    request, binding = Grounder(p).bind(engine, {}, {'action': 'Read record', 'inputs': {'record_id': 23}}, {})
    assert request['query']['record_id'] == 23
    assert binding['provenance'][0]['source'] == 'provided-input'
    engine.context = {}
    request, _ = Grounder(p).bind(engine, {'description': 'Later read record_id=99'}, {'action': 'Read record'}, {})
    assert isinstance(request['query']['record_id'], Unknown)


def test_units_in_literal_cannot_fall_back_to_default_or_context(tmp_path):
    p, store, _ = fixture(tmp_path, {'main.py': '''from fastapi import FastAPI
app=FastAPI()
@app.get("/mass")
def read_mass(weightGrams:int=20):return weightGrams
'''})
    engine = Kernel(p, State(store), context={'narrative': {'weightGrams': 10}})
    request, _ = Grounder(p).bind(engine, {}, {'action': 'Read mass with weight grams=5 kg'}, {})
    assert isinstance(request['query']['weightGrams'], Unknown)


def test_context_distinguishes_system_clock_request_date_and_invalid_dates(tmp_path):
    p, _, _ = fixture(tmp_path, {})
    p.skeleton['context'] = {'date': 'All requests use 2 November 2026; system clock is 2026-10-17.', 'invalid': '2026-02-31'}
    selected, _, _ = facts(p, {})
    assert selected['clock']['value'] == '2026-10-17'
    assert selected['requestdate']['value'] == '2026-11-02'
    p.skeleton['context'] = {'account': 'User profile is at http://example.test/users'}
    assert 'username' not in facts(p, {})[0]


def test_header_alias_is_bound_to_header_and_body_string_is_not_a_dictionary(tmp_path):
    java = '''import org.springframework.web.bind.annotation.*;
@RestController class Echo {
 @PostMapping("/echo") String echo(@RequestHeader("X-Trace") String trace,@RequestBody String payload){return trace+":"+payload;}
}'''
    p, store, _ = fixture(tmp_path, {'Echo.java': java})
    _, detail = analyze(p, store, {}, {'id': 'headers', 'steps': [{'action': 'Create echo with trace="ref-1", payload="hello"'}]})
    step = detail['paths'][0]['steps'][0]
    assert step['request']['headers'] == {'X-Trace': 'ref-1'}
    assert step['request']['body'] == 'hello'
    assert step['response']['body'] == 'ref-1:hello'


def test_post_query_operation_is_retrieved_by_source_name_not_assumed_to_create(tmp_path):
    java = '''import org.springframework.web.bind.annotation.*;
@RestController class Invoice {
 @PostMapping("/query") String findInvoices(){return "found";}
 @PostMapping("/create") String createInvoice(){return "created";}
}'''
    p, store, ids = fixture(tmp_path, {'Invoice.java': java})
    block, detail = analyze(p, store, {}, {'id': 'query', 'steps': [{'action': 'Find invoices'}]})
    assert edge_set(block) == {('scenario:query', 'executes', ids['Invoice.findInvoices'])}
    assert detail['paths'][0]['steps'][0]['response']['body'] == 'found'


def test_identical_parameterless_contracts_stay_ambiguous_even_with_different_neighbours(tmp_path):
    p, store, ids = fixture(tmp_path, {'main.py': '''from fastapi import FastAPI
app=FastAPI()
@app.post("/a/report")
def create_report_a():return 1
@app.post("/b/report")
def create_report_b():return 2
def unrelated():return "create report create report create report"
'''})
    block, detail = analyze(p, store, {}, {'id': 'ambiguous', 'steps': [{'action': 'Create report'}]})
    assert len(detail['paths']) == 2
    assert {e[2] for e in edge_set(block)} == {ids['main.create_report_a'], ids['main.create_report_b']}


def test_implicit_method_dispatch_differs_in_java_and_python(tmp_path):
    p, store, ids = fixture(tmp_path / 'python', {'main.py': '''class Counter:
    def called(self):return 7
    def read(self):return called()
'''})
    key = p.method_by_id[ids['main.read']]
    engine = Kernel(p, State(store), decisions=('normal',)); engine.scenario_id = 'python'
    receiver = engine.create('Counter')
    engine.execute_method(key, receiver=receiver)
    assert not any(target == ids['main.called'] for _, _, target in engine.edges)
    java = '''import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
class Counter {
 final Logger logger=LoggerFactory.getLogger(getClass());
 static int called(){return 7;}
 static int read(){return called();}
}'''
    p, store, ids = fixture(tmp_path / 'java', {'Counter.java': java})
    engine = Kernel(p, State(store)); engine.scenario_id = 'java'
    engine.create('Counter')
    assert engine.execute_method(p.method_by_id[ids['Counter.read']]) == 7
    assert (ids['Counter.read'], 'calls', ids['Counter.called']) in engine.edges
    assert not any(d['code'] == 'unresolved-name' for d in engine.diagnostics)


def test_http_headers_keep_case_insensitivity_multiplicity_and_cross_service_body(tmp_path):
    java = '''import org.springframework.web.bind.annotation.*;
import org.springframework.http.*;
import org.springframework.web.client.RestTemplate;
@RestController class Caller {
 @PostMapping("/proxy") String proxy(@RequestHeader HttpHeaders input){
  HttpHeaders outbound=new HttpHeaders();
  outbound.set("X-Trace",input.getFirst("x-TRACE"));
  outbound.add("X-Note","first");outbound.add("x-note","second");
  if(outbound.get("X-NOTE").size()!=2)return "bad";
  HttpEntity<String> entity=new HttpEntity<>("payload",outbound);
  return new RestTemplate().exchange("http://backend/echo",HttpMethod.POST,entity,String.class).getBody();
 }
}'''
    python = '''from fastapi import FastAPI,Header,Body
app=FastAPI()
@app.post("/echo")
def echo(trace:str=Header(alias="X-Trace"),payload:str=Body()):return trace+":"+payload
'''
    p, store, ids = fixture(tmp_path, {'gateway/Caller.java': java, 'backend/main.py': python}, modules={'gateway': 'gateway', 'backend': 'backend'})
    block, detail = analyze(p, store, {}, scenario({'method': 'POST', 'path': '/proxy', 'module': 'gateway', 'headers': {'X-TRACE': 'trace-7'}}))
    caller, echo = ids['Caller.proxy'], ids['main.echo']
    assert edge_set(block) == {('scenario:arbitrary', 'executes', caller), ('scenario:arbitrary', 'executes', echo), (caller, 'remote', echo)}
    assert detail['paths'][0]['steps'][0]['response']['body'] == 'trace-7:payload'


def test_headers_only_http_entity_has_empty_body_and_forwards_header(tmp_path):
    java = '''import org.springframework.web.bind.annotation.*;
import org.springframework.http.*;
import org.springframework.web.client.RestTemplate;
@RestController class Caller {
 @GetMapping("/proxy") String proxy(){
  HttpHeaders h=new HttpHeaders();h.set("X-Trace","t9");
  return new RestTemplate().exchange("http://backend/echo",HttpMethod.GET,new HttpEntity<>(h),String.class).getBody();
 }
}'''
    python = '''from fastapi import FastAPI,Header
app=FastAPI()
@app.get("/echo")
def echo(trace:str=Header(alias="X-Trace")):return trace
'''
    p, store, ids = fixture(tmp_path, {'gateway/Caller.java': java, 'backend/main.py': python}, modules={'gateway': 'gateway', 'backend': 'backend'})
    block, detail = analyze(p, store, {}, scenario({'path': '/proxy', 'module': 'gateway'}))
    assert (ids['Caller.proxy'], 'remote', ids['main.echo']) in edge_set(block)
    assert detail['paths'][0]['steps'][0]['response']['body'] == 't9'


def test_repeated_login_words_in_an_unrelated_body_do_not_replace_login_contract(tmp_path):
    unrelated = '\n'.join('    print("login username password")' for _ in range(80))
    source = '''from fastapi import FastAPI
app=FastAPI()
@app.post("/login")
def authenticate(username:str,password:str):return "ok"
@app.delete("/leases/{id}")
def cancel_lease(id:int):
''' + unrelated + '\n    return "cancelled"\n'
    p, _, ids = fixture(tmp_path, {'main.py': source})
    ranked = Grounder(p).candidates('Log in with username and password')
    assert [p.methods[p.endpoints[i].method].skeleton_id for i, _ in ranked] == [ids['main.authenticate']]


@pytest.mark.parametrize('value', ['n=1,000', 'n=1/2', 'n=1.2.3', 'n=1-3', 'n=1 000'])
def test_unparsed_numeric_continuation_does_not_become_a_concrete_fragment(value):
    assert isinstance(Grounder.extract(value, 'n', 'int'), Unknown)


@pytest.mark.parametrize('value', ['0042', 'false', 'True'])
def test_string_literal_retains_zeros_and_boolean_spelling(value):
    assert Grounder.extract('username=' + value, 'username', 'str') == value


@pytest.mark.parametrize('version', ['5.3.4', '6.2.0', '7.0.0', ''])
def test_http_entity_integer_body_and_versioned_header_view(tmp_path, version):
    java = '''import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
@RestController class Echo {
 @GetMapping("/entity") int read(){
  HttpEntity<Integer> entity=new HttpEntity<>(42);
  try {entity.getHeaders().set("X-Trace","forbidden");return 0;}
  catch(UnsupportedOperationException error){return entity.getBody();}
 }
}'''
    p, store, _ = fixture(tmp_path, {'Echo.java': java})
    context = {'framework_versions': {'app': {'spring': version}}} if version else {}
    _, detail = analyze(p, store, context, scenario({'path': '/entity'}))
    assert {path['steps'][0]['response']['body'] for path in detail['paths']} == ({42} if version else {0, 42})
    assert bool([d for path in detail['paths'] for d in path['diagnostics'] if d['code'] == 'framework-version-unknown']) == (not version)


def test_maven_explicit_version_is_service_local_and_invalidates_ir_cache(tmp_path):
    sources = {}
    for service, version in [('left', '5.3.4'), ('right', '6.2.0')]:
        sources[service + '/pom.xml'] = '<project xmlns="http://maven.apache.org/POM/4.0.0"><properties><framework>' + version + '</framework></properties><dependencies><dependency><groupId>org.springframework</groupId><artifactId>spring-web</artifactId><version>${framework}</version></dependency></dependencies></project>'
        sources[service + '/Example.java'] = 'class Example {}'
    p, _, _ = fixture(tmp_path, sources, modules={'left': 'left', 'right': 'right'})
    assert p.framework_versions == {'left': {'spring': '5.3.4'}, 'right': {'spring': '6.2.0'}}
    before = p.fingerprint
    path = p.root / 'right/pom.xml'
    path.write_text(path.read_text().replace('6.2.0', '7.0.0'))
    from polygraph.project import Project
    changed = Project(p.root, p.skeleton)
    assert changed.framework_versions['right']['spring'] == '7.0.0'
    assert changed.fingerprint != before


def test_unsupported_read_only_header_list_does_not_expose_a_mutable_list(tmp_path):
    java = '''import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
@RestController class Echo {
 int after(){return 99;}
 @GetMapping("/entity") int read(){
  HttpHeaders h=new HttpHeaders();h.set("X","one");
  HttpEntity<Integer> entity=new HttpEntity<>(42,h);
  entity.getHeaders().get("X").add("two");return after();
 }
}'''
    p, store, ids = fixture(tmp_path, {'Echo.java': java})
    block, detail = analyze(p, store, {'framework_versions': {'app': {'spring': '5.3.4'}}}, scenario({'path': '/entity'}))
    assert not any(target == ids['Echo.after'] for _, _, target in edge_set(block))
    assert detail['status'] == 'partial' and detail['must'] == []
    assert any(d['code'] == 'unsupported' and 'header list' in d['message'] for path in detail['paths'] for d in path['diagnostics'])
