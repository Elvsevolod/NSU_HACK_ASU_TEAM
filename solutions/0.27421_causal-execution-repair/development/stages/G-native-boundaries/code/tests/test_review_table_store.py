from copy import deepcopy
from analyzer.heap_join import clone_execution
from analyzer.state import ScenarioState
from analyzer.table_store import TableStore
from builders import build


def test_snapshot_defers_copying_but_every_mutable_access_is_owned():
    tables=TableStore();tables['items']=[{'id':'a','nested':{'count':1}}]
    other=deepcopy(tables)
    assert tables.raw_get('items') is other.raw_get('items')
    other['items'][0]['nested']['count']=2
    assert tables['items'][0]['nested']['count']==1
    assert other['items'][0]['nested']['count']==2


def test_mutating_the_source_after_snapshot_does_not_change_the_snapshot():
    tables=TableStore();tables['items']=[{'id':'a'}]
    other=deepcopy(tables)
    tables['items'].append({'id':'b'})
    assert other['items']==[{'id':'a'}]


def test_table_and_row_aliases_survive_inside_a_snapshot():
    tables=TableStore();row={'id':'a'}
    tables['one']=[row];tables['two']=[row];tables['alias']=tables['one']
    other=deepcopy(tables)
    assert other['alias'] is other['one']
    assert other['one'][0] is other['two'][0]
    other['one'][0]['id']='changed'
    assert tables['one'][0]['id']=='a'


def test_joint_snapshot_retains_an_input_alias_into_a_table_row(tmp_path):
    _,db,_=build(tmp_path,{'Api.java':'class Api{void entry(){}}'},rows={'items':[{'id':'a'}]})
    state=ScenarioState(db)
    row=state.database.tables[('service','items')][0]
    (owned,params),_=clone_execution(state,{'row':row})
    assert params['row'] is owned.database.tables[('service','items')][0]
    params['row']['id']='changed'
    assert row['id']=='a'


def test_read_only_summary_does_not_materialize_every_shared_table(tmp_path):
    _,db,_=build(tmp_path,{'Api.java':'class Api{void entry(){}}'},rows={'one':[{'id':'a'}],'two':[{'id':'b'}]})
    owned=db.copy()
    before=dict(owned.tables.raw_items())
    assert owned.summary()=={'service.one':1,'service.two':1}
    assert all(owned.tables.raw_get(key) is value for key,value in before.items())
