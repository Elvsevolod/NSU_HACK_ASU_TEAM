"""Native status values and source exception messages retain integral origins."""
import pytest
from builders import build
from analyzer.engine import Engine
from analyzer.state import ScenarioState,U
from analyzer.http_integral_text import integral_text
from analyzer.symbolic_text import concat_text


def run(root,source,parameters=None,state_factory=None):
    p,db,ids=build(root,{'Api.java':source})
    state=ScenarioState(db)
    if state_factory:parameters=state_factory(state)
    e=Engine(p,state);return e.run(ids['Api.entry'],parameters or {}),e,ids


@pytest.mark.parametrize('name,expected',[('OK',200),('CREATED',201),('BAD_REQUEST',400),('NOT_FOUND',404),('INTERNAL_SERVER_ERROR',500)])
@pytest.mark.parametrize('qualified',[False,True])
def test_native_status_value_is_an_integer(tmp_path,name,expected,qualified):
    owner='org.springframework.http.HttpStatus' if qualified else 'HttpStatus'
    value,e,_=run(tmp_path,'import org.springframework.http.HttpStatus;class Api{int entry(){return '+owner+'.'+name+'.value();}}')
    assert type(value) is int and value==expected and not e.approximate


def test_native_status_alias_preserves_its_value(tmp_path):
    value,e,_=run(tmp_path,'''import org.springframework.http.HttpStatus;
      class Api{int entry(){HttpStatus status=HttpStatus.NOT_FOUND;return status.value();}}''')
    assert value==404 and not e.approximate


def test_source_http_status_namesake_uses_its_source_method(tmp_path):
    value,e,ids=run(tmp_path,'''enum HttpStatus{NOT_FOUND;int value(){return 73;}}
      class Api{int entry(){return HttpStatus.NOT_FOUND.value();}}''')
    assert value==73 and not e.approximate
    assert any(kind=='executes' and target==ids['HttpStatus.value'] for _,kind,target in e.edges)


def test_an_ordinary_string_does_not_become_a_status_object(tmp_path):
    value,e,_=run(tmp_path,'''class Code{int value(){return 73;}}
      class Api{int entry(){Code HttpStatus=new Code();return HttpStatus.value();}}''')
    assert value==73 and not e.approximate


def test_status_identity_does_not_equal_its_ordinary_string_spelling(tmp_path):
    value,e,_=run(tmp_path,'''import org.springframework.http.HttpStatus;
      class Api{boolean entry(){return HttpStatus.NOT_FOUND.equals("NOT_FOUND");}}''')
    assert value is False and not e.approximate


@pytest.mark.parametrize('typ',['byte','short','int','long','Byte','Short','Integer','Long'])
@pytest.mark.parametrize('expression',[ '"item="+id', 'id+"/tail"', '"item="+id+"/tail"'])
def test_typed_symbolic_integral_string_concatenation_retains_decimal_identity(tmp_path,typ,expression):
    original=[]
    def parameters(state):
        original.append(state.generated_value(typ,'independent native identity'));return {'id':original[0]}
    value,e,_=run(tmp_path,'class Api{String entry('+typ+' id){return '+expression+';}}',state_factory=parameters)
    text=integral_text(original[0])
    expected=concat_text('item=',text) if expression.startswith('"item=') else text
    if expression.endswith('"/tail"'):expected=concat_text(expected,'/tail')
    assert value==expected and value is not U and not e.approximate


def test_source_exception_get_message_preserves_the_original_string_expression(tmp_path):
    original=[]
    def parameters(state):
        original.append(state.generated_value('Long','independent identity'));return {'id':original[0]}
    value,e,_=run(tmp_path,'''class Missing extends RuntimeException{Missing(String message){super(message);}}
      class Api{String entry(Long id){try{throw new Missing("Missing item "+id);}
        catch(Missing failure){return failure.getMessage();}}}''',state_factory=parameters)
    assert value==concat_text('Missing item ',integral_text(original[0])) and value is not U and not e.approximate


def test_numeric_addition_is_not_converted_to_string_text(tmp_path):
    value,e,_=run(tmp_path,'class Api{long entry(long id){return id+1L;}}',
                  state_factory=lambda state:{'id':state.generated_value('long','arithmetic input')})
    assert value is U or not isinstance(value,dict) or value.get('__type__') not in ('String','java.lang.String')


def test_nullable_boxed_identity_does_not_prove_a_nonnull_decimal(tmp_path):
    value,e,_=run(tmp_path,'class Api{String entry(Long id){return "item="+id;}}',
                  {'id':{'__symbol__':'nullable','__type__':'Long'}})
    assert value is U
