"""Execute source compact-record validation guards without inventing method IDs.

Only if(condition) throw new standard exception(String) guards are supported.
Arbitrary constructor bodies remain an explicit boundary.
"""
from .project import text,walk
from .native_storage import JavaFrame
from .java_exceptions import JavaThrow,native_type
from .source_generics import render


def validate(engine,owner,declaration,fields,arguments,kinds,reason):
    from .engine import AnalysisBoundary
    compact=[c for c in declaration.child_by_field_name('body').named_children if c.type=='compact_constructor_declaration']
    if not compact:return
    if len(compact)!=1:raise AnalysisBoundary('ambiguous record compact constructor: '+reason,category='unsupported_semantics')
    body=compact[0].child_by_field_name('body')
    statements=[n for n in body.named_children if n.type not in ('line_comment','block_comment')]
    guards=[];meta=engine.p.nodes[owner]
    for statement in statements:
        if statement.type!='if_statement' or statement.child_by_field_name('alternative') is not None:
            raise AnalysisBoundary('record compact constructor needs general source execution: '+reason,category='unsupported_semantics')
        condition=statement.child_by_field_name('condition');failure=statement.child_by_field_name('consequence')
        if any(n.type in ('method_invocation','object_creation_expression','assignment_expression','update_expression','field_access') for n in walk(condition)):
            raise AnalysisBoundary('record validation guard has unsupported effects: '+reason,category='unsupported_semantics')
        if failure.type!='throw_statement' or len(failure.named_children)!=1 or failure.named_children[0].type!='object_creation_expression':
            raise AnalysisBoundary('record validation guard completion is unsupported: '+reason,category='unsupported_semantics')
        allocation=failure.named_children[0];written=text(allocation.child_by_field_name('type'))
        if not any(engine.standard_type(written,'java.lang.'+name,meta) for name in ('IllegalArgumentException','IllegalStateException','NullPointerException')):
            raise AnalysisBoundary('record validation exception constructor is unsupported: '+reason,category='unsupported_semantics')
        message=allocation.child_by_field_name('arguments').named_children
        if len(message)>1 or any(n.type in ('method_invocation','object_creation_expression','assignment_expression','update_expression') for arg in message for n in walk(arg)):
            raise AnalysisBoundary('record validation message has unsupported effects: '+reason,category='unsupported_semantics')
        guards.append((condition,written,message))
    previous=engine.variable_types
    local=JavaFrame()
    engine.variable_types=dict(previous)
    try:
        for index,((name,info),value) in enumerate(zip(fields,arguments)):
            written=render(engine.p,info['type'],meta,{},engine.standard_type)
            if not written:raise AnalysisBoundary('record component type is unresolved: '+reason,category='unsupported_semantics')
            engine.variable_types[name]=written
            local.set_value(name,value,kinds[index] if index<len(kinds) else engine.declared_kind(written,meta))
        for condition,written,message in guards:
            value=engine.value(condition,local)
            if type(value) is not bool:
                value=engine.choose(reason+':record-validation:'+str(condition.start_byte),[False,True])
                if value is None:raise AnalysisBoundary('record validation outcome is unresolved: '+reason,category='unsupported_semantics')
            engine.effect_events.append({'model_version':'source-record-validation/1','operation':'record validation','record':owner,
                'source_location':meta['file']+':'+str(condition.start_point.row+1),'condition':text(condition),'value':value})
            if value:raise JavaThrow({'__type__':native_type(written),'message':engine.value(message[0],local) if message else None})
    finally:engine.variable_types=previous
