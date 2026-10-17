import json

from analyzer.engine import Engine
from analyzer.project import Project
from analyzer.request_semantics import enum_scalar_binding
from analyzer.state import Database, ScenarioState


def test_same_enum_name_in_two_packages_preserves_each_constant_and_values(tmp_path):
    sources={
      'alpha/Choice.java':'''package alpha;
        public enum Choice { READY(7); int code; Choice(int code){this.code=code;}
          public int getCode(){return code;} }''',
      'beta/Choice.java':'''package beta;
        public enum Choice { READY(73); int code; Choice(int code){this.code=code;}
          public int getCode(){return code;} }''',
      'app/Api.java':'''package app; import alpha.Choice;
        class Api {
          int alpha(){return Choice.READY.getCode();}
          int count(){return Choice.values().length;}
          boolean check(Input input){return input.getPriority()==Choice.READY.getCode();}
        } class Input {int priority;int getPriority(){return priority;}}''',
      'app/Other.java':'''package app; import beta.Choice;
        class Other {
          int beta(){return Choice.READY.getCode();}
        }'''}
    nodes={'module:m':{'kind':'module','name':'m','deployment_units':['m']}}
    for fqn,file in [('alpha.Choice','alpha/Choice.java'),('beta.Choice','beta/Choice.java'),('app.Api','app/Api.java'),('app.Input','app/Api.java'),('app.Other','app/Other.java')]:
        nodes['type:'+fqn]={'kind':'type','fqn':fqn,'file':file,'module':'m'}
    methods=[('alpha.Choice','getCode','alpha/Choice.java',3,[]),('beta.Choice','getCode','beta/Choice.java',3,[]),
      ('app.Api','alpha','app/Api.java',3,[]),('app.Api','count','app/Api.java',4,[]),
      ('app.Api','check','app/Api.java',5,['Input']),('app.Other','beta','app/Other.java',3,[])]
    for owner,name,file,line,params in methods:
        nodes['method:'+owner+'#'+name]={'kind':'method','owner':'type:'+owner,'name':name,'file':file,
          'module':'m','line':line,'params_as_written':params,'annotations':[]}
    for file,source in sources.items():
        path=tmp_path/file;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(source)
    (tmp_path/'skeleton.json').write_text(json.dumps({'nodes':nodes,'edges':[]}))
    (tmp_path/'initial.sql').write_text('')
    project=Project(tmp_path/'skeleton.json',tmp_path)
    state=ScenarioState(Database(tmp_path/'initial.sql'))
    assert project.enum_reference('Choice.READY','method:app.Api#alpha')=='alpha.Choice.READY'
    assert project.enum_reference('Choice.READY','method:app.Other#beta')=='beta.Choice.READY'
    assert Engine(project,state).run('method:app.Api#alpha',{})==7
    assert Engine(project,state).run('method:app.Other#beta',{})==73
    assert Engine(project,state).run('method:app.Api#count',{})==1
    assert enum_scalar_binding(project,'method:app.Api#check','priority','Select ready priority')[0]==7
