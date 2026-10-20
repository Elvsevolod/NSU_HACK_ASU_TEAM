"""Scenario-owned Java static cells and bounded source initialization.

Internal initializer contexts supply only a source namespace. They never enter
the input graph, handler index or output edges. No JVM/classes are loaded.
"""
from .native_storage import JavaFrame,StaticCells
from .project import text, walk, body_members, declaration_matches, keywords
from .source_literals import literal_default
from .java_exceptions import JavaThrow
from .state import U


def declaration(engine,node):
    meta=engine.p.methods[engine.method]
    if node.type=='identifier':
        name=text(node)
        if name in engine.variable_types:return None
        return (engine.p.static_field_declaration(meta['owner'],name) or
                engine.p.imported_static_field(meta['file'],meta['module'],name))
    if node.type!='field_access':return None
    obj=node.child_by_field_name('object');name=text(node.child_by_field_name('field'))
    receiver=engine.source_type(obj)
    root=text(obj).split('.')[0]
    if root not in engine.variable_types and root not in engine.p.type_fields.get(meta['owner'],{}):
        receiver=receiver or text(obj)
    owner=engine.p.resolve_type(receiver,meta['module'],meta['file'])
    return engine.p.static_field_declaration(owner,name)


def context(project,owner):
    cache=project.__dict__.setdefault('_static_source_contexts',{})
    if owner not in cache:
        meta=project.nodes[owner];key='source-context:static:'+owner
        # Not a skeleton method: no node, callsite, AST method or by-name entry.
        project.methods[key]={'owner':owner,'module':meta['module'],'file':meta['file'],
            'name':'<source-static-initializer>','params_as_written':[],
            'annotations':[],'return_raw':'void','analysis_context':True}
        project.ix.module[key]=meta['module']
        cache[owner]=key
    return cache[owner]


def items(project,owner):
    cache=project.__dict__.setdefault('_static_initializer_items',{})
    if owner not in cache:
        meta=project.nodes[owner]
        declarations=[n for n in walk(project.trees[meta['file']].root_node)
            if n.type in ('class_declaration','enum_declaration') and declaration_matches(n,meta['fqn'])]
        result=[]
        if len(declarations)==1:
            for field in body_members(declarations[0].child_by_field_name('body')):
                if field.type=='static_initializer':result.append((None,field.named_children[-1],None,False))
                elif field.type=='field_declaration' and 'static' in keywords(field):
                    for var in field.named_children:
                        if var.type=='variable_declarator':
                            result.append((text(var.child_by_field_name('name')),var.child_by_field_name('value'),
                                text(field.child_by_field_name('type')),'final' in keywords(field)))
        cache[owner]=result
    return cache[owner]


def constant(project,owner,name):
    # Only primitive/String constant variables bypass active initialization.
    for field,node,written,final in items(project,owner):
        if field==name and final and written in ('String','java.lang.String','boolean','byte','short','char','int','long','float','double'):
            value,kind=literal_default(node)
            if value is not U and value is not None:return True,value,kind
            if node is not None and value is U and not any(n.type in
                    ('method_invocation','object_creation_expression','array_creation_expression','null_literal') for n in walk(node)):
                # This could be a JLS constant expression. Active class
                # initialization would itself be a false effect. Stop until
                # constant-expression proof covers this expression's grammar.
                return None,U,None
    return False,U,None


