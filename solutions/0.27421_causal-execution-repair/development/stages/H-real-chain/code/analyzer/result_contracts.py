"""Source result shapes for request selection, independent of scenario values."""
import re
from .project import text,walk


def result_shape(project,mid,active=None):
    cache=project.__dict__.setdefault('_result_shapes',{})
    if mid in cache:return cache[mid]
    active=set() if active is None else active
    if mid in active or len(active)>16:return set(),False
    active=active|{mid};meta=project.methods[mid]
    def types(written):
        found=set()
        for name in re.findall(r'[\w.$]+',written):
            owner=project.resolve_type(name,meta['module'],meta['file'])
            if owner in project.type_fields and not project.type_variables.get(owner):found.add(project.nodes[owner]['fqn'])
        collection=bool(re.search(r'\b(?:List|Collection|Set|Iterable|Page|Slice)\s*<|\[\]',written))
        return found,collection
    declared=types(meta.get('return_raw',''))
    node=project.ast.get(mid)
    if node is None:return declared
    bindings={}
    for child in walk(node):
        if child.type in ('local_variable_declaration','field_declaration'):
            for variable in child.named_children:
                if variable.type=='variable_declarator':bindings[text(variable.child_by_field_name('name'))]=(text(child.child_by_field_name('type')),variable.child_by_field_name('value'))
    def expression(value,seen=None):
        if value is None:return set(),False
        seen=set() if seen is None else seen
        if value.type=='identifier' and text(value) in bindings and text(value) not in seen:
            written,initializer=bindings[text(value)]
            shape=types(written)
            return shape if shape[0] else expression(initializer,seen|{text(value)})
        if value.type=='method_invocation':
            site=project.site(mid,value)
            targets=project.targets(mid,site) if site else project.source_targets(mid,value)
            if not targets:targets=project.source_targets(mid,value)
            arguments=value.child_by_field_name('arguments').named_children
            name=text(value.child_by_field_name('name'))
            source=project.sources[meta['file']].decode()
            qualifier=text(value.child_by_field_name('object'))
            response_factory=(name=='ok' and (qualifier=='org.springframework.http.ResponseEntity' or
                qualifier=='ResponseEntity' and 'import org.springframework.http.ResponseEntity;' in source or
                not qualifier and 'import static org.springframework.http.ResponseEntity.ok;' in source))
            if not targets and response_factory and len(arguments)==1:return expression(arguments[0],seen)
            shapes=[result_shape(project,target,active) for target in targets]
            return set().union(*(shape[0] for shape in shapes)),any(shape[1] for shape in shapes)
        if value.type=='object_creation_expression':
            written=text(value.child_by_field_name('type'));owner=project.resolve_type(written,meta['module'],meta['file'])
            if owner and project.type_variables.get(owner):
                variables=set(project.type_variables[owner]);arguments=value.child_by_field_name('arguments').named_children
                fields=list(project.type_fields.get(owner,{}).values())
                shapes=[expression(argument,seen) for field,argument in zip(fields,arguments) if field['type'] in variables]
                if shapes:return set().union(*(shape[0] for shape in shapes)),any(shape[1] for shape in shapes)
            return types(written)
        if value.type=='parenthesized_expression':return expression(value.named_children[0],seen)
        if value.type=='ternary_expression':
            shapes=[expression(value.child_by_field_name(side),seen) for side in ('consequence','alternative')]
            return shapes[0][0]|shapes[1][0],any(shape[1] for shape in shapes)
        return set(),False
    shapes=[expression(child.named_children[0]) for child in walk(node) if child.type=='return_statement' and child.named_children]
    result=(declared[0]|set().union(*(shape[0] for shape in shapes)),declared[1] or any(shape[1] for shape in shapes))
    cache[mid]=result
    return result
