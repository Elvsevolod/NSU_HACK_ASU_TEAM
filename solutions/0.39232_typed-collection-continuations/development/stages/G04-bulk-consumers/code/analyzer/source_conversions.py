"""Bounded source compilation contexts, independent of observed heap values."""
from contextlib import contextmanager
from .project import text
from .generic_types import bind_parameters,type_parts,resolve
from .source_generics import render,environment,method_variables

PRIMITIVES={'boolean','byte','short','char','int','long','float','double'}


def bounds(engine,method):
    cache=engine.p.__dict__.setdefault('_declaration_bound_contexts',{})
    if method not in cache:
        p=engine.p;meta=p.methods[method];owner=meta['owner']
        class_bindings=bind_parameters(p,owner,[],p.nodes[owner],{}) or {}
        variables=method_variables(p,method)
        bindings={name:value for name,value in class_bindings.items() if name not in variables}
        bindings.update((name,(bound,meta,bindings)) for name,bound in variables.items())
        flat={name:render(p,name,meta,bindings,engine.standard_type) for name in bindings}
        args=[render(p,name,p.nodes[owner],class_bindings,engine.standard_type) for name in p.type_variables.get(owner,{})]
        receiver=p.nodes[owner]['fqn']
        if args and all(args):receiver+='<'+','.join(args)+'>'
        cache[method]=(flat,receiver)
    return cache[method]


@contextmanager
def declaration_context(engine):
    previous=engine.source_bindings,engine.receiver_type
    engine.source_bindings,engine.receiver_type=bounds(engine,engine.method)
    try:yield
    finally:engine.source_bindings,engine.receiver_type=previous


def compiled_type(engine,node):
    with declaration_context(engine):return engine.source_type(node)


def declaration_erasure(engine,written,method=None,owner=None):
    if owner is not None:
        meta=engine.p.nodes[owner]
        bindings=bind_parameters(engine.p,owner,[],meta,{}) or {}
    else:
        method=engine.method if method is None else method
        meta=engine.p.methods[method];flat,_=bounds(engine,method)
        bindings=environment(flat,meta)
    dimensions=''
    written=written.replace('...','[]').strip()
    while written.endswith('[]'):written=written[:-2];dimensions+='[]'
    written,meta,bindings=resolve(written,meta,bindings)
    base,_=type_parts(written)
    rendered=render(engine.p,base,meta,bindings,engine.standard_type,erase=True)
    return rendered+dimensions if rendered else ''


def field_info(engine,node):
    meta=engine.p.methods[engine.method]
    qualifier=node.child_by_field_name('object')
    receiver=compiled_type(engine,qualifier) if qualifier is not None else bounds(engine,engine.method)[1]
    owner=engine.p.resolve_type(receiver,meta['module'],meta['file'])
    name=text(node.child_by_field_name('field')) if node.type=='field_access' else text(node)
    return engine.p.type_fields.get(owner,{}).get(name)


def storage_type(engine,node):
    if node.type=='identifier' and text(node) in engine.variable_types:
        return declaration_erasure(engine,engine.variable_types[text(node)])
    if node.type in ('identifier','field_access'):
        info=field_info(engine,node)
        if info:return declaration_erasure(engine,info['type'],owner=info['declaring_type'])
    if node.type=='array_access':return compiled_type(engine,node)
    return ''


