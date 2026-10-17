import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.state import ScenarioState, U
from builders import build


def calls(engine):
    return {target for _,relation,target in engine.edges if relation=='calls'}


@pytest.mark.parametrize('expression,wanted',[
 ('rest.getForObject("http://service/records",String.class)','Api.get'),
 ('rest.postForObject("http://service/records","payload",String.class)','Api.post'),
 ('rest.exchange("http://service/records",HttpMethod.GET,null,String.class)','Api.get')])
def test_http_client_operation_preserves_the_verb(tmp_path,expression,wanted):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      @GetMapping("/records") String get(){return "read";}
      @PostMapping("/records") String post(@RequestBody String body){return body;}}
    class Caller {RestTemplate rest;Object entry(){return '''+expression+''';}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Caller.entry'],{})
    targets={target for o in outcomes for _,relation,target in o['engine'].edges if relation=='remote'}
    assert targets=={ids[wanted]}


@pytest.mark.parametrize('failure',[
 'Optional.empty().orElseThrow()',
 'Optional.empty().orElseThrow(()->new IllegalArgumentException())',
 '((String)null).equals("x")'])
def test_guaranteed_value_failure_stops_following_calls(tmp_path,failure):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {void entry(){'''+failure+''';after();}void after(){}}'''})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert ids['Api.after'] not in calls(engine)
    assert engine.outcome=='uncaught application exception'


def test_http_error_status_does_not_become_a_successful_body(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      @GetMapping("/records") ResponseEntity<String> get(){return ResponseEntity.status(HttpStatus.NOT_FOUND).body("missing");}}
    class Caller {RestTemplate rest;void entry(){rest.getForObject("http://service/records",String.class);after();}void after(){}}'''})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Caller.entry'],{})
    assert ids['Caller.after'] not in calls(engine)
    assert engine.outcome=='uncaught application exception'


@pytest.mark.parametrize('continues',[False,True])
def test_filter_requires_a_source_call_to_the_chain(tmp_path,continues):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {@GetMapping("/records") void entry(){work();}void work(){}}
    class Gate extends OncePerRequestFilter {
      void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain){'''+
      ('chain.doFilter(req,res);' if continues else '')+'''}}'''})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert (ids['Api.work'] in calls(engine)) is continues


def test_switch_return_exits_the_method_and_default_does_not_shadow_a_case(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      int entry(){switch(2){default:wrong();break;case 2:return chosen();}after();return 3;}
      int chosen(){return 7;}void wrong(){}void after(){}}'''})
    engine=Engine(project,ScenarioState(db));result=engine.run(ids['Api.entry'],{})
    assert result==7
    assert ids['Api.after'] not in calls(engine) and ids['Api.wrong'] not in calls(engine)


def test_typed_catch_selects_the_first_assignable_exception_handler(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      void entry(){try {throw new IllegalArgumentException();}
        catch(IllegalStateException ex){wrong();}catch(RuntimeException ex){right();}}
      void wrong(){}void right(){}}'''})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert ids['Api.right'] in calls(engine) and ids['Api.wrong'] not in calls(engine)


def test_switch_fallthrough_break_and_arrow_expression(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      int entry(){int answer=0;switch(1){case 1:answer=2;case 2:answer+=3;break;default:answer=8;}
        return answer+(switch(9){case 1 -> 30;default -> 10;});}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})==15


def test_finally_runs_when_a_catch_throws_and_outer_catch_uses_that_type(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {void entry(){try {
      try {throw new IllegalArgumentException();}catch(IllegalArgumentException ex){fail();}finally {cleanup();}
    }catch(IllegalStateException ex){recover();}after();}
    void fail(){throw new IllegalStateException();}void cleanup(){}void recover(){}void after(){}}'''})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert {ids[name] for name in ['Api.cleanup','Api.recover','Api.after']}<=calls(engine)


def test_source_exception_subclass_and_multicatch_are_resolved(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class CustomFailure extends IllegalArgumentException {}
    class Api {int entry(){try {throw new CustomFailure();}catch(IllegalStateException ex){return 1;}
      catch(ArithmeticException | IllegalArgumentException ex){return 2;}}}'''})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==2


def test_controller_executes_inside_the_filter_chain_before_its_cleanup(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {@Autowired Store store;
      @GetMapping("/invoices") void entry(){if(store.findById("new")!=null){present();}else {missing();}}
      void present(){}void missing(){}}
    class Gate extends OncePerRequestFilter {@Autowired Store store;
      void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain){
        Invoice row=new Invoice();row.id="new";store.save(row);chain.doFilter(req,res);store.deleteById("new");}}
    @Entity @Table(name="invoices") class Invoice {@Id String id;}
    interface Store extends JpaRepository<Invoice,String>{Invoice save(Invoice row);Invoice findById(String id);void deleteById(String id);}
    '''},rows={'invoices':[]})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert ids['Api.present'] in calls(engine) and ids['Api.missing'] not in calls(engine)
    assert engine.state.database.rows(project.nodes['res:table:service.invoices'])==[]


