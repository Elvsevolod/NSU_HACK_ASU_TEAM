"""Check the actual HTTP boundary, rather than only planned parameters."""
import argparse,json,sys
from pathlib import Path
V=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(V/'code'),str(V/'code/tests')]
from analyzer.contracts import ContractGrounder,ContractIndex,read_static_context
from analyzer.frontend import Frontend
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from analyzer.request import Request,grounded_request
from analyzer.__main__ import serial
from evidence import capture,chain
from test_actor_credentials_flow import fixture
from builders import build


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=V/'benchmark/boundary-wires')
    output=parser.parse_args().output;assert not output.exists();output.mkdir(parents=True)
    root=output/'actor-inputs';root.mkdir();p,db,ids=fixture(root)
    page=root/'page.html';page.write_text(page.read_text().replace('</html>',
        '<input id="username" value="alice"><input id="password" value="secret"></html>'))
    f=Frontend(p);ctx=read_static_context({'account':'The passenger is the pre-registered user alice / secret'})
    g=ContractGrounder(p,f,ContractIndex(p,f),None,ctx)
    proposals,_=g.step("Log in to the admin console with the administrator's username and password",ScenarioState(db))
    actor_rows=[]
    for proposal in proposals:
        request=grounded_request(p,proposal['entry'],proposal['params'],proposal['bindings'],actor=proposal['actor'])
        e=Engine(p,proposal['state'],conservative=True);value=e.run(proposal['entry'],request)
        actor_rows.append(capture(e,request,value))
        bound=e.request_events[0].get('bound_arguments',[])
        if bound and isinstance(bound[0].get('value'),dict):
            dto=bound[0]['value'];assert dto.get('username')!='alice' and dto.get('password')!='secret'
        assert request.body.get('username')!='alice' and request.body.get('password')!='secret'
    p,db,ids=build(output/'singleton-inputs',{'Api.java':'''import org.springframework.stereotype.Component;
      import javax.annotation.PostConstruct;
      @Component class Counter{int revision;@PostConstruct void init(){revision=7;}
       int set(boolean flag){if(flag){revision=8;}else{revision=9;}revision=10;return revision;}
       int read(){return revision;}}
      class Patch{public boolean flag;}
      class Api{Counter counter;@PostMapping("/counter")int write(@RequestBody Patch input){return counter.set(input.flag);}
       @GetMapping("/counter")int read(){return counter.read();}}'''})
    first=Engine(p,ScenarioState(db),conservative=True);wire=Request.http('service','POST','/counter',body={'flag':U})
    result=first.run(ids['Api.write'],wire);assert result==10
    rows=[capture(first,wire,result)]
    second=Engine(p,first.state);wire=Request.http('service','GET','/counter');value=second.run(ids['Api.read'],wire)
    assert type(value) is int and value==10;rows.append(capture(second,wire,value))
    (output/'checks.json').write_text(json.dumps({'passed':bool(actor_rows),'admin_wire_does_not_borrow_dom_defaults':True,
        'next_http_request_reads_joined_singleton_value':10,'actor_observations':actor_rows,
        'singleton':chain(rows,'singleton/actual-HTTP'),
        'scope':'unknown but valid typed flag; codec completeness diagnostics are retained'},default=serial,indent=2)+'\n')


if __name__=='__main__':main()
