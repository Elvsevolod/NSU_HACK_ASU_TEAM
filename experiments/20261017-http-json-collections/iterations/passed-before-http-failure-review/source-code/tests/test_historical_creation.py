from analyzer.__main__ import analyze
from analyzer.contracts import ContractGrounder, ContractIndex
from analyzer.frontend import Frontend
from analyzer.paths import run_paths
from builders import build


def test_past_creation_identity_survives_later_uncertain_table_state(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import java.util.UUID;class Api {
      @Autowired InvoiceStore store;
      @PostMapping("/invoices") String create(@RequestBody Invoice input){
        input.id=UUID.randomUUID().toString();store.save(input);return "accepted";}
      @GetMapping("/invoices/{invoiceId}") Invoice read(@PathVariable String invoiceId){return store.findById(invoiceId);}
    } @Entity @Table(name="invoices") class Invoice {@Id String id;}
    interface InvoiceStore extends JpaRepository<Invoice,String> {Invoice save(Invoice input);Invoice findById(String id);}'''},rows={'invoices':[]})
    def invalidate_after_creation(p,state,entry,params,limit):
        outcomes=run_paths(p,state,entry,params,limit)
        for outcome in outcomes:
            if entry==ids['Api.create']:
                rows=outcome['state'].database.rows(p.nodes['res:table:service.invoices'])
                outcome['state'].database.invalidate(rows)
                outcome['engine'].approximate=True
                outcome['engine'].warnings.add('simulated later unsupported write')
        return outcomes
    frontend=Frontend(project)
    _,report=analyze(project,frontend,ContractIndex(project,frontend),None,db,{'facts':{},'unresolved':[]},
      {'id':'invoices','steps':[{'n':1,'action':'Create invoice'},{'n':2,'action':'Read the new invoice'}]},
      grounder_type=ContractGrounder,path_runner=invalidate_after_creation)
    created=report['steps'][0]['alternatives'][0]['created_objects'][0]
    read=report['steps'][1]['alternatives'][0]
    assert created['__persistence_observation__']=='unknown'
    assert read['parameters']['invoiceId']==created['id']
    assert read['bindings']['invoiceId']['reference'].startswith('history[0].created_objects')
    assert any('unknown' in item.lower() for item in read['unresolved'])
    # The retained historical identity never resurrects the database row.
    assert read['result'] is None or str(read['result']).startswith('Unknown')


def test_transactional_save_then_throw_does_not_leave_a_certain_live_row(tmp_path):
    from analyzer.engine import Engine
    from analyzer.state import ScenarioState, U
    project,db,ids=build(tmp_path,{'Api.java':'''@Transactional class Api {
      @Autowired InvoiceStore store;
      @PostMapping("/invoices") String create(@RequestBody Invoice input){
        input.id="allocated";store.save(input);throw new RuntimeException();}
      @GetMapping("/invoices/{invoiceId}") Invoice read(@PathVariable String invoiceId){return store.findById(invoiceId);}
    } @Entity @Table(name="invoices") class Invoice {@Id String id;}
    interface InvoiceStore extends JpaRepository<Invoice,String> {Invoice save(Invoice input);Invoice findById(String id);}'''},rows={'invoices':[]})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.create'],{}) is U
    assert engine.created_objects[0]['id']=='allocated'
    assert engine.state.database.rows(project.nodes['res:table:service.invoices']) is None
    assert any('rollback/commit is unknown' in warning for warning in engine.warnings)
    next_request=Engine(project,engine.state)
    assert next_request.run(ids['Api.read'],{'invoiceId':'allocated'}) is U


def test_created_identity_does_not_claim_a_live_row_after_a_modeled_delete(tmp_path):
    project,db,_=build(tmp_path,{'Api.java':'''class Api {
      @Autowired InvoiceStore store;
      @PostMapping("/invoices") String create(@RequestBody Invoice input){
        input.id="allocated";store.save(input);store.deleteById(input.id);return "accepted";}
    } @Entity @Table(name="invoices") class Invoice {@Id String id;}
    interface InvoiceStore extends JpaRepository<Invoice,String> {Invoice save(Invoice input);void deleteById(String id);}
    '''},rows={'invoices':[]})
    frontend=Frontend(project)
    _,report=analyze(project,frontend,ContractIndex(project,frontend),None,db,{'facts':{},'unresolved':[]},
      {'id':'invoices','steps':[{'n':1,'action':'Create invoice'}]},grounder_type=ContractGrounder)
    alternative=report['steps'][0]['alternatives'][0]
    assert alternative['created_objects'][0]['__persistence_observation__']=='modeled_absent'
    assert any('row is absent' in issue for issue in alternative['unresolved'])
    assert not any('current persistence is unknown' in issue for issue in alternative['unresolved'])
