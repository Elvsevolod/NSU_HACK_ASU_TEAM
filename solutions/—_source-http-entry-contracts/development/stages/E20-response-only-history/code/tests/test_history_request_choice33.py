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


@pytest.mark.parametrize('value,outcome,complete,accepted',[
    (7,'returned',True,True),(8,'returned',True,False),
    (7,'HTTP error response',True,False),(7,'returned',False,False),
])
def test_a_later_response_must_prove_the_same_created_identity(tmp_path,value,outcome,complete,accepted):
    p,ids,g,state=fixture(tmp_path);later=deepcopy(state.history[0])
    later.update(step=2,entry=ids['ParcelController.getById'],action='Read the parcel',outcome=outcome)
    later['result']['id']=value;later['exploration']['complete']=complete
    state.history.append(later)
    proposals,detail=g.step('Read the parcel just created again',state)
    assert bool(proposals)==accepted
    if accepted:
        assert proposals[0]['bindings']['id']['reference']=='history[1].result.id'
        proof=detail['source_history_constraint']
        assert proof['creation']['step']==1 and proof['value_producer']['step']==2
        assert proof['creation']['digest']==observation(state.history[0])
        assert proof['value_producer']['digest']==observation(state.history[1])


def test_agreeing_value_does_not_replace_the_identity_of_its_source_producer(tmp_path):
    p,ids,g,state=fixture(tmp_path);later=deepcopy(state.history[0])
    later.update(step=2,entry=None,action='Read the parcel')
    state.history.append(later)
    proposals,detail=g.step('Read the parcel just created again',state)
    assert not proposals and detail['unresolved']


@pytest.mark.parametrize('mutation',[None,'other-path','other-value','other-type','other-producer','unknown-path'])
def test_selected_identity_needs_its_exact_completed_response_field(tmp_path,mutation):
    p,ids,g,state=fixture(tmp_path);later=deepcopy(state.history[0])
    later.update(step=2,entry=ids['ParcelController.getById'],action='Read the parcel')
    selected={'entity':['parcel'],'value':7,'reference':'history[1].result.id',
        'object':deepcopy(later['result']),'qualified_type':'Parcel','deployment':'service',
        'producer_entry':ids['ParcelController.getById']}
    if mutation=='other-path':selected['reference']='history[0].result.id'
    elif mutation=='unknown-path':selected['reference']=U
    elif mutation=='other-value':selected['value']=8
    elif mutation=='other-type':selected['qualified_type']='Unrelated'
    elif mutation=='other-producer':selected['producer_entry']=ids['ParcelController.create']
    later['selected_objects']=[selected];state.history.append(later)
    proposals,detail=g.step('Read the parcel just created again',state)
    if mutation=='unknown-path':
        assert not proposals and detail['unresolved']
        return
    # Selection bookkeeping does not replace the actual complete response.
    assert len(proposals)==1 and proposals[0]['params']=={'id':7}
    assert proposals[0]['bindings']['id']['reference']=='history[1].result.id'
    assert detail['source_history_constraint']['response_reference']=='history[1].result.id'


def test_string_update_response_cannot_replace_the_last_typed_identity_producer(tmp_path):
    p,ids,g,state=fixture(tmp_path,'''@PutMapping("/parcels/{id}")
      String update(@PathVariable Long id){return "updated";}''')
    read=deepcopy(state.history[0]);read.update(step=2,entry=ids['ParcelController.getById'],action='Read parcel')
    state.history.append(read)
    updated=deepcopy(read);updated.update(step=3,entry=ids['ParcelController.update'],action='Update parcel',
        parameters={'id':7},result='updated',selected_objects=[{'entity':['parcel'],'value':7,
            'reference':'history[2].parameters.id','qualified_type':'Parcel','deployment':'service',
            'producer_entry':ids['ParcelController.update'],'object':deepcopy(read['result'])}])
    state.history.append(updated)
    proposals,detail=g.step('Read the parcel just created again',state)
    assert len(proposals)==1 and proposals[0]['params']=={'id':7}
    assert proposals[0]['bindings']['id']['reference']=='history[1].result.id'
    assert detail['source_history_constraint']['value_producer']['step']==2
