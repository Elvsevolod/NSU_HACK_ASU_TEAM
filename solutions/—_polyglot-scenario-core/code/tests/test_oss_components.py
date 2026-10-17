"""Behavioural acceptance and ablations for reused open-source components."""
from decimal import Decimal
import json

import pytest

from polygraph.analysis import analyze
from polygraph.constraints import PathSolver
from polygraph.kernel import Kernel
from polygraph.project import Project
from polygraph.state import State, load_context
from polygraph.values import Formula, Raised, Symbol, Unknown, binary
from support import edge_set, fixture, scenario


def test_sqlglot_postgres_quoted_identifiers_comments_and_exact_decimal(tmp_path):
    p, _, _ = fixture(tmp_path, {}, tables=["stock"])
    sql = tmp_path / "context.sql"
    sql.write_text('''-- a delimiter in a comment ;
CREATE TABLE "app"."stock" ("id" INTEGER, "description" TEXT, "price" NUMERIC);
INSERT INTO "app"."stock" ("description", "price", "id")
VALUES ('-- not a comment; /* text */ O''Brien', 0.10000000000000000001, 3);
''')
    store, _, warnings = load_context(sql, p, "postgres")
    assert warnings == []
    assert store.read("storage:stock") == [{"id": 3, "description": "-- not a comment; /* text */ O'Brien", "price": Decimal("0.10000000000000000001")}]


@pytest.mark.parametrize("mutation", ["UPDATE stock SET id=9", "INSERT INTO stock SELECT id FROM stock", "INSERT INTO stock VALUES (1,2)"])
def test_unmodelled_context_mutation_cannot_prove_empty_table(tmp_path, mutation):
    p, _, _ = fixture(tmp_path, {}, tables=["stock"])
    sql = tmp_path / "context.sql"
    sql.write_text("CREATE TABLE stock (id INT);" + mutation + ";")
    store, _, warnings = load_context(sql, p)
    assert warnings and isinstance(store.read("storage:stock"), Unknown)


def test_libcst_framework_alias_and_annotated_dependency(tmp_path):
    source = '''from fastapi import FastAPI as API, APIRouter as Router, Depends as Inject, HTTPException
from typing import Annotated as Ann
app=API()
router=Router(prefix="/audit")
def guard():raise HTTPException(status_code=403)
@router.get("/value")
def value(auth:Ann[int,Inject(guard)]):return 4
app.include_router(router,prefix="/api")
'''
    p, store, ids = fixture(tmp_path, {"main.py": source})
    block, detail = analyze(p, store, {}, scenario({"path": "/api/audit/value"}))
    assert {target for _, _, target in edge_set(block, "executes")} == {ids["main.guard"]}
    assert detail["paths"][0]["steps"][0]["response"]["status"] == 403


def test_libcst_local_shadow_cannot_call_imported_function(tmp_path):
    source = '''from helper import effect
def value():
    effect()
    effect=1
'''
    p, store, ids = fixture(tmp_path, {"main.py": source, "helper.py": "def effect():return 42\n"})
    engine = Kernel(p, State(store)); engine.scenario_id = "shadow"
    with pytest.raises(Raised, match="UnboundLocalError"):
        engine.execute_method(p.method_by_id[ids["main.value"]])
    assert not any(target == ids["helper.effect"] for _, _, target in engine.edges)


def test_libcst_does_not_treat_same_named_user_class_as_fastapi(tmp_path):
    source = '''class FastAPI:
    def get(self,path):return None
app=FastAPI()
@app.get("/value")
def value():return 3
'''
    p, _, _ = fixture(tmp_path, {"main.py": source})
    assert p.endpoints == []


def test_libcst_reads_python314_exception_syntax_without_running_target(tmp_path):
    root = tmp_path / "src"; root.mkdir()
    source = '''raise RuntimeError("Do not import me")
def value():
    try:
        raise ValueError()
    except ValueError, KeyError:
        return 12
'''
    (root / "main.py").write_text(source)
    graph = {"project": "syntax", "nodes": {"method:opaque": {"kind": "method", "name": "value", "file": "main.py", "line": 2}}, "edges": []}
    p = Project(root, graph)
    engine = Kernel(p); engine.scenario_id = "syntax"
    assert engine.execute_method("main.value") == 12
    assert (root / "main.py").read_text() == source
    assert any(d["code"] == "python-syntax-normalized" for d in p.diagnostics)


