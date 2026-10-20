"""Source-proven Bean Validation constraints at the MVC argument boundary."""
import re

from .project import text,walk
from .state import U
from .java_collections import JavaRecord
from .http_binding import BindingFailure


def validate(engine,target,values):
    p=engine.p;meta=p.methods[target];node=p.ast.get(target)
    if node is None:return
    parameters=[child for child in node.child_by_field_name('parameters').named_children if child.type=='formal_parameter']
    for parameter,value in zip(parameters,values):
        if not re.search(r'@(?:[\w.]+\.)?(?:Valid|Validated)\b',text(parameter)):continue
        if not isinstance(value,JavaRecord):continue
        owner=p.resolve_type(value.declared_type,meta['module'],meta['file'])
        if not owner:continue
        source=p.trees[p.nodes[owner]['file']]
        for field in walk(source.root_node):
            if field.type!='field_declaration':continue
            names=[text(child.child_by_field_name('name')) for child in field.named_children if child.type=='variable_declarator']
            for name in names:
                if name not in p.type_fields[owner]:continue
                actual=value.get(name,U)
                for constraint in re.findall(r'@([\w.]+)(?:\(([^()]*)\))?',text(field)):
                    kind=constraint[0].rsplit('.',1)[-1]
                    qualified=any(engine.standard_type(constraint[0],package+'.'+kind,p.nodes[owner]) for package in
                        ('javax.validation.constraints','jakarta.validation.constraints','org.hibernate.validator.constraints'))
                    if not qualified:continue
                    accepted=True
                    if kind=='NotNull':accepted=actual is not None if actual is not U else U
                    elif kind in ('NotBlank','NotEmpty'):
                        accepted=False if actual is None else bool(actual.strip() if kind=='NotBlank' else actual) if isinstance(actual,(str,list,dict)) else U
                    elif kind=='Size' and actual is not None:
                        bounds=dict((key,int(number)) for key,number in re.findall(r'\b(min|max)\s*=\s*(\d+)',constraint[1]))
                        accepted=bounds.get('min',0)<=len(actual)<=bounds.get('max',2147483647) if isinstance(actual,(str,list,dict)) else U
                    elif kind in ('Min','Max') and actual is not None:
                        bound=re.search(r'(?:value\s*=\s*)?(-?\d+)',constraint[1])
                        accepted=(actual>=int(bound[1]) if kind=='Min' else actual<=int(bound[1])) if bound and type(actual) in (int,float) else U
                    else:continue
                    if accepted is U:
                        accepted=engine.choose(target+':validation:'+name+':'+kind,[True,False])
                        if accepted is None:
                            from .engine import AnalysisBoundary
                            raise AnalysisBoundary('unresolved validation completion: '+name+' '+kind)
                    if not accepted:raise BindingFailure('Bean Validation '+kind+' rejected '+name)
