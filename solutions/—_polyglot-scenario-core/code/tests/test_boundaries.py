import json
from pathlib import Path
import subprocess
import sys

import pytest

from polygraph.analysis import analyze
from polygraph.grounding import Grounder
from polygraph.kernel import Kernel
from polygraph.project import Project
from polygraph.state import State
from polygraph.values import Unknown
from support import edge_set, fixture, scenario


def test_async_call_executes_only_when_awaited(tmp_path):
    source='''from fastapi import FastAPI
app=FastAPI()
async def work():return 7
@app.get("/unawaited")
async def unawaited():
    value=work()
    return 1
@app.get("/awaited")
async def awaited():
    return await work()
'''
    p,store,ids=fixture(tmp_path,{"main.py":source})
    a,da=analyze(p,store,{},scenario({"path":"/unawaited"}))
    b,db=analyze(p,store,{},scenario({"path":"/awaited"}))
    assert not any(t==ids["main.work"] for s,r,t in edge_set(a))
    assert any(t==ids["main.work"] for s,r,t in edge_set(b))
    assert db["paths"][0]["steps"][0]["response"]["body"]==7


def test_async_http_client_is_lazy_and_await_crosses_wire(tmp_path):
    client='''from fastapi import FastAPI
import httpx
app=FastAPI()
@app.get("/read")
async def read():
    async with httpx.AsyncClient() as client:
        response=await client.get("http://server/value")
        return response.json()
'''
    server='''from fastapi import FastAPI
app=FastAPI()
@app.get("/value")
def value():return {"answer":42}
'''
    p,store,ids=fixture(tmp_path,{"client/client.py":client,"server/server.py":server},modules={"client":"client","server":"server"})
    block,d=analyze(p,store,{},scenario({"path":"/read","module":"client"}))
    assert d["paths"][0]["steps"][0]["response"]["body"]=={"answer":42}
    assert (ids["client.read"],"remote",ids["server.value"]) in edge_set(block)


def test_mutable_python_defaults_persist_within_scenario(tmp_path):
    source='''def value(values=[]):
    values.append(1)
    return len(values)
'''
    p,store,ids=fixture(tmp_path,{"defaults.py":source})
    e=Kernel(p,State(store));e.scenario_id="defaults"
    key=p.method_by_id[ids["defaults.value"]]
    assert e.execute_method(key)==1
    assert e.execute_method(key)==2
    other=Kernel(p,State(store));other.scenario_id="other"
    assert other.execute_method(key)==1


def test_supplied_model_value_does_not_run_default_factory(tmp_path):
    source='''from sqlmodel import SQLModel,Field
def make():return 99
class Value(SQLModel):
    number:int=Field(default_factory=make)
'''
    p,store,ids=fixture(tmp_path,{"models.py":source})
    e=Kernel(p,State(store));e.scenario_id="factory"
    assert e.create("Value",kwargs={"number":3}).fields["number"]==3
    assert not e.edges
    assert e.create("Value").fields["number"]==99
    assert any(t==ids["models.make"] for s,r,t in e.edges)


def test_unknown_filter_prevents_unconditional_handler_claim(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;import javax.servlet.*;import javax.servlet.http.*;
import org.springframework.web.filter.OncePerRequestFilter;
class Guard extends OncePerRequestFilter {protected void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain){return;}}
@RestController class Handler {@GetMapping("/value") int read(){return 3;}}
'''
    p,store,ids=fixture(tmp_path,{"Guard.java":source})
    _,d=analyze(p,store,{},scenario({"path":"/value"}))
    assert d["must"]==[] and d["status"]=="partial"
    assert any(x["code"]=="framework-lifecycle" for path in d["paths"] for x in path["diagnostics"])


@pytest.mark.parametrize("value",["weightGrams=5 kg","weightGrams=5 grams","weightGrams: 3lb"])
def test_units_are_not_silently_removed(value):
    assert isinstance(Grounder.extract(value,"weightGrams","int"),Unknown)


def test_required_body_field_rejects_before_fastapi_handler(tmp_path):
    source='''from fastapi import FastAPI
from sqlmodel import SQLModel
app=FastAPI()
class Input(SQLModel):
    value:int
@app.post("/value")
def create(value:Input):return value
'''
    p,store,ids=fixture(tmp_path,{"main.py":source})
    block,d=analyze(p,store,{},scenario({"method":"POST","path":"/value","body":{}}))
    assert not edge_set(block,"executes")
    assert d["paths"][0]["steps"][0]["response"]["status"]==422


def test_offline_cli_arbitrary_path_and_unexecuted_module(tmp_path):
    source='''from fastapi import FastAPI