@pytest.mark.parametrize("language", ["python", "java"])
def test_z3_removes_contradictory_source_paths_in_both_languages(tmp_path, language):
    python = '''from fastapi import FastAPI
app=FastAPI()
def impossible():return -1
def possible():return 1
@app.get("/value")
def value(n:int):
    if n>10:
        if n<5:return impossible()
    return possible()
'''
    java = '''import org.springframework.web.bind.annotation.*;
@RestController class Handler {
int impossible(){return -1;} int possible(){return 1;}
@GetMapping("/value") int value(@RequestParam int n){if(n>10){if(n<5)return impossible();}return possible();}
}'''
    owner, filename, source = ("main", "main.py", python) if language == "python" else ("Handler", "Handler.java", java)
    p, store, ids = fixture(tmp_path, {filename: source})
    request = scenario({"path": "/value"})
    precise, detail = analyze(p, store, {}, request)
    uncorrelated, ablation = analyze(p, store, {}, request, smt=False)
    impossible = ids[owner + ".impossible"]
    assert not any(target == impossible for _, _, target in edge_set(precise))
    assert any(target == impossible for _, _, target in edge_set(uncorrelated))
    assert detail["solver"]["pruned_outcomes"] > 0
    assert detail["fully_explored_in_model"] and len(detail["paths"]) == 2
    assert len(ablation["paths"]) == 3


@pytest.mark.parametrize("language,condition", [("java", "n + 1 < 0"), ("java", "n % 3 == -1"), ("python", "n // -3 == 2 and n % -3 == -1")])
def test_z3_keeps_language_overflow_division_and_remainder(tmp_path, language, condition):
    value = 2147483647 if "+" in condition else -7
    if language == "java":
        filename, owner = "Handler.java", "Handler"
        source = f'''import org.springframework.web.bind.annotation.*;
@RestController class Handler {{
int impossible(){{return -1;}}
@GetMapping("/value") int value(@RequestParam int n){{if(n=={value}){{if({condition})return 1;return impossible();}}return 2;}}
}}'''
    else:
        filename, owner = "main.py", "main"
        source = f'''from fastapi import FastAPI
app=FastAPI()
def impossible():return -1
@app.get("/value")
def value(n:int):
    if n=={value}:
        if {condition}:return 1
        return impossible()
    return 2
'''
    p, store, ids = fixture(tmp_path, {filename: source})
    block, detail = analyze(p, store, {}, scenario({"path": "/value"}))
    assert not any(target == ids[owner + ".impossible"] for _, _, target in edge_set(block))
    assert detail["solver"]["pruned_outcomes"] > 0 and not detail["solver"]["failures"]


def test_z3_preserves_zero_division_exception_path(tmp_path):
    source = '''from fastapi import FastAPI
app=FastAPI()
def zero():return 0
def impossible():return -1
@app.get("/value")
def value(n:int):
    try:
        result=12//n
    except ZeroDivisionError:
        return zero()
    if n==0:return impossible()
    return result
'''
    p, store, ids = fixture(tmp_path, {"main.py": source})
    block, detail = analyze(p, store, {}, scenario({"path": "/value"}))
    targets = {target for _, _, target in edge_set(block)}
    assert ids["main.zero"] in targets and ids["main.impossible"] not in targets
    assert detail["fully_explored_in_model"]


def test_real_z3_unknown_preserves_both_outcomes():
    solver = PathSolver()
    solver.solver.set(rlimit=1)
    x = Symbol("input", "int", sort="int")
    condition = binary(">", binary("*", x, x, "python"), 42, "python")
    choices, _ = solver.outcomes(condition)
    assert choices == (False, True)
    assert solver.statistics["unknown"] > 0 and solver.failures


