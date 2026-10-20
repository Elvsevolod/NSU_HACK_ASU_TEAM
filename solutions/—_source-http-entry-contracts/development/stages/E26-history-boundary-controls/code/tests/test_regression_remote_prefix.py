import json
import pytest

from analyzer.engine import Engine, AnalysisBoundary
from analyzer.project import Project
from analyzer.state import ScenarioState
from builders import build


def remote_project(tmp_path, filter_source=''):
    project,db,ids=build(tmp_path,{
        'Api.java':'''import java.util.UUID;class Api {@GetMapping("/items/{key}") String read(@PathVariable UUID key){return prefix();}
          String prefix(){return "value";}}'''+filter_source,
        'Caller.java':'''import org.springframework.web.client.RestTemplate;
          class Caller {RestTemplate rest;String entry(String key){return rest.getForObject("http://server/items/"+key,String.class);}}''',
    })
    graph=project.skeleton
    for unit in ('client','server'):graph['nodes']['module:'+unit]={'kind':'module','name':unit,'deployment_units':[unit]}
    for node in graph['nodes'].values():
        if node.get('file') in ('Api.java','Caller.java'):node['module']='server' if node['file']=='Api.java' else 'client'
    (tmp_path/'skeleton.json').write_text(json.dumps(graph))
    return Project(tmp_path/'skeleton.json',tmp_path),db,ids


def test_remote_edge_is_recorded_at_handler_entry_even_when_analysis_stops(tmp_path,monkeypatch):
    project,db,ids=remote_project(tmp_path)
    original=Engine.execute
    def stop(self,node,env):
        if self.method==ids['Api.prefix']:raise AnalysisBoundary('fixture work limit reached inside the entered server')
        return original(self,node,env)
    monkeypatch.setattr(Engine,'execute',stop)
    engine=Engine(project,ScenarioState(db))
    engine.run(ids['Caller.entry'],{'key':'12345678-1234-1234-1234-123456789abc'})
    assert ('','executes',ids['Api.read']) in engine.edges
    assert ('','executes',ids['Api.prefix']) in engine.edges
    assert (ids['Caller.entry'],'remote',ids['Api.read']) in engine.edges
    remote=[event for event in engine.events if event['edge'][1]=='remote']
    assert len(remote)==1 and remote[0]['values']['target_request']==2


@pytest.mark.parametrize('key,gate',[
    ('invalid',''),
    ('12345678-1234-1234-1234-123456789abc', '''class Gate extends OncePerRequestFilter{
      void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain){res.setStatus(403);}}'''),
])
def test_rejection_before_handler_entry_has_no_remote_edge(tmp_path,key,gate):
    project,db,ids=remote_project(tmp_path,gate)
    engine=Engine(project,ScenarioState(db));engine.run(ids['Caller.entry'],{'key':key})
    assert ('','executes',ids['Api.read']) not in engine.edges
    assert (ids['Caller.entry'],'remote',ids['Api.read']) not in engine.edges
