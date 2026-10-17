import pytest
from tree_sitter import Language, Parser
import tree_sitter_javascript

from analyzer.option_sources import option_sources


PARSER = Parser(Language(tree_sitter_javascript.language()))

ACCEPTED = '''function(reply){
  if(reply.status==1){
    var rows=reply.data;
    var control=document.getElementById("choice");
    for(var i=0,l=rows.length;i<l;i++){
      var opt=document.createElement("option");
      opt.value=rows[i]["code"];
      opt.innerText=rows[i]["name"];
      control.appendChild(opt);
    }
  }
}'''


def callback(source):
    expression = PARSER.parse(('(' + source + ');').encode()).root_node.named_children[0]
    while expression.type in ('expression_statement', 'parenthesized_expression'):
        expression = expression.named_children[0]
    return expression


def line_of(source, needle):
    return next(index + 1 for index, line in enumerate(source.split('\n')) if needle in line)


def loop_source(*statements, array='var rows=reply.data;', header='for(var i=0,l=rows.length;i<l;i++)'):
    return '''function(reply){
      %s
      var control=document.getElementById("choice");
      %s{
        var opt=document.createElement("option");
        %s
        control.appendChild(opt);
      }
    }''' % (array, header, '\n        '.join(statements))


def test_accepted_loop_with_bracket_field_is_proven():
    assert option_sources(callback(ACCEPTED), 'reply') == [{
        'control': 'choice',
        'value_field': 'code',
        'response_path': 'reply.data',
        'source_line': line_of(ACCEPTED, 'control.appendChild(opt)'),
    }]


def test_member_field_bound_alias_and_single_quoted_id_are_proven():
    source = '''function(other){
      var items=other.rows;
      var select=document.getElementById('select_one');
      for(var k=0,n=items.length;k<n;k++){
        var item=document.createElement("option");
        item.value=items[k].code;
        item.textContent=items[k].label;
        select.appendChild(item);
      }
    }'''
    assert option_sources(callback(source), 'other') == [{
        'control': 'select_one',
        'value_field': 'code',
        'response_path': 'other.rows',
        'source_line': line_of(source, 'select.appendChild(item)'),
    }]


def test_direct_length_condition_without_bound_alias_is_proven():
    source = '''function(reply){
      var rows=reply.data;
      var control=document.getElementById("choice");
      for(var i=0;i<rows.length;i++){
        var opt=document.createElement("option");
        opt.value=rows[i]["code"];
        opt.innerText=rows[i]["name"];
        control.appendChild(opt);
      }
    }'''
    assert option_sources(callback(source), 'reply') == [{
        'control': 'choice',
        'value_field': 'code',
        'response_path': 'reply.data',
        'source_line': line_of(source, 'control.appendChild(opt)'),
    }]


@pytest.mark.parametrize('array', [
    'var rows=reply.data.filter(function(row){return row.ok;});',
    'var rows=reply.data.slice().reverse();',
    'var rows=reply.data.map(function(row){return row;});',
    'var rows=reply.data.sort();',
])
def test_transformed_response_arrays_are_rejected(array):
    source = loop_source('opt.value=rows[i]["code"];', 'opt.innerText=rows[i]["name"];', array=array)
    assert option_sources(callback(source), 'reply') == []


@pytest.mark.parametrize('header', [
    'for(var i=rows.length-1;i>=0;i--)',
    'for(var i=0,l=rows.length;i<l;i--)',
    'for(var i=0,l=rows.length;i<l;i+=2)',
])
def test_non_ascending_loops_are_rejected(header):
    source = loop_source('opt.value=rows[i]["code"];', 'opt.innerText=rows[i]["name"];', header=header)
    assert option_sources(callback(source), 'reply') == []


def test_loop_without_append_or_label_is_rejected():
    without_append = '''function(reply){
      var rows=reply.data;
      var control=document.getElementById("choice");
      for(var i=0,l=rows.length;i<l;i++){
        var opt=document.createElement("option");
        opt.value=rows[i]["code"];
        opt.innerText=rows[i]["name"];
      }
    }'''
    without_label = loop_source('opt.value=rows[i]["code"];')
    assert option_sources(callback(without_append), 'reply') == []
    assert option_sources(callback(without_label), 'reply') == []


def test_callback_binding_does_not_cross_functions():
    taker = ACCEPTED.replace('function(reply)', 'function(other)', 1)
    assert option_sources(callback(ACCEPTED), 'reply')[0]['response_path'] == 'reply.data'
    assert option_sources(callback(taker), 'other') == []
    assert option_sources(callback(taker), 'reply') == []