def test_unsupported_solver_encoding_preserves_both_outcomes():
    solver = PathSolver()
    x = Symbol("input", "int", sort="int")
    condition = Formula("==", (Formula("&", (x, 1), "int", "python"), 0), "bool", "python")
    choices, predicate = solver.outcomes(condition)
    assert choices == (False, True) and predicate is None
    assert solver.statistics["unknown"] == 1


@pytest.mark.parametrize("language", ["java", "python"])
def test_sqlglot_executes_same_relational_plan_for_jdbc_and_sqlalchemy(tmp_path, language):
    query = "SELECT p.name AS title, COUNT(*) AS total FROM products p JOIN sales s ON p.id=s.product_id WHERE s.quantity>=:minimum GROUP BY p.id,p.name ORDER BY p.name"
    if language == "java":
        query = query.replace(":minimum", "?")
        source = '''import org.springframework.web.bind.annotation.*;import org.springframework.jdbc.core.JdbcTemplate;
@RestController class Handler {@GetMapping("/report") Object report(){return new JdbcTemplate().queryForList(''' + json.dumps(query) + ''',2);}}'''
        filename, owner = "Handler.java", "Handler"
    else:
        source = '''from fastapi import FastAPI
from sqlalchemy import text,create_engine
from sqlalchemy.orm import Session
app=FastAPI()
@app.get("/report")
def report():
    session=Session(create_engine("sqlite://"))
    return session.execute(text(''' + repr(query) + '''),{"minimum":2}).mappings().all()
'''
        filename, owner = "main.py", "main"
    p, store, ids = fixture(tmp_path, {filename: source}, ["products", "sales"], {
        "products": [{"id": 1, "name": "Alpha"}, {"id": 2, "name": "Beta"}],
        "sales": [{"product_id": 1, "quantity": 3}, {"product_id": 1, "quantity": 4}, {"product_id": 2, "quantity": 1}]
    })
    block, detail = analyze(p, store, {}, scenario({"path": "/report"}))
    assert detail["paths"][0]["steps"][0]["response"]["body"] == [{"title": "Alpha", "total": 2}]
    assert edge_set(block, "data") == {(ids[owner + ".report"], "data", "storage:" + table) for table in ["products", "sales"]}


def test_sqlglot_native_repository_query_uses_annotation_not_method_name(tmp_path):
    source = '''import javax.persistence.*;import lombok.Data;import java.util.List;
import org.springframework.web.bind.annotation.*;import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.jpa.repository.JpaRepository;import org.springframework.data.jpa.repository.Query;import org.springframework.data.repository.query.Param;
@Entity @Table(name="inventory") @Data class Product {private static final long serialVersionUID=1L;@Id int id;String name;int quantity;}
interface Repo extends JpaRepository<Product,Integer>{
@Query(value="SELECT * FROM inventory WHERE quantity>=:minimum ORDER BY id",nativeQuery=true)
List<Product> lowStock(@Param("minimum") int amount);
}
@RestController class Handler {@Autowired Repo repo;@GetMapping("/report") Object report(){return repo.lowStock(5);}}
'''
    p, store, ids = fixture(tmp_path, {"Handler.java": source}, ["inventory"], {"inventory": [{"id": 1, "name": "A", "quantity": 2}, {"id": 2, "name": "B", "quantity": 8}]})
    block, detail = analyze(p, store, {}, scenario({"path": "/report"}))
    assert detail["paths"][0]["steps"][0]["response"]["body"] == [{"id": 2, "name": "B", "quantity": 8}]
    assert edge_set(block, "data") == {(ids["Handler.report"], "data", "storage:inventory")}


def test_java_static_fields_are_class_state_not_entity_columns(tmp_path):
    source = '''class Value {static final int FACTOR=3;int number=4;int read(){return number*FACTOR;}}'''
    p, store, ids = fixture(tmp_path, {"Value.java": source})
    engine = Kernel(p, State(store)); engine.scenario_id = "static"
    value = engine.create("Value")
    assert value.fields == {"number": 4}
    assert engine.execute_method(p.method_by_id[ids["Value.read"]], receiver=value) == 12