raise RuntimeError("This target module must never be imported")
app=FastAPI()
@app.get("/value")
def value():return 42
'''
    p,store,ids=fixture(tmp_path/"sample",{"main.py":source})
    scenarios=tmp_path/"scenario.json";scenarios.write_text(json.dumps(scenario({"path":"/value"})))
    context=tmp_path/"context.json";context.write_text('{"tables":{}}')
    output=tmp_path/"answer.json";report=tmp_path/"report.json"
    run=Path(__file__).resolve().parents[1]/"offline_run.py"
    result=subprocess.run([sys.executable,"-B",str(run),"--source",str(p.root),"--skeleton",str(tmp_path/"sample/skeleton.json"),"--context",str(context),"--scenarios",str(scenarios),"--output",str(output),"--report",str(report)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    # The source has an unconditional startup failure. Method-body prediction is
    # conditional on a running/warmed application, not a claim startup succeeds.
    assert json.loads(output.read_text())["scenarios"]["arbitrary"]["edges"]
    assert json.loads(report.read_text())["application_executed"] is False


def test_deleted_source_and_profile_change_invalidate_ir_cache(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;import org.springframework.context.annotation.Profile;
@RestController @Profile("dev") class Handler {@GetMapping("/value") int read(){return 1;}}
'''
    cache=tmp_path/"cache.json"
    p,store,ids=fixture(tmp_path,{"Handler.java":source},cache=cache,profiles=["dev"])
    analyze(p,store,{},scenario({"path":"/value"}));p.save_cache()
    changed=Project(p.root,tmp_path/"skeleton.json",cache,profiles=["prod"])
    assert changed.fingerprint!=p.fingerprint and changed.endpoints==[]
    (p.root/"Handler.java").unlink()
    deleted=Project(p.root,tmp_path/"skeleton.json",cache,profiles=["dev"])
    assert deleted.fingerprint!=p.fingerprint and deleted.endpoints==[]


def test_nested_exception_restores_active_exception(tmp_path):
    source='''def value():
    try:
        raise ValueError()
    except ValueError:
        try:
            raise KeyError()
        except KeyError:
            pass
        raise
'''
    from polygraph.values import Raised
    p,store,ids=fixture(tmp_path,{"exceptions.py":source})
    e=Kernel(p,State(store));e.scenario_id="exceptions"
    with pytest.raises(Raised,match="ValueError"):
        e.execute_method(p.method_by_id[ids["exceptions.value"]])


@pytest.mark.parametrize("arguments,keywords",[((1,),{}),((),{}),((),{"number":1,"extra":2})])
def test_invalid_python_argument_binding_does_not_execute_callee(tmp_path,arguments,keywords):
    source='''def value(*,number):return number\n'''
    from polygraph.values import Raised
    p,store,ids=fixture(tmp_path,{"bindings.py":source})
    e=Kernel(p,State(store));e.scenario_id="bad-binding"
    with pytest.raises(Raised,match="TypeError"):
        e.execute_method(p.method_by_id[ids["bindings.value"]],arguments,keywords)
    assert not e.edges


def test_generator_is_lazy_until_framework_or_iteration_drives_it(tmp_path):
    source='''from fastapi import FastAPI
app=FastAPI()
def effect():return 8
def values():
    effect()
    yield 1
@app.get("/value")
def value():
    unused=values()
    return 9
'''
    p,store,ids=fixture(tmp_path,{"main.py":source})
    block,d=analyze(p,store,{},scenario({"path":"/value"}))
    assert {t for s,r,t in edge_set(block,"executes")}=={ids["main.value"]}


def test_unknown_names_are_not_equal_type_references(tmp_path):
    source='''from fastapi import FastAPI
app=FastAPI()
def same():return 1
def different():return 2
@app.get("/value")
def value():
    if unavailable==other_unavailable:
        return same()
    return different()
'''
    p,store,ids=fixture(tmp_path,{"main.py":source})
    block,d=analyze(p,store,{},scenario({"path":"/value"}))
    assert len(d["paths"])==2 and d["status"]=="partial"
    assert not any(e["target"] in {ids["main.same"],ids["main.different"]} for e in d["must"])


def test_python_property_executes_its_source_body(tmp_path):
    source='''class Value:
    def __init__(self):self.number=6
    @property
    def double(self):return self.number*2
def read(value):return value.double
'''
    p,store,ids=fixture(tmp_path,{"properties.py":source})
    e=Kernel(p,State(store));e.scenario_id="property"
    obj=e.create("Value")
    assert e.execute_method(p.method_by_id[ids["properties.read"]],(obj,))==12
    assert any(t==ids["properties.double"] for s,r,t in e.edges)
