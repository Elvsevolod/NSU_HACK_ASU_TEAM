from analyzer.engine import Engine
from analyzer.state import ScenarioState
from analyzer.contracts import ContractIndex
from analyzer.frontend import Frontend
from builders import build


def test_unmodeled_method_security_is_visible_instead_of_confirmed(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      @PreAuthorize("hasRole('ADMIN')") @GetMapping("/items") String entry(){return "ok";}}'''})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert engine.approximate and any('PreAuthorize' in w for w in engine.warnings)


def test_unmodeled_validation_and_custom_http_codecs_are_visible(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      @PostMapping("/items") Item entry(@RequestBody @Valid Item input){return input;}}
      @JsonDeserialize(using=CustomDecoder.class) class Item {String name;}'''})
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{'name':'supplied'})
    assert engine.approximate
    assert any('validation' in w for w in engine.warnings) and any('JsonDeserialize' in w for w in engine.warnings)


def test_unsupported_profile_expression_is_retained_as_possible_and_warned(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''@Profile("default & !production") class Api {
      @GetMapping("/items") String entry(){return "ok";}}'''})
    assert any(c['entry']==ids['Api.entry'] for c in ContractIndex(project,Frontend(project)).contracts.values())
    engine=Engine(project,ScenarioState(db));engine.run(ids['Api.entry'],{})
    assert engine.approximate and any('profile expression' in w for w in engine.warnings)
