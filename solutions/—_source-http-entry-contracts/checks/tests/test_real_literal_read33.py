"""Real-source integration data belongs to the analysis package, not core tests."""
from pathlib import Path
from analyzer.project import Project
from analyzer.state import Database,ScenarioState
from analyzer.frontend import Frontend
from analyzer.contracts import ContractGrounder
from analyzer.lexical_retrieval import LexicalContractIndex
from analyzer.request import grounded_request,BoundParameters
from analyzer.engine import Engine

V=Path(__file__).resolve().parents[2]


def test_real_fresh_state_read_keeps_handler_wire_native_long_and_sql():
    package=V/'development/semantic-holdout-packages-v1/healthcare'
    p=Project(package/'skeleton.json',package/'source');db=Database(package/'initial.sql')
    f=Frontend(p);g=ContractGrounder(p,f,LexicalContractIndex(p,f),None,{'facts':{},'unresolved':[]})
    proposals,detail=g.step('Read patient with id=11',ScenarioState(db))
    expected=[mid for mid,m in p.methods.items() if p.nodes[m['owner']]['fqn'].endswith('.PatientController') and m['name']=='getById']
    assert len(proposals)==1 and proposals[0]['entry']==expected[0]
    proposal=proposals[0];request=grounded_request(p,proposal['entry'],proposal['params'],proposal['bindings'])
    e=Engine(p,proposal['state']);result=e.run(proposal['entry'],BoundParameters(proposal['params'],request))
    assert result['id']==11 and result['name']=='Seed Patient' and not e.approximate
    assert e.request_events[0]['bound_arguments'][0]['native_kind']=='Long'
    assert len(e.data_operations)==1 and e.data_operations[0]['operation']=='findById'
    assert e.data_operations[0]['arguments']==[11] and e.data_operations[0]['argument_kinds']==['Long']
    assert detail['retrieval_decision']['accepted'] is False
