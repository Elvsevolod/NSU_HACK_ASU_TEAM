"""Literal path arguments constrain a refused source request, not its score."""
from copy import deepcopy
import pytest
from builders import build
from analyzer.contracts import ContractIndex,ContractGrounder
from analyzer.frontend import Frontend
from analyzer.lexical_retrieval import LexicalContractIndex
from analyzer.state import ScenarioState
from analyzer.request import grounded_request


class TiedIndex(LexicalContractIndex):
    """Unit input: the retriever supplies existing equally scored source IDs."""
    def rank(self,action,active_page=None,scenario_text=''):
        rows=ContractIndex.rank(self,action,active_page,scenario_text)
        self.last_decision={'accepted':False,'profile':'unicode-source-lexical/1',
            'reason':'source endpoint scores within frozen refusal margin',
            'raw_top':[{'entry':c['entry'],'contract_id':key,'score':1.0} for _,key,c in rows[:6]]}
        return []


def fixture(root,kind='Long',extra='',declarations='',read_annotations=''):
    p,db,ids=build(root,{'Api.java':'''import org.springframework.web.bind.annotation.*;
      import java.util.List;import org.springframework.security.access.prepost.PreAuthorize;
      class Parcel{public '''+kind+''' id;public String name;}
      '''+declarations+'''@RestController class ParcelController{
      '''+read_annotations+'''@GetMapping("/parcels/{id}") Parcel getById(@PathVariable '''+kind+''' id){return null;}
      @GetMapping("/parcels") List<Parcel> getAll(){return null;}
      '''+extra+'''}'''})
    f=Frontend(p);g=ContractGrounder(p,f,TiedIndex(p,f),None,{'facts':{},'unresolved':[]})
    return p,ids,g,ScenarioState(db)


@pytest.mark.parametrize('kind,action,value',[
    ('Long','Read parcel with id=11',11),('Long','Read parcel with id=9007199254740993',9007199254740993),
    ('Long','Read parcel with id=-1',-1),('Integer','Read parcel with id=7',7),
    ('String','Read parcel with id="blue-red"','blue-red'),
])
def test_named_literal_and_source_type_resolve_a_singular_read_tie(tmp_path,kind,action,value):
    p,ids,g,state=fixture(tmp_path,kind);before=deepcopy(state.snapshot(full=True))
    proposals,detail=g.step(action,state)
    assert len(proposals)==1 and proposals[0]['entry']==ids['ParcelController.getById']
    proposal=proposals[0]
    assert proposal['params']=={'id':value} and not proposal['unresolved']
    assert proposal['bindings']['id']['source']=='literal' and proposal['bindings']['id']['quote']
    assert detail['grounding_status']=='source_literal_constraint'
    assert detail['retrieval_decision']['accepted'] is False
    assert state.snapshot(full=True)==before
    request=grounded_request(p,proposal['entry'],proposal['params'],proposal['bindings'])
    assert request.record()['path']==['parcels',str(value)]


@pytest.mark.parametrize('action',[
    'Read record with id=11','Read mushroom with id=11','Read all parcels with id=11',
    'Read parcel','Read parcel with id=9223372036854775808','Read parcel with id=7.5',
])
def test_missing_entity_literal_or_native_domain_cannot_resolve_the_tie(tmp_path,action):
    p,ids,g,state=fixture(tmp_path)
    proposals,detail=g.step(action,state)
    assert not proposals and detail['unresolved']


def test_two_source_reads_with_the_same_literal_remain_ambiguous(tmp_path):
    p,ids,g,state=fixture(tmp_path,extra='''@GetMapping("/mirror/parcels/{id}")
      Parcel mirror(@PathVariable Long id){return null;}''')
    proposals,detail=g.step('Read parcel with id=11',state)
    assert not proposals and detail['unresolved']


def test_a_compound_literal_request_is_not_reduced_to_one_entity(tmp_path):
    p,ids,g,state=fixture(tmp_path,extra='''@GetMapping("/depots/{id}")
      Depot depot(@PathVariable Long id){return null;}''',declarations='class Depot{public Long id;}')
    proposals,detail=g.step('Read parcel with id=11 together with depot 9',state)
    assert not proposals and detail['unresolved']


def test_source_namesake_is_not_a_native_long_proof(tmp_path):
    p,ids,g,state=fixture(tmp_path,declarations='class Long{}')
    proposals,detail=g.step('Read parcel with id=11',state)
    assert not proposals and detail['unresolved']


def test_a_literal_id_does_not_create_a_direct_route_around_a_source_ui_guard(tmp_path,monkeypatch):
    p,ids,g,state=fixture(tmp_path);original=g.index.rank
    def guarded(*args):
        rows=original(*args)
        for row in g.index.last_decision['raw_top']:
            g.index.contracts[row['contract_id']]['site']={'id':'ui:guarded','conditions':['false']}
        return rows
    monkeypatch.setattr(g.index,'rank',guarded)
    proposals,detail=g.step('Read parcel with id=11',state)
    assert not proposals and detail['unresolved']


def test_a_stated_other_actor_does_not_obtain_the_restricted_handler(tmp_path):
    p,ids,g,state=fixture(tmp_path,read_annotations='@PreAuthorize("hasRole(\'ADMIN\')")')
    proposals,detail=g.step('As customer, read parcel with id=11',state)
    assert not proposals and detail['unresolved']


