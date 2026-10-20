"""Read/write classification for source-backed fallback closures."""
import json,re
from .generic_types import type_parts
from .project import text


def proven_read(project,site):
    """Abstract Spring Data reads require a bounded declaration/query proof."""
    node=project.nodes[site];meta=project.methods[node['method']]
    receiver=node.get('receiver_type')
    if not isinstance(receiver,str) or not isinstance(node.get('arg_count'),int):return False
    owner=project.resolve_type(receiver,meta['module'],meta['file'])
    if owner is None:return False
    def standard(name,fqn,context):
        if project.resolve_type(name,context['module'],context['file']):return False
        if name==fqn:return True
        if name!=fqn.rsplit('.',1)[-1]:return False
        imports=[match[1] for n in project.trees[context['file']].root_node.named_children if n.type=='import_declaration'
                 for match in [re.search(r'\bimport\s+([\w.*]+)\s*;',text(n))] if match]
        explicit=[name for name in imports if name.rsplit('.',1)[-1]==fqn.rsplit('.',1)[-1]]
        return explicit==[fqn] or not explicit and (fqn.startswith('java.lang.') or fqn.rsplit('.',1)[0]+'.*' in imports)
    pending=[owner];seen=set();repository=False
    while pending:
        current=pending.pop()
        if current in seen:continue
        seen.add(current);context=project.nodes[current]
        for written in project.generic_parents.get(current,()):
            base,_=type_parts(written)
            parent=project.resolve_type(base,context['module'],context['file'])
            if parent:pending.append(parent);continue
            for fqn in ('org.springframework.data.jpa.repository.JpaRepository','org.springframework.data.repository.CrudRepository',
                        'org.springframework.data.mongodb.repository.MongoRepository'):
                repository |= standard(base,fqn,context)
    if not repository:return False
    name=node.get('callee') or ''
    declared=[mid for mid in project.inherited_methods(owner,name,node.get('arg_count',0))]
    explicit_read=False
    for mid in declared:
        method=project.methods[mid]
        if not method.get('abstract'):return False
        for annotation in method.get('annotations',[]):
            if standard(annotation['name'],'java.lang.Override',method):continue
            if not standard(annotation['name'],'org.springframework.data.jpa.repository.Query',method):return False
            literal=re.fullmatch(r'\(\s*(?:value\s*=\s*)?("(?:\\.|[^"\\])*")(?:\s*,\s*nativeQuery\s*=\s*(?:true|false))?\s*\)',annotation.get('args',''))
            if not literal:return False
            try:query=json.loads(literal[1])
            except ValueError:return False
            parsed=project.repository_queries.get((project.nodes[method['owner']]['fqn'],name))
            # Only a complete, function-free single-table SELECT whose where
            # predicates were parsed by the existing bounded query model.
            if parsed is None or not re.fullmatch(r'\s*(?:select\s+(?:\*|[\w$]+(?:\.\*)?)\s+)?from\s+[\w.$]+(?:\s+(?:as\s+)?(?!where\b)[\w$]+)?(?:\s+where\s+.+)?\s*',query,re.I):return False
            explicit_read=True
    return explicit_read or name in ('findAll','findAllById','findById','count','existsById','getOne','getById','getReferenceById') or bool(
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
        if accessed and not proven_read(project,site):
            writes.update(accessed)
    # A graph-only data edge without an operation witness remains a possible write.
    result=writes | (resources-observed)
    cache[key]=result
    return result
