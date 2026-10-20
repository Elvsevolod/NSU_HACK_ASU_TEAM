"""HTTP contracts independent of any challenge project or scenario name."""
import json
import pytest
from urllib.parse import unquote
from analyzer.engine import Engine
from analyzer.project import Project
from analyzer.state import ScenarioState, U
from analyzer.symbolic_text import concat_text
from analyzer.paths import run_paths
from analyzer.java_collections import is_symbolic
from builders import build


def remote(tmp_path, declaration, body, url, extra='', client='', filters='', uri_values=''):
    project, db, ids = build(tmp_path, {
        'Api.java': 'import java.util.*; class Api {@GetMapping("/items/{key}") String get(' + declaration + '){' + body + '}}' + extra,
        'Caller.java': 'import org.springframework.web.client.RestTemplate; import java.util.*; class Caller {RestTemplate rest; String entry(){' + client +
            'try{return rest.getForObject(' + url + ',String.class' + (','+uri_values if uri_values else '') + ');} catch(HttpClientErrorException e){return rejected();}} String rejected(){return "bad-request";}}',
        'Gate.java': filters,
    })
    for unit in ('client', 'server'):
        project.skeleton['nodes']['module:'+unit] = {'kind':'module','name':unit,'deployment_units':[unit]}
    for node in project.skeleton['nodes'].values():
        if node.get('file'):
            node['module'] = 'client' if node['file']=='Caller.java' else 'server'
    (tmp_path/'skeleton.json').write_text(json.dumps(project.skeleton))
    project = Project(tmp_path/'skeleton.json', tmp_path)
    engine = Engine(project, ScenarioState(db))
    return engine, ids, engine.run(ids['Caller.entry'], {})


def test_query_occurrences_are_not_overwritten():
    address = Engine.request_address('https://catalog/items/k?tag=a&tag=b&empty=&bare#tag=c')
    assert address['query'] == {'tag':['a','b'],'empty':[''],'bare':['']}
    assert address['query_complete'] is True


def test_decoding_is_once_and_plus_is_only_query_space():
    address = Engine.request_address('/items/a+b%2520?x=a+b&x=a%2Bb&y=%2520')
    assert address['segments'] == ['items','a+b%20']
    assert address['query'] == {'x':['a b','a+b'],'y':['%20']}


def test_symbolic_uuid_keeps_known_query_and_fragment():
    atom = {'__symbol__':'fresh','__type__':'String','__uuid_text__':True,'__length__':36}
    address = Engine.request_address(concat_text(concat_text('/items/',atom),'?limit=7&tag=a&tag=b#ignored'))
    assert address['segments'] == ['items',atom]
    assert address['query'] == {'limit':['7'],'tag':['a','b']}
    assert address['query_complete'] is True


def test_raw_opaque_query_keeps_route_but_not_false_absence():
    atom = {'__symbol__':'unescaped','__type__':'String'}
    address = Engine.request_address(concat_text('/items/key?limit=7&text=',atom))
    assert address['segments'] == ['items','key']
    assert address['query']['limit'] == ['7']
    assert address['query_complete'] is False


@pytest.mark.parametrize('typ,query,expression,expected', [
    ('List<String>','tag=a&tag=b','tag.get(0)+"/"+tag.get(1)','a/b'),
    ('String[]','tag=a&tag=b','tag[0]+"/"+tag[1]','a/b'),
    ('String','tag=a&tag=b','tag','a,b'),
    ('List<String>','tag=a, b','tag.get(0)+"/"+tag.get(1)','a/b'),
    ('List<String>','tag=a,b&tag=c','tag.get(0)+"/"+tag.get(1)','a,b/c'),
    ('int','tag=7&tag=9','""+tag','7'),
    ('String','tag=','tag',''),
])
def test_multivalue_binding(tmp_path,typ,query,expression,expected):
    engine,ids,result=remote(tmp_path,'@RequestParam(name="tag") '+typ+' tag','return '+expression+';',json.dumps('http://server/items/k?'+query))
    assert result==expected
    assert (ids['Caller.entry'],'remote',ids['Api.get']) in engine.edges


@pytest.mark.parametrize('url,expected', [('http://server/items/k','9'),('http://server/items/k?limit=','9'),('http://server/items/k?limit=5','5')])
def test_default_missing_and_empty_with_alias(tmp_path,url,expected):
    _,_,result=remote(tmp_path,'@RequestParam(name="limit",defaultValue="9") int maximum','return ""+maximum;',json.dumps(url))
    assert result==expected


