from analyzer.engine import Engine
from analyzer.frontend import Frontend
from analyzer.state import ScenarioState, U
from analyzer.symbolic_text import concat_text, http_text_parts
from builders import build


def test_empty_inner_url_segment_is_preserved_without_crashing():
    atom={'__symbol__':'id','__type__':'String','__uuid_text__':True,'__length__':36}
    url=concat_text('http://service/invoices//',atom)
    assert http_text_parts(url)['segments']==['invoices','',atom]


def test_generated_identity_survives_http_path_and_repository_lookup(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.UUID;import org.springframework.web.client.RestTemplate;import org.springframework.web.client.RestOperations;class Api {@Autowired Store store;
      @GetMapping("/invoices/{id}") Invoice get(@PathVariable String id){
        if(id.length()!=36){wrong();}return store.findById(id);}
      void wrong(){}}
    class Caller {@Autowired Store store;RestTemplate rest;Invoice entry(){
      Invoice row=new Invoice();row.id=UUID.randomUUID().toString();store.save(row);
      return rest.getForObject("http://service/invoices/"+row.id,Invoice.class);}}
    @Entity @Table(name="invoices") class Invoice {@Id public String id;}
    interface Store extends JpaRepository<Invoice,String>{Invoice save(Invoice row);Invoice findById(String id);}
    '''},rows={'invoices':[]})
    engine=Engine(project,ScenarioState(db));result=engine.run(ids['Caller.entry'],{})
    assert result is not U and result['id']['__uuid_text__'] is True
    rows=engine.state.database.rows(project.nodes['res:table:service.invoices'])
    assert result['id']==rows[0]['id']
    assert ids['Api.get'] in {target for _,rel,target in engine.edges if rel=='executes'}
    assert ids['Api.wrong'] not in {target for _,rel,target in engine.edges if rel=='calls'}


def test_browser_url_keeps_uuid_identity_and_relative_path_binding(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      @GetMapping("/invoices/{id}/events") void get(@PathVariable String id){}}'''})
    state=ScenarioState(db);frontend=Frontend(project)
    atom={'__symbol__':'id','__type__':'String','__uuid_text__':True,'__length__':36}
    state.browser['form']['id']=atom
    url=frontend.evaluate('"/invoices/"+this.id+"/events"',state)
    assert Engine(project,state).path_parameters(ids['Api.get'],url)=={'id':atom}
    assert frontend.evaluate('this.id.length',state)==36


def test_unknown_text_is_not_certified_as_a_delimiter_free_path(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'class Api {@GetMapping("/invoices/{id}") void get(@PathVariable String id){}}'})
    state=ScenarioState(db);frontend=Frontend(project)
    state.browser['form']['id']={'__symbol__':'text','__type__':'String'}
    url=frontend.evaluate('"/invoices/"+this.id',state)
    assert Engine(project,state).path_parameters(ids['Api.get'],url)=={}
