from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex, explicit_value
from analyzer.state import U
from builders import build


def test_static_path_beats_same_length_variable_path_and_keeps_real_id(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': '''class Api {
      @GetMapping("/parcels/refund/{id}") String estimate(@PathVariable String id){return id;}
      @GetMapping("/parcels/{id}/{user}") String cancel(@PathVariable String id,@PathVariable String user){return id;}
    }'''})
    assert project.ix.handlers_for('GET','/parcels/refund/p7') == {ids['Api.estimate']}
    assert project.ix.handlers_for('GET','/parcels/p7/u4') == {ids['Api.cancel']}
    (tmp_path/'ui.js').write_text('''function estimate(id){
      $.ajax({url:"/parcels/refund/"+id,type:"GET"});
    }''')
    site=next(iter(Frontend(project).sites.values()))
    assert site['handlers']==[ids['Api.estimate']]


def test_literal_path_priority_is_scoped_by_service_and_method(tmp_path):
    project, _, ids = build(tmp_path, {'Api.java': '''class Api {
      @GetMapping("/items/current") String current(){return "current";}
      @PostMapping("/items/{id}") String save(@PathVariable String id){return id;}
      @GetMapping("/items/{id}") String lookup(@PathVariable String id){return id;}
    }'''})
    assert project.ix.handlers_for('GET','/items/current') == {ids['Api.current']}
    assert project.ix.handlers_for('POST','/items/current') == {ids['Api.save']}
    assert project.ix.handlers_for(None,'/items/current') == {ids['Api.current'],ids['Api.save']}


def test_request_operation_outweighs_related_operation_in_controller_name(tmp_path):
    project, _, ids = build(tmp_path, {'RescheduleController.java': '''class RescheduleController {
      @PostMapping("/reschedule") String reschedule(){return "changed";}
      @PostMapping("/difference") String payDifference(){return "paid";}
    }'''})
    assert ContractIndex(project,Frontend(project)).rank('Reschedule the paid delivery')[0][2]['entry'] == ids['RescheduleController.reschedule']


def test_field_description_is_not_an_unquoted_string_literal():
    assert explicit_value("Change the recipient's name and phone number",'phone','String') == (U,'')
    assert explicit_value('Update the delivery date','delivery','String') == (U,'')
    assert explicit_value('Change phone to a new number','phone','String') == (U,'')
    assert explicit_value('Set phone="number"','phone','String') == ('number','phone="number"')
