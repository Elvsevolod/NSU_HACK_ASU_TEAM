"""Source-proven default class-level Lombok builders; no generated graph IDs."""
from .bean_properties import annotations,declaration
from .java_collections import JavaObject
from .project import text,keywords
from .source_generics import render
from .state import U


class JavaBuilder(dict):
    def __init__(self,owner,fields):
        super().__init__()
        self.owner,self.fields=owner,fields
        self.values={name:False if typ=='boolean' else '\0' if typ=='char' else
                     0.0 if typ in ('float','double') else 0 if typ in ('byte','short','int','long') else None
                     for name,typ in fields.items()}
        self.kinds={}


def boundary(reason,message):
    from .engine import AnalysisBoundary
    raise AnalysisBoundary('Lombok builder '+message+': '+reason,category='unsupported_semantics')


def plan(engine,owner,reason):
    p=engine.p;cache=p.__dict__.setdefault('_default_builder_plans',{})
    if owner in cache:
        fields,error=cache[owner]
        if error:boundary(reason,error)
        return fields
    node=declaration(p,owner);meta=p.nodes[owner]
    notes={name.rsplit('.',1)[-1]:args for name,args in annotations(node)
           if engine.standard_type(name,'lombok.'+name.rsplit('.',1)[-1],meta)} if node is not None else {}
    if 'Builder' not in notes:return None
    body=node.child_by_field_name('body');members=body.named_children if body is not None else []
    error=None
    if node.type!='class_declaration' or 'abstract' in keywords(node) or node.child_by_field_name('type_parameters') is not None or p.type_parents.get(owner):
        error='generic/inherited declaration is outside the default contract'
    elif any(not engine.standard_type(parent,'java.lang.Object',meta) for parent in p.framework_types.get(owner,())):
        error='external parent contract is unresolved'
    elif any(notes.get(name,'').strip('() ') for name in ('Builder','AllArgsConstructor','NoArgsConstructor')):
        error='annotation options are not modeled'
    elif any(member.type in ('class_declaration','interface_declaration','block') for member in members):
        error='nested builder or instance initializer is not modeled'
    elif any(name in notes for name in ('RequiredArgsConstructor','NoArgsConstructor')) and 'AllArgsConstructor' not in notes:
        error='generated all-args constructor is not proved'
    fields={}
    for member in members:
        if member.type!='field_declaration' or 'static' in keywords(member):continue
        if any(any(engine.standard_type(name,fqn,meta) for fqn in ('lombok.Builder.Default','lombok.Singular','lombok.NonNull'))
               for name,_ in annotations(member)):
            error='field default, singular collection or null-check policy is not modeled'
        for variable in member.named_children:
            if variable.type!='variable_declarator':continue
            if variable.child_by_field_name('value') is not None:error='instance field initializer is not modeled'
            written=text(member.child_by_field_name('type'))
            actual=render(p,written,meta,{},engine.standard_type)
            if not actual:error='field type is unresolved'
            fields[text(variable.child_by_field_name('name'))]=actual or written
    constructors=[member for member in members if member.type=='constructor_declaration']
    if constructors and ('AllArgsConstructor' not in notes or any(len([
            param for param in ctor.child_by_field_name('parameters').named_children
            if param.type in ('formal_parameter','spread_parameter')])==len(fields) for ctor in constructors)):
        error='source all-args constructor selection is not proved'
    cache[owner]=fields,error
    if error:boundary(reason,error)
    return fields


def operation(engine,node,obj,args,kinds,reason):
    name=text(node.child_by_field_name('name'));p=engine.p;meta=p.methods[engine.method]
    if isinstance(obj,JavaBuilder):
        if engine.opaque(obj):boundary(reason,'escaped builder contents are unresolved')
        if name=='build' and not args:
            fqn=p.nodes[obj.owner]['fqn']
            value=JavaObject(fqn,{'__type__':fqn,'__http_entity__':False,**obj.values},wire_fields=obj.fields)
            value.source_owner=obj.owner
            value._native_field_kinds={field:obj.kinds.get(field,engine.declared_kind(typ,p.nodes[obj.owner]) if
                typ in ('boolean','byte','short','char','int','long','float','double') else None) for field,typ in obj.fields.items()}
            value._field_reference_types=dict(obj.fields)
            return True,value
        if name in obj.fields and len(args)==1:
            argument=next(child for child in node.child_by_field_name('arguments').named_children
                          if child.type not in ('line_comment','block_comment'))
            value,kind=engine.assignment_value(args[0],kinds[0],obj.fields[name],argument)
            obj.values[name]=value;obj.kinds[name]=kind
            return True,obj
        boundary(reason,'method or overload is outside the default contract')
    qualifier=node.child_by_field_name('object');written=text(qualifier);root=written.split('.')[0]
    if name!='builder' or args or qualifier is None:return False,U
    if root in engine.variable_types or root in p.type_fields.get(meta['owner'],{}):return False,U
    owner=p.resolve_type(written,meta['module'],meta['file'])
    if owner is None:return False,U
    fields=plan(engine,owner,reason)
    if fields is None:return False,U
    from .static_storage import ensure
    ensure(engine,owner)
    return True,JavaBuilder(owner,fields)
