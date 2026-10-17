import pytest
from tree_sitter import Language, Parser
import tree_sitter_javascript

from analyzer.response_arrays import summarize_array_copy


PARSER = Parser(Language(tree_sitter_javascript.language()))

SETUP = 'var vm=this;\n      vm.rows=[];'
HEADER = 'for(var i=0;i<result.data.length;i++)'
STATEMENT = 'vm.rows[i]=result.data[i];'


def callback(source):
    expression = PARSER.parse(('(' + source + ');').encode()).root_node.named_children[0]
    while expression.type in ('expression_statement', 'parenthesized_expression'):
        expression = expression.named_children[0]
    return expression


def line_of(source, needle):
    return next(index + 1 for index, line in enumerate(source.split('\n')) if needle in line)


def summarize(source, initial=None):
    scope = callback(source)
    stack = list(scope.named_children)
    while stack:
        node = stack.pop()
        if node.type == 'for_statement':
            return summarize_array_copy(node, scope, initial)
        stack.extend(node.named_children)
    raise AssertionError('for_statement not found')


def wrapped(setup=SETUP, header=HEADER, statement=STATEMENT):
    return 'function(){\n      %s\n      %s{\n        %s\n      }\n    }' % (setup, header, statement)


@pytest.mark.parametrize('keyword', ['var', 'let'])
def test_inline_length_bound_with_source_verified_alias(keyword):
    header = 'for(%s i=0;i<result.data.length;i++)' % keyword
    source = wrapped(header=header)
    assert summarize(source) == {
        'key': 'rows',
        'expr': 'result.data',
        'target': 'vm.rows',
        'line': line_of(source, header),
    }


def test_alias_bound_alias_source_and_different_names():
    source = '''function(payload){
      var state=this;
      state.rows=[];
      var total=payload.data.length;
      var items=payload.data;
      for(var n=0;n<total;n++){
        state.rows[n]=items[n];
      }
    }'''
    assert summarize(source) == {
        'key': 'rows',
        'expr': 'payload.data',
        'target': 'state.rows',
        'line': line_of(source, 'for(var n=0'),
    }


def test_prefix_increment_with_this_receiver():
    source = '''function(){
      this.rows=[];
      for(var i=0;i<result.data.length;++i){
        this.rows[i]=result.data[i];
      }
    }'''
    assert summarize(source) == {
        'key': 'rows',
        'expr': 'result.data',
        'target': 'this.rows',
        'line': line_of(source, 'for(var i=0'),
    }


def test_initial_receiver_alias_seed():
    source = '''function(){
      vm.rows=[];
      for(var i=0;i<result.data.length;i++){
        vm.rows[i]=result.data[i];
      }
    }'''
    assert summarize(source, {'vm': 'this'}) == {
        'key': 'rows',
        'expr': 'result.data',
        'target': 'vm.rows',
        'line': line_of(source, 'for(var i=0'),
    }


def test_static_string_key_source_read():
    source = '''function(){
      var vm=this;
      vm.rows=[];
      for(var i=0;i<store["rows"].length;i++){
        vm.rows[i]=store["rows"][i];
      }
    }'''
    assert summarize(source) == {
        'key': 'rows',
        'expr': 'store["rows"]',
        'target': 'vm.rows',
        'line': line_of(source, 'for(var i=0'),
    }


def test_comment_in_loop_body_is_ignored():
    source = '''function(){
      var vm=this;
      vm.rows=[];
      for(var i=0;i<result.data.length;i++){
        /* copy */ vm.rows[i]=result.data[i];
      }
    }'''
    assert summarize(source) == {
        'key': 'rows',
        'expr': 'result.data',
        'target': 'vm.rows',
        'line': line_of(source, 'for(var i=0'),
    }


@pytest.mark.parametrize('header', [
    'for(var i=0;i<result.data.length;i--)',
    'for(var i=0;i<result.data.length;i+=1)',
    'for(var i=1;i<result.data.length;i++)',
    'for(var i=0;i<=result.data.length;i++)',
    'for(var i=0;i<result.data.length-1;i++)',
    'for(var i=0,l=result.data.length;i<l;i++)',
    'for(var i=0;i<result.data.length;)',
])
def test_rejects_non_canonical_headers(header):
    assert summarize(wrapped(header=header)) is None


@pytest.mark.parametrize('source', [
    wrapped(statement='vm.rows[0]=result.data[i];'),
    wrapped(statement='vm.rows[i]=result.data[j];'),
    wrapped(statement='vm.rows[i]=result.data[i].value;'),
    wrapped(setup='var vm=this;\n      vm.rows=[];\n      var total=other.data.length;',
            header='for(var i=0;i<total;i++)'),
])
def test_rejects_mismatched_index_or_source(source):
    assert summarize(source) is None


@pytest.mark.parametrize('statement', [
    'vm.rows[i]=result.data[i];total++;',
    'vm.rows[i]=fetch().data[i];',
    'for(var j=0;j<2;j++){vm.rows[j]=result.data[j];}',
    'if(ok){vm.rows[i]=result.data[i];}',
])
def test_rejects_extra_statements_nested_bodies_and_side_effects(statement):
    assert summarize(wrapped(statement=statement)) is None


@pytest.mark.parametrize('setup,statement', [
    ('var vm=this;', STATEMENT),
    (SETUP, 'vm.cells[i]=result.data[i];'),
])
def test_rejects_missing_target_initialization(setup, statement):
    assert summarize(wrapped(setup=setup, statement=statement)) is None


@pytest.mark.parametrize('setup', [
    'var vm=other;\n      vm.rows=[];',
    'vm.rows=[];',
])
def test_rejects_unrelated_receiver(setup):
    assert summarize(wrapped(setup=setup)) is None


def test_rejects_uncertain_target_writes():
    source = '''function(){
      var vm=this;
      vm.rows=[];
      vm.rows[0]=1;
      vm.rows=[];
      for(var i=0;i<result.data.length;i++){
        vm.rows[i]=result.data[i];
      }
    }'''
    assert summarize(source) is None
