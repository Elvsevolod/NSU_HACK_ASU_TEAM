"""Prepare source-only benchmark skeletons, never expected execution labels.

The output edges are deliberately marked May. This utility is benchmark input
preparation, not a new capability of the assessed analyzer.
"""
import hashlib
import json
import re
import shutil
from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_java

BASE = Path(__file__).resolve().parent
TYPE_KINDS = {'class_declaration', 'interface_declaration', 'enum_declaration', 'record_declaration'}


def text(node):
    return node.text.decode() if node else ''


def walk(node):
    yield node
    for child in node.named_children:
        yield from walk(child)


def annotations(node):
    mods = next((child for child in node.named_children if child.type == 'modifiers'), None)
    return [{'name':text(a.child_by_field_name('name')), 'args':text(a.child_by_field_name('arguments'))}
            for a in mods.named_children if a.type in ('annotation', 'marker_annotation')] if mods else []


def flat_scalars(path):
    """Only plain scalar mappings needed by these pinned configuration files."""
    stack = []
    for line_no,line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith(('#', '-')):
            continue
        found = re.match(r'^( *)([\w.-]+):(?:\s+(.*))?$', line)
        if not found:
            continue
        indent,key,value = len(found[1]),found[2],found[3]
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not value:
            stack.append((indent,key))
        else:
            yield '.'.join([key for _,key in stack]+[key]),value.strip('"\''),line_no


