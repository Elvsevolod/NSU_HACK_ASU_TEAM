"""Basic record components and Jackson 2.12+ property creators.

Explicit/compact constructors, annotated component policies and custom component
accessors need separate execution rules; they are never silently skipped.
"""
from .project import text,walk


def components(declaration):
    parameters=declaration.child_by_field_name('parameters')
    return [node for node in parameters.named_children if node.type=='formal_parameter'] if parameters else []


def bean_plan(project,owner,declaration):
    issues=[];props={};accessors={}
    body=declaration.child_by_field_name('body')
    if any(node.type in ('constructor_declaration','compact_constructor_declaration') for node in body.named_children):
        issues.append('record source constructor execution is outside the basic record adapter')
    if any(node.type in ('annotation','marker_annotation') and text(node.child_by_field_name('name')).split('.')[-1].startswith('Json') for node in walk(declaration)):
        issues.append('record-specific Jackson annotation policy is not modeled')
    method_names={text(node.child_by_field_name('name')) for node in body.named_children if node.type=='method_declaration'}
    for node in components(declaration):
        name=text(node.child_by_field_name('name'));typ=text(node.child_by_field_name('type'))
        if name in method_names:issues.append('record custom component accessor is not modeled: '+name)
        prop={'kind':'generated','member':name,'owner':owner,'type':typ,'non_null':False}
        props[name]=prop;accessors[name,0]=prop
    return {'properties':props,'constructor':{'kind':'record','member':None,'owner':owner},
            'generated_accessors':accessors,'ignored_properties':(),
            'issues':tuple(sorted(set(issues))),'complete':not issues,
            'model_version':'java-record-jackson-properties/1','requires':'Jackson 2.12+ default record property creator'}
