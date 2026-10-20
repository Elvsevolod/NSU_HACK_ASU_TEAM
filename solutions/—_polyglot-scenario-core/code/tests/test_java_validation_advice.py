import pytest

from polygraph.analysis import analyze
from support import fixture,scenario,edge_set


def test_source_advice_controls_status_and_execution_without_a_fake_caller(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
import org.springframework.http.HttpStatus;
import org.springframework.util.Assert;
@RestController class Endpoint {@GetMapping("/value") void value(){Assert.notNull(null);}}
@ControllerAdvice class Errors {
 @ExceptionHandler(IllegalArgumentException.class) @ResponseStatus(HttpStatus.BAD_REQUEST)
 void invalid(IllegalArgumentException exception){}
}
'''
    p,store,ids=fixture(tmp_path,{'Endpoint.java':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','module':'app'}))
    assert detail['paths'][0]['steps'][0]['response']['status']==400
    assert edge_set(block)=={('scenario:arbitrary','executes',ids['Endpoint.value']),('scenario:arbitrary','executes',ids['Errors.invalid'])}


def test_narrow_advice_does_not_hide_a_known_405_or_get_called_for_it(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
import org.springframework.http.HttpStatus;
@RestController class Endpoint {@GetMapping("/value") int value(){return 7;}}
@ControllerAdvice class Errors {
 @ExceptionHandler(IllegalArgumentException.class) @ResponseStatus(HttpStatus.BAD_REQUEST)
 void invalid(IllegalArgumentException exception){}
}
'''
    p,store,_=fixture(tmp_path,{'Endpoint.java':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','module':'app','method':'POST'}))
    assert not edge_set(block) and detail['paths'][0]['steps'][0]['response']['status']==405


@pytest.mark.parametrize('body,status', [({'text':'ok'},200),({},400),({'text':None},400),({'text':'😀'},200),({'text':'😀a'},400)])
def test_native_validation_bounds_use_java_utf16_length_and_not_null(tmp_path,body,status):
    source='''import org.springframework.web.bind.annotation.*;
import javax.validation.Valid;
import javax.validation.constraints.NotNull;
import org.hibernate.validator.constraints.Length;
class Input {@NotNull @Length(max=2) private String text;}
@RestController class Endpoint {@PostMapping("/value") int value(@Valid @RequestBody Input body){return 7;}}
'''
    p,store,_=fixture(tmp_path,{'Endpoint.java':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':body}))
    assert detail['paths'][0]['steps'][0]['response']['status']==status
    assert bool(edge_set(block))==(status==200)


def test_cascaded_list_validates_nested_source_fields_before_handler(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
import java.util.List;
import javax.validation.Valid;
import javax.validation.constraints.NotNull;
class Child {@NotNull private String value;}
class Input {@Valid private List<Child> children;}
@RestController class Endpoint {@PostMapping("/value") int value(@Valid @RequestBody Input body){return 7;}}
'''
    p,store,_=fixture(tmp_path,{'Endpoint.java':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':{'children':[{}]}}))
    assert not edge_set(block) and detail['paths'][0]['steps'][0]['response']['status']==400


def test_constraints_are_not_invoked_when_handler_does_not_request_valid(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
import javax.validation.constraints.NotNull;
class Input {@NotNull private String text;}
@RestController class Endpoint {@PostMapping("/value") int value(@RequestBody Input body){return 7;}}
'''
    p,store,_=fixture(tmp_path,{'Endpoint.java':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':{}}))
    assert edge_set(block) and detail['paths'][0]['steps'][0]['response']['status']==200


def test_custom_validator_is_a_diagnostic_instead_of_silently_valid_input(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
import javax.validation.Valid;
import javax.validation.Constraint;
@Constraint(validatedBy={}) @interface Rule {}
class Input {@Rule private String text;}
@RestController class Endpoint {@PostMapping("/value") int value(@Valid @RequestBody Input body){return 7;}}
'''
    p,store,_=fixture(tmp_path,{'Endpoint.java':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':{'text':'unknown'}}))
    assert not edge_set(block) and detail['status']=='partial'
    assert any('Custom field Bean' in d['message'] for d in detail['paths'][0]['diagnostics'])


def test_fully_qualified_validation_annotations_do_not_need_imports(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
class Input {@javax.validation.constraints.NotNull private String text;}
@RestController class Endpoint {@PostMapping("/value") int value(@javax.validation.Valid @RequestBody Input body){return 7;}}
'''
    p,store,_=fixture(tmp_path,{'Endpoint.java':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':{}}))
    assert not edge_set(block) and detail['paths'][0]['steps'][0]['response']['status']==400


def test_local_handler_precedes_more_specific_global_advice(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
import org.springframework.http.HttpStatus;
import org.springframework.util.Assert;
@RestController class Endpoint {
 @GetMapping("/value") void value(){Assert.notNull(null);}
 @ExceptionHandler(RuntimeException.class) @ResponseStatus(HttpStatus.BAD_REQUEST)
 String local(RuntimeException exception){return "local";}
}
@RestControllerAdvice class Errors {
 @ExceptionHandler(IllegalArgumentException.class) @ResponseStatus(HttpStatus.FORBIDDEN)
 String global(IllegalArgumentException exception){return "global";}
}
'''
    p,store,ids=fixture(tmp_path,{'Endpoint.java':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','module':'app'}))
    response=detail['paths'][0]['steps'][0]['response']
    assert response['body']=='local' and response['status']==400
    assert ids['Errors.global'] not in {e[2] for e in edge_set(block,'executes')}


def test_source_exception_shadow_does_not_catch_native_same_short_name(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
import org.springframework.util.Assert;
class IllegalArgumentException extends Exception {}
@RestController class Endpoint {@GetMapping("/value") void value(){Assert.notNull(null);}}
@RestControllerAdvice class Errors {
 @ExceptionHandler(IllegalArgumentException.class)
 String incorrect(IllegalArgumentException exception){return "incorrect";}
}
'''
    p,store,ids=fixture(tmp_path,{'Endpoint.java':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','module':'app'}))
    assert ids['Errors.incorrect'] not in {e[2] for e in edge_set(block,'executes')}
    assert detail['paths'][0]['steps'][0]['response']['status']==500


def test_normal_response_status_annotation_uses_checked_http_constant(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
import org.springframework.http.HttpStatus;
@RestController class Endpoint {@PostMapping("/value") @ResponseStatus(HttpStatus.CREATED) int value(){return 7;}}
'''
    p,store,_=fixture(tmp_path,{'Endpoint.java':source})
    _,detail=analyze(p,store,{},scenario({'path':'/value','module':'app','method':'POST'}))
    assert detail['paths'][0]['steps'][0]['response']['status']==201


@pytest.mark.parametrize('declaration,parameter,reason',[
    ('class Input {java.util.List<@javax.validation.constraints.NotNull String> names;}','@javax.validation.Valid @RequestBody Input body','Type-use'),
    ('@org.hibernate.validator.constraints.ScriptAssert(lang="javascript",script="false") class Input {String name;}','@javax.validation.Valid @RequestBody Input body','Class-level'),
    ('class Input {String name;}','@javax.validation.constraints.NotNull @RequestBody Input body','Executable'),
])
def test_unmodeled_validation_hooks_do_not_confirm_handler_execution(tmp_path,declaration,parameter,reason):
    source='''import org.springframework.web.bind.annotation.*;
'''+declaration+'\n@RestController class Endpoint {@PostMapping("/value") int value('+parameter+'){return 7;}}'
    p,store,ids=fixture(tmp_path,{'Endpoint.java':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value','method':'POST','body':{'names':[None]}}))
    assert not edge_set(block)
    assert all(path['coverage']=='cutoff' for path in detail['paths'])
    assert any(reason in note['message'] for path in detail['paths'] for note in path['diagnostics'])