def test_failed_http_request_does_not_run_the_success_callback(tmp_path):
    from analyzer.__main__ import analyze
    from analyzer.frontend import Frontend
    from analyzer.contracts import ContractGrounder, ContractIndex
    project,db,_=build(tmp_path,{'Api.java':'''class Api {
      @GetMapping("/invoices") ResponseEntity<String> list(){return ResponseEntity.status(404).body("missing");}}'''})
    (tmp_path/'page.html').write_text('<script src="ui.js"></script>')
    (tmp_path/'ui.js').write_text('function list(){$.ajax({url:"/invoices",type:"GET",success:function(res){sessionStorage.setItem("success","yes");}});}')
    frontend=Frontend(project);observed=[]
    def capture(project,state,entry,params,limit):
        paths=run_paths(project,state,entry,params,limit)
        observed.extend(paths)
        return paths
    analyze(project,frontend,ContractIndex(project,frontend),None,db,{'facts':{},'unresolved':[]},
      {'id':'other','steps':[{'n':1,'action':'List invoices'}]},grounder_type=ContractGrounder,path_runner=capture)
    assert observed[0]['engine'].outcome=='HTTP error response'
    assert 'success' not in observed[0]['state'].browser['storage']


@pytest.mark.parametrize('body,expected',[
 ('int n=Integer.MAX_VALUE;return n+1;',-2147483648),
 ('long n=Long.MAX_VALUE;return n+1;',-9223372036854775808),
 ('long n=2147483647L;return n+1;',2147483648),
 ('int n=Integer.MAX_VALUE;n++;return n;',-2147483648),
 ('int n=2147483647;n+=2L;return n;',-2147483647),
 ('int n=-2147483648;return n/-1;',-2147483648)])
def test_java_integer_width_controls_overflow(tmp_path,body,expected):
    project,db,ids=build(tmp_path,{'Api.java':'class Api {long entry(){'+body+'}}'})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==expected


def test_guaranteed_integer_division_failure_is_catchable_and_stops_the_body(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {void entry(){try {int zero=0;int n=5/zero;after();}
      catch(ArithmeticException ex){recover();}}void after(){}void recover(){}}'''})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert ids['Api.after'] not in calls(engine) and ids['Api.recover'] in calls(engine)


def test_generated_uuid_has_uuid_string_structure_without_a_fake_runtime_value(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.UUID;
      class Api {String entry(){String id=UUID.randomUUID().toString();if(id.length()==36){right();}else {wrong();}return id;}
      void right(){}void wrong(){}}'''})
    engine=Engine(project,ScenarioState(db));value=engine.run(ids['Api.entry'],{})
    assert ids['Api.right'] in calls(engine) and ids['Api.wrong'] not in calls(engine)
    assert isinstance(value,dict) and value['__length__']==36
    assert value['__generation__']=='java.util.UUID.randomUUID'


def test_a_null_expression_does_not_dereference_a_source_static_method(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {int entry(){Utility absent=null;return absent.answer();}}
      class Utility {static int answer(){return 42;}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})==42
    assert engine.outcome=='returned'


def test_json_request_body_is_decoded_into_the_receiving_dto_type(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      @PostMapping("/customers") String create(@RequestBody ServerDto input){return input.getId();}}
    class Caller {RestTemplate rest;String entry(){ClientDto value=new ClientDto();value.id="opaque";
      String json=new ObjectMapper().writeValueAsString(value);
      return rest.postForObject("http://service/customers",new HttpEntity(json),String.class);}}
    class ClientDto {String id;}class ServerDto {String id;String getId(){return id;}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='opaque'
    assert ids['ServerDto.getId'] in calls(engine)


def test_unresolved_route_value_is_unknown_instead_of_a_fabricated_null(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      @GetMapping("/records/{key}") String get(@PathVariable String key){return key;}}
    class Caller {RestTemplate rest;String entry(){return rest.getForObject(unknownUrl(),String.class);}
      String unknownUrl(){return opaque();}String opaque(){return null;}}'''})
    # A skeleton may supply a possible target despite an unresolved URL. It
    # cannot supply a concrete value for the route parameter.
    call=next(site for site in project.sites[ids['Caller.entry']] if project.nodes[site]['callee']=='getForObject')
    project.edges[call]['remote_call'].add(ids['Api.get'])
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{}) is U
    assert any('unresolved remote route parameter: key' in message for message in engine.warnings)