@pytest.mark.parametrize('typ,query,expected', [
    ('byte','127','127'),('byte','128','bad-request'),('short','-32768','-32768'),('short','-32769','bad-request'),
    ('int','2147483647','2147483647'),('int','2147483648','bad-request'),
    ('long','9223372036854775807','9223372036854775807'),('long','9223372036854775808','bad-request'),
    ('int','0x20','32'),('int','%23ff','255'),('int','%20%2B1%202%20','12'),('int','012','12'),
    ('int','1.5','bad-request'),('boolean','YES','true'),('boolean','off','false'),('boolean','maybe','bad-request')])
def test_native_scalar_conversion_and_bounds(tmp_path,typ,query,expected):
    engine,ids,result=remote(tmp_path,'@RequestParam '+typ+' n','return ""+n;',
        '"http://server/items/k?n={n}"',uri_values=json.dumps(unquote(query)))
    assert result==expected
    assert ((ids['Caller.entry'],'remote',ids['Api.get']) in engine.edges)==(expected!='bad-request')
    assert (('', 'executes',ids['Api.get']) in engine.edges)==(expected!='bad-request')


def test_optional_and_nullable_missing_values(tmp_path):
    _,_,result=remote(tmp_path,'@RequestParam Optional<Integer> limit, @RequestParam(required=false) String label',
        'if(limit.isPresent()){return "wrong";} if(label!=null){return "wrong";} return "absent";', '"http://server/items/k"')
    assert result=='absent'


def test_uuid_path_survives_with_query_and_uses_known_branch(tmp_path):
    _,_,result=remote(tmp_path,'@PathVariable String key,@RequestParam int limit',
        'if(key.length()==36 && limit==7){return "accepted";} return "wrong";',
        '"http://server/items/"+id+"?limit=7"',client='String id=UUID.randomUUID().toString();')
    assert result=='accepted'


GATE='''class Gate extends OncePerRequestFilter {
  void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain){before();chain.doFilter(req,res);after();}
  void before(){} void after(){}}
'''


@pytest.mark.parametrize('suffix',['','?n=invalid','?n=2147483648','?n='])
def test_binding_failure_runs_filters_but_does_not_enter_handler(tmp_path,suffix):
    engine,ids,result=remote(tmp_path,'@RequestParam int n','return "wrong";',json.dumps('http://server/items/k'+suffix),filters=GATE)
    assert result=='bad-request'
    assert {ids['Gate.before'],ids['Gate.after'],ids['Gate.doFilterInternal'],ids['Caller.rejected']} <= {t for _,r,t in engine.edges if r=='executes'}
    assert ('','executes',ids['Api.get']) not in engine.edges
    assert not any(r=='remote' for _,r,_ in engine.edges)


def test_filter_rejection_precedes_binding_failure(tmp_path):
    filters=GATE.replace('before();chain.doFilter(req,res);after();','res.setStatus(403);')
    engine,ids,result=remote(tmp_path,'@RequestParam int n','return "wrong";','"http://server/items/k"',filters=filters)
    assert result=='bad-request'
    assert not any('binding rejected' in w for w in engine.warnings)
    assert ('','executes',ids['Api.get']) not in engine.edges


def test_missing_required_header_is_rejected_after_filters(tmp_path):
    engine,ids,result=remote(tmp_path,'@RequestHeader("X-Key") String key','return key;','"http://server/items/k"',filters=GATE)
    assert result=='bad-request'
    assert ('','executes',ids['Gate.after']) in engine.edges
    assert ('','executes',ids['Api.get']) not in engine.edges


def test_custom_binder_cannot_prove_standard_conversion_failure(tmp_path):
    engine,ids,result=remote(tmp_path,'@RequestParam int n','return ""+n;', '"http://server/items/k?n=special"',
        extra='class Config {@InitBinder void configure(WebDataBinder b){}}')
    assert result is U or is_symbolic(result)
    assert ('','executes',ids['Api.get']) in engine.edges
    assert any('custom converter or binder' in w for w in engine.warnings)