def test_sqlglot_null_semantics_and_count_on_empty_snapshot(tmp_path):
    from polygraph.ir import Span
    from polygraph.sql_queries import evaluate
    p, store, ids = fixture(tmp_path, {"main.py": "def report():return 1\n"}, ["inventory"], {"inventory": [{"id": 1, "note": "x"}, {"id": 2, "note": None}]})
    engine = Kernel(p, State(store)); engine.scenario_id = "sql"
    # Supply an active caller, as the source library models do.
    engine.frames.append((p.methods[p.method_by_id[ids["main.report"]]], {}))
    value = evaluate(engine, "SELECT id FROM inventory WHERE note=NULL OR (note IS NULL AND id=2)", {}, Span("main.py", 1))
    assert value == [{"id": 2}]
    engine.state.store.replace("storage:inventory", [])
    assert evaluate(engine, "SELECT COUNT(*) AS count FROM inventory", {}, Span("main.py", 1)) == [{"count": 0}]


def test_symbolic_dividend_with_literal_zero_still_throws():
    with pytest.raises(Raised, match="ArithmeticException"):
        binary("/", Symbol("x", "int", sort="bv32"), 0, "java")


def test_mysql_dump_comments_and_versioned_mutations_are_distinguished(tmp_path):
    p, _, _ = fixture(tmp_path, {}, tables=["stock"])
    sql = tmp_path / "context.sql"
    sql.write_text('''-- plain comment ;
/*!40101 SET NAMES utf8mb4 */;
CREATE TABLE stock(id INT,label TEXT);
LOCK TABLES stock WRITE;
/*!40000 ALTER TABLE stock DISABLE KEYS */;
INSERT INTO stock VALUES (1,'/*!9999 UPDATE stock SET id=9 */');
/*!40000 ALTER TABLE stock ENABLE KEYS */;
UNLOCK TABLES;
''')
    store, _, warnings = load_context(sql, p)
    assert warnings == []
    assert store.read("storage:stock") == [{"id": 1, "label": "/*!9999 UPDATE stock SET id=9 */"}]
    with sql.open("a") as stream:
        stream.write("/*!9999 UPDATE stock SET id=9 */;")
    store, _, warnings = load_context(sql, p)
    assert warnings and isinstance(store.read("storage:stock"), Unknown)


def test_sqlalchemy_result_contract_scalars_mapping_and_cardinality(tmp_path):
    source = '''from sqlalchemy import text,create_engine
from sqlalchemy.orm import Session
def values():
    return Session(create_engine("sqlite://")).execute(text("SELECT id FROM stock ORDER BY id")).scalars().all()
def mapping():
    return Session(create_engine("sqlite://")).execute(text("SELECT id FROM stock WHERE id=1")).mappings().one()
def scalar():
    return Session(create_engine("sqlite://")).execute(text("SELECT COUNT(*) FROM stock")).scalar_one()
def too_many():
    return Session(create_engine("sqlite://")).execute(text("SELECT id FROM stock")).one()
'''
    p, store, ids = fixture(tmp_path, {"main.py": source}, ["stock"], {"stock": [{"id": 1}, {"id": 2}]})
    engine = Kernel(p, State(store)); engine.scenario_id = "results"
    for method, expected in [("values", [1, 2]), ("mapping", {"id": 1}), ("scalar", 2)]:
        assert engine.execute_method(p.method_by_id[ids["main." + method]]) == expected
    with pytest.raises(Raised, match="MultipleResultsFound"):
        engine.execute_method(p.method_by_id[ids["main.too_many"]])


def test_session_add_without_flush_has_no_data_edge(tmp_path):
    source = '''from fastapi import FastAPI
from sqlmodel import SQLModel,Field,Session,create_engine
app=FastAPI()
class Entry(SQLModel,table=True):
    id:int=Field(primary_key=True)
    value:int
@app.post("/stage")
def stage():
    db=Session(create_engine("sqlite://"))
    db.add(Entry(id=1,value=4))
    db.rollback()
    return 1
'''
    p, store, ids = fixture(tmp_path, {"main.py": source}, ["entry"], {"entry": []})
    block, detail = analyze(p, store, {}, scenario({"method": "POST", "path": "/stage"}))
    assert not edge_set(block, "data")
    assert detail["paths"][0]["state"]["storage:entry"] == []


