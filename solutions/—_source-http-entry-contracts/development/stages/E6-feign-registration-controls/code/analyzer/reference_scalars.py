"""Conservative identity proofs for immutable scalar references in source."""
from .project import text,walk
from .source_conversions import compiled_type,PRIMITIVES
from .state import U


def origin(engine,node,seen=None):
    if node is None:return None
    while node.type=='parenthesized_expression':node=node.named_children[0]
    if node.type in ('decimal_integer_literal','character_literal','true','false','string_literal'):return node
    if node.type!='identifier':return None
    name=text(node);seen=set() if seen is None else seen
    if name in seen:return None
    seen.add(name)
    root=engine.p.ast.get(engine.method)
    if root is None:return None
    declarations=[n for n in walk(root) if n.type=='variable_declarator' and text(n.child_by_field_name('name'))==name]
    if len(declarations)!=1:return None
    declaration=declarations[0]
    for n in walk(root):
        if n.type=='assignment_expression' and text(n.child_by_field_name('left'))==name:return None
        if n.type=='update_expression' and any(text(c)==name for c in n.named_children):return None
    parent=declaration.parent
    while parent is not None and parent!=root:
        if parent.type in ('for_statement','enhanced_for_statement','while_statement','do_statement'):return None
        parent=parent.parent
    initializer=declaration.child_by_field_name('value')
    return origin(engine,initializer,seen) or initializer


def equal(engine,left,right,a,b,left_kind,right_kind):
    if left_kind!=right_kind:return False
    if left.type==right.type=='identifier' and text(left)==text(right):return True
    if type(a) is not type(b) or type(a) not in (int,str,bool):return U
    if a!=b:return False
    first,second=origin(engine,left),origin(engine,right)
    if first is not None and second is not None:
        if first==second:return True
        source_types=[compiled_type(engine,n) for n in (first,second)]
        literals=('decimal_integer_literal','character_literal','true','false','string_literal')
        if all(n.type in literals for n in (first,second)):
            if left_kind=='String' and source_types==['java.lang.String']*2:return True
            if all(t in PRIMITIVES for t in source_types):
                if left_kind=='Boolean':return True
                if left_kind in ('Byte','Short','Integer','Long') and type(a) is int and -128<=a<=127:return True
                if left_kind=='Character' and type(a) is str and len(a)==1 and ord(a)<=127:return True
    return U
