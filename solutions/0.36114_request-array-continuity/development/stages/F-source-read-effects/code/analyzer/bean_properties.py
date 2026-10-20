"""Source-derived default Jackson 2 properties, without executing bean code."""
from collections import defaultdict
from .project import text,walk,keywords,declaration_matches
from .generic_types import type_parts


def annotations(node):
    mods=next((n for n in node.named_children if n.type=='modifiers'),None)
    return [(text(n.child_by_field_name('name')),text(n.child_by_field_name('arguments')))
            for n in mods.named_children if n.type in ('annotation','marker_annotation')] if mods else []


def declaration(project,owner):
    meta=project.nodes[owner];tree=project.trees.get(meta.get('file'))
    if tree is None:return None
    found=[n for n in walk(tree.root_node) if n.type in ('class_declaration','interface_declaration','enum_declaration','record_declaration')
           and declaration_matches(n,meta['fqn'])]
    if '$' not in meta['fqn'].rsplit('.',1)[-1]:
        found=[n for n in found if not any(p.type in ('class_declaration','interface_declaration','enum_declaration') for p in parents(n))]
    return found[0] if len(found)==1 else None


def parents(node):
    node=node.parent
    while node is not None:
        yield node;node=node.parent


def legacy_name(name,issue):
    if not name:return None
    if not name.isascii():issue('non-ASCII JavaBeans property naming is not modeled');return None
    for index,char in enumerate(name):
        if char.lower()==char:return name[:index].lower()+name[index:]
    return name.lower()