def test_flush_visibility_rollback_and_deferred_write_origin(tmp_path):
    source = '''from fastapi import FastAPI
from sqlmodel import SQLModel,Field,Session,create_engine
app=FastAPI()
class Entry(SQLModel,table=True):
    id:int=Field(primary_key=True)
    value:int
def stage(db):db.add(Entry(id=1,value=4))
@app.post("/stage")
def write():
    db=Session(create_engine("sqlite://"))
    stage(db)
    db.flush()
    result=db.get(Entry,1)
    db.rollback()
    return result.value
'''
    p, store, ids = fixture(tmp_path, {"main.py": source}, ["entry"], {"entry": []})
    block, detail = analyze(p, store, {}, scenario({"method": "POST", "path": "/stage"}))
    assert detail["paths"][0]["steps"][0]["response"]["body"] == 4
    assert detail["paths"][0]["state"]["storage:entry"] == []
    assert edge_set(block, "data") == {(ids["main.stage"], "data", "storage:entry"), (ids["main.write"], "data", "storage:entry")}


def test_unbound_session_fails_before_database_access(tmp_path):
    source = '''from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session
app=FastAPI()
@app.get("/read")
def read():return Session().execute(text("SELECT * FROM stock")).all()
'''
    p, store, ids = fixture(tmp_path, {"main.py": source}, ["stock"], {"stock": [{"id": 1}]})
    block, detail = analyze(p, store, {}, scenario({"path": "/read"}))
    assert edge_set(block, "data") == set()
    assert detail["paths"][0]["steps"][0]["response"]["status"] == 500
    assert any(note.get("exception") == "UnboundExecutionError" for note in detail["paths"][0]["diagnostics"])


def test_java_integer_symbol_uses_python_comparison_semantics_after_http(tmp_path):
    java = '''import org.springframework.web.bind.annotation.*;import org.springframework.web.client.RestTemplate;
@RestController class Gateway {@GetMapping("/call") Object call(@RequestParam int n){return new RestTemplate().getForObject("http://server/value/"+n,Object.class);}}
'''
    python = '''from fastapi import FastAPI
app=FastAPI()
def impossible():return -1
@app.get("/value/{n}")
def value(n:int):
    if n<2147483648:return 1
    return impossible()
'''
    p, store, ids = fixture(tmp_path, {"gateway/Gateway.java": java, "server/main.py": python}, modules={"gateway": "gateway", "server": "server"})
    block, detail = analyze(p, store, {}, scenario({"path": "/call", "module": "gateway"}))
    assert detail["paths"][0]["steps"][0]["response"]["body"] == 1
    assert not any(target == ids["main.impossible"] for _, _, target in edge_set(block))
    assert len(edge_set(block, "remote")) == 1 and detail["solver"]["pruned_outcomes"] > 0


@pytest.mark.parametrize("extra,condition", [
    ("", "n < 2147483648L"),
    ("long extra(){return 1L;}", "n + extra() > 2147483647L"),
    ("long extra=1L;", "n + this.extra > 2147483647L"),
    ("", 'n + Long.parseLong("1") > 2147483647L'),
])
def test_java_long_promotion_survives_ir_and_smt(tmp_path, extra, condition):
    source = '''import org.springframework.web.bind.annotation.*;
@RestController class Handler {''' + extra + ''' int impossible(){return -1;}
@GetMapping("/value") int value(@RequestParam int n){if(n==2147483647){if(''' + condition + ''')return 1;return impossible();}return 1;}}
'''
    p, store, ids = fixture(tmp_path, {"Handler.java": source})
    block, detail = analyze(p, store, {}, scenario({"path": "/value"}))
    assert not any(target == ids["Handler.impossible"] for _, _, target in edge_set(block))
    assert detail["solver"]["pruned_outcomes"] > 0 and not detail["solver"]["failures"]


