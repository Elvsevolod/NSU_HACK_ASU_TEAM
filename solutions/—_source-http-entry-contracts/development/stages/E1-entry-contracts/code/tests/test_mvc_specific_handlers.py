import pytest
from analyzer.engine import Engine
from analyzer.paths import run_paths
from analyzer.request import Request
from analyzer.state import ScenarioState,U
from builders import build


def test_most_specific_handler_receives_exception_and_actual_request(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''import jakarta.servlet.http.*;
      class Missing extends RuntimeException {} record Error(int status,String error_code,String path){}
      @RestController class Api {
        @GetMapping("/items/{id}")Object read(@PathVariable Long id){throw new Missing();}
        @ExceptionHandler(Exception.class) @ResponseStatus(code=HttpStatus.INTERNAL_SERVER_ERROR)
        Error general(Exception ex,HttpServletRequest req){return new Error(500,"WRONG",req.getRequestURI());}
        @ExceptionHandler(Missing.class) @ResponseStatus(code=HttpStatus.NOT_FOUND)
        Error absent(Missing ex,HttpServletRequest req){return new Error(404,"ABSENT",req.getRequestURI());}}
    '''})
    e=Engine(p,ScenarioState(db));result=e.run(ids['Api.read'],Request.http('service','GET','/items/7?extra=x',headers={}))
    assert result=={'status':404,'error_code':'ABSENT','path':'/items/7'},(result,e.warnings)
    assert e.http_responses[-1]['status']==404
    assert ('','executes',ids['Api.absent']) in e.edges
    assert ('','executes',ids['Api.general']) not in e.edges


def test_multiple_unordered_advice_is_not_resolved_by_file_order(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{@GetMapping("/fail")String fail(){throw new IllegalArgumentException();}}
      @ControllerAdvice class First{@ExceptionHandler(Exception.class)String one(Exception ex){return "first";}}
      @ControllerAdvice class Second{@ExceptionHandler(IllegalArgumentException.class)String two(IllegalArgumentException ex){return "second";}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.fail'],Request.http('service','GET','/fail',headers={})) is U
    assert any('advice registration/order' in a for a in e.execution_assumptions)
    assert not any(target in (ids['First.one'],ids['Second.two']) for _,rel,target in e.edges if rel=='executes')


def test_handler_throw_is_not_a_success_response(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class Api{@GetMapping("/fail")String fail(){throw new IllegalArgumentException();}
       @ExceptionHandler(IllegalArgumentException.class)String recover(){throw new IllegalStateException();}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.fail'],Request.http('service','GET','/fail',headers={})) is U
    assert e.outcome=='uncaught application exception'


def test_source_namesake_exception_parent_does_not_use_native_super_contract(tmp_path):
    p,db,ids=build(tmp_path,{'Api.java':'''class RuntimeException {RuntimeException(String value){}}
      class Failure extends RuntimeException {Failure(){super("x");}}
      class Api {Object entry(){return new Failure();}}'''})
    e=Engine(p,ScenarioState(db));assert e.run(ids['Api.entry'],{}) is U
    assert e.outcome=='unsupported_semantics boundary'
