"""Construct skeleton fixtures by parsing Java; never compile or execute them."""
import json
import re
from pathlib import Path
from tree_sitter import Language, Parser
import tree_sitter_java
from analyzer.project import Project, text, walk, body_members
from analyzer.state import Database


def annotations(node):
    mods = next((c for c in node.named_children if c.type == 'modifiers'), None)
    return [{'name': text(a.child_by_field_name('name')), 'args': text(a.child_by_field_name('arguments'))}
            for a in mods.named_children if a.type in ('annotation', 'marker_annotation')] if mods else []


def build(root, sources, module='service', rows=None, context=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    parser = Parser(Language(tree_sitter_java.language()))
    nodes = {'module:' + module: {'kind': 'module', 'name': module, 'deployment_units': [module]}}
    declarations, type_ids, trees = {}, {}, {}
    for file, source in sources.items():
        path = root / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
        tree = parser.parse(source.encode())
        assert not tree.root_node.has_error
        trees[file] = tree
        for decl in walk(tree.root_node):
            if decl.type not in ('class_declaration', 'interface_declaration', 'enum_declaration','record_declaration'):
                continue
            name = text(decl.child_by_field_name('name'))
            tid = 'type:' + module + ':' + name
            type_ids[name] = tid
            nodes[tid] = dict(kind='type', fqn=name, module=module, file=file, annotations=annotations(decl))
            declarations[name] = decl
    ids, methods = {}, []
    for name, decl in declarations.items():
        body = decl.child_by_field_name('body')
        for node in body_members(body):
            if node.type not in ('method_declaration', 'constructor_declaration'):
                continue
            method_name = '<init>' if node.type == 'constructor_declaration' else text(node.child_by_field_name('name'))
            parameters = node.child_by_field_name('parameters')
            pars = [text(p.child_by_field_name('type')) for p in parameters.named_children if p.type == 'formal_parameter']
            mid = f'method:{module}:{name}#{method_name}({",".join(pars)})'
            ids[name + '.' + method_name] = mid
            file = nodes[type_ids[name]]['file']
            nodes[mid] = dict(kind='method', name=method_name, owner=type_ids[name], module=module,
                              file=file, line=node.start_point.row + 1, end=node.end_point.row + 1,
                              params_as_written=pars, abstract=node.child_by_field_name('body') is None,
                              annotations=annotations(node), return_raw=text(node.child_by_field_name('type')))
            methods.append((mid, name, node))
    resources = {}
    for name, decl in declarations.items():
        table = re.search(r'@Table\(name\s*=\s*"([^"]+)"', text(decl))
        if table:
            rid = 'res:table:' + module + '.' + table[1]
            resources[name] = rid
            nodes[rid] = dict(kind='data_resource', resource_kind='table', schema=module,
                              name=table[1], origin=[{'file': nodes[type_ids[name]]['file']}])
    edges = []
    for name, declaration in declarations.items():
        parent = re.search(r'implements\s+(\w+)', text(declaration).split('{', 1)[0])
        if parent and parent[1] in type_ids:
            edges.append({'source': type_ids[name], 'type': 'implements', 'target': type_ids[parent[1]]})
            for key, interface_mid in ids.items():
                if key.startswith(parent[1] + '.'):
                    implementation = ids.get(name + '.' + key.split('.', 1)[1])
                    if implementation:
                        edges.append({'source': implementation, 'type': 'overrides', 'target': interface_mid})
    for mid, owner, method in methods:
        variable_types = {}
        for node in walk(declarations[owner]):
            if node.type in ('field_declaration', 'local_variable_declaration'):
                typ = text(node.child_by_field_name('type'))
                for var in node.named_children:
                    if var.type == 'variable_declarator':
                        variable_types[text(var.child_by_field_name('name'))] = typ
        parameters = method.child_by_field_name('parameters')
        for par in parameters.named_children:
            if par.type == 'formal_parameter':
                variable_types[text(par.child_by_field_name('name'))] = text(par.child_by_field_name('type'))
        for call in walk(method):
            if call.type not in ('method_invocation', 'object_creation_expression'):
                continue
            is_new = call.type == 'object_creation_expression'
            name_node = call.child_by_field_name('name')
            name = '<init>' if is_new else text(name_node)
            receiver = text(call.child_by_field_name('object'))
            typ = text(call.child_by_field_name('type')) if is_new else variable_types.get(receiver.removeprefix('this.'), receiver or owner)
            row, col = (name_node or call).start_point.row + 1, (name_node or call).start_point.column + 1
            cid = f'call:{mid}@{row}:{col}'
            arguments = call.child_by_field_name('arguments')
            count = len(arguments.named_children) if arguments else 0
            nodes[cid] = dict(kind='call_site', method=mid, callee=name, receiver=receiver,
                              receiver_type=typ, line=row, col=col, arg_count=count,
                              file=nodes[mid]['file'])
            target = ids.get(typ + '.' + name)
            if target:
                edges.append({'source': cid, 'type': 'calls', 'target': target})
            declaration = declarations.get(typ)
            repository = re.search(r'extends\s+JpaRepository<\s*(\w+)', text(declaration)) if declaration else None
            if repository and repository[1] in resources:
                edges.append({'source': cid, 'type': 'data_access', 'target': resources[repository[1]]})
    skeleton = root / 'skeleton.json'
    skeleton.write_text(json.dumps({'project': 'fixture', 'nodes': nodes, 'edges': edges, 'context': context or {}}))
    dump = root / 'initial.sql'
    statements = ['USE `' + module + '`;']
    for table, records in (rows or {}).items():
        columns = list(records[0]) if records else ['key']
        statements.append('CREATE TABLE `' + table + '` (\n' + ',\n'.join(' `' + k + '` varchar(80)' for k in columns) + '\n) ENGINE=InnoDB;')
        if records:
            vals = [','.join('NULL' if r[k] is None else str(r[k]) if isinstance(r[k], (int, float)) else "'" + str(r[k]) + "'" for k in columns) for r in records]
            statements.append('INSERT INTO `' + table + '` VALUES ' + ','.join('(' + v + ')' for v in vals) + ';')
    dump.write_text('\n'.join(statements) + '\n')
    return Project(skeleton, root), Database(dump), ids


INVENTORY = {
    'StockController.java': '''import org.springframework.web.bind.annotation.*;
    import org.springframework.beans.factory.annotation.Autowired;
    @RestController class StockController {
      @Autowired StockWorker worker;
      @PostMapping("/reserve") Reservation reserve(@RequestBody StockRequest input) {
        if (input.enabled) { return worker.accept(input.key); }
        return worker.reject(input.key);
      }
      @GetMapping("/inventory") String inspect(String key) { return worker.status(key); }
      @PostMapping("/release") Reservation release(@RequestBody StockRequest input) { return worker.reject(input.key); }
    }''',
    'StockWorker.java': '''import org.springframework.stereotype.Service;
    import org.springframework.beans.factory.annotation.Autowired;
    @Service class StockWorker {
      @Autowired ReservationStore repository;
      Reservation accept(String key) { Reservation item = new Reservation(key); repository.save(item); return item; }
      Reservation reject(String key) { return null; }
      String status(String key) { return "ready"; }
    }''',
    'StockRequest.java': 'class StockRequest { public String key; public boolean enabled; }',
    'Reservation.java': 'import jakarta.persistence.*; @Entity @Table(name="reservations") class Reservation { @Id public String key; protected Reservation() {} Reservation(String key) { this.key = key; } }',
    'ReservationStore.java': 'import org.springframework.data.jpa.repository.JpaRepository; interface ReservationStore extends JpaRepository<Reservation, String> { Reservation save(Reservation item); }',
}

LIBRARY = {
    'BookController.java': '''import org.springframework.web.bind.annotation.*;
    import org.springframework.beans.factory.annotation.Autowired;
    @RestController class BookController {
      @Autowired BookStore repository;
      @GetMapping("/books/{key}") String lookup(@PathVariable String key) {
        Book found = repository.findByKey(key);
        if (found == null) { return missing(); }
        return available(found);
      }
      String missing() { return "absent"; }
      String available(Book found) { return found.title; }
      @GetMapping("/catalog") String search(String query) { return "matches"; }
      @PostMapping("/books") Book add(@RequestBody Book input) { repository.save(input); return input; }
    }''',
    'Book.java': 'import jakarta.persistence.*; @Entity @Table(name="books") class Book { @Id public String key; public String title; }',
    'BookStore.java': 'import org.springframework.data.jpa.repository.JpaRepository; interface BookStore extends JpaRepository<Book, String> { Book findByKey(String key); Book save(Book input); }',
}
