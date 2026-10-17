"""Different deployments can legitimately use identical Python package names."""
import pytest

from polygraph.analysis import analyze
from support import edge_set, fixture, scenario


def method_id(project, module, name):
    matches = [key for key, node in project.nodes.items() if node.get("kind") == "method" and node.get("module") == module and node.get("name") == name]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.parametrize("package", ["", "app/"])
def test_same_python_module_and_handler_in_two_services(tmp_path, package):
    sources = {
        "client/" + package + "main.py": '''from fastapi import FastAPI
import requests
app=FastAPI()
@app.get("/call")
def value():return requests.get("http://server/value").json()
''',
        "server/" + package + "main.py": '''from fastapi import FastAPI
app=FastAPI()
@app.get("/value")
def value():return {"answer":42}
''',
    }
    if package:
        sources.update({"client/app/__init__.py": "", "server/app/__init__.py": ""})
    p, store, _ = fixture(tmp_path, sources, modules={"client": "client", "server": "server"})
    block, detail = analyze(p, store, {}, scenario({"path": "/call", "module": "client"}))
    client, server = method_id(p, "client", "value"), method_id(p, "server", "value")
    assert edge_set(block) == {("scenario:arbitrary", "executes", client), ("scenario:arbitrary", "executes", server), (client, "remote", server)}
    assert detail["paths"][0]["steps"][0]["response"]["body"] == {"answer": 42}
    assert len(p.methods) == 2


def test_relative_imports_classes_and_globals_are_service_local(tmp_path):
    sources = {}
    for service, initial in [("client", 0), ("server", 10)]:
        sources[service + "/app/__init__.py"] = ""
        sources[service + "/app/helpers.py"] = f'''counter={{"n":{initial}}}
class Counter:
    def __init__(self,n):self.n=n
    def read(self):return self.n
def current():return Counter(counter["n"]).read()
'''
        sources[service + "/app/main.py"] = '''from fastapi import FastAPI
from .helpers import counter,current
app=FastAPI()
@app.post("/inc")
def increment():
    counter["n"]=counter["n"]+1
    return current()
@app.get("/read")
def read():return current()
'''
    p, store, _ = fixture(tmp_path, sources, modules={"client": "client", "server": "server"})
    _, detail = analyze(p, store, {}, scenario({"method": "POST", "path": "/inc", "module": "client"}, {"path": "/read", "module": "server"}, {"method": "POST", "path": "/inc", "module": "client"}))
    assert [step["response"]["body"] for step in detail["paths"][0]["steps"]] == [1, 10, 2]
    _, fresh = analyze(p, store, {}, scenario({"path": "/read", "module": "client"}))
    assert fresh["paths"][0]["steps"][0]["response"]["body"] == 0
    assert len([info for info in p.types.values() if info.name == "Counter"]) == 2


def test_same_package_names_keep_all_four_relations_and_separate_tables(tmp_path):
    sources = {}
    for service in ["client", "server"]:
        sources[service + "/app/__init__.py"] = ""
        sources[service + "/app/helpers.py"] = f'''from sqlmodel import SQLModel,Field,Session,create_engine
class Item(SQLModel,table=True):
    __tablename__="{service}_inventory"
    id:int=Field(primary_key=True)
    value:int
def read():
    return Session(create_engine("postgresql://user:pass@db/{service}")).get(Item,1).value
'''
    sources["client/app/main.py"] = '''from fastapi import FastAPI
from .helpers import read
import requests
app=FastAPI()
@app.get("/value")
def value():return {"local":read(),"remote":requests.get("http://server/value").json()}
'''
    sources["server/app/main.py"] = '''from fastapi import FastAPI
from .helpers import read
app=FastAPI()
@app.get("/value")
def value():return read()
'''
    p, store, _ = fixture(tmp_path, sources, ["client_inventory", "server_inventory"], {"client_inventory": [{"id": 1, "value": 10}], "server_inventory": [{"id": 1, "value": 42}]}, modules={"client": "client", "server": "server"})
    block, detail = analyze(p, store, {}, scenario({"path": "/value", "module": "client"}))
    client, server = method_id(p, "client", "value"), method_id(p, "server", "value")
    client_read, server_read = method_id(p, "client", "read"), method_id(p, "server", "read")
    expected = {("scenario:arbitrary", "executes", key) for key in [client, server, client_read, server_read]}
    expected |= {(client, "calls", client_read), (server, "calls", server_read), (client, "remote", server),
                 (client_read, "data", "storage:client_inventory"), (server_read, "data", "storage:server_inventory")}
    assert edge_set(block) == expected
    assert detail["paths"][0]["steps"][0]["response"]["body"] == {"local": 10, "remote": 42}
    assert all(edge_set(block, kind) for kind in ["executes", "calls", "remote", "data"])