@pytest.mark.parametrize("expression,expected", [("1 << 32L", 1), ("1 << -1", -2147483648), ("-1 >>> 1", 2147483647), ("1L << 64", 1)])
def test_java_shift_width_and_masked_distance(tmp_path, expression, expected):
    p, store, ids = fixture(tmp_path, {"Handler.java": "class Handler {long value(){return " + expression + ";}}"})
    engine = Kernel(p, State(store)); engine.scenario_id = "shifts"
    assert engine.execute_method(p.method_by_id[ids["Handler.value"]], receiver=engine.create("Handler")) == expected


def test_java_symbolic_shift_distance_does_not_promote_left_operand(tmp_path):
    source = '''import org.springframework.web.bind.annotation.*;
@RestController class Handler {int impossible(){return -1;}
@GetMapping("/value") int value(@RequestParam int n,@RequestParam long distance){if(n==1 && distance==32L){if((n<<distance)==1)return 1;return impossible();}return 1;}}
'''
    p, store, ids = fixture(tmp_path, {"Handler.java": source})
    block, detail = analyze(p, store, {}, scenario({"path": "/value"}))
    assert not any(target == ids["Handler.impossible"] for _, _, target in edge_set(block))
    assert detail["fully_explored_in_model"] and not detail["solver"]["failures"]


@pytest.mark.parametrize("initialization", ["module", "default"])
def test_python_initialization_calls_are_not_scenario_executions(tmp_path, initialization):
    source = '''from fastapi import FastAPI
app=FastAPI()
def prepare():return 7
'''
    source += '''VALUE=prepare()
@app.get("/read")
def read():return VALUE
''' if initialization == "module" else '''@app.get("/read")
def read(value:int=prepare()):return value
'''
    p, store, ids = fixture(tmp_path, {"main.py": source})
    block, detail = analyze(p, store, {}, scenario({"path": "/read"}))
    assert {target for _, _, target in edge_set(block, "executes")} == {ids["main.read"]}
    assert any(note["code"] == "definition-time-value" for path in detail["paths"] for note in path["diagnostics"])
    context = {"globals": {"main.VALUE" if initialization == "module" else "main.read:default:value": 7}}
    block, detail = analyze(p, store, context, scenario({"path": "/read"}))
    assert detail["paths"][0]["steps"][0]["response"]["body"] == 7
    assert not any(target == ids["main.prepare"] for _, _, target in edge_set(block))


@pytest.mark.parametrize("binding", ["data={'active':False};alias=data", "alias=[False]", "alias=global_data"])
def test_unknown_call_invalidates_mutable_container_aliases(tmp_path, binding):
    source = '''from fastapi import FastAPI
app=FastAPI()
global_data={'active':False}
def yes():return 1
def no():return 0
@app.get("/read")
def read():
    ''' + binding + '''
    opaque.touch(alias)
    if alias[0 if isinstance(alias,list) else "active"]:return yes()
    return no()
'''
    p, store, ids = fixture(tmp_path, {"main.py": source})
    block, detail = analyze(p, store, {}, scenario({"path": "/read"}))
    targets = {target for _, _, target in edge_set(block, "executes")}
    assert {ids["main.yes"], ids["main.no"]} <= targets
    assert not any(edge["target"] in {ids["main.yes"], ids["main.no"]} for edge in detail["must"])


def test_unknown_call_cannot_restore_unread_global_from_initial_literal(tmp_path):
    source = '''from fastapi import FastAPI
app=FastAPI()
flag=False
def yes():return 1
def no():return 0
@app.get("/read")
def read():
    opaque.touch()
    if flag:return yes()
    return no()
'''
    p, store, ids = fixture(tmp_path, {"main.py": source})
    block, detail = analyze(p, store, {}, scenario({"path": "/read"}))
    assert {ids["main.yes"], ids["main.no"]} <= {target for _, _, target in edge_set(block, "executes")}