def default_bean_plan(project,owner,direction,standard_type):
    assert direction in ('serialize','deserialize')
    cache=project.__dict__.setdefault('_default_bean_plan_cache',{})
    key=owner,direction
    if key in cache:return cache[key]
    node=declaration(project,owner)
    if node is not None and node.type=='record_declaration':
        from .records import bean_plan
        cache[key]=bean_plan(project,owner,node)
        return cache[key]
    issues=set();issue=issues.add;fields={};all_fields=defaultdict(list);ignore_flags=defaultdict(set)
    getters=defaultdict(list);setters=defaultdict(list);accessors=defaultdict(list);classes={};levels={};pending=[(owner,0)]
    methods=project.__dict__.get('_bean_methods_by_owner')
    if methods is None:
        methods=defaultdict(list)
        for mid,meta in project.methods.items():methods[meta['owner']].append(mid)
        project._bean_methods_by_owner=methods
    while pending:
        current,depth=pending.pop(0)
        if current in levels:continue
        levels[current]=depth
        node=declaration(project,current)
        if node is None:issue('bean source declaration is unavailable: '+str(current));continue
        classes[current]=node;meta=project.nodes[current]
        for parent in project.framework_types.get(current,()):
            base,_=type_parts(parent)
            if project.resolve_type(base,meta['module'],meta['file']):continue
            if not any(standard_type(base,native,meta) for native in
                       ('java.lang.Object','java.io.Serializable','java.lang.Cloneable','java.lang.Comparable','org.springframework.security.core.userdetails.UserDetails')):
                issue('external bean parent introspection is not modeled: '+base)
        pending.extend((parent,depth+1) for parent in sorted(project.type_parents.get(current,())))
    def external(name,fqn,context):return standard_type(name,fqn,context)
    def jackson_notes(node,context):
        for name,args in annotations(node):
            leaf=name.rsplit('.',1)[-1]
            if not external(name,'com.fasterxml.jackson.annotation.'+leaf,context) and not external(name,'com.fasterxml.jackson.databind.annotation.'+leaf,context):continue
            if leaf=='JsonIgnoreProperties' and args.replace(' ','')=='(ignoreUnknown=true)':continue
            if leaf=='JsonIgnore' and args.replace(' ','') in ('','()','(true)','(value=true)','(false)','(value=false)'):continue
            if direction=='serialize' and leaf=='JsonCreator':continue
            issue('Jackson annotation is not modeled in bean plan: '+name)
    def ignore(node,context):
        values=[args.replace(' ','') for name,args in annotations(node)
                if external(name,'com.fasterxml.jackson.annotation.JsonIgnore',context)]
        return None if not values else values[0] not in ('(false)','(value=false)')
    def ignore_property(name,marker):
        if marker is not None:ignore_flags[name].add(marker)
    def lombok(node,context):
        found={}
        for name,args in annotations(node):
            leaf=name.rsplit('.',1)[-1]
            package='lombok.experimental.' if leaf in ('Accessors','NonFinal','PackagePrivate','Tolerate') else 'lombok.'
            if not external(name,package+leaf,context):continue
            found[leaf]=args
            if leaf=='Accessors':issue('Lombok Accessors policy is not modeled')
            if leaf in ('Data','Value','RequiredArgsConstructor','AllArgsConstructor') and args not in ('','()'):
                issue('Lombok constructor annotation options are not modeled: '+leaf)
        return found
    def access(args,default):
        if args is None:return default
        value=args.strip('() ').removeprefix('value=').strip()
        if not value:return 'PUBLIC'
        level=value.rsplit('.',1)[-1]
        if level not in ('PUBLIC','PROTECTED','PRIVATE','PACKAGE','MODULE','NONE'):
            issue('Lombok accessor annotation options are not modeled');return 'NONE'
        return level
    def prop(kind,member,declared,typ,non_null=False):
        return {'kind':kind,'member':member,'owner':declared,'type':typ,'non_null':non_null}
    lombok_seen=False;lombok_classes={};source_fields={}
    for current,node in classes.items():
        meta=project.nodes[current];depth=levels[current]
        jackson_notes(node,meta)
        generated=lombok(node,meta);lombok_classes[current]=generated;lombok_seen|=bool(generated)
        body=node.child_by_field_name('body');own_fields={}
        for field in body.named_children if body else []:
            if field.type=='block' and not any(project.ast.get(mid) is not None and not project.parameters(mid)
                    for mid in methods.get(current,()) if project.methods[mid]['name']=='<init>'):
                issue('implicit JSON instance initializer needs a source construction context')
            if field.type!='field_declaration' or 'static' in keywords(field):continue
            jackson_notes(field,meta);flags=keywords(field);field_lombok=lombok(field,meta)
            if 'Value' in generated:
                if 'NonFinal' not in field_lombok:flags.add('final')
            lombok_seen|=bool(field_lombok)
            for var in field.named_children:
                if var.type!='variable_declarator':continue
                name=text(var.child_by_field_name('name'));typ=text(field.child_by_field_name('type'))
                ignore_property(name,ignore(field,meta))
                info={'name':name,'type':typ,'owner':current,'depth':depth,'flags':flags,'initialized':var.child_by_field_name('value') is not None,
                      'lombok':field_lombok,'non_null':'NonNull' in field_lombok}
                own_fields[name]=info;all_fields[name].append(info)
                if name not in fields or depth<fields[name]['depth']:fields[name]=info
                elif depth==fields[name]['depth'] and current!=fields[name]['owner']:issue('inherited field conflict is not modeled: '+name)
        source_fields[current]=own_fields
        if node.type=='interface_declaration' or 'abstract' in keywords(node):
            if current==owner and direction=='serialize':issue('abstract bean runtime implementation is unobserved')
        own_methods=[];missing_methods=[]
        source_methods=[n for n in body.named_children if n.type=='method_declaration'] if body else []
        for mid in methods.get(current,()):
            source=project.ast.get(mid);m=project.methods[mid]
            if source is None:
                # Generated accessors are derived from their actual annotations below.
                if m['name'].startswith(('get','is','set')):missing_methods.append((mid,m))
                continue
            own_methods.append((mid,m,source))
            jackson_notes(source,m)
            for par in (source.child_by_field_name('parameters').named_children if source.child_by_field_name('parameters') else []):
                jackson_notes(par,m)
                if any(external(a,'lombok.NonNull',m) for a,_ in annotations(par)):
                    issue('generated parameter NonNull checks in source methods are not modeled')
            flags=keywords(source)
            if source.parent is not None and source.parent.parent is not None and source.parent.parent.type=='interface_declaration' and 'private' not in flags:flags.add('public')
            if 'static' in flags:continue
            if m['name']=='<init>':
                if ignore(source,m):issue('ignored JSON constructor selection is not modeled')
                continue
            pars=project.parameters(mid);name=m['name'];ret=m.get('return_raw','')
            source_pars=[n for n in source.child_by_field_name('parameters').named_children if n.type in ('formal_parameter','spread_parameter')]
            if len(source_pars)!=len(pars):
                if name.startswith('set'):issue('varargs JSON setter binding is not modeled: '+name)
                continue
            if source.child_by_field_name('body') is None and name.startswith(('get','is','set')):
                issue('bean accessor implementation is unavailable: '+name)
            if len(pars)==1 and name.startswith('set'):
                wire=legacy_name(name[3:],issue)
                if wire:
                    ignore_property(wire,ignore(source,m))
                    setters[wire].append((depth,0,prop('method',mid,current,pars[0][1])))
            if not pars and 'public' in flags and ret!='void' and not external(ret,'java.lang.Void',m):
                prefix='get' if name.startswith('get') else 'is' if name.startswith('is') else None
                if prefix=='is' and not (ret=='boolean' or external(ret,'java.lang.Boolean',m)):
                    if ret in project.type_variables.get(current,{}) or '<' in text(source.child_by_field_name('type_parameters')):
                        issue('is-getter type-variable erasure is not modeled: '+name)
                    continue
                if prefix:
                    wire=legacy_name(name[len(prefix):],issue)
                    if wire:
                        ignore_property(wire,ignore(source,m))
                        getters[wire].append((depth,0 if prefix=='get' else 1,prop('method',mid,current,ret)))
        for name,info in own_fields.items():
            opts=info['lombok'];has_get='Getter' in opts or 'Getter' in generated or 'Data' in generated or 'Value' in generated
            has_set='Setter' in opts or 'Setter' in generated or 'Data' in generated
            get_access=access(opts.get('Getter',generated.get('Getter')), 'PUBLIC' if has_get else 'NONE')
            set_access=access(opts.get('Setter',generated.get('Setter')), 'PUBLIC' if has_set else 'NONE')
            if not name.isascii():
                if has_get or has_set:issue('non-ASCII Lombok accessor naming is not modeled')
                continue
            boolean=info['type']=='boolean'
            is_prefix=boolean and name.startswith('is') and len(name)>2 and not name[2].islower()
            stem=name[2:] if is_prefix else name[0].upper()+name[1:]
            getter=('is' if boolean else 'get')+stem;setter='set'+stem
            # Lombok suppresses generation by name and arity, including static methods.
            def exists(names,count):
                for source in source_methods:
                    if text(source.child_by_field_name('name')).lower() not in {n.lower() for n in names}:continue
                    if any(external(a,'lombok.experimental.Tolerate',meta) for a,_ in annotations(source)):continue
                    pars=[n for n in source.child_by_field_name('parameters').named_children if n.type in ('formal_parameter','spread_parameter')]
                    spread=any(n.type=='spread_parameter' for n in pars)
                    if len(pars)==count or spread and count>=len(pars)-1:return True
                return False
            stems={name[0].upper()+name[1:],stem}
            getter_names={prefix+s for s in stems for prefix in ('get','is')} if boolean else {getter}
            setter_names={'set'+s for s in stems} if boolean else {setter}
            if get_access!='NONE' and not exists(getter_names,0):
                if name in ignore_flags:issue('Lombok Jackson annotation copying is not modeled: '+name)
                accessor=prop('generated',name,current,info['type'])
                accessors[(getter,0)].append((depth,0,accessor))
                wire=legacy_name(getter[2:] if boolean else getter[3:],issue)
                if wire and get_access=='PUBLIC':getters[wire].append((depth,1 if boolean else 0,accessor))
            if has_set and set_access!='NONE' and 'final' not in info['flags'] and not exists(setter_names,1):
                if name in ignore_flags:issue('Lombok Jackson annotation copying is not modeled: '+name)
                accessor=prop('generated',name,current,info['type'],info['non_null'])
                accessors[(setter,1)].append((depth,0,accessor))
                wire=legacy_name(setter[3:],issue)
                if wire:setters[wire].append((depth,0,accessor))
        for mid,m in missing_methods:
            candidates=accessors.get((m['name'],len(m.get('params_as_written',()))),())
            if not any(p['owner']==current for _,_,p in candidates):
                issue('bean method source body is unavailable: '+m['name'])
    if lombok_seen:
        present=project.__dict__.get('_bean_lombok_config_present')
        if present is None:
            present=any(project.root.rglob('lombok.config'));project._bean_lombok_config_present=present
        if present:issue('observed lombok.config policy is not modeled')
    for name,items in all_fields.items():
        if len({item['owner'] for item in items})>1:
            issue('hidden Java fields need separate declaring-class storage: '+name)
    def select(candidates,label):
        if not candidates:return None
        best=min((depth,rank) for depth,rank,_ in candidates)
        selected=[p for depth,rank,p in candidates if (depth,rank)==best]
        if len(selected)!=1:
            issue('overloaded or conflicting bean '+label+' selection is not modeled');return None
        p=selected[0]
        if p['kind']=='method' and project.methods[p['member']].get('abstract'):
            issue('abstract bean accessor requires a concrete implementation');return None
        return p
    selected_getters={name:select(items,'getter '+name) for name,items in getters.items()}
    selected_setters={name:select(items,'setter '+name) for name,items in setters.items()}
    for name,flags in ignore_flags.items():
        if len(flags)>1:issue('conflicting inherited JsonIgnore overrides are not modeled: '+name)
    ignored={name for name,flags in ignore_flags.items() if True in flags}
    result={};getter_only={}
    for name in sorted(set(fields)|set(getters)|set(setters)):
        if name in ignored:continue
        f=fields.get(name);getter=selected_getters.get(name);setter=selected_setters.get(name)
        field=prop('field',name,f['owner'],f['type']) if f and 'transient' not in f['flags'] and ('public' in f['flags'] or direction=='deserialize' and getter is not None) else None
        if direction=='serialize':chosen=getter or field
        else:
            chosen=setter or field
            if chosen is None and getter is not None and any(standard_type(type_parts(getter['type'])[0],
                    'java.util.'+native,project.nodes[getter['owner']]) for native in ('Map','List','Set','Collection')):
                getter_only[name]=getter
        if chosen is not None:result[name]=chosen
    construction={'kind':'implicit','member':None,'owner':owner}
    if direction=='deserialize':
        if owner in project.json_construction_limits:
            construction['kind']='unsupported';issue(project.json_construction_limits[owner])
        ctors=[mid for mid in methods.get(owner,()) if project.methods[mid]['name']=='<init>' and project.ast.get(mid) is not None]
        source_ctor=any(n.type=='constructor_declaration' for n in classes[owner].child_by_field_name('body').named_children) if owner in classes else False
        if source_ctor and not ctors:issue('declared constructor source binding is unavailable')
        noarg=[mid for mid in ctors if not any(n.type in ('formal_parameter','spread_parameter')
               for n in project.ast[mid].child_by_field_name('parameters').named_children)]
        if construction['kind']!='unsupported':
            if len(noarg)==1:construction.update(kind='source',member=noarg[0])
            elif len(noarg)>1:construction['kind']='unsupported';issue('multiple noarg constructors are not modeled')
            else:
                gen=lombok_classes.get(owner,{});own=source_fields.get(owner,{})
                required=any(not f['initialized'] and ('final' in f['flags'] or f['non_null']) for f in own.values())
                if 'NoArgsConstructor' in gen:
                    if gen['NoArgsConstructor'] not in ('','()'):
                        issue('NoArgsConstructor options are not modeled');construction['kind']='unsupported'
                    elif any('final' in f['flags'] and not f['initialized'] for f in own.values()):
                        issue('NoArgsConstructor final-field policy is not modeled');construction['kind']='unsupported'
                    else:construction['kind']='generated'
                elif ctors:construction['kind']='missing'
                elif 'Builder' in gen:
                    issue('Builder constructor generation is not modeled');construction['kind']='unsupported'
                elif ('AllArgsConstructor' in gen or 'Value' in gen) and own or ('Data' in gen or 'RequiredArgsConstructor' in gen) and required:
                    construction['kind']='missing'
                elif gen.keys() & {'Data','RequiredArgsConstructor','AllArgsConstructor','Value'}:construction['kind']='generated'
        for current,node in classes.items():
            if current==owner:continue
            if any(project.ast.get(mid) is not None for mid in methods.get(current,()) if project.methods[mid]['name']=='<init>'):
                issue('JSON superclass constructor chaining is not modeled')
    selected_accessors={key:select(items,'generated accessor '+key[0]) for key,items in accessors.items()}
    plan={'properties':result,'constructor':construction,'generated_accessors':selected_accessors,'ignored_properties':tuple(sorted(ignored)),
          'issues':tuple(sorted(issues)),'complete':not issues,'getter_only_properties':getter_only}
    cache[key]=plan
    return plan


def generated_accessor(project,owner,name,count,standard_type):
    if owner not in project.type_fields:return None
    plan=default_bean_plan(project,owner,'serialize',standard_type)
    return plan['generated_accessors'].get((name,count)) if plan['complete'] else None
