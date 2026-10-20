from copy import deepcopy

from analyzer.paths import join_states
from analyzer.provenance import history_value, selected_field
from analyzer.selection import selected_objects
from analyzer.state import ScenarioState, U
from builders import build, LIBRARY


def test_selection_requires_entity_and_observed_identity(tmp_path):
    sources = dict(LIBRARY)
    sources['Reader.java'] = 'class Reader { @Id String key; String title; }'
    project, _, ids = build(tmp_path, sources)
    history = [{'action': 'List books', 'result': [
        {'__type__': 'Book', 'key': 'b2', 'title': 'Two'},
        {'__type__': 'Book', 'key': 'b1', 'title': 'One'}]}]
    assert selected_objects(project, ids['BookController.lookup'], 'Open book', history) == []
    assert selected_objects(project, ids['BookController.lookup'], 'Open reader', history) == []
    assert selected_objects(project, ids['BookController.lookup'], 'Open new book', history) == []
    assert selected_objects(project, ids['BookController.lookup'], 'Open third book', history) == []
    selected = selected_objects(project, ids['BookController.lookup'], 'Open second book', history)
    assert selected[0]['value'] == 'b1'
    history.append({'selected_objects': selected})
    assert history_value(project, ids['BookController.lookup'], 'key', 'Read book', history)[1] == 'b1'
    assert selected_field(project, 'title', {'bookId': 'b1'}, history)[1] == 'One'
    assert selected_field(project, 'title', {'bookId': 'b2'}, history) is None
    assert selected_field(project, 'title', {'readerId': 'b1'}, history) is None


def test_conflicting_path_selections_are_unknown_after_join(tmp_path):
    project, db, ids = build(tmp_path, LIBRARY)
    initial = ScenarioState(db)
    initial.history = [{'result': [{'__type__': 'Book', 'key': 'b1'}, {'__type__': 'Book', 'key': 'b2'}]}]
    alternatives = []
    for action in ('Open first book', 'Open second book'):
        state = deepcopy(initial)
        state.history.append({'selected_objects': selected_objects(project, ids['BookController.lookup'], action, state.history)})
        alternatives.append(state)
    joined = join_states(alternatives)
    assert joined.history[-1]['selected_objects'] is U
    assert history_value(project, ids['BookController.lookup'], 'key', 'Read book', joined.history) is None


def test_explicit_ordinal_overrides_earlier_focus(tmp_path):
    project, _, ids = build(tmp_path, LIBRARY)
    history = [{'result': [{'__type__': 'Book', 'key': 'b1'}, {'__type__': 'Book', 'key': 'b2'}]}]
    history.append({'selected_objects': selected_objects(project, ids['BookController.lookup'], 'Open first book', history)})
    assert history_value(project, ids['BookController.lookup'], 'key', 'Read second book', history)[1] == 'b2'


def test_new_qualifier_for_another_entity_does_not_erase_known_identity(tmp_path):
    sources = dict(LIBRARY)
    sources['Reader.java'] = 'class Reader { @Id String id; }'
    project, _, ids = build(tmp_path, sources)
    history = [{'action': 'List books', 'result': {'__type__': 'Book', 'key': 'b1'}}]
    assert history_value(project, ids['BookController.lookup'], 'key', 'Read book for a new reader', history)[1] == 'b1'
    assert history_value(project, ids['BookController.lookup'], 'readerId', 'Read book for a new reader', history) is None


def test_search_noun_and_returned_old_object_are_not_creation_evidence(tmp_path):
    project, _, ids=build(tmp_path,LIBRARY)
    old={'__type__':'Book','key':'old'}
    for action in ('Find book "X"','Add book'):
        history=[{'action':action,'result':old}]
        assert history_value(project,ids['BookController.lookup'],'key','Open new book',history) is None


def test_definite_reference_uses_confirmed_creation_until_explicit_reselection(tmp_path):
    project, _, ids=build(tmp_path,LIBRARY)
    new={'__type__':'Book','key':'new'}
    history=[{'action':'Reserve a copy','created_objects':[new]},
             {'action':'List books','result':[{'__type__':'Book','key':'old'},new]}]
    assert history_value(project,ids['BookController.lookup'],'key','Read the book',history)[1]=='new'
    assert history_value(project,ids['BookController.lookup'],'key','Read a book',history) is None
    history.append({'selected_objects':selected_objects(project,ids['BookController.lookup'],'Open first book',history)})
    assert history_value(project,ids['BookController.lookup'],'key','Read the book',history)[1]=='old'
    history.append({'created_objects':[{'__type__':'Book','key':'newer'}]})
    assert history_value(project,ids['BookController.lookup'],'key','Read the book',history)[1]=='newer'
    history=[{'created_objects':[new,{'__type__':'Book','key':'other'}]}]
    assert history_value(project,ids['BookController.lookup'],'key','Read the book',history) is None


def test_search_date_is_linked_through_result_identity_not_static_timetable(tmp_path):
    from analyzer.provenance import history_role_value
    project, _, _=build(tmp_path,{'Api.java':'''class Api {String show(){return "ok";}}
      class Slot {String tripId;String startTime;String endTime;}'''})
    history=[{'parameters':{'departureDate':'2026-10-01','startPlace':'A','endPlace':'C'},
              'result':{'__type__':'Slot','tripId':'s1','startTime':'2013-01-01 09:00','endTime':'2013-01-01 10:00'}}]
    assert history_role_value(project,'date',{'tripId':'s1'},history)[1]=='2026-10-01'
    assert history_role_value(project,'date',{'tripId':'s2'},history) is None
    # The enclosing search may cover several segments; it cannot replace a leg's origin/end.
    assert history_role_value(project,'from',{'tripId':'s1'},history) is None
    history[0]['parameters']={'startTime':'09:00'}
    assert history_role_value(project,'date',{'tripId':'s1'},history) is None
    history[0]['parameters']['tripId']='s1'
    assert history_role_value(project,'date',{'tripId':'s1'},history) is None


