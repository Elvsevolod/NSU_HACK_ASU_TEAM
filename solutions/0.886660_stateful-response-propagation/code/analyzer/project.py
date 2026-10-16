"""Source and skeleton indexes. No application code is executed."""
from collections import defaultdict
from pathlib import Path
import re
import json

from tree_sitter import Language, Parser
import tree_sitter_java
from baseline_closure import Index, load_json


def text(node):
    return node.text.decode('utf-8') if node is not None else ''


def walk(node):
    yield node
    for child in node.named_children:
        yield from walk(child)


class Project:
    def __init__(self, skeleton, root):
        self.skeleton = load_json(str(skeleton))
        self.ix = Index(self.skeleton)
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
        for file, tree in self.trees.items():
            declarations[file] = [n for n in walk(tree.root_node) if n.type in ('method_declaration', 'constructor_declaration')]
            for node in walk(tree.root_node):
                if node.type == 'enum_declaration':
                    name = text(node.child_by_field_name('name'))
                    for const in walk(node):
                        if const.type == 'enum_constant':
                            args = const.child_by_field_name('arguments')
                            if args and args.named_children:
                                raw = text(args.named_children[0])
                                enum_key = name + '.' + text(const.child_by_field_name('name'))
                                if raw.startswith('"'):
                                    self.enum_objects[enum_key] = {'__enum__': enum_key, 'name': json.loads(raw)}
                                if re.fullmatch(r'-?\d+', raw):
                                    self.enums[enum_key] = int(raw)
                                    self.enum_objects[enum_key] = {'__enum__': enum_key, 'code': int(raw)}
                                    if len(args.named_children) > 1 and text(args.named_children[1]).startswith('"'):
                                        self.enum_objects[enum_key]['name'] = json.loads(text(args.named_children[1]))
        for mid, method in self.methods.items():
            name = method['name'] if method['name'] != '<init>' else self.nodes[method['owner']]['fqn'].split('.')[-1]
            matches = [n for n in declarations[method['file']]
                       if text(n.child_by_field_name('name')) == name
                       and n.start_point.row + 1 <= method['line'] <= n.end_point.row + 1]
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
            query = re.search(r'@Query\([^\n]*?value\s*=\s*"([^"]+)"', text(node))
            if query:
                owner = self.nodes[self.methods[mid]['owner']]['fqn']
                predicates = re.findall(r'(\w+)\s*(=|\bin\b)\s*\?(\d+)', query[1], re.I)
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

    def parameters(self, mid):
        node = self.ast.get(mid)
        pars = node.child_by_field_name('parameters') if node else None
        return [(text(p.child_by_field_name('name')), text(p.child_by_field_name('type')))
                for p in pars.named_children if p.type == 'formal_parameter'] if pars else []

    def site(self, mid, node):
        name_node = node.child_by_field_name('name')
        name = '<init>' if node.type == 'object_creation_expression' else text(name_node)
        row = (name_node or node).start_point.row + 1
        candidates = self.by_line.get((mid, row, name), [])
        if not candidates and node.type == 'object_creation_expression':
            candidates = self.by_line.get((mid, node.start_point.row + 1, name), [])
        return min(candidates, key=lambda k: abs(self.nodes[k]['col'] - (name_node or node).start_point.column - 1)) if candidates else None

    def targets(self, mid, site):
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
        return sorted(m for m in out if unit in self.ix.units.get(self.methods[m]['module'], ()))

    def methods_of(self, owner, name):
        return [mid for mid in self.by_name.get(name, []) if self.methods[mid]['owner'] == owner and not self.methods[mid].get('abstract')]
