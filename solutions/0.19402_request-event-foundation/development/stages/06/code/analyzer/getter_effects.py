"""Source read/write summaries used only to prove JSON getter commutation."""
from .project import text,walk

VERSION='source-getter-effects/1'


def footprint(engine,prop,active=()):
    if prop['kind']!='method':return {prop['member']},set()
    mid=prop['member']
    if mid in active:return None
    source=engine.p.ast.get(mid)
    if source is None:return None
    meta=engine.p.methods[mid]
    fields=engine.p.type_fields.get(meta['owner'],{})
    reads,writes=set(),set()
    fresh={text(node.child_by_field_name('name')) for node in walk(source)
           if node.type=='variable_declarator' and node.child_by_field_name('value') is not None
           and node.child_by_field_name('value').type=='object_creation_expression'}
    for node in walk(source.child_by_field_name('body')):
        if node.type in ('throw_statement','synchronized_statement','lambda_expression'):return None
        if node.type=='identifier' and text(node) in fields:reads.add(text(node))
        if node.type in ('assignment_expression','update_expression'):
            lhs=node.child_by_field_name('left') if node.type=='assignment_expression' else node.named_children[0]
            name=text(lhs).removeprefix('this.')
            if name in fields:writes.add(name)
            elif lhs.type!='identifier':return None
        if node.type=='object_creation_expression':
            written=text(node.child_by_field_name('type')).split('<')[0]
            allowed=('java.util.ArrayList','java.util.HashSet','org.springframework.beans.support.MutableSortDefinition')
            if not any(engine.standard_type(written,fqn,meta) for fqn in allowed):return None
        if node.type!='method_invocation':continue
        receiver=text(node.child_by_field_name('object'))
        name=text(node.child_by_field_name('name'))
        if receiver in ('','this'):
            targets=[mid for mid in engine.p.methods_of(meta['owner'],name) if engine.p.ast.get(mid) is not None]
            if len(targets)!=1:return None
            nested=footprint(engine,{'kind':'method','member':targets[0]},(*active,mid))
            if nested is None:return None
            reads.update(nested[0]);writes.update(nested[1])
        elif name=='unmodifiableList' and engine.standard_type(receiver,'java.util.Collections',meta):pass
        elif name=='sort' and engine.standard_type(receiver,'org.springframework.beans.support.PropertyComparator',meta):
            args=node.child_by_field_name('arguments').named_children
            if not args or text(args[0]) not in fresh:return None
        else:return None
    return reads,writes


def commute(engine,props):
    footprints=[footprint(engine,prop) for prop in props.values()]
    if any(value is None for value in footprints):return False
    return all(not (a[1] & (b[0]|b[1]) or b[1] & (a[0]|a[1]))
               for i,a in enumerate(footprints) for b in footprints[i+1:])
