"""Counterexamples chosen independently of the main happy-path fixtures."""
from copy import deepcopy

import pytest

from polygraph.analysis import analyze
from polygraph.kernel import Kernel
from polygraph.state import State
from polygraph.values import Object, Raised, Symbol, Text, Unknown, binary, equal
from support import edge_set, fixture, scenario


@pytest.mark.parametrize("java,python,expected_java,expected_python", [
    ("2147483647+1", "2147483647+1", -2147483648, 2147483648),
    ("-7/3", "-7//3", -2, -3),
    ("-7%3", "-7%3", -1, 2),
    ("Long.MAX_VALUE+1L", "9223372036854775807+1", -9223372036854775808, 9223372036854775808),
    ("'A'+1", "ord_missing", 66, None),
])
def test_numeric_semantics(tmp_path, java, python, expected_java, expected_python):
    sources={"Numbers.java":"class Numbers { long value(){return "+java+";} }", "numbers.py":"def value():\n    return "+("0" if python=="ord_missing" else python)+"\n"}
    p,store,ids=fixture(tmp_path,sources)
    for key,expected in [("Numbers.value",expected_java),("numbers.value",expected_python)]:
        if expected is None:continue
        engine=Kernel(p,State(store));engine.scenario_id="n"
        mid=p.method_by_id[ids[key]]
        receiver=engine.create("Numbers") if key.startswith("Numbers") else None
        assert engine.execute_method(mid,receiver=receiver)==expected


@pytest.mark.parametrize("body,expected", [
    ("int n=1; {int inner=8;inner=inner+1;} return n;",1),
    ("int n=1; for(int i=0;i<3;i++){n=n+2;} return n;",7),
    ("int n=1; return ++n;",2),
    ("int n=1; return n++;",1),
    ("try {return 1;} finally {return 2;}",2),
    ("int n=1; do {n++;} while(n<3); return n;",3),
])
def test_java_local_scope_and_control(tmp_path,body,expected):
    p,store,ids=fixture(tmp_path,{"Scope.java":"class Scope {int n=20; int value(){"+body+"}}"})
    engine=Kernel(p,State(store));engine.scenario_id="scope"
    obj=engine.create("Scope")
    assert engine.execute_method(p.method_by_id[ids["Scope.value"]],receiver=obj)==expected
    assert obj.fields["n"]==20


def test_python_alias_and_global_state_is_scenario_local(tmp_path):
    source='''from fastapi import FastAPI
app=FastAPI()
data={"n":0}
@app.post("/inc")
def inc():
    alias=data
    alias["n"]=alias["n"]+1
    return data
@app.get("/read")
def read():return data
'''
    p,store,ids=fixture(tmp_path,{"main.py":source})
    _,detail=analyze(p,store,{},scenario({"method":"POST","path":"/inc"},{"path":"/read"}))
    assert detail["paths"][0]["steps"][-1]["response"]["body"]=={"n":1}
    _,detail=analyze(p,store,{},scenario({"path":"/read"}))
    assert detail["paths"][0]["steps"][0]["response"]["body"]=={"n":0}


def test_depends_rejection_before_controller(tmp_path):
    source='''from fastapi import FastAPI, APIRouter, Depends, HTTPException
app=FastAPI()
def auth():raise HTTPException(status_code=403)
router=APIRouter(prefix="/protected",dependencies=[Depends(auth)])
@router.get("/")
def controller():return 99
app.include_router(router)
'''
    p,store,ids=fixture(tmp_path,{"main.py":source})
    block,detail=analyze(p,store,{},scenario({"path":"/protected/"}))
    executed={t for s,r,t in edge_set(block,"executes")}
    assert executed=={ids["main.auth"]}
    assert detail["paths"][0]["steps"][0]["response"]["status"]==403


