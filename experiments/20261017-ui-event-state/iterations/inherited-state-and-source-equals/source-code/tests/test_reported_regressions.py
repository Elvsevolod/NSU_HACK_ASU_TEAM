"""Independent reproductions of the user's portability findings."""
from analyzer.engine import Engine
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex
from analyzer.models import unwrap
from analyzer.state import ScenarioState
from analyzer.__main__ import analyze
from analyzer.contracts import ContractGrounder
from builders import build


def test_mapping_http_methods_and_only_path_attributes(tmp_path):
    sources = {'Api.java': '''@RestController @RequestMapping(path={"/api", "/v2"}) class Api {
      @RequestMapping(value="/pets/{id}", method=RequestMethod.GET, produces="application/json")
      String read(@PathVariable String id) { return id; }
      @RequestMapping(path="/pets/{id}", method={RequestMethod.PUT, RequestMethod.PATCH}, consumes="application/json")
      String edit(@PathVariable String id) { return id; }
      @RequestMapping(value="/pets/{id}", method=RequestMethod.DELETE, headers="x=value")
      String remove(@PathVariable String id) { return id; }
    }'''}
    project, _, ids = build(tmp_path, sources)
    for prefix in ('/api', '/v2'):
        for verb, name in [('GET','read'), ('PUT','edit'), ('PATCH','edit'), ('DELETE','remove')]:
            assert project.ix.handlers_for(verb, prefix + '/pets/12') == {ids['Api.' + name]}
        assert project.ix.handlers_for('POST', prefix + '/pets/12') == set()
    assert all('application' not in '/'.join(route) and 'x=value' not in route
               for _, _, route in project.ix.handlers)


def test_class_and_method_request_method_sets_combine_by_union(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': '''
      @RequestMapping(value="/reports", method=RequestMethod.GET) class Api {
        @RequestMapping("/latest") String read() { return "yes"; }
        @RequestMapping(value="/refresh", method=RequestMethod.POST) String refresh() { return "yes"; }
      }'''})
    assert project.ix.handlers_for('GET', '/reports/latest') == {ids['Api.read']}
    assert project.ix.handlers_for('DELETE', '/reports/latest') == set()
    assert project.ix.handlers_for('GET', '/reports/refresh') == {ids['Api.refresh']}
    assert project.ix.handlers_for('POST', '/reports/refresh') == {ids['Api.refresh']}
    assert project.ix.handlers_for('DELETE', '/reports/refresh') == set()


def test_list_entity_is_not_list_of_related_entity_types(tmp_path):
    source = {'Api.java': '''@RestController @RequestMapping("/api/pets") class PetRestController {
      @GetMapping("") ResponseEntity<Collection<Pet>> getPets() { return null; }
      @GetMapping("/{petId}") ResponseEntity<Pet> getPet(@PathVariable int petId) {return null;}
      @GetMapping("/lastname/{lastName}") ResponseEntity<Collection<Pet>> getPetsList(@PathVariable String petLastName){return null;}
      @GetMapping("/petTypes") ResponseEntity<Collection<PetType>> getPetTypes() { return null; }
    }
    @RestController @RequestMapping("/api/petTypes") class PetTypeRestController {
      @GetMapping("") ResponseEntity<Collection<PetType>> getAllPetTypes() { return null; }
      @GetMapping("/{petTypeId}") ResponseEntity<PetType> getPetType(@PathVariable int petTypeId){return null;}
    }
    class Pet { String id; } class PetType { String id; }'''}
    project, _, ids = build(tmp_path, source)
    index = ContractIndex(project, Frontend(project))
    assert index.rank('List all pets')[0][2]['entry'] == ids['PetRestController.getPets']
    assert index.rank('List all pet types')[0][2]['entry'] == ids['PetTypeRestController.getAllPetTypes']


def test_repository_list_keeps_65th_row_and_correct_branch(tmp_path):
    sources = {'Api.java': '''@RestController class Api {
      @Autowired ItemStore repository;
      @GetMapping("/items") String check() {
        List<Item> rows = repository.findAll();
        if (rows.size() > 64) { return large(); }
        return small();
      }
      String large() { return "large"; }
      String small() { return "small"; }
    }
    @Entity @Table(name="items") class Item { @Id String key; }
    interface ItemStore extends JpaRepository<Item,String> { List<Item> findAll(); }
    '''}
    project, db, ids = build(tmp_path, sources, rows={'items':[{'key':str(i)} for i in range(65)]})
    engine = Engine(project, ScenarioState(db))
    assert engine.run(ids['Api.check'], {}) == 'large'
    assert (ids['Api.check'], 'calls', ids['Api.large']) in engine.edges
    assert (ids['Api.check'], 'calls', ids['Api.small']) not in engine.edges
    assert not engine.approximate


def test_plain_body_property_preserves_entity_across_steps(tmp_path):
    sources = {'Api.java': '''@RestController class Api {
      @PostMapping("/messages") Message create(@RequestBody Message input) { return input; }
      @GetMapping("/messages/{id}") String read(@PathVariable String id) { return id; }
    } class Message { @Id String id; String body; }'''}
    project, db, ids = build(tmp_path, sources)
    frontend = Frontend(project)
    scenario = {'id':'letters', 'steps':[
      {'n':1,'action':'Create message id "m-9" body "Hello"'},
      {'n':2,'action':'Read new message'}]}
    _, report = analyze(project, frontend, ContractIndex(project,frontend), None, db,
        {'facts':{},'unresolved':[]}, scenario, grounder_type=ContractGrounder)
    first = report['steps'][0]['alternatives'][0]
    second = report['steps'][1]['alternatives'][0]
    assert first['result']['id'] == 'm-9'
    assert second['parameters']['id'] == 'm-9'
    assert not second['unresolved']
    assert unwrap({'body':'ordinary','id':'m-9'}) == {'body':'ordinary','id':'m-9'}
    assert unwrap({'__type__':'Letter','body':'ordinary','id':'m-9'})['id'] == 'm-9'
    assert unwrap({'__type__':'ResponseEntity','body':{'id':'m-9'}}) == {'id':'m-9'}
