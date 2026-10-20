"""A failed latest query cannot become an ordinal producer or erase client inputs."""
from copy import deepcopy
import pytest
from builders import build
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from analyzer.request import grounded_request,BoundParameters
from analyzer.provenance import history_value,history_role_value
from analyzer.history_agreement import agree_completed
from analyzer.history_refs import references


def fixture(root):
    return build(root,{'Api.java':'''import org.springframework.web.bind.annotation.*;
      import org.springframework.http.ResponseEntity;
      import org.springframework.boot.autoconfigure.SpringBootApplication;
      import java.util.List;import java.util.ArrayList;
      @SpringBootApplication class App{}
      class Parcel{public Long id;}
      @RestController class ParcelController{
      Parcel make(Long id){Parcel p=new Parcel();p.id=id;return p;}
      @GetMapping("/parcels/list/{fail}") ResponseEntity<List<Parcel>> list(@PathVariable boolean fail){
        List<Parcel> rows=new ArrayList<>();rows.add(make(8L));rows.add(make(9L));
        return ResponseEntity.status(fail?500:200).body(rows);}
      @GetMapping("/parcels/{id}") Parcel read(@PathVariable Long id){return null;}
      @GetMapping("/parcels/{parcelId}/origin") ResponseEntity<String> origin(@PathVariable Long parcelId,@RequestParam String origin){
        return ResponseEntity.status(500).body("error-body-origin");}}'''})


def invoke(p,state,entry,params,step):
    request=grounded_request(p,entry,params,{})
    paths=run_paths(p,state,entry,BoundParameters(params,request),limit=4)
    assert len(paths)==1
    out=paths[0];following=out['state']
    item={'step':step,'action':'List parcels','entry':entry,'parameters':deepcopy(params),
        'result':deepcopy(out['result']),'created_objects':[],'selected_objects':[],
        'outcome':out['engine'].outcome,'exploration':deepcopy(out['exploration'])}
    following.history.append(item)
    return following


@pytest.mark.parametrize('saved_refs',[False,True])
def test_latest_failed_collection_is_not_replaced_with_the_old_first_row(tmp_path,saved_refs):
    p,db,ids=fixture(tmp_path);state=invoke(p,ScenarioState(db),ids['ParcelController.list'],{'fail':False},1)
    first=history_value(p,ids['ParcelController.read'],'id','Read first parcel',state.history)
    assert first==('history[0].result[0].id',8)
    state=invoke(p,state,ids['ParcelController.list'],{'fail':True},2)
    assert state.history[-1]['outcome']=='HTTP error response'
    assert [row['id'] for row in state.history[-1]['result']]==[8,9]
    if saved_refs:
        for i,item in enumerate(state.history):item['response_refs']=references(p,item,i)
    assert history_value(p,ids['ParcelController.read'],'id','Read first parcel',state.history) is None


def test_known_client_parameter_survives_a_failed_response_without_using_its_body(tmp_path):
    p,db,ids=fixture(tmp_path)
    state=invoke(p,ScenarioState(db),ids['ParcelController.origin'],{'parcelId':8,'origin':'client-origin'},1)
    assert state.history[0]['outcome']=='HTTP error response' and state.history[0]['result']=='error-body-origin'
    assert history_role_value(p,'origin',{'parcelId':8},state.history)==('history[0].parameters.origin','client-origin')


@pytest.mark.parametrize('metadata,available',[
    ({'outcome':'returned','exploration':{'complete':True}},True),
    ({'outcome':'HTTP error response','exploration':{'complete':True}},False),
    ({'outcome':U,'exploration':{'complete':True}},False),
    ({'outcome':'returned','exploration':{'complete':False}},False),
    ({'outcome':'returned','exploration':{'complete':U}},False),
    ({'outcome':'returned','exploration':{}},False),
    ({'outcome':'returned','exploration':U},False),
])
def test_engine_outcome_and_coverage_metadata_cannot_be_inferred_from_payload(metadata,available):
    from analyzer.history_agreement import response_available
    item={'result':{'id':8},**metadata}
    assert response_available(item)==available


def test_a_legacy_supplied_observation_is_not_promoted_to_completed_group_agreement():
    from analyzer.history_agreement import response_available
    supplied={'result':{'id':8}}
    assert response_available(supplied) is True
    assert agree_completed([supplied],lambda row:row['result']) is None
