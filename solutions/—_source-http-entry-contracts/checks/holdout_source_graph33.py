"""Test-input extraction only: source declarations and conservative may-call facts.

This does not infer scenario execution, run Java, read expected answers or add
target business rules to the submitted analyzer. The ready skeleton is an input.
"""
from collections import defaultdict
import hashlib
import json
import re
from pathlib import Path
from tree_sitter import Language,Parser
import tree_sitter_java


def text(node):return node.text.decode() if node is not None else ''


def walk(node):
    yield node
    for child in node.named_children:yield from walk(child)


def annotations(node):
    mods=next((n for n in node.named_children if n.type=='modifiers'),None)
    return [{'name':text(n.child_by_field_name('name')),'args':text(n.child_by_field_name('arguments'))}
        for n in mods.named_children if n.type in ('annotation','marker_annotation')] if mods else []


def snake(name):return re.sub(r'(?<!^)([A-Z])',r'_\1',name).lower()


def extract(root,modules,project,context,schemas):
    parser=Parser(Language(tree_sitter_java.language()));nodes={};edges=[];sources={};trees={};declarations={};methods={};imports={};packages={}
    short=defaultdict(list);file_modules={};diagnostics=[]
    for module in modules:
        nodes['module:'+module]={'kind':'module','name':module,'deployment_units':[module]}
        for path in sorted((root/module/'src/main/java').rglob('*.java')):
            file=path.relative_to(root).as_posix();data=path.read_bytes();tree=parser.parse(data)
            assert not tree.root_node.has_error,file
            trees[file]=tree;sources[file]=hashlib.sha256(data).hexdigest();file_modules[file]=module
            packages[file]=next((text(n).removeprefix('package').strip(' ;\n') for n in tree.root_node.named_children if n.type=='package_declaration'),'')
            imports[file]=[text(n).removeprefix('import').strip(' ;\n') for n in tree.root_node.named_children if n.type=='import_declaration' and not text(n).startswith('import static')]
            for decl in walk(tree.root_node):
                if decl.type not in ('class_declaration','interface_declaration','enum_declaration','record_declaration'):continue
                names=[];current=decl
                while current is not None:
                    if current.type in ('class_declaration','interface_declaration','enum_declaration','record_declaration'):names.append(text(current.child_by_field_name('name')))
                    current=current.parent
                fqn=(packages[file]+'.' if packages[file] else '')+'$'.join(reversed(names));tid='type:'+module+':'+fqn
                nodes[tid]={'kind':'type','fqn':fqn,'module':module,'file':file,'line':decl.start_point.row+1,'annotations':annotations(decl)}
                declarations[tid]=decl;short[module,fqn.rsplit('.',1)[-1]].append(tid)
    def resolve(written,module,file):
        written=re.sub(r'<.*>|\[\]|\?\s*(?:extends|super)?\s*','',written).strip()
        exact=[key for key,row in nodes.items() if row['kind']=='type' and row['fqn']==written]
        if len(exact)==1:return exact[0]
        names=[name for name in imports[file] if name.endswith('.'+written)]
        names+=[packages[file]+'.'+written]+[name[:-1]+written for name in imports[file] if name.endswith('.*')]
        found=[key for key,row in nodes.items() if row['kind']=='type' and row['fqn'] in names]
        if len(set(found))==1:return found[0]
        found=short.get((module,written),[])
        return found[0] if len(found)==1 else None
    by_owner=defaultdict(list);by_name=defaultdict(list);fields={};parents=defaultdict(list)
    for tid,decl in declarations.items():
        meta=nodes[tid];body=decl.child_by_field_name('body');fields[tid]={}
        for part in decl.named_children:
            if part.type in ('superclass','super_interfaces','extends_interfaces'):
                for raw in re.findall(r'[\w.]+(?:\s*<[^;{}]+>)?',text(part).removeprefix('extends').removeprefix('implements')):
                    parent=resolve(raw,meta['module'],meta['file'])
                    if parent:
                        parents[tid].append(parent);edges.append({'source':tid,'type':'implements' if part.type=='super_interfaces' else 'extends','target':parent})
        for node in body.named_children if body else []:
            if node.type=='field_declaration':
                for var in node.named_children:
                    if var.type=='variable_declarator':fields[tid][text(var.child_by_field_name('name'))]=text(node.child_by_field_name('type'))
            if node.type not in ('method_declaration','constructor_declaration'):continue
            name='<init>' if node.type=='constructor_declaration' else text(node.child_by_field_name('name'))
            pars=[text(n.child_by_field_name('type'))+('...' if n.type=='spread_parameter' else '') for n in node.child_by_field_name('parameters').named_children if n.type in ('formal_parameter','spread_parameter')]
            mid='method:'+meta['module']+':'+meta['fqn']+'#'+name+'('+','.join(pars)+')'
            nodes[mid]={'kind':'method','name':name,'owner':tid,'module':meta['module'],'file':meta['file'],
                'line':node.start_point.row+1,'end':node.end_point.row+1,'params_as_written':pars,'abstract':node.child_by_field_name('body') is None,
                'annotations':annotations(node),'return_raw':text(node.child_by_field_name('type'))}
            methods[mid]=node;by_owner[tid].append(mid);by_name[name].append(mid)
    for owner,bases in parents.items():
        for mid in by_owner[owner]:
            for base in bases:
                for target in by_owner[base]:
                    if nodes[mid]['name']==nodes[target]['name'] and nodes[mid]['params_as_written']==nodes[target]['params_as_written']:
                        edges.append({'source':mid,'type':'overrides','target':target})
    entities={}
    for owner,decl in declarations.items():
        meta=nodes[owner]
        if not any(a['name'].rsplit('.',1)[-1]=='Entity' for a in meta['annotations']):continue
        table=next((a for a in meta['annotations'] if a['name'].rsplit('.',1)[-1]=='Table'),None)
        match=re.search(r'\bname\s*=\s*"([^"]+)"',table['args']) if table else None
        name=match[1] if match else snake(meta['fqn'].rsplit('.',1)[-1]);schema=schemas[meta['module']]
        rid='res:table:'+schema+'.'+name
        nodes[rid]={'kind':'data_resource','resource_kind':'table','schema':schema,'name':name,
            'origin':[{'file':meta['file'],'line':decl.start_point.row+1}]};entities[owner]=rid
    repositories={}
    for owner,decl in declarations.items():
        match=re.search(r'(?:JpaRepository|CrudRepository|PagingAndSortingRepository)\s*<\s*([\w.]+)',text(decl).split('{',1)[0])
        if match:
            meta=nodes[owner];entity=resolve(match[1],meta['module'],meta['file'])
            if entity in entities:repositories[owner]=entities[entity]
            else:diagnostics.append('Repository entity/resource unresolved: '+meta['fqn'])
    def inherited(owner):
        pending=[owner];seen=set()
        while pending:
            value=pending.pop()
            if value in seen:continue
            seen.add(value);pending.extend(parents.get(value,()))
        return seen
    for mid,method in methods.items():
        meta=nodes[mid];owner=meta['owner'];variable_types={**fields[owner]}
        pars=method.child_by_field_name('parameters')
        for par in pars.named_children:
            if par.type in ('formal_parameter','spread_parameter'):variable_types[text(par.child_by_field_name('name'))]=text(par.child_by_field_name('type'))
        body=method.child_by_field_name('body')
        if body is None:continue
        for node in walk(body):
            if node.type=='local_variable_declaration':
                for var in node.named_children:
                    if var.type=='variable_declarator':variable_types[text(var.child_by_field_name('name'))]=text(node.child_by_field_name('type'))
            if node.type not in ('method_invocation','object_creation_expression'):continue
            new=node.type=='object_creation_expression';receiver=text(node.child_by_field_name('object'))
            name='<init>' if new else text(node.child_by_field_name('name'));typ=text(node.child_by_field_name('type')) if new else variable_types.get(receiver.removeprefix('this.'),receiver)
            target_owner=owner if not new and receiver in ('','this') else resolve(typ,meta['module'],meta['file'])
            arguments=[n for n in node.child_by_field_name('arguments').named_children if n.type not in ('line_comment','block_comment')]
            name_node=node.child_by_field_name('name') or node;line=name_node.start_point.row+1;column=name_node.start_point.column+1
            cid='call:'+meta['module']+':'+meta['file']+':'+str(line)+':'+str(column)+':'+name
            nodes[cid]={'kind':'call_site','method':mid,'callee':name,'receiver':receiver,'receiver_type':typ,'file':meta['file'],'line':line,'col':column,'arg_count':len(arguments)}
            for target in by_name[name]:
                if target_owner in declarations and nodes[target]['owner'] in inherited(target_owner) and len(nodes[target]['params_as_written'])==len(arguments):
                    edges.append({'source':cid,'type':'calls','target':target})
            if target_owner in repositories:edges.append({'source':cid,'type':'data_access','target':repositories[target_owner]})
    for module in modules:
        for path in sorted((root/module/'src/main/resources').rglob('*.properties')):
            file=path.relative_to(root).as_posix()
            for number,line in enumerate(path.read_text().splitlines(),1):
                stripped=line.strip()
                if not stripped or stripped.startswith(('#','!')):continue
                match=re.fullmatch(r'([\w.\[\]-]+)\s*[=:]\s*(.*)',stripped)
                if not match:diagnostics.append('Properties syntax not extracted: '+file+':'+str(number));continue
                value=match[2]
                if value in ('true','false'):value=value=='true'
                elif re.fullmatch(r'-?\d+',value):value=int(value)
                cid='config:'+module+':'+file+':'+str(number)
                nodes[cid]={'kind':'config_entry','module':module,'file':file,'line':number,'key':match[1],'value':value}
    result={'project':project,'nodes':nodes,'edges':edges,'context':context}
    provenance={'source_sha256':sources,'modules':modules,'schemas':schemas,'diagnostics':diagnostics,
        'graph_scope':'Production source declarations, owner-resolved may calls and repository table facts; no execution or labels.',
        'entity_resources':entities,'repository_resources':repositories,'targets_executed':False,'predictions_read':False}
    return result,provenance
