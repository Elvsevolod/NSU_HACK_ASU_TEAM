"""Source-owned generic descriptors; bindings never contain scenario values."""
import re


def type_parts(written):
    written=re.sub(r'\s+','',written)
    if '<' not in written:return written,[]
    base,tail=written.split('<',1)
    if not tail.endswith('>'):return base,None
    result,start,depth=[],0,0
    for index,char in enumerate(tail[:-1]):
        if char=='<':depth+=1
        elif char=='>':depth-=1
        elif char==',' and depth==0:result.append(tail[start:index]);start=index+1
        if depth<0:return base,None
    result.append(tail[start:-1])
    return base,result if depth==0 and all(result) else None


def resolve(written,context,bindings):
    seen=set()
    for _ in range(64):
        if written not in bindings:return written,context,bindings
        key=(written,id(bindings))
        if key in seen:break
        seen.add(key)
        written,context,bindings=bindings[written]
    return '',context,{}


def bind_parameters(project,owner,arguments,context,bindings):
    variables=project.type_variables.get(owner,{})
    if arguments is None or arguments and len(arguments)!=len(variables):return None
    if arguments:return {name:(arg,context,bindings) for name,arg in zip(variables,arguments)}
    local={}
    # Raw types use declared bounds, not a class guessed from the variable's
    # spelling. Bounds may refer to other parameters in this same scope.
    local.update((name,(bound or '',project.nodes[owner],local)) for name,bound in variables.items())
    return local


def inheritance_path(project,owner,declared):
    cache=project.__dict__.setdefault('_generic_inheritance_paths',{})
    key=(owner,declared)
    if key in cache:return cache[key]
    paths=[];visits=0;invalid=False
    def visit(current,path,active):
        nonlocal visits,invalid
        visits+=1
        if current in active or len(path)>=64 or visits>4096:invalid=True;return
        if current==declared:paths.append(path)
        meta=project.nodes[current]
        for written in project.generic_parents.get(current,()):
            base,_=type_parts(written)
            if base in project.type_variables.get(current,{}):invalid=True;continue
            parent=project.resolve_type(base,meta['module'],meta['file'])
            if parent:visit(parent,[*path,(parent,written)],active|{current})
            if invalid:return
    visit(owner,[],set())
    cache[key]=paths[0] if not invalid and len(paths)==1 else None
    return cache[key]


def declaring_bindings(project,owner,declared,bindings):
    path=inheritance_path(project,owner,declared)
    if path is None:return None
    current=owner
    for parent,written in path:
        _,arguments=type_parts(written)
        bindings=bind_parameters(project,parent,arguments,project.nodes[current],bindings)
        if bindings is None:return None
        current=parent
    return bindings
