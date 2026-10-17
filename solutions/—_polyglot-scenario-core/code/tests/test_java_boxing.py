"""Reference/class distinctions that affect branches and collection contents."""
import pytest

from polygraph.analysis import analyze
from polygraph.values import TypeRef,Predicate,binary
from support import edge_set,fixture,scenario
from test_java_streams import probe,response


def test_java_class_literals_do_not_change_python_query_predicates():
    assert binary('==',TypeRef('java.lang.Integer'),TypeRef('java.lang.Integer'),'java') is True
    assert isinstance(binary('==',TypeRef('Row.id'),TypeRef('Other.id'),'python'),Predicate)


@pytest.mark.parametrize('body',[
    'java.util.Set<Object> items=new java.util.HashSet<Object>();items.add(1);items.add(1L);return items.size();',
    'return Arrays.asList(1,1L).stream().collect(Collectors.toSet()).size();',
])
def test_numeric_values_of_distinct_wrapper_classes_do_not_merge(tmp_path,body):
    _,detail,_=probe(tmp_path,body)
    assert response(detail)==2


def test_boxed_map_keys_preserve_numeric_runtime_class(tmp_path):
    _,detail,_=probe(tmp_path,'java.util.Map<Object,String> values=new java.util.HashMap<Object,String>();values.put(1,"integer");values.put(1L,"long");return Arrays.asList(values.size(),values.get(1),values.get(1L));')
    assert response(detail)==[2,'integer','long']


@pytest.mark.parametrize('body,expected',[
    ('Integer left=new Integer(1);Integer right=new Integer(1);return Arrays.asList(left==right,left.equals(right));',[False,True]),
    ('Integer left=127;Integer right=127;return left==right;',True),
    ('Integer left=1000;Integer alias=left;return left==alias;',True),
    ('Integer left=1;Long right=1L;return left.equals(right);',False),
    ('Integer left=1;return left==1;',True),
    ('Long value=2147483647L;return value+1;',2147483648),
    ('Long value=1L;return value<<32L;',4294967296),
    ('int value=2;return Arrays.asList(value>1,value==2,!(value<0),value>0&&value<3);',[True,True,True,True]),
    ('Boolean flag=true;return flag;',True),
    ('return Boolean.valueOf((String)null);',False),
    ('return new Boolean((String)null);',False),
])
def test_boxing_unboxing_and_result_types(tmp_path,body,expected):
    _,detail,_=probe(tmp_path,body)
    assert response(detail)==expected


def test_extended_cache_identity_remains_undecided(tmp_path):
    _,detail,_=probe(tmp_path,'Integer left=1000;Integer right=1000;if(left==right)return true;return false;')
    assert {step['response']['body'] for path in detail['paths'] for step in path['steps']}=={False,True}


def test_unboxing_failure_happens_before_source_callee_entry(tmp_path):
    block,detail,ids=probe(tmp_path,'Integer value=null;try{return take(value);}catch(NullPointerException e){return "unbox";}',
        '@org.springframework.transaction.annotation.Transactional int take(int value){return value;}')
    assert response(detail)=='unbox'
    assert ids['Endpoint.take'] not in {edge[2] for edge in edge_set(block,'executes')}
    assert not any(event['kind']=='rollback' for path in detail['paths'] for event in path['events'])


@pytest.mark.parametrize('expression',[
    'Integer.parseInt("2147483648")','Integer.parseInt(" 1")','Integer.parseInt("1_0")',
    'Long.parseLong("9223372036854775808")',
])
def test_parse_failures_are_not_narrowed_or_accepted_by_python(tmp_path,expression):
    _,detail,_=probe(tmp_path,'try{return '+expression+';}catch(NumberFormatException e){return "invalid";}')
    assert response(detail)=='invalid'


@pytest.mark.parametrize('body,expected',[
    ('return Long.parseLong("9223372036854775807");',9223372036854775807),
    ('Integer value=1;return Arrays.asList(value instanceof Number,value instanceof Object,value.getClass()==Integer.class);',[True,True,True]),
    ('Integer value=1;return String.valueOf(value);','1'),
])
def test_scalar_library_boundaries_keep_wrapper_semantics(tmp_path,body,expected):
    _,detail,_=probe(tmp_path,body)
    assert response(detail)==expected


