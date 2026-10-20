"""Repetition changes the request count, not the source operation or JSON text."""
import pytest
from builders import build
from analyzer.contracts import ContractGrounder
from analyzer.frontend import Frontend
from analyzer.lexical_retrieval import LexicalContractIndex,intent
from analyzer.state import ScenarioState
from analyzer.request import grounded_request


@pytest.mark.parametrize('action,expected',[
    ('Repeat reading parcel with id=11',0),('Repeat getting parcel with id=11',0),
    ('Repeat creating parcel',1),('Repeat adding parcel',1),('Repeat saving parcel',1),
    ('Repeat deleting parcel with id=11',2),('Repeat removing parcel with id=11',2),
    ('Repeat updating parcel with id=11',3),('Repeat editing parcel with id=11',3),
    ('Repeat modifying parcel with id=11',3),('Repeat paying invoice',5),
    ('Repeat charging account',5),('As admin, repeat updating parcel',3),
])
def test_repeat_preserves_the_stated_operation(action,expected):
    assert intent(action)==expected


@pytest.mark.parametrize('action,expected',[
    ('Repeat report update parcel',None),('Do not repeat deleting parcel',None),
    ('Create parcel: {"name":"Repeat deleting"}',1),('Read repeat update logs',0),
])
def test_a_verb_inside_an_object_or_a_negated_prefix_is_not_the_repeat_operation(action,expected):
    assert intent(action)==expected


@pytest.mark.parametrize('action,name,method',[
    ('Repeat updating parcel with id=11: {"name":"Repeat creating"}','update','PUT'),
    ('Repeat creating parcel: {"name":"Repeat deleting"}','create','POST'),
    ('Repeat deleting parcel with id=11','delete','DELETE'),
])
def test_repeat_selects_the_source_handler_and_keeps_literal_body_verbatim(tmp_path,action,name,method):
    p,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.bind.annotation.*;
      class Parcel{public Long id;public String name;}
      @RestController class ParcelController{
      @PostMapping("/parcels") Parcel create(@RequestBody Parcel parcel){return parcel;}
      @PutMapping("/parcels/{id}") Parcel update(@PathVariable Long id,@RequestBody Parcel parcel){return parcel;}
      @DeleteMapping("/parcels/{id}") void delete(@PathVariable Long id){}
      @GetMapping("/parcels/{id}") Parcel read(@PathVariable Long id){return null;}}'''})
    f=Frontend(p);g=ContractGrounder(p,f,LexicalContractIndex(p,f),None,{'facts':{},'unresolved':[]})
    proposals,detail=g.step(action,ScenarioState(db))
    assert len(proposals)==1 and proposals[0]['entry']==ids['ParcelController.'+name]
    proposal=proposals[0];request=grounded_request(p,proposal['entry'],proposal['params'],proposal['bindings'])
    assert request.method==method and not proposal['unresolved']
    if name!='create':
        assert proposal['params']['id']==11 and proposal['bindings']['id']['source']=='literal'
    if name!='delete':
        assert request.body=={'name':'Repeat creating' if name=='update' else 'Repeat deleting'}
        assert proposal['bindings']['parcel']['source']=='literal'
