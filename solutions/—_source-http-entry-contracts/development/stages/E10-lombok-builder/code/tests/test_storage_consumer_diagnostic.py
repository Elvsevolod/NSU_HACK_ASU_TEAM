from analyzer.frontend import Frontend
from analyzer.state import ScenarioState,U
from builders import build


def test_storage_keys_of_different_clients_do_not_create_a_session(tmp_path):
    project,db,_=build(tmp_path,{'Api.java':'class Api{void entry(){}}'})
    frontend=Frontend(project);state=ScenarioState(db)
    state.browser['storage']['staff_token']='staff-proof'
    assert frontend.evaluate('sessionStorage.getItem("visitor_token")',state,{}, {}) is U
    assert state.browser['storage']=={'staff_token':'staff-proof'}
    assert state.limitations==['Source storage consumer has no established value: visitor_token']
