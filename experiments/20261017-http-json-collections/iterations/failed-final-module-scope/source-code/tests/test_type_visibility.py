import json
from analyzer.engine import Engine
from analyzer.project import Project
from analyzer.state import ScenarioState
from builders import build


def qualify(project,root,packages,remove_target=None):
    skeleton=project.skeleton
    for node in skeleton['nodes'].values():
        if node['kind']=='type':node['fqn']=packages[node['file']]+'.'+node['fqn']
    if remove_target:
        skeleton['edges']=[edge for edge in skeleton['edges'] if edge['target']!=remove_target]
    (root/'skeleton.json').write_text(json.dumps(skeleton))
    return Project(root/'skeleton.json',root)


def test_an_invisible_namesake_does_not_shadow_java_lang(tmp_path):
    project,db,ids=build(tmp_path,{
      'Integer.java':'package unrelated;public class Integer {public static int parseInt(String value){return 7;}}',
      'Api.java':'''package app;class Api {String entry(){try{Integer.parseInt("bad");return after();}
        catch(NumberFormatException failure){return "rejected";}}String after(){return "wrong";}}''',
    })
    # The simple fixture index has no compiler: correct its unrelated same-name
    # candidate before analysis, as a valid supplied skeleton would do.
    project=qualify(project,tmp_path,{'Integer.java':'unrelated','Api.java':'app'},ids['Integer.parseInt'])
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})=='rejected'
    executed={target for _,kind,target in engine.edges if kind=='executes'}
    assert ids['Integer.parseInt'] not in executed and ids['Api.after'] not in executed


def test_a_wildcard_jdk_import_is_not_replaced_by_an_invisible_project_type(tmp_path):
    project,db,ids=build(tmp_path,{
      'HashMap.java':'package unrelated;public class HashMap {}',
      'Api.java':'''package app;import java.util.*;class Api {String entry(){HashMap data=new HashMap();
        data.put("mode","known");return (String)data.get("mode");}}''',
    })
    project=qualify(project,tmp_path,{'HashMap.java':'unrelated','Api.java':'app'})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})=='known'