def test_cyclic_response_is_diagnostic_not_analyzer_recursion_crash(tmp_path):
    source = '''from fastapi import FastAPI
app=FastAPI()
@app.get("/cycle")
def cycle():
    values=[]
    values.append(values)
    return values
@app.get("/later")
def later():return 1
'''
    p, store, ids = fixture(tmp_path, {"main.py": source})
    block, detail = analyze(p, store, {}, scenario({"path": "/cycle"}, {"path": "/later"}))
    assert detail["status"] == "partial"
    assert any(note["code"] == "serialization-unknown" for path in detail["paths"] for note in path["diagnostics"])
    assert not any(edge["target"] == ids["main.later"] for edge in detail["must"])
    json.dumps(detail)


def test_cyclic_outgoing_body_does_not_claim_remote_execution(tmp_path):
    client = '''from fastapi import FastAPI
import requests
app=FastAPI()
@app.get("/send")
def send():
    data=[]
    data.append(data)
    return requests.post("http://server/receive",json=data)
'''
    server = '''from fastapi import FastAPI
app=FastAPI()
@app.post("/receive")
def receive():return 1
'''
    p, store, ids = fixture(tmp_path, {"client/client.py": client, "server/main.py": server}, modules={"client": "client", "server": "server"})
    block, detail = analyze(p, store, {}, scenario({"path": "/send", "module": "client"}))
    assert not edge_set(block, "remote")
    assert not any(target == ids["main.receive"] for _, _, target in edge_set(block))
    assert detail["must"] == [] and detail["status"] == "partial"


def test_java_final_binding_survives_unknown_call(tmp_path):
    source = '''import org.springframework.web.bind.annotation.*;import org.slf4j.Logger;import org.slf4j.LoggerFactory;
@RestController class Handler {private static final int FACTOR=3;private static final Logger LOG=LoggerFactory.getLogger(Handler.class);
int impossible(){return -1;}@GetMapping("/value")int value(){opaque.touch();LOG.info("ready");if(FACTOR==3)return 1;return impossible();}}
'''
    p, store, ids = fixture(tmp_path, {"Handler.java": source})
    block, detail = analyze(p, store, {}, scenario({"path": "/value"}))
    assert not any(target == ids["Handler.impossible"] for _, _, target in edge_set(block))
    assert any(step["response"]["body"] == 1 for path in detail["paths"] for step in path["steps"])


def test_unmodeled_java_static_block_does_not_provide_zero_constant(tmp_path):
    source = '''class Value {static final int NUMBER;static{NUMBER=7;}int value(){return NUMBER;}}'''
    p, store, ids = fixture(tmp_path, {"Value.java": source})
    engine = Kernel(p, State(store));engine.scenario_id = "static-block"
    value = engine.execute_method(p.method_by_id[ids["Value.value"]], receiver=engine.create("Value"))
    assert isinstance(value, Unknown)
    assert engine.partial


def test_fastapi_overlapping_routers_are_not_ordered_by_file_index(tmp_path):
    source = '''from fastapi import FastAPI,APIRouter
app=FastAPI()
first=APIRouter()
second=APIRouter()
@first.get("/value")
def one():return 1
@second.get("/value")
def two():return 2
app.include_router(second)
app.include_router(first)
'''
    p, store, ids = fixture(tmp_path, {"main.py": source})
    block, detail = analyze(p, store, {}, scenario({"path": "/value"}))
    assert detail["status"] == "partial" and detail["must"] == []
    assert {ids["main.one"], ids["main.two"]} <= {target for _, _, target in edge_set(block, "executes")}
    assert any(note["code"] == "registration-order-unknown" for path in detail["paths"] for note in path["diagnostics"])


def test_fastapi_same_router_same_file_preserves_declaration_order(tmp_path):
    source = '''from fastapi import FastAPI
app=FastAPI()
@app.get("/items/{name}")
def generic(name:str):return 1
@app.get("/items/special")
def special():return 2
'''
    p, store, ids = fixture(tmp_path, {"main.py": source})
    block, detail = analyze(p, store, {}, scenario({"path": "/items/special"}))
    assert {target for _, _, target in edge_set(block, "executes")} == {ids["main.generic"]}
    assert detail["paths"][0]["steps"][0]["response"]["body"] == 1
