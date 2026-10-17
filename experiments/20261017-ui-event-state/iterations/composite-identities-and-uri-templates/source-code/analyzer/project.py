"""Source and skeleton indexes. No application code is executed."""
from collections import defaultdict
from pathlib import Path
import re
import json
import warnings

from tree_sitter import Language, Parser
import tree_sitter_java
from baseline_closure import Index, load_json, RouteWarning
from .state import U
from .models import date_value


def text(node):
    return node.text.decode('utf-8') if node is not None else ''


def walk(node):
    yield node
    for child in node.named_children:
        yield from walk(child)


class Project:
    def __init__(self, skeleton, root):
        self.skeleton = load_json(str(skeleton))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always', RouteWarning)
            self.ix = Index(self.skeleton)
        self.route_warnings = list(dict.fromkeys(str(item.message) for item in caught))
        self.nodes = self.ix.N
        self.root = Path(root)
        self.methods = {k: v for k, v in self.nodes.items() if v['kind'] == 'method'}
        self.by_name = defaultdict(list)
        self.trees, self.sources, self.ast, self.source_errors = {}, {}, {}, []
        self.edges = defaultdict(lambda: defaultdict(set))
        self.sites = defaultdict(list)
        self.by_line = defaultdict(list)
        self.enums = {}
        self.enum_objects = {}
        type_names = defaultdict(list)
        qualified_types = defaultdict(list)
        for tid, node in self.nodes.items():
            if node['kind'] == 'type':
                type_names[node['fqn'].split('.')[-1]].append(tid)
                qualified_types[node['fqn']].append(tid)
        self.enum_prefixes = {tid: (tid if len(qualified_types[node['fqn']]) > 1 else node['fqn'] if len(type_names[node['fqn'].split('.')[-1]]) > 1 else node['fqn'].split('.')[-1])
                              for tid, node in self.nodes.items() if node['kind'] == 'type'}
        self.builder_types = {}
        self.all_args_types = {}
        self.constants = {}
        parser = Parser(Language(tree_sitter_java.language()))
        for mid, method in self.methods.items():
            self.by_name[method['name']].append(mid)
            file = method['file']
            if file not in self.trees:
                self.sources[file] = (self.root / file).read_bytes()
                tree = parser.parse(self.sources[file])
                self.trees[file] = tree
                if tree.root_node.has_error:
                    self.source_errors.append(file)
        declarations = {}
        for tid, meta in self.nodes.items():
            if meta['kind'] != 'type' or not meta.get('file', '').endswith('.java'): continue
            file = meta['file']
            tree = self.trees.get(file)
            if tree is None:
                self.sources[file] = (self.root / file).read_bytes()
                tree = parser.parse(self.sources[file])
                self.trees[file] = tree
                if tree.root_node.has_error:
                    self.source_errors.append(file)
            for decl in walk(tree.root_node):
                if decl.type not in ('class_declaration', 'enum_declaration') or text(decl.child_by_field_name('name')) != meta['fqn'].split('.')[-1]: continue
                body = decl.child_by_field_name('body')
                fields = []
                for field in body.named_children if body else []:
                    if field.type != 'field_declaration': continue
                    for var in field.named_children:
                        if var.type != 'variable_declarator': continue
                        name = text(var.child_by_field_name('name'))
                        if re.search(r'\bstatic\b', text(field)):
                            try: self.constants[meta['fqn'].split('.')[-1] + '.' + name] = json.loads(text(var.child_by_field_name('value')))
                            except ValueError: pass
                        else:
                            fields.append((name, text(field.child_by_field_name('type'))))
                modifiers = next((text(c) for c in decl.named_children if c.type == 'modifiers'), '')
                if '@Builder' in modifiers: self.builder_types[meta['fqn']] = fields
                if '@AllArgsConstructor' in modifiers: self.all_args_types[meta['fqn']] = fields
        for file, tree in self.trees.items():
            declarations[file] = [n for n in walk(tree.root_node) if n.type in ('method_declaration', 'constructor_declaration')]
            for node in walk(tree.root_node):
                if node.type == 'enum_declaration':
                    name = text(node.child_by_field_name('name'))
                    owners = [tid for tid in type_names[name] if self.nodes[tid].get('file') == file]
                    if len(owners) != 1:
                        continue
                    enum_tid = owners[0]
                    prefix = self.enum_prefixes[enum_tid]
                    constructors = [n for n in walk(node) if n.type == 'constructor_declaration']
                    for const in walk(node):
                        if const.type == 'enum_constant':
                            args = const.child_by_field_name('arguments')
                            if args and args.named_children:
                                raw = text(args.named_children[0])
                                enum_key = prefix + '.' + text(const.child_by_field_name('name'))
                                if raw.startswith('"'):
                                    self.enum_objects[enum_key] = {'__enum__': enum_key, 'name': json.loads(raw)}
                                if re.fullmatch(r'-?\d+', raw):
                                    self.enums[enum_key] = int(raw)
                                    self.enum_objects[enum_key] = {'__enum__': enum_key, 'code': int(raw)}
                                    if len(args.named_children) > 1 and text(args.named_children[1]).startswith('"'):
                                        self.enum_objects[enum_key]['name'] = json.loads(text(args.named_children[1]))
                                for ctor in constructors:
                                    params = ctor.child_by_field_name('parameters').named_children
                                    if len(params) != len(args.named_children): continue
                                    bindings = {}
                                    for par, arg in zip(params, args.named_children):
                                        try: val = json.loads(text(arg))
                                        except ValueError: val = U
                                        bindings[text(par.child_by_field_name('name'))] = val
                                    obj = {'__enum__': enum_key}
                                    for assignment in walk(ctor):
                                        if assignment.type != 'assignment_expression': continue
                                        lhs = text(assignment.child_by_field_name('left'))
                                        rhs = text(assignment.child_by_field_name('right'))
                                        if lhs.startswith('this.') and rhs in bindings:
                                            obj[lhs[5:]] = bindings[rhs]
                                    self.enum_objects[enum_key] = obj
                                self.enum_objects[enum_key]['__enum_type__'] = enum_tid
        for mid, method in self.methods.items():
            name = method['name'] if method['name'] != '<init>' else self.nodes[method['owner']]['fqn'].split('.')[-1].split('$')[-1]
            matches = [n for n in declarations[method['file']]
                       if text(n.child_by_field_name('name')) == name
                       and n.start_point.row + 1 <= method['line'] <= n.end_point.row + 1
                       and [text(p.child_by_field_name('type')) for p in n.child_by_field_name('parameters').named_children
                            if p.type in ('formal_parameter', 'spread_parameter')]
                           == method.get('params_as_written', [])]
            if matches:
                self.ast[mid] = min(matches, key=lambda n: n.end_byte - n.start_byte)
        for nid, node in self.nodes.items():
            if node['kind'] == 'call_site':
                self.sites[node['method']].append(nid)
                self.by_line[(node['method'], node['line'], node['callee'])].append(nid)
        for edge in self.skeleton['edges']:
            self.edges[edge['source']][edge['type']].add(edge['target'])
        self.repository_queries = {}
        for mid, node in self.ast.items():
            query = re.search(r'@Query\(\s*(?:value\s*=\s*)?"((?:\\.|[^"\\])*)"', text(node), re.S)
            if query:
                owner = self.nodes[self.methods[mid]['owner']]['fqn']
                where = re.search(r'\bwhere\b(.+)', query[1], re.I | re.S)
                predicates = []
                if not re.match(r'\s*(?:select\s+(?:\*|\w+\.?\*)?\s*from|select\s+\w+\s+from|from)\b', query[1], re.I):
                    predicates = None
                elif re.search(r'\b(join|order|group|having|limit|union)\b', query[1], re.I):
                    predicates = None
                elif where:
                    for part in re.split(r'\band\b', where[1], flags=re.I):
                        match = re.fullmatch(r'\s*(?:\w+\.)?(\w+)\s*(=|in)\s*\(?\s*\?(\d+)\s*\)?\s*', part, re.I)
                        if not match:
                            predicates = None
                            break
                        predicates.append(match.groups())
                self.repository_queries[(owner, self.methods[mid]['name'])] = predicates
        self.entities = {}
        self.column_aliases = {}
        self.generated_ids = {}
        self.collections = {}
        for rid, resource in self.nodes.items():
            if resource['kind'] != 'data_resource' or resource.get('collection_of'):
                continue
            files = {o.get('file') for o in resource.get('origin', [])}
            types = [tid for tid, n in self.nodes.items() if n['kind'] == 'type' and n.get('file') in files]
            if len(types) > 1:
                explicit = [tid for tid in types for annotation in self.nodes[tid].get('annotations', [])
                            if annotation['name'].split('.')[-1] == 'Table' and re.search(
                                r'\bname\s*=\s*"' + re.escape(resource['name']) + r'"', annotation.get('args') or '')]
                entities = [tid for tid in types if any(a['name'].split('.')[-1] == 'Entity' for a in self.nodes[tid].get('annotations', []))]
                types = explicit if len(explicit) == 1 else entities
            if len(types) == 1:
                self.entities[rid] = types[0]
            aliases = {}
            collections = []
            for file in sorted(f for f in files if f):
                tree = self.trees.get(file) or parser.parse((self.root / file).read_bytes())
                for field in walk(tree.root_node):
                    if field.type != 'field_declaration': continue
                    collection = re.search(r'@CollectionTable\(\s*name\s*=\s*"([^"]+)".*?@JoinColumn\(\s*name\s*=\s*"([^"]+)"', text(field), re.S)
                    if collection:
                        from .state import camel
                        for var in field.named_children:
                            if var.type == 'variable_declarator':
                                collections.append((text(var.child_by_field_name('name')), collection[1], camel(collection[2])))
                    if '@GeneratedValue' in text(field):
                        for var in field.named_children:
                            if var.type == 'variable_declarator':
                                self.generated_ids[rid] = text(var.child_by_field_name('name'))
                    column = re.search(r'@Column\([^)]*\bname\s*=\s*"([^"]+)"', text(field))
                    if column:
                        from .state import camel
                        for var in field.named_children:
                            if var.type == 'variable_declarator':
                                aliases[camel(column[1])] = text(var.child_by_field_name('name'))
            self.column_aliases[rid] = aliases
            self.collections[rid] = collections
        self.extract_metadata()
        self.extract_element_collections()
        self.custom_http_error_units=set()
        for mid,node in self.ast.items():
            if any(child.type=='method_invocation' and text(child.child_by_field_name('name')) in ('setErrorHandler','errorHandler')
                   for child in walk(node)):
                self.custom_http_error_units.update(self.ix.units.get(self.methods[mid]['module'],()))

    def extract_element_collections(self):
        """Source/skeleton-backed scalar collections, including default JPA names."""
        from .state import camel
        for rid, tid in self.entities.items():
            owner = self.nodes[tid]
            tree = self.trees.get(owner.get('file'))
            keys = self.id_fields.get(rid, [])
            if tree is None or len(keys) != 1:
                continue
            key_column = self.type_fields[tid][keys[0]]['column']
            entity_name = owner['fqn'].split('.')[-1]
            for annotation in owner.get('annotations', []):
                if annotation['name'].split('.')[-1] == 'Entity':
                    explicit = re.search(r'\bname\s*=\s*"([^"]+)"', annotation.get('args') or '')
                    if explicit:
                        entity_name = explicit[1]
            for field in walk(tree.root_node):
                raw = text(field)
                if field.type != 'field_declaration' or '@ElementCollection' not in raw:
                    continue
                typ = text(field.child_by_field_name('type'))
                if not re.fullmatch(r'(?:java\.util\.)?(?:List|Set|Collection)<(?:String|Integer|Long|Double|Float|Boolean)>', typ):
                    continue
                for var in field.named_children:
                    if var.type != 'variable_declarator':
                        continue
                    prop = text(var.child_by_field_name('name'))
                    resources = [n for n in self.nodes.values() if n['kind'] == 'data_resource' and n.get('collection_of') == tid
                                 and any(o.get('file') == owner.get('file') and field.start_point.row + 1 <= o.get('line', 0) <= field.end_point.row + 1
                                         for o in n.get('origin', []))]
                    existing = next((c for c in self.collections.get(rid, []) if c[0] == prop), None)
                    if len(resources) != 1 and existing is None:
                        continue
                    table = resources[0]['name'] if len(resources) == 1 else existing[1]
                    join = re.search(r'@JoinColumn\([^)]*\bname\s*=\s*"([^"]+)"', raw)
                    foreign = camel(join[1] if join else entity_name[:1].lower() + entity_name[1:] + '_' + key_column)
                    column = re.search(r'@Column\([^)]*\bname\s*=\s*"([^"]+)"', raw)
                    value_column = camel(column[1] if column else prop)
                    order = re.search(r'@OrderColumn\b(?:\(([^)]*)\))?', raw)
                    explicit_order = re.search(r'\bname\s*=\s*"([^"]+)"', order[1] or '') if order else None
                    order_column = camel(explicit_order[1] if explicit_order else prop + '_ORDER') if order else None
                    mapping = (prop, table, foreign, value_column, order_column)
                    self.collections[rid] = [c for c in self.collections.get(rid, []) if c[0] != prop] + [mapping]

    def extract_metadata(self):
        """Derive field, enum and datasource contracts from source declarations."""
        self.type_fields, self.enum_members, self.id_fields, self.framework_types = {}, {}, {}, {}
        self.config = [dict(id=i, **n) for i, n in self.nodes.items() if n['kind'] == 'config_entry']
        self.schemas = {}
        self.active_profiles = {'default'}
        for item in self.config:
            if item['key'].endswith('profiles.active'):
                self.active_profiles = set(re.split(r'[,\s]+', str(item['value'])))
            if item['key'].endswith('datasource.url'):
                match = re.search(r'jdbc:[^:]+://[^/]+/([^?;]+)', str(item['value']))
                if match:
                    self.schemas[item['module']] = match[1]
        for tid, meta in self.nodes.items():
            if meta['kind'] != 'type':
                continue
            tree = self.trees.get(meta.get('file'))
            if not tree:
                continue
            declarations = [n for n in walk(tree.root_node)
                            if n.type in ('class_declaration', 'enum_declaration')
                            and text(n.child_by_field_name('name')) == meta['fqn'].split('.')[-1]]
            if not declarations:
                continue
            decl = declarations[0]
            header = text(decl).split('{', 1)[0]
            self.framework_types[tid] = set(re.findall(r'\b(?:implements|extends)\s+([\w.]+)', header))
            if decl.type == 'enum_declaration':
                members = []
                for n in walk(decl):
                    if n.type != 'enum_constant':
                        continue
                    key = self.enum_prefixes[tid] + '.' + text(n.child_by_field_name('name'))
                    self.enum_objects.setdefault(key, {'__enum__': key, '__enum_type__': tid, 'name': key.rsplit('.', 1)[-1]})
                    members.append(key)
                self.enum_members[tid] = members
            fields = {}
            body = decl.child_by_field_name('body')
            for field in body.named_children if body else []:
                if field.type != 'field_declaration' or re.search(r'\bstatic\b', text(field)):
                    continue
                raw = text(field)
                column = re.search(r'@Column\([^)]*\bname\s*=\s*"([^"]+)"', raw)
                for var in field.named_children:
                    if var.type != 'variable_declarator':
                        continue
                    name = text(var.child_by_field_name('name'))
                    value = var.child_by_field_name('value')
                    default = U
                    if value:
                        try:
                            default = json.loads(text(value))
                        except ValueError:
                            pass
                    fields[name] = {'type': text(field.child_by_field_name('type')),
                                    'default': default, 'has_initializer': value is not None,
                                    'column': column[1] if column else name,
                                    'embedded': bool(re.search(r'@Embedded(?:Id)?\b', raw)),
                                    'id': bool(re.search(r'@(?:Id|EmbeddedId)\b', raw)),
                                    'generated':bool(re.search(r'@GeneratedValue\b',raw)),
                                    'qualifier': (re.search(r'@Qualifier\(\s*"([^"]+)"', raw)[1]
                                                  if re.search(r'@Qualifier\(\s*"([^"]+)"', raw) else None),
                                    'enum_string': 'EnumType.STRING' in raw,
                                    'file': meta['file'], 'line': field.start_point.row + 1}
            self.type_fields[tid] = fields
        self.type_parents={tid:sorted({parent for name in names
                                      if (parent:=self.resolve_type(name,self.nodes[tid]['module'],self.nodes[tid]['file']))})
                           for tid,names in self.framework_types.items()}
        declared_fields=dict(self.type_fields)
        def inherited_fields(tid,seen):
            if tid in seen:return {}
            fields={}
            for parent in self.type_parents.get(tid,[]):
                fields.update(inherited_fields(parent,seen|{tid}))
            return {**fields,**declared_fields.get(tid,{})}
        self.type_fields={tid:inherited_fields(tid,set()) for tid in declared_fields}
        for rid, tid in self.entities.items():
            fields=self.type_fields.get(tid,{})
            self.id_fields[rid] = [name for name,field in fields.items() if field['id']]
            generated=[name for name,field in fields.items() if field['id'] and field['generated']]
            if len(generated)==1:self.generated_ids[rid]=generated[0]
            from .state import camel
            self.column_aliases.setdefault(rid,{}).update({camel(field['column']):name for name,field in fields.items()})

    def enum_reference(self, expression, mid):
        if '.' not in expression or mid not in self.methods:
            return None
        owner, member = expression.rsplit('.', 1)
        meta = self.methods[mid]
        tid = self.resolve_type(owner, meta['module'], meta['file'])
        if tid not in self.enum_members:
            return None
        key = self.enum_prefixes[tid] + '.' + member
        return key if key in self.enum_members[tid] else None

    def resolve_type(self, name, module, file=None):
        namespace=self.__dict__.get('_source_namespaces',{}).get(file)
        key=(name,module,file,(namespace[0],tuple(namespace[1])) if namespace else None)
        cache=self.__dict__.setdefault('_resolved_type_cache',{})
        if key not in cache:cache[key]=self._resolve_type(name,module,file)
        return cache[key]

    def _resolve_type(self,name,module,file):
        written = name.split('<')[0].replace('[]', '').strip()
        name = written.split('.')[-1]
        candidates = [tid for tid, node in self.nodes.items() if node['kind'] == 'type'
                      and node['fqn'].split('.')[-1] == name]
        exact = [tid for tid in candidates if self.nodes[tid]['fqn'] == written]
        if '.' in written:
            local = [tid for tid in exact if self.nodes[tid].get('module') == module]
            return local[0] if len(local) == 1 else exact[0] if len(exact) == 1 else None
        if file and candidates:
            cache = self.__dict__.setdefault('_source_namespaces', {})
            if file not in cache:
                root = self.trees[file].root_node
                package_node = next((n for n in root.named_children if n.type == 'package_declaration'), None)
                package = re.search(r'\bpackage\s+([\w.]+)\s*;', text(package_node))
                imports = [match[1] for node in root.named_children if node.type == 'import_declaration'
                           for match in [re.search(r'\bimport\s+(?!static\b)([\w.*]+)\s*;', text(node))] if match]
                cache[file] = (package[1] if package else '', imports)
            package, imports = cache[file]
            imported = [tid for tid in candidates if self.nodes[tid]['fqn'] in imports]
            if imported:
                return imported[0] if len(imported) == 1 else None
            if any(not imported.endswith('.*') and imported.rsplit('.', 1)[-1] == name for imported in imports):
                return None
            same_package = [tid for tid in candidates if self.nodes[tid]['fqn'] == (package + '.' if package else '') + name]
            if same_package:
                return same_package[0] if len(same_package) == 1 else None
            wildcard = [tid for tid in candidates if self.nodes[tid]['fqn'].rsplit('.', 1)[0] + '.*' in imports]
            if wildcard:
                return wildcard[0] if len(wildcard) == 1 else None
        same = [tid for tid in candidates if self.nodes[tid].get('module') == module]
        return same[0] if len(same) == 1 else candidates[0] if len(candidates) == 1 else None

    def request_fields(self, mid):
        fields = {}
        for name, typ in self.parameters(mid):
            tid = self.resolve_type(typ, self.methods[mid]['module'])
            nested = self.type_fields.get(tid, {})
            if nested:
                fields.update({key: value['type'] for key, value in nested.items()})
            else:
                fields[name] = typ
        return fields

    def http_parameters(self, mid):
        """Declared HTTP envelopes and aliases; ordinary Java names are preserved."""
        node = self.ast.get(mid)
        pars = node.child_by_field_name('parameters') if node else None
        result = []
        for par in pars.named_children if pars else []:
            if par.type != 'formal_parameter':
                continue
            name = text(par.child_by_field_name('name'))
            typ = text(par.child_by_field_name('type'))
            annotation = re.search(r'@(RequestBody|PathVariable|RequestParam|RequestHeader)\b(?:\(([^)]*)\))?', text(par))
            kind, options = (annotation[1], annotation[2] or '') if annotation else ('', '')
            alias = re.search(r'^\s*"([^"]+)"|\b(?:value|name)\s*=\s*"([^"]+)"', options)
            default = re.search(r'\bdefaultValue\s*=\s*"([^"]*)"', options)
            result.append({'name': name, 'type': typ, 'kind': kind,
                           'wire_name': next((v for v in alias.groups() if v is not None), name) if alias else name,
                           'required': not bool(re.search(r'\brequired\s*=\s*false\b', options)) and default is None,
                           'default': default[1] if default else U})
        return result

    def request_body_defaults(self, mid):
        """Java field defaults for known omitted JSON properties, not unknown inputs."""
        result = {}
        for parameter in self.http_parameters(mid):
            if parameter['kind'] != 'RequestBody':
                continue
            tid = self.resolve_type(parameter['type'], self.methods[mid]['module'], self.methods[mid]['file'])
            if not tid:
                continue
            if any(a['name'].split('.')[-1] == 'JsonDeserialize' for a in self.nodes[tid].get('annotations', [])):
                continue
            # Straight assignments preserve independent literal fields. An
            # opaque RHS stays unknown; access to this may invalidate siblings.
            constructors = [m for m, meta in self.methods.items() if meta['owner'] == tid and meta['name'] == '<init>']
            if any('JsonCreator' in text(self.ast.get(m)) for m in constructors):
                continue
            noarg = [self.ast.get(m) for m in constructors if not self.parameters(m)]
            assigned, supported = {}, True
            for constructor in noarg:
                body = constructor.child_by_field_name('body') if constructor else None
                for statement in body.named_children if body else []:
                    if statement.type in ('line_comment', 'block_comment'):
                        continue
                    expression = statement.named_children[0] if statement.type == 'expression_statement' and statement.named_children else None
                    if expression is None or expression.type != 'assignment_expression' or text(expression.child_by_field_name('operator')) != '=':
                        supported = False
                        break
                    key = text(expression.child_by_field_name('left')).removeprefix('this.')
                    try:
                        value = json.loads(text(expression.child_by_field_name('right')))
                    except ValueError:
                        rhs = expression.child_by_field_name('right')
                        declared = self.type_fields.get(tid, {})
                        if any(child.type in ('this', 'assignment_expression', 'update_expression')
                               or child.type == 'identifier' and text(child) in declared
                               or child.type == 'method_invocation' and child.child_by_field_name('object') is None for child in walk(rhs)):
                            supported = False
                            break
                        value = U
                    if key not in self.type_fields.get(tid, {}):
                        supported = False
                        break
                    assigned[key] = value
            if not supported:
                continue
            for key, field in self.type_fields.get(tid, {}).items():
                typ = field['type']
                value = (field['default'] if field['has_initializer'] else False if typ == 'boolean'
                         else 0 if typ in ('byte', 'short', 'int', 'long', 'float', 'double')
                         else U if typ == 'char' else None)
                result[key] = assigned.get(key, value)
        return result

    def materialize(self, database, rid, row):
        resource = self.nodes[rid]
        keys = self.id_fields.get(rid, [])
        record = database.materialize(resource, row, self.column_aliases.get(rid), self.collections.get(rid), keys[0] if len(keys) == 1 else None)
        tid = self.entities.get(rid)

        def fill(owner, obj, values=None):
            facts=record if values is None else values
            for name, field in self.type_fields.get(owner, {}).items():
                target = self.resolve_type(field['type'], self.nodes[owner].get('module'), field['file'])
                if field['embedded'] and target:
                    if name in facts:
                        nested=facts[name]
                        obj[name]=fill(target,dict(nested),nested) if isinstance(nested,dict) else nested if nested is None else U
                    else:obj[name] = fill(target, {'__type__': self.nodes[target]['fqn']},facts)
                    continue
                key = re.sub(r'_([a-z])', lambda m: m[1].upper(), field['column'])
                val = facts.get(name, facts.get(key,U))
                if field['type'].split('.')[-1] == 'Date' and target is None and val is not None:
                    val = date_value(val)
                if isinstance(val, list) and re.search(r'(?:List|Set|Collection)<(?:String|Integer|Long|Double)>', field['type']):
                    val = [v.get(key, U) if isinstance(v, dict) else v for v in val]
                elif isinstance(val, list):
                    element = re.fullmatch(r'(?:List|Set|Collection)<([\w.]+)>', field['type'])
                    target = self.resolve_type(element[1], self.nodes[owner].get('module'), field['file']) if element else None
                    if target in self.type_fields:
                        val = [{'__type__': self.nodes[target]['fqn'], **item} if isinstance(item, dict) and '__type__' not in item else item for item in val]
                if target in self.enum_members and val is not U:
                    members = self.enum_members[target]
                    match=(val['__enum__'] if isinstance(val,dict) and val.get('__enum__') in members else
                           next((x for x in members if x.rsplit('.', 1)[-1] == val),None) if isinstance(val,str) else
                           members[val] if type(val) is int and 0<=val<len(members) else None)
                    val = dict(self.enum_objects[match]) if match else U
                obj[name] = val
            return obj

        return fill(tid, record) if tid else record

    def parameters(self, mid):
        cache = self.__dict__.setdefault('_parameter_cache', {})
        if mid in cache:
            return list(cache[mid])
        node = self.ast.get(mid)
        pars = node.child_by_field_name('parameters') if node else None
        result = []
        for p in pars.named_children if pars else []:
            if p.type != 'formal_parameter':
                continue
            typ = text(p.child_by_field_name('type'))
            tid = self.resolve_type(typ, self.methods[mid]['module'], self.methods[mid]['file'])
            if tid and '<' not in typ and '[' not in typ:
                typ = self.nodes[tid]['fqn']
            result.append((text(p.child_by_field_name('name')), typ))
        cache[mid] = tuple(result)
        return result

    def site(self, mid, node):
        name_node = node.child_by_field_name('name')
        name = '<init>' if node.type == 'object_creation_expression' else text(name_node)
        row = (name_node or node).start_point.row + 1
        candidates = self.by_line.get((mid, row, name), [])
        if not candidates and node.type == 'object_creation_expression':
            candidates = self.by_line.get((mid, node.start_point.row + 1, name), [])
        return min(candidates, key=lambda k: abs(self.nodes[k]['col'] - (name_node or node).start_point.column - 1)) if candidates else None

    def targets(self, mid, site):
        key=(mid,site,frozenset(self.active_profiles))
        cache=self.__dict__.setdefault('_target_cache',{})
        if key not in cache:cache[key]=tuple(self._targets(mid,site))
        return list(cache[key])

    def _targets(self,mid,site):
        if not site:
            return []
        edges = self.edges[site]
        targets = edges.get('runtime_dispatch') or edges.get('calls', set())
        out = set()
        for target in targets:
            if target not in self.methods:
                continue
            if not self.methods[target].get('abstract'):
                out.add(target)
            else:
                out.update(m for m in self.ix.cha(target) if not self.methods[m].get('abstract'))
        if not out:
            cs = self.nodes[site]
            owner = cs.get('receiver_type')
            for candidate in self.by_name.get(cs['callee'], []):
                meta = self.methods[candidate]
                enum_owner = (cs.get('receiver') or '').split('.')[0]
                fqn = self.nodes[meta['owner']]['fqn']
                owner_matches = fqn == owner or (not owner and fqn.split('.')[-1] == enum_owner and any(k.startswith(enum_owner + '.') for k in self.enums))
                if (not meta.get('abstract') and owner_matches
                        and len(meta.get('params_as_written', [])) == cs['arg_count']):
                    out.add(candidate)
        unit = self.ix.unit_of(mid)
        receiver = self.nodes[site].get('receiver', '')
        field = self.type_fields.get(self.methods[mid]['owner'], {}).get(receiver, {})
        qualifier = field.get('qualifier')
        if qualifier:
            selected = set()
            for m in out:
                owner = self.nodes[self.methods[m]['owner']]
                simple = owner['fqn'].split('.')[-1]
                bean_names = {simple[:1].lower() + simple[1:]}
                for annotation in owner.get('annotations', []):
                    if annotation['name'].split('.')[-1] in ('Service', 'Component', 'Repository', 'Qualifier'):
                        bean_names.update(re.findall(r'"([^"]+)"', annotation.get('args', '')))
                if qualifier in bean_names:
                    selected.add(m)
            out = selected
        return sorted(m for m in out if unit in self.ix.units.get(self.methods[m]['module'], ())
                      and self.enabled_type(self.methods[m]['owner']))

    def methods_of(self, owner, name):
        return [mid for mid in self.by_name.get(name, []) if self.methods[mid]['owner'] == owner and not self.methods[mid].get('abstract')]

    def inherited_methods(self,owner,name,count):
        """Resolve explicit source accessors through the nearest declaring class."""
        pending,seen=[owner],set()
        while pending:
            found=[mid for mid in self.by_name.get(name,[]) if self.methods[mid]['owner'] in pending
                   and len(self.methods[mid].get('params_as_written',[]))==count]
            if found:return found
            seen.update(pending)
            pending=sorted({parent for tid in pending for parent in self.type_parents.get(tid,[]) if parent not in seen})
        return []

    def profile_status(self,owner):
        annotations = self.nodes[owner].get('annotations', [])
        profiles = [a for a in annotations if a['name'].split('.')[-1] == 'Profile']
        if not profiles:
            return True
        values = re.findall(r'"([^"]+)"', profiles[0].get('args', ''))
        if not values or any(re.search(r'[&|()!]',value.lstrip('!')) for value in values):return U
        return any((value[1:] not in self.active_profiles) if value.startswith('!') else value in self.active_profiles
                   for value in values)

    def enabled_type(self,owner):
        return self.profile_status(owner) is not False

    def source_targets(self, mid, node):
        """Resolve simple source calls even when a call-site edge is absent."""
        key=(mid,node.start_byte,node.end_byte,node.type,frozenset(self.active_profiles))
        cache=self.__dict__.setdefault('_source_target_cache',{})
        if key not in cache:cache[key]=tuple(self._source_targets(mid,node))
        return list(cache[key])

    def _source_targets(self,mid,node):
        owner = self.methods[mid]['owner']
        module = self.methods[mid]['module']
        if node.type == 'object_creation_expression':
            target_type = self.resolve_type(text(node.child_by_field_name('type')), module, self.methods[mid]['file'])
            name = '<init>'
        else:
            name = text(node.child_by_field_name('name'))
            receiver = text(node.child_by_field_name('object'))
            if not receiver or receiver == 'this':
                target_type = owner
            else:
                info = self.type_fields.get(owner, {}).get(receiver.removeprefix('this.'))
                target_type = self.resolve_type(info['type'] if info else receiver, module, self.methods[mid]['file'])
        if not target_type:
            return []
        args = node.child_by_field_name('arguments')
        count = len([a for a in args.named_children if a.type not in ('line_comment', 'block_comment')]) if args else 0
        result = []
        for target in self.by_name.get(name, []):
            meta = self.methods[target]
            if meta['owner'] == target_type and len(meta.get('params_as_written', [])) == count:
                result.extend(self.ix.cha(target) if meta.get('abstract') else [target])
        unit = self.ix.unit_of(mid)
        return sorted(m for m in set(result) if not self.methods[m].get('abstract')
                      and unit in self.ix.units.get(self.methods[m]['module'], ())
                      and self.enabled_type(self.methods[m]['owner']))
