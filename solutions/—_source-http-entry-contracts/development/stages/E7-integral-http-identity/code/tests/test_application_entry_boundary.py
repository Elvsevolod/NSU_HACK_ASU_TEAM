from analyzer.paths import run_paths
from analyzer.request import Request
from analyzer.state import ScenarioState
from builders import build


def test_application_slice_is_explicit_and_default_still_runs_filter(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import jakarta.servlet.http.*;
      @RestController class Api { @GetMapping("/items") int read(){return 8;} }
      class Gate extends OncePerRequestFilter {
        void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain){res.setStatus(403);}
      }'''})
    request=Request.http(None,'GET','/items',headers={})
    normal=run_paths(project,ScenarioState(db),ids['Api.read'],request)
    assert all(p['engine'].http_responses[0]['status']==403 for p in normal)
    sliced=run_paths(project,ScenarioState(db),ids['Api.read'],request,
                     entry_boundary='application_after_authentication')
    assert len(sliced)==1 and sliced[0]['result']==8
    event=sliced[0]['engine'].request_events[0]
    assert event['entry_boundary']=='application_after_authentication'
    assert event['security_evaluated'] is False
    assert sliced[0]['engine'].http_responses[0]['body']==8