def ensure(engine,owner):
    if not owner or not items(engine.p,owner) and not engine.p.type_parents.get(owner):return
    from .engine import AnalysisBoundary
    state=engine.state;record=state.class_initialization.get(owner)
    if record:
        if not isinstance(record,dict):raise AnalysisBoundary('joined static initialization status is unresolved: '+owner,category='unsupported_semantics')
        if record['status']=='initialized':return
        if record['status']=='failed':raise JavaThrow({'__type__':'NoClassDefFoundError'})
        if record['status']=='initializing':
            if engine.initializer_context and engine.initializer_context[0]==owner:return
            raise AnalysisBoundary('cyclic static initialization: '+owner,category='unsupported_semantics')
        raise AnalysisBoundary('unresolved static initialization: '+owner,category='unsupported_semantics')
    state.class_initialization[owner]={'status':'initializing','versions':{}}
    cells=state.static_fields.setdefault(owner,StaticCells())
    for name,node,written,_ in items(engine.p,owner):
        if name is not None:
            value=False if written=='boolean' else '\0' if written=='char' else 0 if written in ('byte','short','int','long','float','double') else None
            cells.set_value(name,value,engine.declared_kind(written,engine.p.nodes[owner]))
            state.class_initialization[owner]['versions'][name]=0
    previous=(engine.method,engine.variable_types,engine.source_bindings,engine.receiver_type,engine.initializer_context)
    try:
        # A class initializes its source superclass, never an unrelated class.
        for parent in sorted(engine.p.type_parents.get(owner,())):
            if engine.p.nodes.get(parent,{}).get('kind')=='type':ensure(engine,parent)
        engine.method=context(engine.p,owner);engine.variable_types={}
        engine.source_bindings={};engine.receiver_type=engine.p.nodes[owner]['fqn']
        engine.initializer_context=(owner,engine.method,True)
        env=JavaFrame()
        for name,node,written,_ in items(engine.p,owner):
            if node is None:continue
            if name is None:
                value,control=engine.execute(node,env)
                if control=='throw':raise JavaThrow(value)
                if control:raise AnalysisBoundary('unsupported static initializer completion: '+owner,category='unsupported_semantics')
            else:
                value=engine.value(node,env)
                kind=engine.source_reference_kind(node,engine.last_reference_kind)
                value,kind=engine.assignment_value(value,kind,written,node)
                write(engine,owner,name,value,kind)
        engine.state.class_initialization[owner]['status']='initialized'
    except JavaThrow as failure:
        engine.state.class_initialization[owner]['status']='failed'
        raise JavaThrow({'__type__':'ExceptionInInitializerError','cause':failure.value}) from None
    except BaseException:
        engine.state.class_initialization[owner]['status']='unresolved'
        raise
    finally:
        engine.method,engine.variable_types,engine.source_bindings,engine.receiver_type,engine.initializer_context=previous


def cell(engine,node,env):
    found=declaration(engine,node)
    if not found:return None
    owner,written=found;name=text(node.child_by_field_name('field')) if node.type=='field_access' else text(node)
    if node.type=='field_access':
        obj=node.child_by_field_name('object');root=text(obj).split('.')[0]
        if root in env or root in engine.variable_types or root in engine.p.type_fields.get(engine.p.methods[engine.method]['owner'],{}):
            engine.value(obj,env)  # static access evaluates an expression qualifier, even null
    # Reads/writes during this owner's initializer use its preallocated cells.
    own=engine.initializer_context and engine.initializer_context[0]==owner
    if not own:ensure(engine,owner)
    return owner,name,written


def read(engine,node,env):
    found=declaration(engine,node)
    if not found:return False,U
    owner,_=found;name=text(node.child_by_field_name('field')) if node.type=='field_access' else text(node)
    is_constant,value,kind=constant(engine.p,owner,name)
    if is_constant is None:
        from .engine import AnalysisBoundary
        raise AnalysisBoundary('compile-time static constant expression is outside the literal proof: '+owner+'.'+name,category='unsupported_semantics')
    if is_constant:
        engine.remember_reference_kind(kind);return True,value
    owner,name,_=cell(engine,node,env)
    cells=engine.state.static_fields[owner]
    engine.remember_reference_kind(cells.kinds.get(name))
    return True,cells.get(name,U)


def write(engine,owner,name,value,kind):
    engine.state.static_fields[owner].set_value(name,value,kind)
    record=engine.state.class_initialization[owner]
    previous=record['versions'].get(name,0)
    record['versions'][name]=previous+1 if type(previous) is int else None
