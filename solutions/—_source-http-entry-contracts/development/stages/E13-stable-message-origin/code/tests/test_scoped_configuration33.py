import json
import pytest
from analyzer.project import Project
from analyzer.state import U
from builders import build


def fixture(root,entries,provided=None):
    p,db,ids=build(root,{'A.java':'@RestController @Profile("red") class A{@GetMapping("/items")String read(){return "a";}}',
                       'B.java':'@RestController @Profile("blue") class B{@GetMapping("/items")String read(){return "b";}}'})
    graph=p.skeleton
    for module in ('a','b'):graph['nodes']['module:'+module]={'kind':'module','name':module,'deployment_units':[module]}
    for node in graph['nodes'].values():
        if node.get('file') in ('A.java','B.java'):node['module']=node['file'][0].lower()
    for i,(module,key,value,file,doc) in enumerate(entries):
        graph['nodes']['config:'+str(i)]={'kind':'config_entry','module':module,'key':key,'value':value,'file':file,'doc':doc}
    if provided:graph['context']['configuration']=provided
    (root/'skeleton.json').write_text(json.dumps(graph))
    return Project(root/'skeleton.json',root),ids


def row(key,value,module='a',file='src/main/resources/application.yml',doc=0):return module,key,value,file,doc


@pytest.mark.parametrize('reverse',[False,True])
def test_active_profile_is_scoped_to_its_deployment(tmp_path,reverse):
    entries=[row('spring.profiles.active','red'),row('spring.profiles.active','blue',module='b')]
    p,ids=fixture(tmp_path,list(reversed(entries)) if reverse else entries)
    assert p.profile_status(p.methods[ids['A.read']]['owner']) is True
    assert p.profile_status(p.methods[ids['B.read']]['owner']) is True


def test_context_path_placeholder_comes_from_same_module(tmp_path):
    p,ids=fixture(tmp_path,[row('server.servlet.context-path','${root:/fallback}'),row('root','/tenant')])
    assert p.ix.handlers_for('GET','/tenant/items','a')=={ids['A.read']}
    assert not p.ix.handlers_for('GET','/fallback/items','a')


def test_profile_file_priority_is_independent_of_graph_insertion_order(tmp_path):
    p,ids=fixture(tmp_path,[row('spring.profiles.active','red'),
        row('server.servlet.context-path','/profile',file='src/main/resources/application-red.yml'),
        row('server.servlet.context-path','/base')])
    assert p.ix.handlers_for('GET','/profile/items','a')=={ids['A.read']}
    assert not p.ix.handlers_for('GET','/base/items','a')


@pytest.mark.parametrize('extra',[
    [row('spring.cloud.config.uri','http://configserver')],
    [row('spring.config.import','optional:configserver:http://configserver')],
    [row('root','${other}'),row('other','${root}'),row('server.servlet.context-path','${root}')],
])
def test_unresolved_configuration_does_not_prove_a_bare_or_local_http_route(tmp_path,extra):
    p,ids=fixture(tmp_path,[row('server.servlet.context-path','/local'),*extra])
    assert not any(mid==ids['A.read'] for mid,_,_ in p.ix.handlers)
    assert p.route_warnings


def test_disabled_config_server_keeps_source_local_values(tmp_path):
    p,ids=fixture(tmp_path,[row('server.servlet.context-path','/local'),row('spring.cloud.config.uri','http://configserver'),
                          row('spring.cloud.config.enabled','false')])
    assert p.ix.handlers_for('GET','/local/items','a')=={ids['A.read']}


def test_resolved_property_sources_use_first_source_and_expand_placeholders(tmp_path):
    p,ids=fixture(tmp_path,[row('server.servlet.context-path','/local'),row('spring.cloud.config.uri','http://configserver')],
        provided={'a':{'profiles':['red'],'propertySources':[
            {'source':{'server.servlet.context-path':'${root}','root':'/first'}},
            {'source':{'root':'/second'}}]}})
    assert p.ix.handlers_for('GET','/first/items','a')=={ids['A.read']}
    assert p.profile_status(p.methods[ids['A.read']]['owner']) is True


def test_datasource_placeholder_is_resolved_without_process_environment(tmp_path,monkeypatch):
    monkeypatch.setenv('database','wrong-environment')
    p,ids=fixture(tmp_path,[row('spring.datasource.url','jdbc:mysql://db/${database:parcels}')])
    assert p.schemas['a']=='parcels'


def test_unknown_remote_environment_keeps_profile_status_unknown(tmp_path):
    p,ids=fixture(tmp_path,[row('spring.profiles.active','red'),row('spring.cloud.config.uri','http://configserver')])
    assert p.profile_status(p.methods[ids['A.read']]['owner']) is U