@pytest.mark.parametrize('statements', [
    ('opt.value=rows[i]["code"]+100;', 'opt.innerText=rows[i]["name"];'),
    ('opt.value=Number(rows[i]["code"]);', 'opt.innerText=rows[i]["name"];'),
    ('opt.value=rows[i]["code"];', 'opt.value=rows[i]["name"];', 'opt.innerText=rows[i]["name"];'),
])
def test_transformed_or_duplicated_values_are_rejected(statements):
    assert option_sources(callback(loop_source(*statements)), 'reply') == []


@pytest.mark.parametrize('statements', [
    ('opt.value=rows[i]["code"];', 'opt.innerText=rows[i]["name"];', 'opt.disabled=true;'),
    ('opt.value=rows[i]["code"];', 'opt.innerText=rows[i]["name"];', 'opt.setAttribute("class","row");'),
    ('opt.value=rows[i]["code"];', 'opt.innerText=String(rows[i]["name"]);'),
])
def test_extra_properties_and_label_calls_are_rejected(statements):
    assert option_sources(callback(loop_source(*statements)), 'reply') == []


def test_local_array_and_missing_callback_yield_nothing():
    local = '''function(reply){
      var rows=[1,2,3];
      var control=document.getElementById("choice");
      for(var i=0,l=rows.length;i<l;i++){
        var opt=document.createElement("option");
        opt.value=rows[i]["code"];
        opt.innerText=rows[i]["name"];
        control.appendChild(opt);
      }
    }'''
    assert option_sources(callback(local), 'reply') == []
    assert option_sources(None, 'reply') == []


def test_computed_control_id_is_rejected():
    source = '''function(reply){
      var rows=reply.data;
      var control=document.getElementById(controlName);
      for(var i=0,l=rows.length;i<l;i++){
        var opt=document.createElement("option");
        opt.value=rows[i]["code"];
        opt.innerText=rows[i]["name"];
        control.appendChild(opt);
      }
    }'''
    assert option_sources(callback(source), 'reply') == []


@pytest.mark.parametrize('mutation', ['rows.reverse();', 'rows.sort();', 'reply.data.reverse();'])
def test_pre_loop_array_mutation_is_rejected(mutation):
    source = '''function(reply){
      var rows=reply.data;
      var control=document.getElementById("choice");
      %s
      for(var i=0,l=rows.length;i<l;i++){
        var opt=document.createElement("option");
        opt.value=rows[i]["code"];
        opt.innerText=rows[i]["name"];
        control.appendChild(opt);
      }
    }''' % mutation
    assert option_sources(callback(source), 'reply') == []


@pytest.mark.parametrize('statements', [
    ('var rows=document.createElement("option");', 'rows.value=rows[i]["code"];',
     'rows.innerText=rows[i]["name"];', 'control.appendChild(rows);'),
    ('var control=document.createElement("option");', 'control.value=rows[i]["code"];',
     'control.innerText=rows[i]["name"];', 'control.appendChild(control);'),
    ('var l=document.createElement("option");', 'l.value=rows[i]["code"];',
     'l.innerText=rows[i]["name"];', 'control.appendChild(l);'),
])
def test_option_name_shadowing_loop_bindings_is_rejected(statements):
    source = '''function(reply){
      var rows=reply.data;
      var control=document.getElementById("choice");
      for(var i=0,l=rows.length;i<l;i++){
        %s
      }
    }''' % '\n        '.join(statements)
    assert option_sources(callback(source), 'reply') == []


@pytest.mark.parametrize('mutation', ['control.innerHTML="";', 'control.replaceChildren();'])
def test_post_loop_control_mutation_is_rejected(mutation):
    source = '''function(reply){
      var rows=reply.data;
      var control=document.getElementById("choice");
      for(var i=0,l=rows.length;i<l;i++){
        var opt=document.createElement("option");
        opt.value=rows[i]["code"];
        opt.innerText=rows[i]["name"];
        control.appendChild(opt);
      }
      %s
    }''' % mutation
    assert option_sources(callback(source), 'reply') == []


def test_pre_loop_control_clearing_does_not_invalidate():
    source = '''function(reply){
      var rows=reply.data;
      var control=document.getElementById("choice");
      control.innerHTML="";
      for(var i=0,l=rows.length;i<l;i++){
        var opt=document.createElement("option");
        opt.value=rows[i]["code"];
        opt.innerText=rows[i]["name"];
        control.appendChild(opt);
      }
    }'''
    facts = option_sources(callback(source), 'reply')
    assert facts[0]['control'] == 'choice'
    assert facts[0]['response_path'] == 'reply.data'


def test_delete_label_is_rejected():
    source = '''function(reply){
      var rows=reply.data;
      var control=document.getElementById("choice");
      for(var i=0,l=rows.length;i<l;i++){
        var opt=document.createElement("option");
        opt.value=rows[i]["code"];
        opt.innerText=(delete opt.value);
        control.appendChild(opt);
      }
    }'''
    assert option_sources(callback(source), 'reply') == []
