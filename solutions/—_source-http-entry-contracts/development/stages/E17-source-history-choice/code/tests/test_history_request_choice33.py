"""Source/result constraints may resolve a lexical tie, never replace a producer."""
from copy import deepcopy
import pytest
from builders import build
from analyzer.contracts import ContractGrounder
from analyzer.frontend import Frontend
from analyzer.history_agreement import observation
from analyzer.java_collections import JsonObject
from analyzer.lexical_retrieval import LexicalContractIndex
from analyzer.paths import join_states
from analyzer.state import ScenarioState,U


def fixture(root,extra=''):
    p,db,ids=build(root,{'Api.java':'''import org.springframework.web.bind.annotation.*;
      import java.util.List;
      class Parcel{public Long id;public String name;}
      @RestController class ParcelController{
      @PostMapping("/parcels") Parcel create(@RequestBody Parcel parcel){return parcel;}
      @GetMapping("/parcels/{id}") Parcel getById(@PathVariable Long id){return null;}
      @GetMapping("/parcels") List<Parcel> getAll(){return null;}
      @GetMapping("/parcels/search") List<Parcel> searchParcels(@RequestParam String name){return null;}
      '''+extra+'''}'''})
    frontend=Frontend(p);index=LexicalContractIndex(p,frontend)
    g=ContractGrounder(p,frontend,index,None,{'facts':{},'unresolved':[]})
    state=ScenarioState(db)
    state.history=[{'step':1,'action':'Create a parcel','entry':ids['ParcelController.create'],
        'parameters':{},'result':JsonObject({'id':7,'name':'package'},'Parcel'),
        'created_objects':[],'selected_objects':[],'outcome':'returned','exploration':{'complete':True}}]
    return p,ids,g,state


@pytest.mark.parametrize('value',[7,{'__symbol__':'created-id','__type__':'Long','__constraints__':['non_null']}])
def test_source_single_record_and_complete_previous_result_resolve_a_read_tie(tmp_path,value):
    p,ids,g,state=fixture(tmp_path);state.history[0]['result']['id']=value
    before=deepcopy(state.history)
    proposals,detail=g.step('Read the parcel just created',state)
    assert len(proposals)==1 and proposals[0]['entry']==ids['ParcelController.getById']
    proposal=proposals[0]
    assert proposal['params']=={'id':value} and not proposal['unresolved']
    proof=proposal['bindings']['id']
    assert proof['source']=='history' and proof['reference']=='history[0].result.id'
    assert proof['producer_observation']['digest']==observation(state.history[0])
    assert detail['retrieval_decision']['accepted'] is False
    assert detail['grounding_status']=='source_history_constraint'
    assert state.history==before


@pytest.mark.parametrize('mutation',[
    'missing','partial','failed','unknown','wrong-kind','foreign-type','not-created','collection',
])
def test_missing_partial_failed_wrong_typed_or_noncreation_result_does_not_resolve_tie(tmp_path,mutation):
    p,ids,g,state=fixture(tmp_path);item=state.history[0]
    if mutation=='missing':state.history=[]
    elif mutation=='partial':item['exploration']['complete']=False
    elif mutation=='failed':item['outcome']='HTTP error response'
    elif mutation=='unknown':item['result']['id']=U
    elif mutation=='wrong-kind':item['result']['id']='7'
    elif mutation=='foreign-type':item['result'].origin_type='Unrelated'
    elif mutation=='not-created':item['entry']=ids['ParcelController.getById']
    elif mutation=='collection':item['result']=[item['result']]
    proposals,detail=g.step('Read the parcel just created',state)
    assert not proposals and detail['unresolved']


@pytest.mark.parametrize('action',['Read parcel','Read all parcels just created'])
def test_history_cannot_silently_qualify_an_action_without_a_single_prior_reference(tmp_path,action):
    p,ids,g,state=fixture(tmp_path)
    proposals,detail=g.step(action,state)
    assert not proposals and detail['unresolved']


def test_explicit_identity_keeps_its_literal_producer(tmp_path):
    p,ids,g,state=fixture(tmp_path)
    proposals,detail=g.step('Read the parcel with id=9',state)
    assert len(proposals)==1 and proposals[0]['params']=={'id':9}
    assert proposals[0]['bindings']['id']['source']=='literal'


def test_two_singular_source_endpoints_remain_ambiguous(tmp_path):
    p,ids,g,state=fixture(tmp_path,'''@GetMapping("/mirror/parcels/{id}")
      Parcel getMirrorById(@PathVariable Long id){return null;}''')
    proposals,detail=g.step('Read the parcel just created',state)
    assert not proposals and detail['unresolved']


@pytest.mark.parametrize('other_value',[7,8])
def test_every_joined_producer_alternative_must_agree_before_request_selection(tmp_path,other_value):
    p,ids,g,state=fixture(tmp_path);other=deepcopy(state)
    other.history[0]['result']['id']=other_value
    joined=join_states([state,other])
    proposals,detail=g.step('Read the parcel just created',joined)
    assert bool(proposals)==(other_value==7)


def test_an_incomplete_later_creation_cannot_fall_back_to_an_older_success(tmp_path):
    p,ids,g,state=fixture(tmp_path);later=deepcopy(state.history[0]);later['step']=2
    later['result']['id']=8;later['exploration']['complete']=False
    state.history.append(later)
    proposals,detail=g.step('Read the parcel just created',state)
    assert not proposals and detail['unresolved']
