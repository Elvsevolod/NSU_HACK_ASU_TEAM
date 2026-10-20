"""Default grounding must use the same response eligibility as explicit recipes."""
from copy import deepcopy
import pytest
from builders import build
from analyzer.paths import run_paths
from analyzer.state import ScenarioState,U
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex,ContractGrounder
from analyzer.request import grounded_request,BoundParameters
from analyzer.java_collections import JsonObject
from analyzer.provenance import related_selection_value,selected_field,history_role_value


def fixture(root,status=200,choice=True,limit=4):
    source='''import org.springframework.web.bind.annotation.*;import org.springframework.http.ResponseEntity;
      import org.springframework.boot.autoconfigure.SpringBootApplication;
      @SpringBootApplication class App{}
      class Parcel{public Long id;public Long supplierId=9L;public String city="returned-city";public String origin="returned-origin";}
      class Supplier{public Long id;}
      @RestController class ParcelController{
      @PostMapping("/parcels/{choice}") ResponseEntity<Parcel> create(@PathVariable boolean choice,@RequestBody Parcel input){
        Parcel p=new Parcel();if(choice)p.id=7L;else p.id=9L;
        return ResponseEntity.status('''+str(status)+''').body(p);}
      @GetMapping("/parcels/{id}") Parcel read(@PathVariable Long id){return null;}
      @PutMapping("/parcels/{parcelId}") Parcel update(@PathVariable Long parcelId,@RequestBody Parcel input){return input;}
      @GetMapping("/suppliers/{supplierId}") Supplier supplier(@PathVariable Long supplierId){return null;}}
      '''
    p,db,ids=build(root,{'Api.java':source});params={'choice':choice,'input':{}}
    request=grounded_request(p,ids['ParcelController.create'],params,{})
    paths=run_paths(p,ScenarioState(db),ids['ParcelController.create'],BoundParameters(params,request),limit=limit)
    out=paths[0];state=out['state'];engine=out['engine']
    state.history.append({'step':1,'action':'Create parcel','entry':ids['ParcelController.create'],
        'parameters':params,'result':out['result'],'selected_objects':[],'created_objects':[],
        'outcome':engine.outcome,'exploration':out['exploration']})
    f=Frontend(p);g=ContractGrounder(p,f,ContractIndex(p,f),None,{'facts':{},'unresolved':[]})
    return p,ids,g,state


@pytest.mark.parametrize('status,choice,limit,eligible',[
    (200,True,4,True),(500,True,4,False),(200,U,1,False),
])
def test_default_grounding_does_not_promote_failed_or_unexplored_response_to_a_known_id(tmp_path,status,choice,limit,eligible):
    p,ids,g,state=fixture(tmp_path,status,choice,limit)
    assert state.history[0]['exploration']['complete']==(choice is not U)
    assert state.history[0]['outcome']==('returned' if status==200 else 'HTTP error response')
    proposals,detail=g.step('Read the new parcel',state)
    resolved=[x for x in proposals if x['bindings'].get('id',{}).get('source')=='history' and x['bindings']['id'].get('resolved')]
    assert bool(resolved)==eligible
    if eligible:assert resolved[0]['params']['id']==7


@pytest.mark.parametrize('action',['Read the new parcel','Read the parcel just created'])
def test_a_failed_later_creation_cannot_select_the_old_successful_creation(tmp_path,action):
    p,ids,g,state=fixture(tmp_path,500)
    old=deepcopy(state.history[0]);old.update(step=1,outcome='returned',result=JsonObject({'id':5},'Parcel'))
    state.history[0]['step']=2;state.history.insert(0,old)
    proposals,detail=g.step(action,state)
    assert not any(x['bindings'].get('id',{}).get('resolved') for x in proposals)


@pytest.mark.parametrize('case',['failed','partial'])
@pytest.mark.parametrize('consumer',['related','selected','role'])
def test_selected_and_related_fields_from_an_unavailable_response_are_not_inputs(tmp_path,case,consumer):
    p,ids,g,state=fixture(tmp_path,500 if case=='failed' else 200,U if case=='partial' else True,1 if case=='partial' else 4)
    item=state.history[0]
    item['selected_objects']=[{'entity':['parcel'],'value':7,'object':deepcopy(item['result']),
        'qualified_type':'Parcel','producer_entry':ids['ParcelController.create'],'reference':'history[0].result.id'}]
    if consumer=='related':assert related_selection_value(p,ids['ParcelController.supplier'],'supplierId','Read its supplier',state.history) is None
    elif consumer=='selected':assert selected_field(p,'city',{'parcelId':7},state.history,ids['ParcelController.update']) is None
    else:assert history_role_value(p,'origin',{'parcelId':7},state.history) is None


def test_explicit_literal_is_independent_of_an_earlier_failed_response(tmp_path):
    p,ids,g,state=fixture(tmp_path,500)
    proposals,detail=g.step('Read parcel with id=11',state)
    assert len(proposals)==1 and proposals[0]['params']['id']==11
    assert proposals[0]['bindings']['id']['source']=='literal'
