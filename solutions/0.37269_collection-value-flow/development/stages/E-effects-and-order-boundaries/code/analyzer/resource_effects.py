"""Read/write classification for source-backed fallback closures."""
import re
from .generic_types import type_parts
from .project import text


def proven_read(project,site):
    """Only abstract, unannotated Spring Data standard/derived reads are proven."""
    node=project.nodes[site];meta=project.methods[node['method']]
    owner=project.resolve_type(node.get('receiver_type',''),meta['module'],meta['file'])
    if owner is None:return False
    pending=[owner];seen=set();repository=False
    while pending:
        current=pending.pop()
        if current in seen:continue
        seen.add(current);context=project.nodes[current]
        for written in project.generic_parents.get(current,()):
            base,_=type_parts(written)
            parent=project.resolve_type(base,context['module'],context['file'])
            if parent:pending.append(parent);continue
            imports=[match[1] for n in project.trees[context['file']].root_node.named_children if n.type=='import_declaration'
                     for match in [re.search(r'\bimport\s+([\w.*]+)\s*;',text(n))] if match]
            for fqn in ('org.springframework.data.jpa.repository.JpaRepository','org.springframework.data.repository.CrudRepository',
                        'org.springframework.data.mongodb.repository.MongoRepository'):
                explicit=[name for name in imports if name.rsplit('.',1)[-1]==base]
                repository |= base==fqn or base==fqn.rsplit('.',1)[-1] and (
                    explicit==[fqn] or not explicit and fqn.rsplit('.',1)[0]+'.*' in imports)
    if not repository:return False
    name=node.get('callee','')
    declared=[mid for mid in project.inherited_methods(owner,name,node.get('arg_count',0))]
    for mid in declared:
        method=project.methods[mid]
        if not method.get('abstract'):return False
        # Query/Procedure/Modifying and unknown query customizations need their
        # own effect proof; a friendly method name is not such a proof.
        if method.get('annotations'):return False
    return name in ('findAll','findAllById','findById','count','existsById','getOne','getById','getReferenceById') or bool(
        re.fullmatch(r'(?:find|read|get|query|search|stream|count|exists)[A-Z]\w*By[A-Z]\w*',name) or
        re.fullmatch(r'(?:find|read|get|query|search|stream|count|exists)By[A-Z]\w*',name))


def possible_writes(project, methods, data, active_transaction=False):
    resources={target for _,target in data}
    cache=project.__dict__.setdefault('_source_write_resources',{})
    key=(frozenset(methods),frozenset(data),active_transaction)
    if key in cache:return cache[key]
    # An open persistence context can flush managed changes without save().
    transactional=active_transaction or any(any(a['name'].rsplit('.',1)[-1]=='Transactional'
        for a in [*project.methods[mid].get('annotations',[]),
                  *project.nodes[project.methods[mid]['owner']].get('annotations',[])]) for mid in methods)
    if transactional:
        cache[key]=resources;return resources
    observed=set();writes=set()
    for site in (site for mid in methods for site in project.sites.get(mid,())):
        node=project.nodes[site]
        accessed=project.edges.get(site,{}).get('data_access',set()) & resources
        observed.update(accessed)
        if not proven_read(project,site):
            writes.update(accessed)
    # A graph-only data edge without an operation witness remains a possible write.
    result=writes | (resources-observed)
    cache[key]=result
    return result