def argument_type(engine,call,index):
    p=engine.p;mid=engine.method;site=p.site(mid,call)
    targets=p.targets(mid,site) if site else p.source_targets(mid,call)
    if not targets:targets=p.source_targets(mid,call)
    obj=call.child_by_field_name('object');receiver=compiled_type(engine,obj)
    if not targets and obj is not None:
        meta=p.methods[mid];owner=p.resolve_type(receiver,meta['module'],meta['file'])
        arguments=call.child_by_field_name('arguments')
        arity=sum(c.type not in ('line_comment','block_comment') for c in arguments.named_children)
        if owner:targets=p.inherited_methods(owner,text(call.child_by_field_name('name')),arity)
    if targets:
        found=set()
        with declaration_context(engine):
            for target in targets:
                pars=p.parameters(target)
                if index>=len(pars) or pars[index][1].endswith('...'):return ''
                meta=p.methods[target];bindings,_,_=engine.generic_call_context(target,call)
                found.add(render(p,pars[index][1],meta,environment(bindings,meta),engine.standard_type,erase=True))
        return next(iter(found)) if len(found)==1 else ''
    base,args=type_parts(receiver);name=text(call.child_by_field_name('name'))
    standard=lambda short:engine.standard_type(base,'java.util.'+short)
    if any(standard(kind) for kind in ('List','ArrayList','LinkedList','Collection','Set','HashSet')):
        element=args[0] if args and len(args)==1 else 'java.lang.Object'
        if name in ('contains','indexOf','lastIndexOf','remove'):return 'java.lang.Object'
        if name in ('get','set') and index==0:return 'int'
        arity=sum(c.type not in ('line_comment','block_comment') for c in call.child_by_field_name('arguments').named_children)
        if name=='add' and arity>1 and index==0:return 'int'
        if name in ('add','set'):return element
        if name in ('removeAll','retainAll') and arity==1 and index==0:return 'java.util.Collection'
        if name=='addAll':
            if arity==1 and index==0:return 'java.util.Collection'
            if arity==2 and any(standard(kind) for kind in ('List','ArrayList','LinkedList')):
                return 'int' if index==0 else 'java.util.Collection' if index==1 else ''
    if any(standard(kind) for kind in ('Map','HashMap','LinkedHashMap')):
        if name in ('get','containsKey','containsValue','remove'):return 'java.lang.Object'
        if name=='put' and index<2:return args[index] if args and len(args)==2 else 'java.lang.Object'
    if name=='equals' and index==0:return 'java.lang.Object'
    if name=='asList' and engine.standard_type(text(obj),'java.util.Arrays'):
        result=compiled_type(engine,call);_,elements=type_parts(result)
        return elements[0] if elements and len(elements)==1 else ''
    return ''


def consumer_type(engine,node):
    """Expected erased type; Object also denotes a discarded read result."""
    current=node;parent=current.parent
    while parent is not None and parent.type=='parenthesized_expression':current,parent=parent,parent.parent
    if parent is None:return ''
    kind=parent.type
    if kind=='variable_declarator':
        written=text(parent.parent.child_by_field_name('type'))
        meta=engine.p.methods[engine.method]
        keyword=written=='var' and not engine.p.resolve_type(written,meta['module'],meta['file'])
        return compiled_type(engine,node) if keyword else declaration_erasure(engine,written)
    if kind=='assignment_expression' and parent.child_by_field_name('right')==current:
        return storage_type(engine,parent.child_by_field_name('left')) if text(parent.child_by_field_name('operator'))=='=' else compiled_type(engine,node)
    if kind=='return_statement':return declaration_erasure(engine,engine.return_type_override or engine.p.methods[engine.method].get('return_raw',''))
    if kind=='cast_expression':return declaration_erasure(engine,text(parent.child_by_field_name('type')))
    if kind=='argument_list':
        children=[c for c in parent.named_children if c.type not in ('line_comment','block_comment')]
        return argument_type(engine,parent.parent,children.index(current)) if current in children else ''
    if kind=='expression_statement':return 'java.lang.Object'
    if kind=='binary_expression':
        side='left' if parent.child_by_field_name('left')==current else 'right'
        return compiled_type(engine,node) if engine.binary_unboxes(parent,side) else 'java.lang.Object'
    if kind in ('unary_expression','update_expression'):return compiled_type(engine,node)
    if kind in ('if_statement','while_statement','do_statement','for_statement','ternary_expression') and parent.child_by_field_name('condition')==current:return 'boolean'
    if kind=='ternary_expression':return compiled_type(engine,parent) or consumer_type(engine,parent)
    if kind in ('field_access','method_invocation') and parent.child_by_field_name('object')==current:return compiled_type(engine,node)
    if kind=='array_access' and parent.child_by_field_name('index')==current:return 'int'
    if kind=='array_access' and parent.child_by_field_name('array')==current:return compiled_type(engine,node)
    if kind=='array_initializer':
        outer=parent.parent
        if outer.type=='variable_declarator':return declaration_erasure(engine,text(outer.parent.child_by_field_name('type'))).removesuffix('[]')
        if outer.type=='array_creation_expression':return declaration_erasure(engine,text(outer.child_by_field_name('type')))
    return ''