@pytest.mark.parametrize("client,expects_after",[("java",False),("python",True)])
def test_http_404_client_contracts(tmp_path,client,expects_after):
    server='''from fastapi import FastAPI, HTTPException
app=FastAPI()
@app.get("/missing")
def missing():raise HTTPException(status_code=404)
'''
    java='''import org.springframework.web.bind.annotation.*;import org.springframework.web.client.RestTemplate;
@RestController class Client { int after(){return 2;} @GetMapping("/call") int invoke(){new RestTemplate().getForObject("http://server/missing",Object.class);return after();}}
'''
    python='''from fastapi import FastAPI
import requests
app=FastAPI()
def after():return 2
@app.get("/call")
def invoke():
    requests.get("http://server/missing")
    return after()
'''
    sources={"server/main.py":server,"client/Client.java" if client=="java" else "client/client.py":java if client=="java" else python}
    p,store,ids=fixture(tmp_path,sources,modules={"server":"server","client":"client"})
    block,d=analyze(p,store,{},scenario({"path":"/call","module":"client"}))
    after=ids["Client.after" if client=="java" else "client.after"]
    assert any(t==after for s,r,t in edge_set(block))==expects_after


def test_symbolic_id_survives_wire_and_later_request(tmp_path):
    java='''import org.springframework.web.bind.annotation.*;import org.springframework.web.client.RestTemplate;import java.util.Map;
@RestController class Gateway {
 @PostMapping("/make") Object make(){return new RestTemplate().postForObject("http://items/items",Map.of("quantity",6),Object.class);}
 @GetMapping("/load/{id}") Object load(@PathVariable String id){return new RestTemplate().getForObject("http://items/items/"+id,Object.class);}
}'''
    python='''import uuid
from fastapi import FastAPI, Depends
from sqlmodel import SQLModel, Field, Session,create_engine
app=FastAPI()
class Item(SQLModel,table=True):
    id:str=Field(default_factory=uuid.uuid4,primary_key=True)
    quantity:int
def db():return Session(create_engine("sqlite://"))
@app.post("/items")
def create(value:Item,session:Session=Depends(db)):
    session.add(value)
    session.commit()
    return value
@app.get("/items/{id}")
def read(id:str,session:Session=Depends(db)):
    return session.get(Item,id)
'''
    p,store,ids=fixture(tmp_path,{"gateway/Gateway.java":java,"items/main.py":python},["item"],{"item":[]},modules={"gateway":"gateway","items":"items"})
    req1={"method":"POST","path":"/make","module":"gateway"}
    req2={"path":"/load/{id}","path_params":{"id":{"$ref":"steps.1.body.id"}},"module":"gateway"}
    block,d=analyze(p,store,{},scenario(req1,req2))
    assert len(d["paths"])==1,d
    bodies=[s["response"]["body"] for s in d["paths"][0]["steps"]]
    assert bodies[0]["id"]["kind"]=="Symbol", d
    assert bodies[1]==bodies[0]
    assert len(edge_set(block,"remote"))==2
    assert len(edge_set(block,"data"))==2
    assert not any("symbolic-1" in str(v) for v in bodies)


def test_transaction_rollback_preserves_attempted_data_edge(tmp_path):
    source='''import javax.persistence.*;import org.springframework.transaction.annotation.Transactional;
import org.springframework.beans.factory.annotation.Autowired;import org.springframework.data.jpa.repository.JpaRepository;
@Entity @Table(name="entries") class Entry {@Id int id; int value;}
interface Repo extends JpaRepository<Entry,Integer>{}
class Worker {@Autowired Repo repo; @Transactional int work(){Entry e=new Entry();e.id=2;e.value=7;repo.save(e);throw new IllegalArgumentException();}}
'''
    p,store,ids=fixture(tmp_path,{"Transaction.java":source},["entries"],{"entries":[]})
    e=Kernel(p,State(deepcopy(store)));e.scenario_id="rollback"
    obj=e.create("Worker",bean=True)
    with pytest.raises(Raised,match="IllegalArgumentException"):
        e.execute_method(p.method_by_id[ids["Worker.work"]],receiver=obj)
    assert e.state.store.read("storage:entries")==[]
    assert (ids["Worker.work"],"data","storage:entries") in e.edges
    assert any(x["kind"]=="rollback" for x in e.events)


def test_python_exclude_unset_distinguishes_absent_and_null(tmp_path):
    source='''from sqlmodel import SQLModel
class Update(SQLModel):
    title:str|None=None
    description:str|None=None
def dump(value:Update):return value.model_dump(exclude_unset=True)
'''
    p,store,ids=fixture(tmp_path,{"models.py":source})
    e=Kernel(p,State(store));e.scenario_id="unset"
    one=e.create("Update",kwargs={"title":"After"})
    null=e.create("Update",kwargs={"description":None})
    key=p.method_by_id[ids["models.dump"]]
    assert e.execute_method(key,(one,))=={"title":"After"}
    assert e.execute_method(key,(null,))=={"description":None}