def test_source_type_named_number_is_not_java_lang_number(tmp_path):
    _,detail,_=probe(tmp_path,'Object value=Integer.valueOf(1);return Arrays.asList(value instanceof Number,value instanceof java.lang.Number);',classes='class Number {}')
    assert response(detail)==[False,True]


def test_source_type_named_integer_keeps_its_source_contract(tmp_path):
    _,detail,_=probe(tmp_path,'Integer value=new Integer(7);return read(value);',
        'int read(Integer value){return value.number();}',
        'class Integer {private int value;Integer(int value){this.value=value;}int number(){return value;}}')
    assert response(detail)==7


def test_polluted_generic_stream_fails_before_primitive_callback(tmp_path):
    block,detail,ids=probe(tmp_path,'List<Integer> typed=new ArrayList<Integer>();List raw=typed;raw.add(1L);try{return typed.stream().map(this::take).collect(Collectors.toList());}catch(ClassCastException e){return "cast";}',
        'int take(int value){return value;}')
    assert response(detail)=='cast'
    assert ids['Endpoint.take'] not in {edge[2] for edge in edge_set(block,'executes')}


def test_integer_stream_can_widen_unboxed_input_for_long_callback(tmp_path):
    _,detail,_=probe(tmp_path,'List<Integer> typed=new ArrayList<Integer>();typed.add(7);return typed.stream().map(this::take).collect(Collectors.toList());',
        'long take(long value){return value+2147483647L;}')
    assert response(detail)==[2147483654]


def test_polluted_generic_terminal_fails_before_source_consumer(tmp_path):
    block,detail,ids=probe(tmp_path,'List<Integer> typed=new ArrayList<Integer>();List raw=typed;raw.add(1L);try{typed.stream().forEach(this::take);return "wrong";}catch(ClassCastException e){return "cast";}',
        'void take(int value){seen++;}')
    assert response(detail)=='cast'
    assert ids['Endpoint.take'] not in {edge[2] for edge in edge_set(block,'executes')}


@pytest.mark.parametrize('target,number,expected',[
    ('Object','1',[True,True]),('Object','2147483648',[False,True]),('Integer','1',[True,True]),
])
def test_python_json_number_acquires_java_wrapper_class_at_http_boundary(tmp_path,target,number,expected):
    sources={'java/Endpoint.java':'''import org.springframework.web.bind.annotation.*;import org.springframework.web.client.RestTemplate;import java.util.Arrays;
@RestController class Endpoint {@GetMapping("/value") Object value(){Object result=new RestTemplate().getForObject("http://py/number",'''+target+'''.class);return Arrays.asList(result instanceof Integer,result instanceof Number);}}''',
        'py/main.py':'from fastapi import FastAPI\napp=FastAPI()\n@app.get("/number")\ndef number():\n return '+number+'\n'}
    project,store,_=fixture(tmp_path,sources,modules={'gateway':'java','py':'py'})
    _,detail=analyze(project,store,{},scenario({'path':'/value'}))
    assert response(detail)==expected


def test_java_json_integer_overflow_is_not_silently_truncated(tmp_path):
    sources={'java/Endpoint.java':'''import org.springframework.web.bind.annotation.*;import org.springframework.web.client.RestTemplate;
@RestController class Endpoint {@GetMapping("/value") Object value(){return new RestTemplate().getForObject("http://py/number",Integer.class);}}''',
        'py/main.py':'from fastapi import FastAPI\napp=FastAPI()\n@app.get("/number")\ndef number():\n return 4294967296\n'}
    project,store,_=fixture(tmp_path,sources,modules={'gateway':'java','py':'py'})
    _,detail=analyze(project,store,{},scenario({'path':'/value'}))
    assert all(path['coverage']=='cutoff' and not path['steps'] for path in detail['paths'])
    assert any('integer range/coercion' in note['message'] for path in detail['paths'] for note in path['diagnostics'])
