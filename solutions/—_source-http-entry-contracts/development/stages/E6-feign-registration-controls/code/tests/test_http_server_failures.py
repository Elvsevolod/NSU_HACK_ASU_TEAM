from analyzer.engine import Engine
from analyzer.state import ScenarioState
from builders import build
from analyzer.project import Project
from analyzer.paths import run_paths
import json


def test_uncaught_server_exception_uses_http_client_error_type(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;
      class Api {@GetMapping("/fail") String fail(){throw new IllegalArgumentException();}}
      class Caller {RestTemplate rest;String entry(){try{
        rest.getForObject("http://service/fail",String.class);return after();}
        catch(IllegalArgumentException failure){return wrong();}
        catch(HttpServerErrorException failure){return "rejected";}}
        String after(){return "wrong";}String wrong(){return "wrong-java-exception";}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='rejected'
    executed={target for _,kind,target in engine.edges if kind=='executes'}
    assert ids['Api.fail'] in executed and ids['Caller.after'] not in executed and ids['Caller.wrong'] not in executed


def test_a_failed_remote_handler_still_has_an_executed_remote_edge(tmp_path):
    project,db,ids=build(tmp_path,{
      'Api.java':'''class Api {@GetMapping("/fail") String fail(){throw new IllegalArgumentException();}}''',
      'Caller.java':'''import org.springframework.web.client.RestTemplate;
        class Caller {RestTemplate rest;String entry(){try{
          rest.getForObject("http://server/fail",String.class);return "wrong";}
          catch(HttpServerErrorException failure){return "rejected";}}}''',
    })
    skeleton=project.skeleton
    for unit in ('client','server'):skeleton['nodes']['module:'+unit]={'kind':'module','name':unit,'deployment_units':[unit]}
    for node in skeleton['nodes'].values():
        if node.get('file') in ('Api.java','Caller.java'):node['module']='server' if node['file']=='Api.java' else 'client'
    (tmp_path/'skeleton.json').write_text(json.dumps(skeleton));project=Project(tmp_path/'skeleton.json',tmp_path)
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{})=='rejected'
    assert (ids['Caller.entry'],'remote',ids['Api.fail']) in engine.edges


def test_source_exception_handler_supplies_the_default_success_status(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;
      class Api {@GetMapping("/fail") String fail(){throw new IllegalArgumentException();}
        @ExceptionHandler(IllegalArgumentException.class) String recover(){return "recovered";}}
      class Caller {RestTemplate rest;String entry(){try{
        rest.getForObject("http://service/fail",String.class);return "after";}
        catch(Exception failure){return "rejected";}}}'''})
    outcomes=run_paths(project,ScenarioState(db),ids['Caller.entry'],{})
    assert {outcome['result'] for outcome in outcomes}=={'after'}
    assert all(('', 'executes',ids['Api.recover']) in outcome['engine'].edges for outcome in outcomes)
    assert all((ids['Api.fail'],'calls',ids['Api.recover']) not in outcome['engine'].edges for outcome in outcomes)
    assert all(outcome['engine'].http_responses[-1]['status']==200 for outcome in outcomes)
