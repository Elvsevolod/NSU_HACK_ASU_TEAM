from tree_sitter import Language, Parser
import tree_sitter_javascript
from analyzer.option_sources import option_sources


SOURCE='''function(reply){var rows=reply.data;var control=document.getElementById("choice");
  BEFORE
  for(var i=0,l=rows.length;i<l;i++){
    var opt=document.createElement("option");
    opt.value=rows[i].code;opt.innerText=rows[i].name;control.appendChild(opt);
  }
  AFTER
}'''


def facts(source):
    parser=Parser(Language(tree_sitter_javascript.language()))
    node=parser.parse(('('+source+');').encode()).root_node.named_children[0]
    while node.type in ('expression_statement','parenthesized_expression'):
        node=node.named_children[0]
    return option_sources(node,'reply')


def test_mutating_response_array_before_loop_does_not_prove_original_order():
    for statement in ('rows.reverse();','reply.data.reverse();','rows.sort();'):
        assert facts(SOURCE.replace('BEFORE',statement).replace('AFTER',''))==[]


def test_loop_local_cannot_replace_source_array_or_control():
    for variable in ('rows','control','l'):
        source=SOURCE.replace('BEFORE','').replace('AFTER','').replace('var opt=','var '+variable+'=').replace('opt.value',variable+'.value').replace('opt.innerText',variable+'.innerText').replace('appendChild(opt)','appendChild('+variable+')')
        assert facts(source)==[]


def test_later_control_clear_invalidates_published_option_source():
    for statement in ('control.innerHTML="";','control.replaceChildren();'):
        assert facts(SOURCE.replace('BEFORE','').replace('AFTER',statement))==[]


def test_label_expression_cannot_delete_the_known_option_value():
    source=SOURCE.replace('BEFORE','').replace('AFTER','').replace('opt.innerText=rows[i].name','opt.innerText=(delete opt.value)')
    assert facts(source)==[]
