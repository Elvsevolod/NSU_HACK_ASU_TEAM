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


def test_definite_reference_uses_confirmed_creation_until_explicit_reselection(tmp_path):
    project, _, ids=build(tmp_path,LIBRARY)
    new={'__type__':'Book','key':'new'}
    history=[{'action':'Reserve a copy','created_objects':[new]},
             {'action':'List books','result':[{'__type__':'Book','key':'old'},new]}]
    assert history_value(project,ids['BookController.lookup'],'key','Read the book',history)[1]=='new'
    assert history_value(project,ids['BookController.lookup'],'key','Read a book',history) is None
    history.append({'selected_objects':selected_objects(project,ids['BookController.lookup'],'Open first book',history)})
    assert history_value(project,ids['BookController.lookup'],'key','Read the book',history)[1]=='old'
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
