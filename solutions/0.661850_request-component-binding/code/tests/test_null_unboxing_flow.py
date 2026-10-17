import pytest
from analyzer.engine import Engine
from analyzer.state import ScenarioState
from builders import build


@pytest.mark.parametrize('body',[
 'Integer input=null;int result=input+side();',
 'Integer input=null;int result=input;',
 'Integer input=null;int result=(int)input;',
 'Integer input=null;int result=0;result=input;',
 'Integer input=null;input++;',
 'Integer input=null;input+=side();',
 'int result=primitive();',
 'Integer input=null;int result=true?input:1;',
 'Integer input=null;consume(input,side());',
 'int result=nullable();',
 'Integer input=null;int result=side()+input;',
 'Integer input=null;boolean result=input==1;',
 'Character input=null;int result=input+1;',
 'Boolean input=null;if(input){after();}',
 'Boolean input=null;boolean result=input&&sideBool();',
 'Boolean input=null;boolean result=!input;',
 'Boolean input=null;String result=input?"yes":"no";',
 'Boolean input=null;while(input){after();}',
])
def test_null_unboxing_stops_execution_before_the_next_statement(tmp_path,body):
    source='''class Api{String entry(){try{'''+body+'''return after();}catch(NullPointerException failure){return failed();}}
    Integer nullable(){return null;}int primitive(){Integer value=null;return value;}void consume(int value,int later){}int side(){return 1;}boolean sideBool(){return true;}String after(){return "wrong";}String failed(){return "caught";}}'''
    project,db,ids=build(tmp_path,{'Api.java':source});engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Api.entry'],{})=='caught'
    assert ('','executes',ids['Api.after']) not in engine.edges
    if 'input+side()' in body or 'consume(input' in body or 'input+=side()' in body:assert ('','executes',ids['Api.side']) not in engine.edges
    if 'sideBool' in body:assert ('','executes',ids['Api.sideBool']) not in engine.edges


@pytest.mark.parametrize('body,expected',[
 ('Integer input=null;return "prefix"+input;','prefixnull'),
 ('Integer input=null;String text=null;return text+input;','nullnull'),
 ('Boolean input=null;return false&&input;',False),
 ('Integer left=null;Integer right=null;return left==right;',True),
])
def test_concat_reference_equality_and_short_circuit_do_not_unbox(tmp_path,body,expected):
    project,db,ids=build(tmp_path,{'Api.java':'class Api{Object entry(){'+body+'}}'})
    assert Engine(project,ScenarioState(db)).run(ids['Api.entry'],{})==expected
