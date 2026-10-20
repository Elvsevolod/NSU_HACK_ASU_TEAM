from analyzer.state import ScenarioState,U
from builders import build


def test_full_evidence_freezes_known_rows_and_marks_unknown_tables(tmp_path):
    _,db,_=build(tmp_path,{'Api.java':'class Api{void entry(){}}'},rows={'items':[{'id':'a'}],'other':[{'id':'b'}]})
    state=ScenarioState(db);state.database.unknown_tables.add(('service','other'))
    snapshot=state.snapshot(full=True)
    state.database.tables[('service','items')][0]['id']='later'
    assert snapshot['tables']['service.items']==[{'id':'a'}]
    assert snapshot['tables']['service.other'] is U
