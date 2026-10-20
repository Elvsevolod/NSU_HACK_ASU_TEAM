"""Read/write classification for source-backed fallback closures."""


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
        operation=node.get('callee','')
        if not operation.startswith(('find','query','get','read','exists','count','select','stream')):
            writes.update(accessed)
    # A graph-only data edge without an operation witness remains a possible write.
    result=writes | (resources-observed)
    cache[key]=result
    return result
