"""Unknown optional properties must preserve independent explicit inputs."""
import pytest
from analyzer.paths import run_paths
from analyzer.request_inputs import RequestInputs
from analyzer.state import ScenarioState, U
from builders import build


@pytest.mark.parametrize('limit', [1, 4, 8])
def test_optional_comment_keeps_revision_and_approval_through_handler(tmp_path, limit):
    project, db, ids = build(tmp_path, {'Api.java': '''class Approval {
      public int revision; public boolean approved; private String comment;
      public void setComment(String value){comment=value;}}
      class Api{@PostMapping("/approvals") String entry(@RequestBody Approval input){
      if(input.revision==7 && input.approved){return accept();}return reject();}
      String accept(){return "accepted";}String reject(){return "rejected";}}'''})
    params = RequestInputs({'revision':7, 'approved':True}, flat_bodies=['input'],
                           body_unknowns={'input':{'comment':'unobserved'}})
    outcomes = run_paths(project, ScenarioState(db), ids['Api.entry'], params, limit=limit)
    assert {row['result'] for row in outcomes} == {'accepted'}
    assert all(ids['Api.reject'] not in {t for _,k,t in row['engine'].edges if k=='executes'} for row in outcomes)


def test_setter_with_additional_writes_does_not_preserve_a_false_revision(tmp_path):
    project, db, ids = build(tmp_path, {'Api.java': '''class Approval {
      public int revision; private String comment;
      public void setComment(String value){comment=value;revision=0;}}
      class Api{@PostMapping("/approvals") int entry(@RequestBody Approval input){return input.revision;}}'''})
    params = RequestInputs({'revision':7}, flat_bodies=['input'],
                           body_unknowns={'input':{'comment':'unobserved'}})
    outcomes = run_paths(project, ScenarioState(db), ids['Api.entry'], params, limit=1)
    assert all(row['result'] is U for row in outcomes)