def prepare(label):
    origin = json.loads((BASE/'sources'/f'{label}.origin.json').read_text())
    original = next((BASE/'sources'/label).iterdir())
    package = BASE/'packages'/label
    source = package/'source'
    source.mkdir(parents=True, exist_ok=False)
    selected = [p for p in original.rglob('*') if p.is_file() and
                ('/src/main/' in str(p) or p.name == 'pom.xml' or p.name.upper().startswith(('LICENSE','NOTICE')))]
    for path in selected:
        target = source/path.relative_to(original)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path,target)
    parser = Parser(Language(tree_sitter_java.language()))
    nodes,edges,types,methods,calls,configs = {},[],{}, {},[],[]
    for path in sorted(source.rglob('*.java')):
        file = path.relative_to(source).as_posix()
        module = file.split('/')[0]
        tree = parser.parse(path.read_bytes())
        assert not tree.root_node.has_error, file
        package_name = next((text(n).removeprefix('package').strip(' ;\n') for n in tree.root_node.named_children if n.type == 'package_declaration'), '')
        nodes.setdefault('module:'+module, {'kind':'module','name':module,'deployment_units':[module]})
        for declaration in walk(tree.root_node):
            if declaration.type not in TYPE_KINDS:
                continue
            names = [text(declaration.child_by_field_name('name'))]
            parent = declaration.parent
            while parent:
                if parent.type in TYPE_KINDS:
                    names.append(text(parent.child_by_field_name('name')))
                parent = parent.parent
            fqn = package_name+'.'+'$'.join(reversed(names))
            tid = 'type:'+module+':'+fqn
            nodes[tid] = {'kind':'type','fqn':fqn,'module':module,'file':file,
                          'line':declaration.start_point.row+1,'end':declaration.end_point.row+1,
                          'annotations':annotations(declaration)}
            types[tid] = declaration
            body = declaration.child_by_field_name('body')
            fields = {}
            for member in body.named_children if body else []:
                if member.type == 'field_declaration':
                    for var in member.named_children:
                        if var.type == 'variable_declarator':
                            fields[text(var.child_by_field_name('name'))] = text(member.child_by_field_name('type'))
            for member in body.named_children if body else []:
                if member.type not in ('method_declaration','constructor_declaration'):
                    continue
                params = member.child_by_field_name('parameters')
                written = [text(p.child_by_field_name('type')) for p in params.named_children if p.type in ('formal_parameter','spread_parameter')]
                name = '<init>' if member.type == 'constructor_declaration' else text(member.child_by_field_name('name'))
                mid = f'method:{module}:{fqn}#{name}('+','.join(written)+')'
                assert mid not in nodes, mid
                nodes[mid] = {'kind':'method','name':name,'owner':tid,'module':module,'file':file,
                              'line':member.start_point.row+1,'end':member.end_point.row+1,
                              'params_as_written':written,'abstract':member.child_by_field_name('body') is None,
                              'annotations':annotations(member)}
                methods[mid] = member
                locals_ = {text(p.child_by_field_name('name')):text(p.child_by_field_name('type')) for p in params.named_children if p.type in ('formal_parameter','spread_parameter')}
                locals_.update(fields)
                for call in walk(member.child_by_field_name('body')) if member.child_by_field_name('body') else []:
                    if call.type not in ('method_invocation','object_creation_expression'):
                        continue
                    callee = '<init>' if call.type == 'object_creation_expression' else text(call.child_by_field_name('name'))
                    where = call.child_by_field_name('name') or call
                    args = call.child_by_field_name('arguments')
                    receiver = text(call.child_by_field_name('object'))
                    raw_type = text(call.child_by_field_name('type')) if callee == '<init>' else locals_.get(receiver.removeprefix('this.'), '')
                    cid = f'call:{module}:{file}:{where.start_point.row+1}:{where.start_point.column+1}:{callee}'
                    if cid in nodes:
                        continue
                    nodes[cid] = {'kind':'call_site','method':mid,'module':module,'file':file,
                                  'line':where.start_point.row+1,'col':where.start_point.column+1,
                                  'callee':callee,'arg_count':len(args.named_children) if args else 0,
                                  'receiver':receiver,'receiver_type':raw_type}
                    calls.append(cid)
    for module in [n['name'] for n in nodes.values() if n['kind']=='module']:
        resource = source/module/'src/main/resources'
        for path in sorted(resource.glob('application.y*ml')):
            for key,value,line in flat_scalars(path):
                if key.startswith(('spring.application.', 'spring.datasource.', 'server.', 'lms.')):
                    cid = 'config:'+module+':'+key
                    nodes[cid] = {'kind':'config_entry','module':module,'key':key,'value':value,'file':path.relative_to(source).as_posix(),'line':line}
                    configs.append(cid)
                    if key == 'spring.application.name':
                        nodes['module:'+module]['deployment_units'] = [value]
    resources = {}
    for tid,declaration in types.items():
        anns = nodes[tid]['annotations']
        persistent = next((a for a in anns if a['name'].split('.')[-1] in ('Entity','Document')), None)
        if not persistent:
            continue
        explicit = next((a for a in anns if a['name'].split('.')[-1] == 'Table'), persistent)
        found = re.search(r'\b(?:name|collection)\s*=\s*"([^"]+)"', explicit['args'])
        name = found[1] if found else re.sub(r'(?<!^)(?=[A-Z])','_',nodes[tid]['fqn'].split('.')[-1]).lower()
        module = nodes[tid]['module']
        rid = 'res:table:'+module+'.'+name
        nodes[rid] = {'kind':'data_resource','resource_type':'table','name':name,'schema':module,'module':module,
                      'storage':'mongodb_collection' if persistent['name'].split('.')[-1] == 'Document' else 'jpa_table',
                      'origin':[{'file':nodes[tid]['file'],'line':nodes[tid]['line']}]}
        resources[tid] = rid
    # Name/arity candidates are May edges, never observed execution or labels.
    for cid in calls:
        call = nodes[cid]
        for mid,node in list(nodes.items()):
            if node['kind'] != 'method' or len(node['params_as_written']) != call['arg_count']:
                continue
            owner = nodes[node['owner']]
            if node['name'] == call['callee'] and (node['module'] == call['module'] or call['receiver_type'].split('.')[-1] == owner['fqn'].split('.')[-1]):
                edges.append({'source':cid,'type':'calls','target':mid,'evidence':'source-name-arity-may'})
        if re.match(r'^(?:find|save|delete|exists|count|update)',call['callee']) and 'repositor' in call['receiver'].lower():
            for tid,rid in resources.items():
                if nodes[tid]['module'] == call['module']:
                    edges.append({'source':cid,'type':'data_access','target':rid,'evidence':'same-module-repository-may'})
    skeleton = {'project':label,'nodes':nodes,'edges':edges,
                'context':{'clock':'2026-10-19T12:00:00'},
                'preparation_scope':'Production Java declarations/config and broad source-name/arity May edges. No inference results, scenario labels, or observed execution used. Generated framework controllers and anonymous class methods are not expanded.'}
    (package/'skeleton.json').write_text(json.dumps(skeleton,ensure_ascii=False,indent=2)+'\n')
    files = {p.relative_to(package).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(package.rglob('*')) if p.is_file()}
    record = {'origin':origin,'source_files':len(selected),'types':len(types),'methods':len(methods),'call_sites':len(calls),'data_resources':len(resources),
              'source_only':True,'inference_run':False,'files':files}
    (package/'source-freeze.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in record.items() if k not in ('origin','files')}),flush=True)


if __name__ == '__main__':
    for selected_project in ('organization','library'):
        prepare(selected_project)