def test_unknown_query_does_not_supply_default_or_prove_missing(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''class Api {
      @GetMapping("/items/{key}") void get(@PathVariable String key,@RequestParam(defaultValue="9") int n){}}'''})
    atom={'__symbol__':'raw','__type__':'String'}
    engine=Engine(project,ScenarioState(db))
    values=engine.request_arguments(ids['Api.get'],concat_text('/items/k?text=',atom),{},None,'probe')
    assert values==['k',U]


def test_rest_template_string_percent_literals_are_encoded_before_transport(tmp_path):
    _,_,result=remote(tmp_path,'@PathVariable String key,@RequestParam String q','return key+"/"+q;',
        '"http://server/items/a%20b?q=c%2Bd"')
    assert result=='a%20b/c%2Bd'


def test_template_query_value_does_not_create_extra_parameters(tmp_path):
    _,_,result=remote(tmp_path,'@RequestParam String q,@RequestParam(defaultValue="9") int n','return q+"/"+n;',
        '"http://server/items/k?q={q}"',uri_values='"x&n=99#end"')
    assert result=='x&n=99#end/9'


def test_unknown_template_query_preserves_other_known_components(tmp_path):
    engine,ids,result=remote(tmp_path,'@PathVariable String key,@RequestParam int n,@RequestParam String text',
        'if(n==7 && key.equals("k")){return "known";}return "wrong";',
        '"http://server/items/k?n=7&text={text}"',client='String text;',uri_values='text')
    assert result=='known'
    assert any('unknown parameter text' in warning for warning in engine.warnings)


def test_uri_atom_markers_cannot_be_forged_by_percent_decoding():
    atom={'__symbol__':'id','__type__':'String','__uuid_text__':True,'__length__':36}
    address=Engine.request_address(concat_text(concat_text('/items/',atom),'?q=%5F%5Furi_atom_0%5F%5F'))
    assert address['query']['q']==['__uri_atom_0__']


def test_opaque_raw_query_still_dispatches_the_known_path(tmp_path):
    engine,ids,result=remote(tmp_path,'@PathVariable String key,@RequestParam(defaultValue="9") int n',
        'if(key.equals("k")){return "known-path";}return "wrong";',
        '"http://server/items/k?text="+text',client='String text;')
    assert result=='known-path'
    assert (ids['Caller.entry'],'remote',ids['Api.get']) in engine.edges
    assert any('parameter presence or URL layout' in warning for warning in engine.warnings)


def test_unknown_custom_type_empty_text_is_not_a_proven_rejection(tmp_path):
    engine,ids,_=remote(tmp_path,'@RequestParam Domain n','return "entered";',
        '"http://server/items/k?n="',extra='class Domain {Domain(String text){}}')
    assert ('','executes',ids['Api.get']) in engine.edges
    assert any('unsupported declared parameter type' in warning for warning in engine.warnings)


@pytest.mark.parametrize('digits,expected',[('9'*5000,'bad-request'),('0'*5000+'7','7')])
def test_huge_numeric_text_has_java_width_not_python_digit_limit(tmp_path,digits,expected):
    _,_,result=remote(tmp_path,'@RequestParam long n','return ""+n;',json.dumps('http://server/items/k?n='+digits))
    assert result==expected


def test_optional_flag_with_whitespace_is_still_a_literal(tmp_path):
    _,_,result=remote(tmp_path,'@RequestParam(required = false) String text',
        'return text==null ? "absent" : "wrong";','"http://server/items/k"')
    assert result=='absent'


def test_unregistered_database_converter_does_not_erase_native_path(tmp_path):
    _,_,result=remote(tmp_path,'@PathVariable String key','return key;','"http://server/items/k"',
        extra='class RowConverter implements org.springframework.core.convert.converter.Converter<DbRow,Domain> {public Domain convert(DbRow r){return null;}} class DbRow {} class Domain {}')
    assert result=='k'


def test_symbolic_url_literals_use_the_same_client_encoding(tmp_path):
    _,_,result=remote(tmp_path,'@PathVariable String key,@RequestParam String text',
        'return text;', '"http://server/items/"+id+"?text=a%20b"',client='String id=UUID.randomUUID().toString();')
    assert result=='a%20b'


def test_unknown_numeric_addition_to_char_does_not_fabricate_text(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':"class Api {int add(int n){return 'a'+n;}}"})
    result=Engine(project,ScenarioState(db)).run(ids['Api.add'],{})
    assert result is U


def test_custom_uri_handler_never_claims_default_encoding(tmp_path):
    project,db,ids=build(tmp_path,{'Api.java':'''import org.springframework.web.client.RestTemplate;
      class Api {@GetMapping("/items/{key}") String get(@PathVariable String key){return key;}}
      class Caller {RestTemplate rest;void configure(){rest.setUriTemplateHandler(custom());}
      String entry(){return rest.getForObject("http://service/items/k",String.class);}}'''})
    engine=Engine(project,ScenarioState(db))
    assert engine.run(ids['Caller.entry'],{}) is U
    assert any('custom URI template handler' in warning for warning in engine.warnings)
