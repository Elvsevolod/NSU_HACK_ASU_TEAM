import json
from copy import deepcopy

import pytest

from polygraph.analysis import analyze, validate
from polygraph.kernel import Kernel
from polygraph.state import State, load_context
from polygraph.values import Object, Raised, Symbol, Unknown, binary
from support import edge_set, fixture, scenario


JAVA = '''import org.springframework.web.bind.annotation.*;
import org.springframework.stereotype.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.jpa.repository.JpaRepository;
import javax.persistence.*;
@Entity @Table(name="stock") class Stock {
 @Id int id; int quantity;
 public int getId(){return id;}
 public int getQuantity(){return quantity;}
 public void setQuantity(int n){quantity=n;}
}
interface StockRepo extends JpaRepository<Stock,Integer> {}
@Service class Worker {
 @Autowired StockRepo repo;
 public Stock read(int id){return repo.findById(id).orElse(null);}
 public Stock change(int id,int quantity){Stock s=read(id); if(s==null) return null; s.setQuantity(quantity); return repo.save(s);}
}
@RestController @RequestMapping("/stock") class Controller {
 @Autowired Worker worker;
 @GetMapping("/{id}") public Stock read(@PathVariable int id){return worker.read(id);}
 @PutMapping("/{id}") public Stock change(@PathVariable int id,@RequestBody Stock value){return worker.change(id,value.getQuantity());}
}
'''

PYTHON = '''from fastapi import FastAPI, APIRouter, Depends, HTTPException
from sqlmodel import SQLModel, Field, Session, select,create_engine
app=FastAPI()
router=APIRouter(prefix="/stock")
class Stock(SQLModel,table=True):
    __tablename__="stock"
    id:int=Field(primary_key=True)
    quantity:int
def session():
    return Session(create_engine("sqlite://"))
def read_one(db:Session,id:int):
    return db.get(Stock,id)
@router.get("/{id}")
def read(id:int,db:Session=Depends(session)):
    s=read_one(db,id)
    if s is None:
        raise HTTPException(status_code=404,detail="missing")
    return s
@router.put("/{id}")
def change(id:int,value:Stock,db:Session=Depends(session)):
    s=read_one(db,id)
    if s is None:
        raise HTTPException(status_code=404,detail="missing")
    s.quantity=value.quantity
    db.add(s)
    db.commit()
    return s
app.include_router(router,prefix="/api")
'''


@pytest.mark.parametrize("language", ["java", "python"])
def test_stateful_flow_uses_one_kernel(tmp_path, language):
    source = {"Stock.java": JAVA} if language == "java" else {"app.py": PYTHON}
    p, store, ids = fixture(tmp_path, source, ["stock"], {"stock": [{"id": 7, "quantity": 5}]})
    prefix = "" if language == "java" else "/api"
    s = scenario({"method": "GET", "path": prefix + "/stock/7"},
                 {"method": "PUT", "path": prefix + "/stock/7", "body": {"id": 7, "quantity": 9}},
                 {"method": "GET", "path": prefix + "/stock/7"})
    block, detail = analyze(p, store, {}, s)
    assert len(detail["paths"]) == 1, detail
    path = detail["paths"][0]
    assert [r["response"]["body"]["quantity"] for r in path["steps"]] == [5, 9, 9], detail
    assert path["state"]["storage:stock"][0]["quantity"] == 9
    assert store.read("storage:stock")[0]["quantity"] == 5
    assert len(edge_set(block, "data")) >= 1
    assert len(edge_set(block, "calls")) >= 1
    assert detail["fully_explored_in_model"]
    validate(p, {"project": p.skeleton["project"], "scenarios": {s["id"]: block}})
    second, d2 = analyze(p, store, {}, scenario({"method": "GET", "path": prefix + "/stock/7"}))
    assert d2["paths"][0]["steps"][0]["response"]["body"]["quantity"] == 5
    assert p.lowered > 0


@pytest.mark.parametrize("language", ["java", "python"])
def test_arithmetic_language_boundary(tmp_path, language):
    source = {"Arithmetic.java": '''class Arithmetic { public int value(){int n=2147483647;return n+1;} }'''} if language == "java" else {"arithmetic.py": "def value():\n    n=2147483647\n    return n+1\n"}
    p, store, ids = fixture(tmp_path, source)
    key = p.method_by_id[ids["Arithmetic.value" if language == "java" else "arithmetic.value"]]
    engine = Kernel(p, State(store)); engine.scenario_id = "numbers"
    obj = engine.create(p.methods[key].owner, span=p.methods[key].span) if language == "java" else None
    assert engine.execute_method(key, receiver=obj) == (-2147483648 if language == "java" else 2147483648)


def test_java_control_and_typed_catches(tmp_path):
    source = '''class Control {
 public int value(){int n=0;try {throw new IllegalArgumentException();}
 catch(NullPointerException e){return 99;} catch(IllegalArgumentException e){n=2;} finally {n=n+3;} return n;}
 public int switchReturn(int n){switch(n){case 1:return 7;default:return 8;} }
 public int stopped(){String x=null; x.equals("a"); return later();}
 public int later(){return 99;}
}'''
    p, store, ids = fixture(tmp_path, {"Control.java": source})
    e = Kernel(p, State(store));e.scenario_id="control"
    obj=e.create("Control")
    assert e.execute_method(p.method_by_id[ids["Control.value"]], receiver=obj) == 5
    assert e.execute_method(p.method_by_id[ids["Control.switchReturn"]], (1,), receiver=obj) == 7
    with pytest.raises(Raised, match="NullPointerException"):
        e.execute_method(p.method_by_id[ids["Control.stopped"]], receiver=obj)
    assert not any(t == ids["Control.later"] for a,b,t in e.edges)


