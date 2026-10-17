from analyzer.state import Database
from analyzer.contracts import ContractGrounder,ContractIndex
from analyzer.frontend import Frontend
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from builders import build


def test_mysql_insert_column_order_and_doubled_quote_are_preserved(tmp_path):
    dump=tmp_path/'initial.sql'
    dump.write_text('''USE `service`;
    CREATE TABLE `people` (
      `id` varchar(80),
      `name` varchar(80)
    ) ENGINE=InnoDB;
    INSERT INTO `people` (`name`,`id`) VALUES ('O''Brien','one'),('Dianne\\\'s','two');
    ''')
    database=Database(dump)
    assert database.tables[('service','people')]==[{'id':'one','name':"O'Brien"},{'id':'two','name':"Dianne's"}]
    assert not database.warnings and not database.unknown_tables


def test_unsupported_insert_is_not_silently_treated_as_an_empty_table(tmp_path):
    dump=tmp_path/'initial.sql'
    dump.write_text('''USE `service`;
    CREATE TABLE `people` (
      `id` varchar(80)
    ) ENGINE=InnoDB;
    INSERT IGNORE INTO `people` VALUES ('one');
    ''')
    database=Database(dump)
    assert database.warnings and database.unknown_tables=={('service','people')}


def test_scenario_title_and_description_resolve_an_unqualified_action(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class CustomerController {
      @PostMapping("/customers") String create(@RequestBody Input input){return input.name;}}
    class ProductController {@PostMapping("/products") String create(@RequestBody Input input){return input.name;}}
    class Input {String name;}'''})
    frontend=Frontend(project);index=ContractIndex(project,frontend)
    grounder=ContractGrounder(project,frontend,index,None,{'facts':{}})
    for noun in ('Customer','Product'):
        proposals,_=grounder.step('Create name="Alpha"',ScenarioState(db),'Create '+noun.lower())
        assert proposals[0]['entry']==ids[noun+'Controller.create']
    # An explicit step entity takes precedence over an unrelated scenario title.
    assert grounder.step('Create product name="Alpha"',ScenarioState(db),'Create customer')[0][0]['entry']==ids['ProductController.create']


def test_inactive_controller_is_excluded_from_contracts_and_request_execution(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''@Profile("production") class HiddenController {
      @GetMapping("/hidden") String read(){return "hidden";}}
    class Api {@GetMapping("/visible") String read(){return "visible";}}'''})
    index=ContractIndex(project,Frontend(project))
    assert all(contract['entry']!=ids['HiddenController.read'] for contract in index.contracts.values())
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['HiddenController.read'],{}) is U
    assert not engine.edges and engine.outcome=='inactive request handler'


def test_unsupported_browser_clients_and_sfc_syntax_are_visible(tmp_path):
    project,_,_=build(tmp_path,{'Api.java':'class Api {@GetMapping("/items") String list(){return "ok";}}'})
    (tmp_path/'ui.js').write_text('fetch("/items");axios.get("/items");')
    (tmp_path/'Items.vue').write_text('<template><button>List</button></template><script>fetch("/items")</script>')
    frontend=Frontend(project)
    assert any('HTTP client fetch:' in message for message in frontend.unsupported)
    assert any('HTTP client axios.get:' in message for message in frontend.unsupported)
    assert any('syntax .vue:' in message for message in frontend.unsupported)
    assert set(frontend.unsupported)<=set(frontend.warnings)


def test_explicit_input_named_sample_is_allowed_but_reference_gold_stays_blocked(tmp_path,monkeypatch):
    import offline_run
    import pytest
    root=tmp_path/'sample';root.mkdir()
    monkeypatch.setattr(offline_run,'declared_inputs',[(root,True)])
    offline_run.audit('open',(str(root/'Api.java'),'r',0))
    gold=root/'gold';gold.mkdir()
    monkeypatch.setattr(offline_run,'protected_gold',gold)
    with pytest.raises(PermissionError):offline_run.audit('open',(str(gold/'answer.json'),'r',0))


def test_formatter_patterns_are_honored_or_explicitly_unsupported(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      String decimal(){return new DecimalFormat("0.000").format(new BigDecimal("1.25"));}
      String date(){return new SimpleDateFormat("dd/MM/yyyy").format(new Date(0));}
      String unsupported(){return new DecimalFormat("0.0E0").format(4.5);}}'''})
    decimal=Engine(project,ScenarioState(db))
    assert decimal.run(ids['Api.decimal'],{})=='1.250'
    date=Engine(project,ScenarioState(db))
    assert date.run(ids['Api.date'],{})=='01/01/1970'
    unsupported=Engine(project,ScenarioState(db))
    assert unsupported.run(ids['Api.unsupported'],{}) is U
    assert any('unsupported call:' in warning and 'format' in warning for warning in unsupported.warnings)
    assert any('locale/time zone' in warning for warning in date.warnings)