def test_session_flush_then_rollback_does_not_commit(tmp_path):
    source='''from fastapi import FastAPI
from sqlmodel import SQLModel,Field,Session,create_engine
app=FastAPI()
class Entry(SQLModel,table=True):
    id:int=Field(primary_key=True)
    value:int
@app.post("/try")
def write():
    session=Session(create_engine("sqlite://"))
    session.add(Entry(id=2,value=8))
    session.flush()
    session.rollback()
    return 1
'''
    p,store,ids=fixture(tmp_path,{"main.py":source},["entry"],{"entry":[]})
    block,d=analyze(p,store,{},scenario({"method":"POST","path":"/try"}))
    assert d["paths"][0]["state"]["storage:entry"]==[]
    assert len(edge_set(block,"data"))==1


def test_entity_queries_do_not_join_different_id_fields(tmp_path):
    source='''from fastapi import FastAPI,Depends
from sqlmodel import SQLModel,Field,Session,select,create_engine
app=FastAPI()
class Item(SQLModel,table=True):
    id:int=Field(primary_key=True)
    owner_id:int
class Account(SQLModel,table=True):
    id:int=Field(primary_key=True)
    label:str
@app.get("/items")
def read():
    session=Session(create_engine("sqlite://"))
    return session.exec(select(Item).where(Item.owner_id==2)).all()
'''
    p,store,ids=fixture(tmp_path,{"main.py":source},["item","account"],{"item":[{"id":2,"owner_id":1},{"id":3,"owner_id":2}],"account":[{"id":2,"label":"owner"}]})
    block,d=analyze(p,store,{},scenario({"path":"/items"}))
    assert [r["id"] for r in d["paths"][0]["steps"][0]["response"]["body"]]==[3]
    assert {t for s,r,t in edge_set(block,"data")}=={"storage:item"}


def test_profile_and_conditional_mount_are_not_confirmed(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;import org.springframework.context.annotation.Profile;
@RestController @Profile("prod") class Prod {@GetMapping("/prod") int read(){return 1;}}
@RestController @Profile("dev") class Dev {@GetMapping("/dev") int read(){return 2;}}
'''
    p,store,ids=fixture(tmp_path,{"Profile.java":source},profiles=["dev"])
    assert [e.path for e in p.endpoints]==["/dev"]
    source='''from fastapi import FastAPI,APIRouter
app=FastAPI()
router=APIRouter()
@router.get("/conditional")
def read():return 1
if unknown_config:
    app.include_router(router)
'''
    p,store,ids=fixture(tmp_path/"conditional",{"main.py":source})
    block,d=analyze(p,store,{},scenario({"path":"/conditional"}))
    assert d["must"]==[] and d["status"]=="partial"
    assert len(d["paths"])==2


def test_ambiguous_grounding_preserves_both_candidates(tmp_path):
    source='''from fastapi import FastAPI
app=FastAPI()
@app.post("/a/item")
def create_item_a():return 1
@app.post("/b/item")
def create_item_b():return 2
'''
    p,store,ids=fixture(tmp_path,{"main.py":source})
    s={"id":"ambiguous","steps":[{"action":"Create item"}]}
    block,d=analyze(p,store,{},s)
    assert len(d["paths"])==2 and d["must"]==[]
    assert {t for s,r,t in edge_set(block,"executes")}=={ids["main.create_item_a"],ids["main.create_item_b"]}


def test_unknown_initial_table_is_not_assumed_empty(tmp_path):
    source='''from fastapi import FastAPI
from sqlmodel import SQLModel,Field,Session,create_engine
app=FastAPI()
class Item(SQLModel,table=True):
    id:int=Field(primary_key=True)
@app.get("/{id}")
def read(id:int):return Session(create_engine("sqlite://")).get(Item,id)
'''
    p,store,ids=fixture(tmp_path,{"main.py":source},["item"])
    _,d=analyze(p,store,{},scenario({"path":"/3"}))
    assert d["paths"][0]["steps"][0]["response"]["body"]["kind"]=="Unknown"