def test_cheapest_reference_uses_matching_search_and_rejects_incomparable_prices(tmp_path):
    project, _, ids=build(tmp_path,{'Api.java':'''class Api {
      @GetMapping("/products/{productId}") String details(@PathVariable String productId){return productId;}
    } class Offer {String productId;String retailPrice;String wholesalePrice;}'''})
    a={'__type__':'Offer','productId':'a','retailPrice':'10','wholesalePrice':'5'}
    b={'__type__':'Offer','productId':'b','retailPrice':'20','wholesalePrice':'5'}
    history=[{'action':'Search cheapest products','result':[a,b]},
             {'action':'Search quickest products','result':[{'__type__':'Offer','productId':'z','retailPrice':'1','wholesalePrice':'1'}]}]
    assert history_value(project,ids['Api.details'],'productId','Open details of the cheapest product',history)[1]=='a'
    selected=selected_objects(project,ids['Api.details'],'Open details of the cheapest product',history)
    assert selected[0]['entity']==['product'] and selected[0]['value']=='a'
    history[0]['result'][1]['wholesalePrice']='3'
    assert history_value(project,ids['Api.details'],'productId','Open details of the cheapest product',history) is None
    history[0]['result'][1]['wholesalePrice']=U
    assert history_value(project,ids['Api.details'],'productId','Open details of the cheapest product',history) is None


def test_request_reusing_observed_typed_id_carries_focus_to_next_action(tmp_path):
    project, _, ids=build(tmp_path,{'Api.java':'''class Api {
      @PostMapping("/invoices/{invoiceId}/pay") String pay(@PathVariable String invoiceId){return invoiceId;}
      @DeleteMapping("/invoices/{invoiceId}") String cancel(@PathVariable String invoiceId){return invoiceId;}
    } class Invoice {@Id String id;} class Customer {@Id String id;}'''})
    history=[{'result':[{'__type__':'Invoice','id':'old'},{'__type__':'Invoice','id':'chosen'},
                        {'__type__':'Customer','id':'chosen'}]}]
    focused=selected_objects(project,ids['Api.pay'],'Pay this invoice',history,{'invoiceId':'chosen'})
    assert len(focused)==1 and focused[0]['entity']==['invoice'] and focused[0]['value']=='chosen'
    history.append({'selected_objects':focused,'result':None})
    assert history_value(project,ids['Api.cancel'],'invoiceId','Cancel the paid invoice',history)[1]=='chosen'
    assert selected_objects(project,ids['Api.pay'],'Pay invoice',history,{'invoiceId':'unobserved'})==[]


def test_foreign_record_id_and_title_do_not_become_the_new_record_own_fields(tmp_path):
    project, _, ids=build(tmp_path,{'Api.java':'''class Api {
      @PutMapping("/reviews") String edit(@RequestBody Review input){return input.id;}
      @PutMapping("/books") String book(@RequestBody Book input){return input.key;}
    } class Review {@Id String id;String bookId;String title;}
    class Book {@Id String key;String title;}'''})
    book={'__type__':'Book','key':'b1','title':'Source title'}
    history=[{'selected_objects':[{'entity':['book'],'value':'b1','object':book}]}]
    assert selected_field(project,'id',{'bookId':'b1'},history,ids['Api.edit']) is None
    assert selected_field(project,'title',{'bookId':'b1'},history,ids['Api.edit']) is None
    assert selected_field(project,'title',{'bookId':'b1'},history,ids['Api.book'])[1]=='Source title'


def test_route_role_values_follow_a_declared_id_alias_but_never_supply_another_entity_id(tmp_path):
    from analyzer.provenance import history_role_value
    project,_,_=build(tmp_path,{'Api.java':'''class Api {String show(){return "ok";}}
      class Delivery {@Id String id;String from;String to;}'''})
    history=[{'result':{'__type__':'Delivery','id':'d1','from':'North','to':'South'}}]
    assert history_role_value(project,'from',{'deliveryId':'d1'},history)[1]=='North'
    assert history_role_value(project,'to',{'deliveryId':'d1'},history)[1]=='South'
    assert history_role_value(project,'from',{'deliveryId':'other'},history) is None
    assert history_role_value(project,'from',{'customerId':'d1'},history) is None
    assert history_role_value(project,'id',{'deliveryId':'d1'},history) is None


def test_empty_ui_identity_placeholder_does_not_count_as_a_selected_record(tmp_path):
    from analyzer.contracts import ContractGrounder, ContractIndex
    from analyzer.frontend import Frontend
    project,db,_=build(tmp_path,{'Api.java':'''class Api {
      @PostMapping("/invoices/details") String show(@RequestBody Lookup input){return input.invoiceId;}
    } class Lookup {String invoiceId;} class Invoice {@Id String id;}'''})
    (tmp_path/'ui.js').write_text('''new Vue({data:{invoiceId:""},methods:{show(){
      $.ajax({url:"/invoices/details",type:"POST",data:{invoiceId:this.invoiceId}});
    }}});''')
    frontend=Frontend(project)
    grounder=ContractGrounder(project,frontend,ContractIndex(project,frontend),None,{'facts':{}})
    state=ScenarioState(db)
    choices,_=grounder.step('Read the invoice',state)
    assert 'invoiceId' not in choices[0]['params']
    assert 'Unknown input: invoiceId' in choices[0]['unresolved']
    state.history=[{'result':{'__type__':'Invoice','id':'known'}}]
    choices,_=grounder.step('Read the invoice',state)
    assert choices[0]['params']['invoiceId']=='known'
