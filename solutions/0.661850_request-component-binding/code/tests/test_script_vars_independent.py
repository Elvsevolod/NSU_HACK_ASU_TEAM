import pytest
from tree_sitter import Language, Parser
import tree_sitter_javascript
from analyzer.project import text, walk
from analyzer.script_vars import ScriptVars


PARSER=Parser(Language(tree_sitter_javascript.language()))


def scope(source):
    root=PARSER.parse(source.encode()).root_node
    return ScriptVars(root),root


def reads(source):
    model,root=scope(source)
    calls=[n for n in walk(root) if n.type=='call_expression' and text(n.child_by_field_name('function'))=='use']
    return model,[model.resolve(n,'cache') for n in calls],calls


@pytest.mark.parametrize('source,expected',[
    ('var cache=null;function load(){use(cache);}', ['cache']),
    ('function load(){use(cache);}var cache=null;', ['cache']),
    ('var cache=null;function load(cache){use(cache);}', [None]),
    ('var cache=null;function load(){use(cache);var cache;}', [None]),
    ('var cache=null;function load(){{use(cache);let cache;}use(cache);}', [None,'cache']),
    ('var cache=null;function load(){try{}catch(cache){use(cache);}use(cache);}', [None,'cache']),
    ('var cache=null;function load(){for(let cache=0;cache<2;cache++){use(cache);}use(cache);}', [None,'cache']),
    ('var cache=null;function load(){for(let cache of rows){use(cache);}use(cache);}', [None,'cache']),
    ('var cache=null;function load(){for(var cache of rows){use(cache);}use(cache);}', [None,None]),
    ('var cache=null;var run=function cache(){use(cache);};', [None]),
    ('var cache=null;function load(){function unrelated(){var cache;use(cache);}use(cache);}', [None,'cache']),
    ('var cache=null;var load=(cache)=>use(cache);', [None]),
    ('var cache=null;function load(){switch(mode){case 0:use(cache);break;case 1:let cache=[];}}', [None]),
    ('var cache=null;function load(){switch(mode){case 0:{let cache=[];use(cache);}break;case 1:use(cache);}}', [None,'cache']),
])
def test_lexical_read_resolution(source,expected):
    _,actual,_=reads(source)
    assert actual==expected


def test_completed_block_shadow_is_exposed_for_conservative_ssa_injection():
    model,values,calls=reads('var cache=null;function load(){{let cache;}use(cache);}')
    assert values==['cache']
    assert 'cache' in model.function_shadow_names(calls[0])


@pytest.mark.parametrize('source',[
    'var cache=null;var cache=[];',
    'var cache=null;function cache(){}',
    'var cache=null;let cache=[];',
])
def test_program_collisions_are_diagnosed(source):
    model,_=scope(source)
    assert 'cache' in model.program_names
    assert 'cache' not in model.bindings
    assert model.diagnostics


@pytest.mark.parametrize('source',[
    'var cache=null;function f({value}){}',
    'var cache=null;function f(value=cache){}',
    'var cache=null;class Other{}',
    'var cache=null;eval("cache=[]");',
    'var cache=null;with(object){cache=[];}',
    'var cache=null;export {cache};',
    'var cache=null;function bad( {',
])
def test_unsupported_scope_is_fail_closed(source):
    model,_=scope(source)
    assert not model.bindings and model.diagnostics


def test_assignment_operator_is_anonymous_for_plain_assignment():
    model,root=scope('var cache=null;cache=reply;cache+=reply;function local(cache){cache=reply;}')
    writes=[n for n in walk(root) if n.type in ('assignment_expression','augmented_assignment_expression')]
    assert writes[0].child_by_field_name('operator') is None
    assert [model.write(node) for node in writes]==['cache',None,None]


@pytest.mark.parametrize('source,safe',[
    ('var cache=null;',True),
    ('function load(){}var cache=[{id:"literal"}];',True),
    ('call();var cache=[];',False),
    ('var previous=call(),cache=[];',False),
    ('var previous;var cache=[];',True),
    ('var cache=[1,2,];',True),
    ('var cache=[,1];',False),
    ('var cache=[1,,2];',False),
    ('var cache=[1/* comment */,2];',False),
    ('var cache={["id"]:"computed"};',False),
    ('var cache={id:call()};',False),
    (r"var cache='escaped\n';",False),
    ('var cache={__proto__:{items:[]}};',False),
    ('var cache={"__proto__":{items:[]}};',False),
])
def test_literal_initialization_has_a_safe_prelude(source,safe):
    model,_=scope(source)
    assert model.bindings['cache']['initializer_safe'] is safe


def test_scope_anchor_from_another_tree_cannot_lend_a_program_binding():
    model,_=scope('var cache=null;')
    _,other=scope('function unrelated(){use(cache);}')
    assert model.resolve(other,'cache') is None
    assert model.resolve(None,'cache') is None


def test_ordinary_function_has_implicit_arguments_binding_but_top_arrow_does_not():
    model,root=scope('var arguments=null;function load(){use(arguments);}var arrow=()=>use(arguments);')
    calls=[n for n in walk(root) if n.type=='call_expression' and text(n.child_by_field_name('function'))=='use']
    assert [model.resolve(node,'arguments') for node in calls]==[None,'arguments']


def test_block_function_collision_does_not_resolve_a_program_variable():
    model,actual,_=reads('var cache=null;{function cache(){}use(cache);}')
    assert actual==[None]
    assert model.diagnostics