def test_python_exception_finally_and_short_circuit(tmp_path):
    source = '''def later():
    return 99
def value():
    n=0
    try:
        raise ValueError()
    except KeyError:
        return 99
    except ValueError:
        n=2
    finally:
        n=n+3
    return n
def short():
    return False and later()
'''
    p, store, ids = fixture(tmp_path,{"control.py":source})
    e=Kernel(p,State(store));e.scenario_id="c"
    assert e.execute_method(p.method_by_id[ids["control.value"]]) == 5
    assert e.execute_method(p.method_by_id[ids["control.short"]]) is False
    assert not any(t==ids["control.later"] for a,b,t in e.edges)


def test_http_method_and_mixed_language_remote(tmp_path):
    java = '''import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
@RestController class Gateway {
 @GetMapping("/proxy") public Object proxy(){RestTemplate c=new RestTemplate();return c.getForObject("http://catalog/items/3",Object.class);}
}'''
    python = '''from fastapi import FastAPI
app=FastAPI()
def helper():return {"quantity":4}
@app.get("/items/{id}")
def read(id:int):return helper()
@app.post("/items/{id}")
def wrong(id:int):return {"quantity":99}
'''
    p, store, ids = fixture(tmp_path, {"gateway/Gateway.java": java, "catalog/main.py": python},modules={"gateway":"gateway","catalog":"catalog"})
    block,d=analyze(p,store,{},scenario({"method":"GET","path":"/proxy","module":"gateway"}))
    assert d["paths"][0]["steps"][0]["response"]["body"] == {"quantity":4}, d
    assert (ids["Gateway.proxy"],"remote",ids["main.read"]) in edge_set(block)
    assert (ids["Gateway.proxy"],"calls",ids["main.read"]) not in edge_set(block)
    assert not any(t==ids["main.wrong"] for a,b,t in edge_set(block))
    assert (ids["main.read"],"calls",ids["main.helper"]) in edge_set(block)


def test_opaque_call_and_loop_budget_never_claim_complete(tmp_path):
    source = '''from fastapi import FastAPI
app=FastAPI()
def after():return 1
@app.get("/opaque")
def opaque():
    external_mutation()
    return after()
@app.get("/loop")
def loop():
    while True:
        after()
    return 99
'''
    p,store,ids=fixture(tmp_path,{"main.py":source})
    block,d=analyze(p,store,{},scenario({"path":"/opaque"}),path_limit=1)
    assert d["status"] == "partial"
    assert d["must"] == []
    block,d=analyze(p,store,{},scenario({"path":"/loop"}),loop_limit=2)
    assert d["paths"][0]["coverage"] == "cutoff"
    assert not d["fully_explored_in_model"] and d["must"] == []


def test_sql_named_columns_escaping_and_unknown_state(tmp_path):
    p,store,ids=fixture(tmp_path,{"Empty.java":"class Empty{}"},["stock"])
    path=tmp_path/"initial.sql"
    path.write_text("USE app;CREATE TABLE `stock` (\n`id` int,\n`label` varchar(80)); INSERT INTO `stock` (`label`,`id`) VALUES ('O''Brien; store',7),('a\\'b',8);")
    store,context,warnings=load_context(path,p)
    assert warnings==[]
    assert store.read("storage:stock")==[{"label":"O'Brien; store","id":7},{"label":"a'b","id":8}]
    other=deepcopy(store);other.havoc()
    assert isinstance(other.read("storage:stock"),Unknown)
    assert not isinstance(store.read("storage:stock"),Unknown)


def test_persistent_ir_cache_and_source_invalidation(tmp_path):
    cache=tmp_path/"cache.json"
    p,store,ids=fixture(tmp_path,{"main.py":"from fastapi import FastAPI\napp=FastAPI()\n@app.get('/value')\ndef value():return 1\n"},cache=cache)
    first,detail=analyze(p,store,{},scenario({"path":"/value"}));p.save_cache()
    from polygraph.project import Project
    warm=Project(p.root,tmp_path/"skeleton.json",cache)
    second,detail=analyze(warm,store,{},scenario({"path":"/value"}))
    assert first==second and warm.cache_hits>0 and warm.lowered==0
    file=p.root/"main.py";file.write_text(file.read_text().replace("return 1","return 2"))
    changed=Project(p.root,tmp_path/"skeleton.json",cache)
    _,detail=analyze(changed,store,{},scenario({"path":"/value"}))
    assert changed.cache_hits==0
    assert detail["paths"][0]["steps"][0]["response"]["body"]==2


def test_scenario_identifier_never_selects_behavior(tmp_path):
    p,store,ids=fixture(tmp_path,{"main.py":PYTHON},["stock"],{"stock":[{"id":7,"quantity":5}]})
    request={"path":"/api/stock/7"}
    a,da=analyze(p,store,{},scenario(request,identifier="one"))
    b,db=analyze(p,store,{},scenario(request,identifier="unrelated"))
    assert {(r if r!="executes" else "executes",t) for s,r,t in edge_set(a)}=={(r,t) for s,r,t in edge_set(b)}


def test_unknown_cannot_be_used_as_python_boolean():
    with pytest.raises(TypeError):bool(Unknown("missing"))
