from analyzer.contracts import ContractGrounder,ContractIndex
from analyzer.engine import Engine
from analyzer.frontend import Frontend
from analyzer.request import grounded_request
from analyzer.state import ScenarioState
from builders import build


def test_grounded_field_cannot_disappear_between_plan_wire_and_java_args(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Filter {public int state;public String name;}
      class Api {@PostMapping("/items/query") int query(@RequestBody Filter filter){return filter.state;}}'''})
    (tmp_path/'ui.js').write_text('''function query(){$.ajax({url:"/items/query",type:"POST",contentType:"application/json",data:JSON.stringify({name:$("#name").val()})});}''')
    ui=Frontend(project);grounder=ContractGrounder(project,ui,ContractIndex(project,ui),None,{'facts':{}})
    proposals,_=grounder.step('Query items state 1 name "A"',ScenarioState(db))
    assert len(proposals)==1
    proposal=proposals[0]
    request=grounded_request(project,proposal['entry'],proposal['params'])
    engine=Engine(project,proposal['state'])
    assert proposal['params']['state']==request.body['state']==engine.bind_request(proposal['entry'],request,'check')[0]['state']==1
    assert engine.run(proposal['entry'],request)==1
    assert proposal['site'] is None
    assert any('UI omits' in reason for reason in proposal['unresolved'])
